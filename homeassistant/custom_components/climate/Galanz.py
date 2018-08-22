"""
Galanz空调
"""
from datetime import timedelta
from base64 import b64encode, b64decode
import asyncio
import binascii
import logging
import socket

import voluptuous as vol

from homeassistant.core import callback
from homeassistant.components.climate import (
    ATTR_TARGET_TEMP_HIGH, ATTR_TARGET_TEMP_LOW, DOMAIN,
    ClimateDevice, PLATFORM_SCHEMA, STATE_AUTO,
    STATE_COOL, STATE_HEAT, SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_TARGET_TEMPERATURE_HIGH, SUPPORT_TARGET_TEMPERATURE_LOW,
    SUPPORT_OPERATION_MODE)
from homeassistant.const import (
    TEMP_CELSIUS, TEMP_FAHRENHEIT, ATTR_TEMPERATURE, ATTR_UNIT_OF_MEASUREMENT,
    CONF_NAME, CONF_HOST, CONF_MAC, CONF_TIMEOUT)
from homeassistant.helpers import condition
from homeassistant.helpers.event import (
    async_track_state_change, async_track_time_interval)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['sensor']

DEFAULT_TOLERANCE = 0.3
DEFAULT_NAME = 'Galanz Thermostat'

DEFAULT_TIMEOUT = 10
DEFAULT_RETRY = 3

DEFAULT_MIN_TMEP = 16
DEFAULT_MAX_TMEP = 31
DEFAULT_STEP = 1

CONF_SENSOR = 'target_sensor'
CONF_TARGET_TEMP = 'target_temp'
devtype = 0x2712

SUPPORT_FLAGS = (SUPPORT_TARGET_TEMPERATURE | SUPPORT_OPERATION_MODE)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_MAC): cv.string,
    vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
    vol.Required(CONF_SENSOR): cv.entity_id,
    vol.Optional(CONF_TARGET_TEMP): vol.Coerce(float)
})

@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    """Set up the generic thermostat platform."""
    import broadlink
    ip_addr = config.get(CONF_HOST)
    mac_addr = binascii.unhexlify(
        config.get(CONF_MAC).encode().replace(b':', b''))

    name = config.get(CONF_NAME)
    sensor_entity_id = config.get(CONF_SENSOR)
    target_temp = config.get(CONF_TARGET_TEMP)

    broadlink_device = broadlink.rm((ip_addr, 80), mac_addr, devtype)
    broadlink_device.timeout = config.get(CONF_TIMEOUT)
    try:
        broadlink_device.auth()
    except socket.timeout:
        _LOGGER.error("Failed to connect to device")

    async_add_devices([DemoClimate(
            hass, name, target_temp, None, None, None, None, None,
            None, 'off', None, DEFAULT_MAX_TMEP, DEFAULT_MIN_TMEP, 
            broadlink_device, sensor_entity_id)])


