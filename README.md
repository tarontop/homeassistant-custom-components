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
**customize** (Optional): List of options to customize.<br />
  **- operations** (Optional*): List of operation modes (default: Off, Heat, Cool, Auto)<br />
  **- fan_modes** (Optional*): List of fan modes (default: Low, Mid, High, Auto)<br />
  
#### Example:
```
climate:
  - platform: broadlink
    name: Toyotomi Akira
    host: 192.168.1.85
    mac: 'B4:43:0D:E4:29:4B'
    ircodes_ini: 'broadlink_climate_codes/toyotomi_akira.ini'
    min_temp: 16
    max_temp: 30
    target_temp: 20
    default_operation: 'Off'
    default_fan_mode: Mid
    customize:
      operations:
        - 'Off'
        - Cool
        - Heat
      fan_modes:
        - Low
        - Mid
        - High
        - Auto
```
