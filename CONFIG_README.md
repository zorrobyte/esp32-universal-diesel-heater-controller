# General Settings
- `USE_WEBSERVER`: Enables the built-in AP and webpage for modifying settings. (True/False)
- `USE_WIFI`: Enables or disables Wi-Fi functionality. (True/False)
- `USE_MQTT`: Enables or disables MQTT functionality. (True/False)
- `IS_WATER_HEATER`: Set to True if this device is controlling a water or coolant heater. (True/False)
- `HAS_SECOND_PUMP`: Set to True if there is a secondary water pump in the system. (True/False)
- `IS_SIMULATION`: Set to True to simulate without sensors, etc., connected. Useful for development on an ESP32 without hardware. (True/False)

# Network Settings
- `SSID`: SSID of the WiFi network to connect to.
- `PASSWORD`: Password of the WiFi network.
- `MQTT_SERVER`: Address of the MQTT broker.
- `MQTT_CLIENT_ID`: MQTT client ID.
- `MQTT_USERNAME`: MQTT username.
- `MQTT_PASSWORD`: MQTT password.
- MQTT Topics:
  - `SENSOR_VALUES_TOPIC`: Topic to publish sensor values.
  - `SET_TEMP_TOPIC`: Topic to receive the target temperature.
  - `COMMAND_TOPIC`: Topic to receive commands like "start" and "stop".

# Safety Limits
- `EXHAUST_SAFE_TEMP`: Max safe temperature for exhaust in Celsius.
- `OUTPUT_SAFE_TEMP`: Max safe temperature for output in Celsius.

# Sensor Settings
- Thermistor type options for `OUTPUT_SENSOR_TYPE` and `EXHAUST_SENSOR_TYPE`: 
  - `'NTC_10k'`, `'NTC_50k'`, `'NTC_100k'`, `'PTC_500'`, `'PTC_1k'`, `'PTC_2.3k'`.
- Use a matching resistor in your voltage divider for the thermistors, which is assumed for calculations.
- `OUTPUT_SENSOR_BETA`: BETA value for the output temperature sensor.
- `EXHAUST_SENSOR_BETA`: BETA value for the exhaust temperature sensor.

# Device Control
- Temperature Control:
  - `TARGET_TEMP`: Target temperature to maintain in Celsius.
  - `CONTROL_MAX_DELTA`: Maximum temperature delta for control logic in Celsius.
- Fan Control:
  - `FAN_RPM_SENSOR`: If using a hall effect sensor for fan RPM (True/False).
  - `MIN_FAN_RPM`: Minimum fan RPM.
  - `MAX_FAN_RPM`: Maximum fan RPM.
  - `FAN_MAX_DUTY`: Maximum duty cycle for the fan's PWM signal.
- Fuel Pump Control:
  - `MIN_PUMP_FREQUENCY`: Minimum frequency of the water pump in Hertz.
  - `MAX_PUMP_FREQUENCY`: Maximum frequency of the water pump in Hertz.
  - `PUMP_ON_TIME`: Duration the pump is on during each pulse, in seconds.
- Emergency Handling:
  - `FAILURE_STATE_RETRIES`: How many times will we attempt a restart due to failed STARTING or flame out when RUNNING.
  - `EMERGENCY_STOP_TIMER`: Time after emergency stop triggered until system reboot, in milliseconds.

# Startup Settings
- `STARTUP_TIME_LIMIT`: Maximum time allowed for startup, in seconds.
- `GLOW_PLUG_HEAT_UP_TIME`: Time for the glow plug to heat up, in seconds.
- `INITIAL_FAN_SPEED_PERCENTAGE`: Initial fan speed as a percentage of the maximum speed.

# Shutdown Settings
- `SHUTDOWN_TIME_LIMIT`: Maximum time allowed for shutdown, in seconds.
- `COOLDOWN_MIN_TIME`: Minimum time for the system to cool down, in seconds, regardless of temperature.
- `EXHAUST_SHUTDOWN_TEMP`: Temperature at which we consider the heater cooled down in Celsius.

# Flame-out Detection
- `EXHAUST_TEMP_HISTORY_LENGTH`: Length of the deque storing the last N exhaust temperature readings.
- `MIN_TEMP_DELTA`: The minimum meaningful temperature decrease in Celsius.

# Logging Level
- `LOG_LEVEL`: Logging level: 0 for None, 1 for Errors, 2 for Info, 3 for Debug.

# Pin Assignments
- `FUEL_PIN`: Pin assigned for fuel control.
- `AIR_PIN`: Pin assigned for air control.
- `GLOW_PIN`: Pin assigned for glow plug control.
- `WATER_PIN`: Pin assigned for water control (if `IS_WATER_HEATER` is True).
- `WATER_SECONDARY_PIN`: Pin assigned for secondary water pump control (if `HAS_SECOND_PUMP` is True).
- `FAN_RPM_PIN`: Pin assigned for fan RPM sensor (if `FAN_RPM_SENSOR` is True).
- `SWITCH_PIN`: Pin assigned for switch control.
- `OUTPUT_TEMP_ADC`: Pin assigned for output temperature ADC.
- `EXHAUST_TEMP_ADC`: Pin assigned for exhaust temperature ADC.

# Calibration and Beta Value
- To calibrate the beta value for a thermistor, follow these steps:
  1. Measure the resistance of the thermistor at two known temperatures (e.g., ice water at 0°C and boiling water at 100°C).
  2. Use the following formula to calculate the beta value:
  \[
  \beta = \frac{\ln(R2/R1)}{\frac{1}{T2} - \frac{1}{T1}}
  \]
  where:
  - \( R1 \) is the resistance at temperature \( T1 \) (in Kelvin),
  - \( R2 \) is the resistance at temperature \( T2 \) (in Kelvin),
  - \( \ln \) is the natural logarithm.
  3. Replace the `OUTPUT_SENSOR_BETA` or `EXHAUST_SENSOR_BETA` in the settings with the calculated beta value.
  4. Ensure the beta value is in accordance with the thermistor's datasheet for accurate temperature measurement.

# Notes:
- The beta value is crucial for accurate temperature measurements.
- Calibration should be performed in the environment where the sensor will be used.
- A precise multimeter should be used for measuring thermistor resistance.
- It is recommended to consult the thermistor's datasheet for detailed calibration instructions and beta value information.

Remember to save changes to the configuration after editing.
