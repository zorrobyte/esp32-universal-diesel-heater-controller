import machine
import time

# ┌─────────────────────┐
# │ General Settings    │
# └─────────────────────┘
USE_WIFI = False  # Enable or disable Wi-Fi functionality (not yet implemented).
USE_MQTT = False  # Enable or disable MQTT functionality (not yet implemented).
IS_WATER_HEATER = True  # Set to True if this device is controlling a water or coolant heater.
HAS_SECOND_PUMP = True  # Set to True if there is a secondary water pump in the system.
IS_SIMULATION = True  # Set to True if you wish to simulate without sensors, etc connected

# ┌─────────────────────┐
# │ Network Settings    │
# └─────────────────────┘
SSID = 'Your_WiFi_SSID'  # SSID of the WiFi network to connect to
PASSWORD = 'Your_WiFi_Password'  # Password of the WiFi network
MQTT_SERVER = 'mqtt.example.com'  # Address of the MQTT broker
MQTT_CLIENT_ID = 'your_client_id'  # MQTT client ID
MQTT_USERNAME = 'mqtt_username'  # MQTT username (optional)
MQTT_PASSWORD = 'mqtt_password'  # MQTT password (optional)

# MQTT Topics
SENSOR_VALUES_TOPIC = 'sensors/values'  # Topic to publish sensor values
SET_TEMP_TOPIC = 'set/temperature'  # Topic to receive the target temperature
COMMAND_TOPIC = 'command'  # Topic to receive commands like "start" and "stop"

# ┌─────────────────────┐
# │ Safety Limits       │
# └─────────────────────┘
EXHAUST_SAFE_TEMP = 160  # Max safe temperature for exhaust in C.
OUTPUT_SAFE_TEMP = 90  # Max safe temperature for output in C.

# ┌─────────────────────┐
# │ Sensor Settings     │
# └─────────────────────┘
# Specify the type of thermistor used for measuring temperatures.
# Available options: 'NTC_10k', 'NTC_50k', 'NTC_100k', 'PTC_500', 'PTC_1k', 'PTC_2.3k'
OUTPUT_SENSOR_TYPE = 'NTC_50k'
OUTPUT_SENSOR_BETA = 3950  # BETA value for the output temperature sensor, typically found in the datasheet.
EXHAUST_SENSOR_TYPE = 'PTC_1k'
EXHAUST_SENSOR_BETA = 3000  # BETA value for the exhaust temperature sensor, typically found in the datasheet.

# ┌─────────────────────┐
# │ Device Control      │
# └─────────────────────┘
TARGET_TEMP = 60.0  # Target temperature to maintain in C.
MIN_FAN_PERCENTAGE = 20  # Minimum fan speed as a percentage of the maximum speed.
MAX_FAN_PERCENTAGE = 100  # Maximum fan speed as a percentage of the maximum speed.
MIN_PUMP_FREQUENCY = 1  # Minimum frequency of the water pump in Hz.
MAX_PUMP_FREQUENCY = 5  # Maximum frequency of the water pump in Hz.
PUMP_ON_TIME = 0.02  # Duration the pump is on during each pulse, in seconds.
FAN_MAX_DUTY = 1023  # Maximum duty cycle for the fan's PWM signal.
CONTROL_MAX_DELTA = 20  # Maximum temperature delta for control logic in C.
EMERGENCY_STOP_TIMER = 600000  # Time before an emergency stop triggers a system reboot, in milliseconds.

# ┌─────────────────────┐
# │ Startup Settings    │
# └─────────────────────┘
STARTUP_TIME_LIMIT = 300  # Maximum time allowed for startup, in seconds.
GLOW_PLUG_HEAT_UP_TIME = 60  # Time for the glow plug to heat up, in seconds.
INITIAL_FAN_SPEED_PERCENTAGE = 20  # Initial fan speed as a percentage of the maximum speed.

# ┌─────────────────────┐
# │ Shutdown Settings   │
# └─────────────────────┘
SHUTDOWN_TIME_LIMIT = 300  # Maximum time allowed for shutdown, in seconds Exceeding this puts us in an EMERGENCY state.
COOLDOWN_MIN_TIME = 30  # Minimum time for the system to cool down, in seconds, regardless of temperature.
EXHAUST_SHUTDOWN_TEMP = 80.0  # Temperature at which we consider the heater cooled down in C.

# ┌─────────────────────┐
# │ Flame-out Detection │
# └─────────────────────┘
# Length of the deque storing the last N exhaust temperature readings.
# This helps in detecting a consistent decrease in exhaust temperature,
# which may signify a flame-out condition.
EXHAUST_TEMP_HISTORY_LENGTH = 5

# The minimum meaningful temperature decrease in Celsius.
# If the exhaust temperature consistently falls by this amount or more,
# it may indicate a flame-out.
MIN_TEMP_DELTA = 0.5

# ┌─────────────────────┐
# │ Logging Level       │
# └─────────────────────┘
LOG_LEVEL = 3  # Logging level: 0 for None, 1 for Errors, 2 for Info, 3 for Debug.

# ┌─────────────────────┐
# │ Global Variables    │
# └─────────────────────┘
# These are global variables used in the program.
pump_frequency = 0
startup_attempts = 0
startup_successful = True
current_state = 'INIT'
emergency_reason = None
output_temp = 0
exhaust_temp = 0
heartbeat = time.time()

# ┌─────────────────────┐
# │ Pin Assignments     │
# └─────────────────────┘
# Define the hardware pins for various components.
GLOW_PIN = machine.Pin(21, machine.Pin.OUT)
GLOW_PIN.off()  # Ensure is initialized to OFF when booting, just in case
if IS_WATER_HEATER:
    WATER_PIN = machine.Pin(19, machine.Pin.OUT)
    WATER_PIN.off()  # Ensure is initialized to OFF when booting, just in case
if HAS_SECOND_PUMP:
    WATER_SECONDARY_PIN = machine.Pin(18, machine.Pin.OUT)
    WATER_SECONDARY_PIN.off()  # Ensure is initialized to OFF when booting, just in case

AIR_PIN = machine.Pin(23, machine.Pin.OUT)
FUEL_PIN = machine.Pin(5, machine.Pin.OUT)
FUEL_PIN.off()  # Ensure is initialized to OFF when booting, just in case
SWITCH_PIN = machine.Pin(33, machine.Pin.IN, machine.Pin.PULL_UP)

# Initialize ADC for temperature sensors
OUTPUT_TEMP_ADC = machine.ADC(machine.Pin(32))
OUTPUT_TEMP_ADC.atten(machine.ADC.ATTN_11DB)
EXHAUST_TEMP_ADC = machine.ADC(machine.Pin(34))
EXHAUST_TEMP_ADC.atten(machine.ADC.ATTN_11DB)

# Initialize PWM for air control
air_pwm = machine.PWM(AIR_PIN)
air_pwm.freq(1000)
air_pwm.duty(0)  # Ensure is initialized to OFF when booting, just in case
