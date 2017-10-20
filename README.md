# Custom components for Home Assistant
## Broadlink IR Climate Component

#### Configuration variables:
**name** (Optional): Name of climate component<br />
**host** (Required): The hostname/IP address of broadlink rm device<br />
**mac** (Required): Broadlink rm device MAC address<br />
**timeout** (Optional): Timeout in seconds for the connection to the device<br />
**ircodes_ini** (Required): The path of ir codes ini file<br />
**min_temp** (Optional): Set minimum set point available (default: 16)<br />
**max_temp** (Optional): Set maximum set point available (default: 30)<br />
**target_temp** (Optional): Set initial target temperature. (default: 20)<br />
**temp_sensor** (Optional): **entity_id** for a temperature sensor, **target_sensor.state must be temperature.**<br />
**customize** (Optional): List of options to customize.<br />
  **- operations** (Optional*): List of operation modes (default: idle, heat, cool, auto)<br />
  **- fan_modes** (Optional*): List of fan modes (default: low, mid, high, auto)<br />
  
#### Example:
```
climate:
  - platform: broadlink
    name: Toyotomi Akira
    host: 192.168.1.85
    mac: 'BB:BB:BB:BB:BB:BB'
    ircodes_ini: 'broadlink_climate_codes/toyotomi_akira.ini'
    min_temp: 16
    max_temp: 30
    target_temp: 20
    temp_sensor: sensor.living_room_temperature
    default_operation: idle
    default_fan_mode: mid
    customize:
      operations:
        - idle
        - cool
        - heat
      fan_modes:
        - low
        - mid
        - high
        - auto
```


## Broadlink IR Media Player

#### Configuration variables:
**name** (Optional): Name of climate component<br />
**host** (Required): The hostname/IP address of broadlink rm device<br />
**mac** (Required): Broadlink rm device MAC address<br />
**timeout** (Optional): Timeout in seconds for the connection to the device<br />
**ircodes_ini** (Required): The path of ir codes ini file<br />

#### Example:
```
media_player:
  - platform: broadlink
    name: Master Bedroom TV
    host: 192.168.1.85
    mac: 'BB:BB:BB:BB:BB:BB'
    ircodes_ini: 'broadlink_media_codes/philips.ini'
```



## Broadlink RF Fan

#### Configuration variables:
**name** (Optional): Name of fan component<br />
**host** (Required): The hostname/IP address of broadlink rm device<br />
**mac** (Required): Broadlink rm device MAC address<br />
**timeout** (Optional): Timeout in seconds for the connection to the device<br />
**rfcodes_ini** (Required): The path of RF codes ini file<br />
**default_speed** (Optional): Default fan speed when fan is turned on<br />
**default_direction** (Optional): Default fan rotation direction when turned on. Possible values are right (clockwise) and left (anti-clockwise). (default: left)<br />
**customize** (Optional): List of options to customize.<br />
  **- speeds** (Optional*): List of supported speeds (default: low, medium, high)<br />

#### Example:
```
fan:
  - platform: broadlink
    name: Living Room Fan
    host: 192.168.1.85
    mac: 'BB:BB:BB:BB:BB:BB'
    rfcodes_ini: 'broadlink_fan_codes/living_room_fan.ini'
    default_speed: low
    defaut_direction: left
    customize:
        speeds:
            - low
            - medium
            - high
            - highest
```

#### How to make your INI Files:
The INI file must have a [general] section and optionally a [sources] section.
In the [general] section you must fill all keys and values. The keys are: 
```
[general]
turn_off = ...
turn_on = ...
previous_channel = ...
next_channel = ...
volume_down = ...
volume_up = ...
mute = ...
```
You are free to set any key name under [sources] section.
```
[sources]
My source 1 = ...
My source 2 = ...
.
.
.
```