class DemoClimate(ClimateDevice):
    """Representation of a demo climate device."""

    def __init__(self, hass, name, target_temperature, target_humidity,
                away, hold, current_fan_mode, current_humidity,
                current_swing_mode, current_operation, aux,
                target_temp_high, target_temp_low,
                broadlink_device, sensor_entity_id):
                 
        """Initialize the climate device."""
        self.hass = hass
        self._name = name if name else DEFAULT_NAME
        self._target_temperature = target_temperature
        self._target_humidity = target_humidity
        self._away = away
        self._hold = hold
        self._current_humidity = current_humidity
        self._current_fan_mode = current_fan_mode
        self._current_operation = current_operation
        self._aux = aux
        self._current_swing_mode = current_swing_mode
        self._fan_list = ['On Low', 'On High', 'Auto Low', 'Auto High', 'Off']
        self._operation_list = ['heat', 'cool', 'auto', 'off']
        self._swing_list = ['Auto', '1', '2', '3', 'Off']
        self._target_temperature_high = target_temp_high
        self._target_temperature_low = target_temp_low
        self._max_temp = target_temp_high + 1
        self._min_temp = target_temp_low - 1
        self._target_temp_step = DEFAULT_STEP

        self._unit_of_measurement = TEMP_CELSIUS
        self._current_temperature = None

        self._device = broadlink_device

        async_track_state_change(
            hass, sensor_entity_id, self._async_sensor_changed)
        
        sensor_state = hass.states.get(sensor_entity_id)
        if sensor_state:
            self._async_update_temp(sensor_state)

    @callback
    def _async_update_temp(self, state):
        """Update thermostat with latest state from sensor."""
        unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)

        try:
            self._current_temperature = self.hass.config.units.temperature(
                float(state.state), unit)
        except ValueError as ex:
            _LOGGER.error('Unable to update from sensor: %s', ex)

    @asyncio.coroutine
    def _async_sensor_changed(self, entity_id, old_state, new_state):
        """Handle temperature changes."""
        if new_state is None:
            return

        self._async_update_temp(new_state)
        yield from self.async_update_ha_state()

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return self._min_temp

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return self._max_temp
    
    @property
    def target_temperature_step(self):
        return self._target_temp_step
    
    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def name(self):
        """Return the name of the climate device."""
        return self._name

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature


    @property
    def target_temperature_high(self):
        """Return the highbound target temperature we try to reach."""
        return self._target_temperature_high

    @property
    def target_temperature_low(self):
        """Return the lowbound target temperature we try to reach."""
        return self._target_temperature_low

    @property
    def current_humidity(self):
        """Return the current humidity."""
        return self._current_humidity

    @property
    def target_humidity(self):
        """Return the humidity we try to reach."""
        return self._target_humidity

    @property
    def current_operation(self):
        """Return current operation ie. heat, cool, idle."""
        return self._current_operation

    @property
    def operation_list(self):
        """Return the list of available operation modes."""
        return self._operation_list

    @property
    def is_away_mode_on(self):
        """Return if away mode is on."""
        return self._away

    @property
    def current_hold_mode(self):
        """Return hold mode setting."""
        return self._hold

    @property
    def is_aux_heat_on(self):
        """Return true if away mode is on."""
        return self._aux

    @property
    def current_fan_mode(self):
        """Return the fan setting."""
        return self._current_fan_mode

    @property
    def fan_list(self):
        """Return the list of available fan modes."""
        return self._fan_list

    def set_temperature(self, **kwargs):
        """Set new target temperatures."""
        if kwargs.get(ATTR_TEMPERATURE) is not None:
            self._target_temperature = kwargs.get(ATTR_TEMPERATURE)
        if kwargs.get(ATTR_TARGET_TEMP_HIGH) is not None and \
           kwargs.get(ATTR_TARGET_TEMP_LOW) is not None:
            self._target_temperature_high = kwargs.get(ATTR_TARGET_TEMP_HIGH)
            self._target_temperature_low = kwargs.get(ATTR_TARGET_TEMP_LOW)

        if self._target_temperature < self._target_temperature_low:
            self._current_operation = 'off'
            self._target_temperature = self._target_temperature_low
        elif self._target_temperature > self._target_temperature_high:
            self._current_operation = 'off'
            self._target_temperature = self._target_temperature_high
        elif self._current_temperature and (self._current_operation == "off" or self._current_operation == "idle"):
            self.set_operation_mode('auto')
            return
        
        self._sendpacket()
        self.schedule_update_ha_state()
        
        

    def set_humidity(self, humidity):
        """Set new target temperature."""
        self._target_humidity = humidity
        self.schedule_update_ha_state()

    def set_swing_mode(self, swing_mode):
        """Set new target temperature."""
        self._current_swing_mode = swing_mode
        self.schedule_update_ha_state()

    def set_fan_mode(self, fan):
        """Set new target temperature."""
        self._current_fan_mode = fan
        self.schedule_update_ha_state()

    def set_operation_mode(self, operation_mode):
        """Set new target temperature."""
        self._current_operation = operation_mode
        self._sendpacket()
        self.schedule_update_ha_state()

    @property
    def current_swing_mode(self):
        """Return the swing setting."""
        return self._current_swing_mode

    @property
    def swing_list(self):
        """List of available swing modes."""
        return self._swing_list

    def turn_away_mode_on(self):
        """Turn away mode on."""
        self._away = True
        self.schedule_update_ha_state()

    def turn_away_mode_off(self):
        """Turn away mode off."""
        self._away = False
        self.schedule_update_ha_state()

    def set_hold_mode(self, hold):
        """Update hold mode on."""
        self._hold = hold
        self.schedule_update_ha_state()

    def turn_aux_heat_on(self):
        """Turn away auxillary heater on."""
        self._aux = True
        self.schedule_update_ha_state()

    def turn_aux_heat_off(self):
        """Turn auxillary heater off."""
        self._aux = False
        self.schedule_update_ha_state()
    
    def _auth(self, retry=2):
        try:
            auth = self._device.auth()
        except socket.timeout:
            auth = False
        if not auth and retry > 0:
            return self._auth(retry-1)
        return auth    

    def _sendpacket(self,retry=2):
        """Send packet to device."""
        cool = ("JgDmAHY1DyQPJQ8PDw0QDQ4lDw8PDRAkDyUQDA8lDw4QDRAkDyQPDg8lDyUODxAMECQPDg4PECMSCw8ODw4QDQ8NDw8ODhAMDw8PDRANDw0RDQ8NDw4QDRANDyQPDw8NECQPDQ8PECMQJBANDw0PDw8NEA0ODxAkECMPJQ8lDw4PDQ8ODw4QJA8kECQQJBAkECQPDQ8OEA0PEA0OEAwPDg4PEA0PDQ8OEA0RCw8PDw0QDQ4PEA0PJBAkECQQJA8NDw8PDQ8NDw8PDRANDw4PJRAMEA0PDhEjEQwODg8lDw4QJBAMECQQAA0FAAA=",
"JgDmAHkzDyUOJQ8OEgsQDQ4lDw4RDBEjESMRCw8lDw4QDREjESMRCw8lDyUODhIMDyQRDA8NESMRDBEMDw4QDRELDw4RDBANDg4RDBEMDw0RDRELDw4QDRANDiUPDhANESMRDA4OESMQJBEMEQsPDhEMEA0PDRENECMRIxEjEQsPDhANEQwPJA8lDyUPJQ8lDyQPDhILEQwPDRENEQsPDhANEQwODhILEA0PDRENEQsPDhEMEAwPJQ8lDyUPJQ4OEgwQDA8OEA0RCw8lDw4QIxIMEQsPDhANEQwOJQ8lDw4QIxIMESIPAA0FAAA=",
"JgDmAHY2ESMRIxELDw4RDBEjEQsPDhEjESIQDg8kDw4PDREjESMRDBAkECQQDA8OEiIQDREMDiUPDhEMDw4ODhAOEAwPDhEMEQsPDhEMEQwODhAOEAwPDhEMESMQDA8ODyQSDA8NDyUPJQ8NEA4ODg8OEA0PDQ8lDw4RIxEiEgwPDQ8ODw4PJREjDyQPJQ8lESMPDQ8OEQwQDQ4OEgsRDA8NEA4PDQ8OEA0QDQ4OEA0RDA8NEA4PJBAkESMRIxELDw4SCw8ODg4RDRAjEQwPJQ4OEgsRDA8lDiUPDhAkDw4RIxELDyQRAA0FAAA=",
"JgDmAHY1ESMRIxELDw4RDA8lEA0ODhEjECQQDRAkDw0PDhAkECMRDRAjESMPDg8NECQRDBANDyUODhAODg4PDhANEAwPDhANEQwODhENDw0PDRENEQsPDhANESMRCw8OECQRDBANDiUPJQ8OEA0RCw8OEQwRDA8NEA4OJRAkEA0ODhENDw0PJQ8lDiUPJQ8lDyUPDRIMDg4PDhANDw0PDhANEA0ODhENDg4PDhEMDw0PDhANEA0OJQ8lDyUPJQ8NEgwPDQ8ODw4QDQ4lDw4PJRANEAwPDhILDyURDA4lDw4RIxANDyQPAA0FAAA=",
"JgDmAHc0EiIRIxEMDw4PDRAkEA0QDQ8lDiUPDhAkDw4QDQ4lDyUPDhAjESMRDQ8NDyUPDRAOESIRDA8NEQ0PDQ8OEQwPDg4OEQwQDQ8NEA4QDA8ODw4QDQ4OECQQDRANDiUPDhILECQQJBAMDw4PDhEMDg4QDhAjESMQDQ4lDw4RDBANDw0QJBAkECQPJBAkECQRDBANDw0SDBAMDw4QDRANDg4QDRANDw0RDQ4ODw4PDhELDw4QJBAkDyQQJBANEA0PDRENEAwPDg8lDw4RIxELDw4QDRAkEAwPDhAkEA0QJBELDyQRAA0FAAA=",
"JgDmAHY0DyUQJA8OEA0QDBAkEA0QDQ8lECQPDQ8lDw0QDhEiEiIRDA8lDiUQDREMECQQDQ4OESMQDRANDw0RDA8ODw4RDBAMEA0QDRANDw4QDA8ODw4QDRELECQQDRANECQPDQ8OECQQIxENEAwQDRANEQsPDhILDyUQDQ4lEA0QDRANDw0RIxEjECQQIxEjESMRDA8ODg4RDRELEA0QDRAMDw4RDBANDw0QDg8NDw4QDRAMEA0RIxAkECMRIxEMEA0PDRENEAwPDhAkEA0QJA8NDw4QDRAMEA0RDBAkEQwOJQ8OECQOAA0FAAA=",
"JgDmAHkzECQQJBEMEQwODhIiEQwRDA4lDyUPDg8lDw4RCw8lDyUPDg8kEiISCxEMDyUPDRIMECMRDA8NEgwQDA8ODw4PDg4OEQwRDA8NEgwQDA8OEQwRCw8OECQRDBEMDiUPDhEMESMRIxELDw4PDhEMDg4QDREjEA0ODhIiEQwRDA8NEgwPJBEjESISIxEjECMRDA8NEgwPDQ8ODw4RDA4OEQwRDA8NEA4PDQ8ODw4RDA4OEA0RIxEiEiMRIxAMDw4PDhELDw4PDhEjEQwOJQ8OEQwRDA4lDyUPJQ8NEA4RIw8NDyQSAA0FAAA=",
"JgDmAHY1DyQQJBANDw4PDREjEA4QDA8lDyUODhIiEQwRDA8lDiUPDhAkDyQQDhELDyUPDg8OECQQDA8OEQwRDA4OEA0PDg8NEA4QDA8OEQwRCw8OEA0PDg8NECQQDRANDyUODhIMDiUPJREMDg4QDREMDw0QDg8NDw4RDBEjEQsPDg8ODw4OJQ8lDyUPJQ8lDiUPDhANEA0PDRIMEAwPDg8OEQsPDhANDw4PDRIMEAwPDhEMEQsPJQ8lDyUPJA8OEA0PDg8ODw4QDA8lDw4PJBIMEAwPDg8ODyURIhEMDw4PJBAODiUOAA0FAAA=",
"JgDmAHozDyUPJQ8NEA4RCw8lDw4QDREjESIRDA8lDw0SDBAjEiIRDA4lDyUPDhEMESMRCw8OESMRDBELDw4RDBEMDw0SDBAMDw4RDBELDw4SCxEMDw0SDBAMDyUPDRIMECMRDA8OESISIhILEQwPDRIMEQsPDg8lESISIhILEQwPDRENEQsPJQ8lDyUOJQ8lDyUPDhEMEQsPDhEMEQwODhIMEAwPDhEMEQsPDhEMEQwODhILEQwPJQ8kDyUPJQ8OEQwRCw8OEgsRDA8lDg4SIhILEQwODhEjEQwRIxEMDg4SIhILESIPAA0FAAA=",
"JgDmAHc0DyUPJQ8NEA4QDA8lDw4RDBEjESIRDA8lDw0SDA8kDyUQDQ4lDyUPDhEMESMRCw8OESMRDBEMDg4QDQ8ODw0SDBELDw4PDg8NDw4QDQ8ODw0SDBAMDyUPDRIMDyQPDg8ODyQRIxILEQwPDRIMEQsPDg8ODyURIw8NDw4QDRELDw4SIhEjESISIhIiEiIRDBEMDg4QDQ8ODw0SDBAMDw4PDhEMDg4QDQ8ODw0RDQ8NDw4RIw8kEiISIhEMEQwODhIMEAwPDg8kEQ0QIxEMDw0SDA8NDw4RIxEMDw0PJQ8OECMRAA0FAAA=",
"JgDmAHU2ECQRIxEMDg4QDRAkEA0ODhAkECQPDhAkEQsPDg8lESIQDhEjECMPDg8NECQQDQ8ODyUODhAODw0PDg8ODw0PDg8ODw4ODhAODw0PDg8OEAwPDhANECQQDA8OECQPDhANDiUPJQ8OEA0RDA4OEA0RDA8lDg4QJBANEA0PDRAODw0PJQ8lDiUPJQ8lDyUPDRAOEAwPDg8ODw0PDg8OERARDA8ODw0RDQ8NDw4PDhEMDg4QJBAkECMQJBIMDg4PDg8OEAwPDg8lDw4QJBELDw4QDQ8lECQPDQ8ODw4QJBAMDyQSAA0FAAA=",
"JgDmAHU2ECMSIhIMEAwPDg8kEQ0QDA8lDyUPDREjEA0QDQ8lDiUPDhAkECQQDRAMDyUPDhEMDyUPDQ8ODw4PDg4OEQwQDQ8NEQ0PDQ8ODw4QDQ4OEQwQDQ8NESMRDRAMDyUPDRENDyQRIxEMDg4SDA8NDw4QDRELDw4QJBANEAwPDhANDw4PJQ4lDyUPJQ8lDiUPDhEMEA0PDRENDg4PDg8ODw4ODhEMEA0PDRENDw0PDg8OEQsPJQ8lDyUPJQ4OEQwQDQ8NEQ0QDA8lDw4PJREMDg4PDg8OESMQDA8OEA0QJBAMDyURAA0FAAA=",
"JgDmAHY1EiISIhEMEQwODhIiEgsRDA4lECQPDhEjEQwRCw8lDyUPDhEiEiISCxEMDyUODhIMECMRDA8NEQ0ODg8OEQwRDBELEgsRDA8NEgwQDA8OEQwRCw8OEiIRDBEMDiUQDREMESMRIxELDw4RDBANDg4SCxEjESMPDRANEgsRDA8NEgwRIhEjESMRIw8lECMRDA8NEgwQDA8OEQwRDA4OEgsRDA8NEgwQDA8OEQwPDRANEgsRIxEjESMRIhEMDw4RDBELDw4RDA8lEQsPJQ8OEQwRDA4lDw4RDBEMDg4RIxILESISAA0FAAA=",
"JgDmAHc0EiISIhEMEQsPDhEjEQwRDA4lDyUPDhEiEwsQDA8lDyUPDRIiEiISCxEMDiUPDhILESMRDA4OEgsRDA8NEgwRCw8OEQwRDA4OEwoRDA8NEgwRCw8OESISDBELDyUPDhEMESMRIhEMDw0SDBELDw4RDBEMDiUPDhMKEQwODhIMEAwPJQ8lDiUPJQ8lDyUPDRIMEQsPDhEMEQsPDhILEQwPDRIMEAwPDhILEQsPDhILEQwOJQ8lDyUPJQ8NEgwRCw8OEQwRDA4lDw4SIhEMEQsPDhILEQwPDRIMEAwPJQ8NEiITAA0FAAA=",
"JgDmAHY1ESMRIhILEA0PDg8lEQsQDREjDyUPDhEiEgsQDQ8lDyUPDREjESMRCxAODyQRDBELECQQDg4OEQwPDg8NDw4RDA8OEQsQDREMEQwPDg8NEgsRDA8OESISCxANESMPDg4OECQQJA8ODw0SCxANDw4PDRAkEA0RDBELEA4PDREMEQwPJQ8lDyQPJQ8lDyUPDQ8ODw4PDhELEA0PDhELEA4PDREMDw4PDhELEA0RDBELEgwRIg8lDyUPJQ8NEgsQDQ8OEQsQDhAjDw4RIxELEA0PDhEjESISIhIiESMRCxAODyQQAA0FAAA=",
"JgDmAHgzECQQJA8OEQwPDRAkEA0RDA8lDyQPDhAkDw0RDQ4lDyUPDg8kECQQDREMDyUPDRANECQQDQ8NEA0QDQ8ODw0RDQ4OEA0QDQ8NEA0QDQ8ODw0RDQ4OECQQDBENDiUPDg8OECMRIxEMDw4PDRENDw0QDRANDw4PDREMDw4PDRENDg4QJA8lDyUPJBEjECQPDRENDw0QDRANDw4PDRQODw0RDQ4OEA0QDQ8NEA0QDQ8ODw0RIxEjESMQIxENDg4QDRANDw0QDREjEA0PJQ8NEA0QDQ8ODyQQJBAkECQPDRENDiURAA0FAAA=")
        off = "JgDmAHY1ESIQJBANEQwPDg8kEA0QDREjDyUQDBAkEA0RDA8lDyUODhAkDyUPDRENECMQDQ8ODyQSCw8ODw4PDg4OEA0QDQ8ODw0SCxANDw0QDg4OEA0QDQ8ODw0SCw8ODyUPDRANESMPJREMDg4RDA8ODw4QDQ4lDw4QJA8NEgwQDBANEA0PDRAkEA0QJBAjESMRDA8ODw0QDg8NEA4ODhEMDw0RDA8ODw0SDA4OEA0PDg8ODw0RIw8lECQQIxENDg4PDhANDw0QDREjEQwRCxANEA0PDg8NESMRDA8lDw4RCxIMDiUPAA0FAAA="
        heat = ("JgDmAHY1ECMRIxIMEAwPDREjEgwQDA8lDyUODhIiEQwRDA8kDyUPDhEjESISDBELDyUPDhANESMRCw8OEA0RDA4OEgsRDA8NEQ0PDQ8OEA0RCw8OEA0RDA8NESMRDBEMDyUODhEMESMRDA8NEQ0RCw8OEA0RCw8lDyUPJQ8lDg4RDBEMDw0SIhEjESMRIxAjESMSCxEMDw0SDBELDw4SCxEMDg4SCxEMDw0RDRELDw4QDRANDg4RIxAkESIRIxENEAwPDhANEQsPDhANEQwOJQ8OEQwRDA8kDyUPJQ8OEA0RIxELDyUPAA0FAAA=",
"JgDmAHgzEiIRIxILDg4SCxEjEQwODhIiEiIRDBEjEQsPDhIiESISDBEiEiIRDA8NEiISCxEMDyUODhIMEAwPDhEMEQsPDhILEQwODhIREQsPDhEMEQwODhILESMRDA4OEiISCxEMDiUPDhILEQwPDRIMEAwPDhEMESMRIhIiEQwPDRIMEQsPJQ8lDyUOJQ8lDyUPDRENEQsPDhEMEQwODhILEQwPDRIMEQsPDhEMEQwODhILEQwPJQ4lDyUPJQ8OEQwRCw8OEgsRDA4lDw4SIhEMEQwODhILESMRDA4lDw4SIhEMESIQAA0FAAA=",
"JgDmAHkzESMRIhEMDw4RDBEjEQsPDhEiEiISDA8kEQwPDRIiEiISCxEjESMRCw8OEiIRDBELDyUPDhEMEQwODhILEQwPDRIMEQsPDhEMEQwODhEMEQwPDRIMECMRDA8NEiISDBAMDyUPDRIMEAwPDhEMEQsPDhIiEQwRIxEjEgoPDhEMEQsPJQ8lDyUPJQ4lDyUPDhEMEQwODhILEQwPDRIMEQsPDhEMEQwODhILEQwPDRIMEAwPJQ8lDiUPJQ8OEQwRDA4OEgsRDA8lDw0SIhILEQwPDRIiEgsRDA8lDw0SIhILESIQAA0FAAA=",
"JgDmAHU2ESMRIhIMDw0QDREjEQwPDQ8lECQPDRIiEgwQDA8lDyUODhIiECQRDA8ODyQPDhILESMRCxANEgsRDA8NEgwQDBANEA0RCw8OEgsPDg8NEgwODhANECMSDBAMECQPDRIMDyQSCw8OEQwRCxANEgsRDA8NEgwQIxEjDw4PDRILEQwPJQ4lECQPJRAkDyUPDRILEQwPDhEMDw0PDhILEQwODhILEQwPDRIMEQsQDREMDw4OJQ8lDyUPJQ8NEgwODhANEQwRCxIiDw4QJBEMEQsPDhEMDw4ODhIiEA0QJBEMDyQRAA0FAAA=",
"JgDmAHkzDyUPJQ4OEgsRDA8lDg4SDBAjESMRDA4lDw4SCxEjESMRCw8lDyUPDRIMESISCw8OESISDBELDw4RDBELDw4SCxEMDw0SDBAMDw4RDBELDw4SCxEMDiUPDhILESMRDA4OEiISCxEMDg4SDBELDw4RDBEjESIRDA8lDw0SDBELDw4RIhIiEiISIhEjESISDBELDw4RDBELDw4SCxEMDw0SDBELDw4RDBELDw4SCxEMDg4SIhIiEiIRIhIMEQwODhANEQwODhIiEgsRIxIKDw4SCxEjESMRIxELDw4RIhIMESIRAA0FAAA=",
"JgDmAHgzECQPJQ8OEQwRCw8lDw4RDBEjDyQRDA8lDw0SDBEiEiISCw8kDyUPDhILESMRCw8OECQRDA8ODw0SCxEMDw0SDBELEA0RDBEMDg4SCxEMDw0SDBAMDyUPDRENESIRDA8OESISDBELDw4RDA8NEA0SCxEMDyUODhIiEgsRDA4OEgwQIxEjDyURIxEiESMRDA8NEgwRCw8OEQwPDRANEgsRDA8NEgwQDBANEQwRCw8OEgsRIw8lESMQIxEMDw0SDBELDw4RDBEjEQsPJRANEQwRCw8OEiIQJBEMEQsQJA8OESIPAA0FAAA=",
"JgDmAHY1EiISIhEMDg4SCxEjEQwODhIiEiIRDBEjEQsPDhIiESISDBIhEiISCw8NEiISCxEMDyUPDRIMEQsPDhEMEQsPDhILEQwODhIMEAwPDhEMEQsPDhILESMRCw8OEiIRDBEMDiUPDhILEQwODhIMEAwPDhEiEgwRCw8lDw0SDBELDw4QJBEiEiISIhIiESISDBELDw4SCxEMDg4SCxEMDw0SDBELDw4RDBEMDg4SCxEMDw0SIhIiEiISIhEMEQsPDhILEQwVDhEjEQsPJQ8OEQwRDA4lDw4RIxEMEQsPJQ8OESIRAA0FAAA=",
"JgDmAHU2ESISIhIMEAwPDhEiEgwRCw8lDyUODhIiEgsRDA8lDiUPDhEjECQQDRELDyUPDhEMESMRCw8OEQwRDA4OEgsRDA8NEgwRCw8OEQwRDA4OEgsRDA8NEiISCxEMDyUODhIMECMRDA8NEgwRCw8OEQwRCw8OEgsRDA8lDg4SCxEMDw0SIhIiEiIRIxEiEiISCxEMDw4RDBELDw4SCxEMDg4SCxEMDw0SDBELDw4RDBEMDg4SIhIiESMRIhIMEAwPDhEMEQsPDhIiEQwRIxIKDw4RDBEMDg4SIhILEQwOJQ8OEiIPAA0FAAA=",
"JgDmAHkzDyQPJQ8OEgsRDA4lDw4SCxEjESMRCw8lDw4RDBEjEiESCw8lDyUODhENECMRDA8NEiISCxEMDw0SDBELDw4RDBEMDg4RDBEMDw0SDBAMDw4QDRANDiUPDhANESMRCw8OEiIRDBEMDg4RDBEMDw0SDBEiEiISIhILDg4SCxEMDw0SIhIiEiIQJBEiESMSCxEMDw0SDBELDw4RDBEMDg4SCxEMDw0SDBELDw4QDREMDg4SIhIiESISIhIMEAwPDhEMEQsPDhEjEQwRIxELDw4RDBEjEiIRCw8OEQwRIxELDyURAA0FAAA=",
"JgDmAHY1EiISIhEMEQsPDhIiEQwRDA4lDyUPDhAkEQwRCw8lDyUPDRIiEiISCxEMDyUODhILESMRDA4OEgwRCw8OEQwRCw8OEgsRDA4OEgwQDA8OEQwRCw8OESMRDBELDyUPDhEMESMRCw8OEQwRDA4OEgwQDA8OESISIhILEQwPDRENEQsPJQ8lDyUOJQ8lDyUPDhEMEQsPDhEMEQwODhILEQwPDRIMEQsPDhEMEQwODhEMEQwPJQ4lDyUPJQ8OEQwRCw8OEgsRDA4lDw4SIhILEQwODhILESMSCw4OEgwQIxEMDyURAA0FAAA=",
"JgDmAHY1EiISIhANEQwODhIiEgsRDA8lDiUPDhAkEQwRDA4lDyUPDhEiEiISDBAMDyUPDRIMDyQRDA8NEgwRCw8OEQwRDA4OEQwQDQ8NEgwRCw8OEQwRDA4OESMRDBEMDiUPDhILESMRDA4OEgsRDA8NEQ0RCw8lDw4RIhIMEQsPDhEMEQsPJRAkDyUPJQ4lDyUPDhANEQsPDhILEQwPDRIMEQsPDhEMEQsQDRILEQwPDRIMEQsPJQ8lDiUPJQ8OEQwRDA4OEgsRDA8lDg4RIxILEQwPDREjEQwRDA8NEQ0RIhILDyUSAA0FAAA=",
"JgDmAHc0ECQQJA8NEgwODhEjEA0QDQ8lDiUPDg8lDw0SCw8lDyUPDg8kECQQDRANDyUPDRANESMRDA8NEA0QDQ8ODw0RDQ4OEA0RDA8NEA4RCw8ODw0RDQ4OECQPDRIMDiUPDhANESIRDQ4OEA0RDA8NEA0RDA8ODw4RIhEMDw4PDhEMDg4SIg8lDyQQJBAkECQPDRIMDg4QDRANDw4PDhELDw4PDRIMDg4QDRANDw0RDBILDw4QJA8kECQQJA8OEA0PDRANEA0PDg8kEA0RIxEMDw4PDRILDw4PDhEMDg4QJA8OECMRAA0FAAA=",
"JgDmAHgzDyUPJQ8OEA0RCw8lDw4QDRAkESMRCw8lDw4QDREiEiIRDA8lDiUPDhEMESMSCw4OESMRDBEMDg4RDQ8NDw4QDRELEA0QDRANDg4RDRAMDw4QDRELDyUPDhANECQQDA8OECQQDRELDw4QDREMDg4RDBEjESMRDA4OEQwRDA8NEgwRIhEjESMSIhEjESIRDA8OEA0RCw8OEA0RDA8NEQwRDA8NEQ0QDA8OEA0RDA4OEQwRIxEjEiIRIxELDw4QDRAMDw4QDREjEQsQJA8OEQwRDA4lDyUPJQ8lDyUODhEMESIRAA0FAAA=",
"JgDmAHc0DyUPJQ8NEQ0RCw8lDw0RDRAjEiIRDA8lDg4RDBEjESMRDA4lDyUPDhANESMQDBANECQRDBELDw4QDREMDg4RDBEMDw4QDRAMDw4QDREMDg4RDBEMDyUPDRIMDyQRDA8NESMRDRAMDw4RDBELDw4QDRANDiUPDhEMEQwODhENEQsPJQ8lDiUPJQ8lDyUPDRENEQsPDhANEAwPDhEMEQwPDRIMEAwPDhANEQsPDhANEA0OJg4lDyUPJQ8NEQ0RCw8OEA0RDA4lDw4QJBEMEQsPDhANESMRIxEjESIRDA8OECMPAA0FAAA=",
"JgDmAHY2ECMRIxEMDg4SCxEjEQwPDREjEiISCxAkEQsPDhEjECQRDBEjESIRDA8NESMSDBELDyUPDRENEQsPDhEMEQsPDhILEQwPDRIMEQsPDhEMEQsPDhILESMRDA4OESMQDREMDiUPDhEMEQwPDRIMEQsPDhEiEQ0RCw8OEQwRDA4OEgsRIxEjESMRIxEiESMRDA4OEQwRDA8OEQwRCw8OEgsRDA4OEQwRDA8NEgwRCw8OEA0RIxEjESIRIxEMDw0RDRELDw4QDREjEQsPJQ8OEA0RCw8lDw4RIhIiESMRDBANDyQQAA0FAAA=",
"JgDmAHY1DyUPJA8OEA0QDQ4mDg4RDBAkESMQDA8lDw4QDREjECQRCw8lDyUPDRENECMQDQ8NESMRDBEMDw4QDQ8NEA0QDREMDw0RDQ8NDw4QDRELDw4QDREMDiUQDRANECQRCxANESMQDRANDg4RDBEMDw0RDRAMDw4QDREMDw0RDBANDw0RIxEjESMQJBAjESMRDBANDw4QDRELDw4QDRANDg4RDBEMDw4QDRELDw4QDREMDw0RIxAkECQQIxENDw0PDhANEQsPDhAkEA0RIxELDw4QDRANDg4RIxAkECQQDRELDyURAA0FAAA=")
        
        if (self._current_operation == 'idle') or (self._current_operation =='off'):
            sendir = b64decode(off)
        elif self._current_operation == 'heat':
            sendir = b64decode(heat[int(self._target_temperature) - self._target_temperature_low])
        elif self._current_operation == 'cool':
            sendir = b64decode(cool[int(self._target_temperature) - self._target_temperature_low])
        else:
            if self._current_temperature and (self._current_temperature < self._target_temperature_low):
                sendir = b64decode(heat[int(self._target_temperature) - self._target_temperature_low])
            else:
                sendir = b64decode(cool[int(self._target_temperature) - self._target_temperature_low])
        
        try:
            self._device.send_data(sendir)
        except (socket.timeout, ValueError) as error:
            if retry < 1:
                _LOGGER.error(error)
                return False
            if not self._auth():
                return False
            return self._sendpacket(retry-1)
        return True