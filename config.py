import machine
import time

# ┌─────────────────────┐
# │  General Settings   │
# └─────────────────────┘
USE_WIFI = False  # Use Wi-Fi (not functional yet)
USE_MQTT = False  # Use MQTT (not functional yet)
IS_WATER_HEATER = True  # True if controlling a Water/Coolant Heater
HAS_SECOND_PUMP = True  # True if driving a second water pump

# ┌─────────────────────┐
# │  Safety Limits      │
# └─────────────────────┘
EXHAUST_SAFE_TEMP = 160  # Max safe temp for exhaust (°C)
OUTPUT_SAFE_TEMP = 90  # Max safe temp for output (°C)
EXHAUST_SHUTDOWN_TEMP = 80.0  # Exhaust shutdown temp (°C)

# ┌─────────────────────┐
# │  WiFi Settings      │
# └─────────────────────┘
SSID = "MYSSID"  # WiFi SSID
PASSWORD = "PASSWORD"  # WiFi Password

# ┌─────────────────────┐
# │  MQTT Settings      │
# └─────────────────────┘
MQTT_SERVER = "10.0.0.137"  # MQTT Server IP
MQTT_CLIENT_ID = "esp32_heater"  # MQTT Client ID
SET_TEMP_TOPIC = "heater/set_temp"  # Topic for setting temp
SENSOR_VALUES_TOPIC = "heater/sensor_values"  # Topic for sensor values
COMMAND_TOPIC = "heater/command"  # Topic for commands

# ┌─────────────────────┐
# │  Sensor Settings    │
# └─────────────────────┘

# OUTPUT_SENSOR_TYPE: Specifies the type of thermistor used for measuring output temperature.
# Available options: 'NTC_50k', 'NTC_10k', 'PTC_1k', 'PTC_500', 'PTC_100', 'PTC_2000'
# Refer to your thermistor's datasheet to select the appropriate type.
OUTPUT_SENSOR_TYPE = 'NTC_50k'

# OUTPUT_SENSOR_BETA: Specifies the BETA value for the output temperature sensor.
# This value is specific to the thermistor and is often available in the datasheet.
# It is used in temperature calculation and should be as accurate as possible for precise measurements.
OUTPUT_SENSOR_BETA = 3950  # Customize the BETA value

# EXHAUST_SENSOR_TYPE: Specifies the type of thermistor used for measuring exhaust temperature.
# Available options: 'NTC_50k', 'NTC_10k', 'PTC_1k', 'PTC_500', 'PTC_100', 'PTC_2000'
# Refer to your thermistor's datasheet to select the appropriate type.
EXHAUST_SENSOR_TYPE = 'PTC_1k'

# EXHAUST_SENSOR_BETA: Specifies the BETA value for the exhaust temperature sensor.
# This value is specific to the thermistor and is often available in the datasheet.
# It is used in temperature calculation and should be as accurate as possible for precise measurements.
EXHAUST_SENSOR_BETA = 3000  # Customize the BETA value

# ┌─────────────────────┐
# │  Device Control     │
# └─────────────────────┘
TARGET_TEMP = 60.0  # Target temp (°C)
MIN_FAN_PERCENTAGE = 20  # Min fan speed (%)
MAX_FAN_PERCENTAGE = 100  # Max fan speed (%)
MIN_PUMP_FREQUENCY = 1  # Min pump freq (Hz)
MAX_PUMP_FREQUENCY = 5  # Max pump freq (Hz)
PUMP_ON_TIME = 0.02  # Pump on time per pulse (s)
FAN_MAX_DUTY = 1023  # Maximum PWM duty cycle for the fan, ranging from 0 to 1023
CONTROL_MAX_DELTA = 20  # Max temperature delta for control logic
EMERGENCY_STOP_TIMER = 600000  # Timer for emergency stop in milliseconds before reboot (10 minutes)


# ┌─────────────────────┐
# │  Startup Settings   │
# └─────────────────────┘
STARTUP_TIME_LIMIT = 300  # 5 minutes in seconds
GLOW_PLUG_HEAT_UP_TIME = 60  # 1 minute in seconds
INITIAL_FAN_SPEED_PERCENTAGE = 20  # Initial fan speed in percentage

# ┌─────────────────────┐
# │   Shutdown Settings │
# └─────────────────────┘
SHUTDOWN_TIME_LIMIT = 300  # 5 minutes in seconds
COOLDOWN_MIN_TIME = 30  # 30 seconds

# ┌─────────────────────┐
# │  Logging Level      │
# └─────────────────────┘
LOG_LEVEL = 3  # 0: None, 1: Errors, 2: Info, 3: Debug

# ┌─────────────────────┐
# │  Global Variables   │
# └─────────────────────┘
pump_frequency = 0  # Hz of the fuel pump, MUST be a global as it's ran in another thread
startup_attempts = 0  # Counter for failed startup attempts
startup_successful = True  # Flag to indicate if startup was successful
current_state = 'INIT'  # State the control is in
emergency_reason = None
output_temp = None
exhaust_temp = None
heartbeat = time.time()

# ┌─────────────────────┐
# │  Pin Assignments    │
# └─────────────────────┘
GLOW_PIN = machine.Pin(21, machine.Pin.OUT)  # K1 Relay
GLOW_PIN.off()
if IS_WATER_HEATER:
    WATER_PIN = machine.Pin(19, machine.Pin.OUT)  # K2 Relay
    WATER_PIN.off()
if HAS_SECOND_PUMP:
    WATER_SECONDARY_PIN = machine.Pin(18, machine.Pin.OUT)  # K3 Relay
    WATER_SECONDARY_PIN.off()

# Pin Definitions
AIR_PIN = machine.Pin(23, machine.Pin.OUT)
FUEL_PIN = machine.Pin(4, machine.Pin.OUT)  # K4 Relay is 5
FUEL_PIN.off()
SWITCH_PIN = machine.Pin(33, machine.Pin.IN, machine.Pin.PULL_UP)

# Initialize ADC for output and exhaust temperature
OUTPUT_TEMP_ADC = machine.ADC(machine.Pin(32))  # Changed to a valid ADC pin
OUTPUT_TEMP_ADC.atten(machine.ADC.ATTN_11DB)  # Corrected: Full range: 3.3v
EXHAUST_TEMP_ADC = machine.ADC(machine.Pin(34))  # Changed to a valid ADC pin
EXHAUST_TEMP_ADC.atten(machine.ADC.ATTN_11DB)  # Corrected: Full range: 3.3v

# Initialize PWM for air
air_pwm = machine.PWM(AIR_PIN)
air_pwm.freq(1000)
air_pwm.duty(0)  # Ensure the fan isn't initially on after init
