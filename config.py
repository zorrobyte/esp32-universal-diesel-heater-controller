import machine
import utime
import json

# Load the configuration from config.json
with open('config.json') as config_file:
    config = json.load(config_file)

# Assign the loaded values to variables
# ┌─────────────────────┐
# │ General Settings    │
# └─────────────────────┘
USE_WEBSERVER = config['GeneralSettings']['USE_WEBSERVER']
USE_WIFI = config['GeneralSettings']['USE_WIFI']
USE_MQTT = config['GeneralSettings']['USE_MQTT']
IS_WATER_HEATER = config['GeneralSettings']['IS_WATER_HEATER']
HAS_SECOND_PUMP = config['GeneralSettings']['HAS_SECOND_PUMP']
IS_SIMULATION = config['GeneralSettings']['IS_SIMULATION']

# ┌─────────────────────┐
# │ Network Settings    │
# └─────────────────────┘
SSID = config['NetworkSettings']['SSID']
PASSWORD = config['NetworkSettings']['PASSWORD']
MQTT_SERVER = config['NetworkSettings']['MQTT_SERVER']
MQTT_CLIENT_ID = config['NetworkSettings']['MQTT_CLIENT_ID']
MQTT_USERNAME = config['NetworkSettings']['MQTT_USERNAME']
MQTT_PASSWORD = config['NetworkSettings']['MQTT_PASSWORD']

SENSOR_VALUES_TOPIC = config['NetworkSettings']['SENSOR_VALUES_TOPIC']
SET_TEMP_TOPIC = config['NetworkSettings']['SET_TEMP_TOPIC']
COMMAND_TOPIC = config['NetworkSettings']['COMMAND_TOPIC']

# ┌─────────────────────┐
# │ Safety Limits       │
# └─────────────────────┘
EXHAUST_SAFE_TEMP = config['SafetyLimits']['EXHAUST_SAFE_TEMP']
OUTPUT_SAFE_TEMP = config['SafetyLimits']['OUTPUT_SAFE_TEMP']

# ┌─────────────────────┐
# │ Sensor Settings     │
# └─────────────────────┘
OUTPUT_SENSOR_TYPE = config['SensorSettings']['OUTPUT_SENSOR_TYPE']
OUTPUT_SENSOR_BETA = config['SensorSettings']['OUTPUT_SENSOR_BETA']
EXHAUST_SENSOR_TYPE = config['SensorSettings']['EXHAUST_SENSOR_TYPE']
EXHAUST_SENSOR_BETA = config['SensorSettings']['EXHAUST_SENSOR_BETA']

# ┌─────────────────────┐
# │ Temperature Control │
# └─────────────────────┘
TARGET_TEMP = config['TemperatureControl']['TARGET_TEMP']
CONTROL_MAX_DELTA = config['TemperatureControl']['CONTROL_MAX_DELTA']

# ┌─────────────────────┐
# │ Fan Control         │
# └─────────────────────┘
FAN_RPM_SENSOR = config['FanControl']['FAN_RPM_SENSOR']
MIN_FAN_RPM = config['FanControl']['MIN_FAN_RPM']
MAX_FAN_RPM = config['FanControl']['MAX_FAN_RPM']
FAN_MAX_DUTY = config['FanControl']['FAN_MAX_DUTY']

# ┌─────────────────────┐
# │ Fuel Pump Control   │
# └─────────────────────┘
MIN_PUMP_FREQUENCY = config['FuelPumpControl']['MIN_PUMP_FREQUENCY']
MAX_PUMP_FREQUENCY = config['FuelPumpControl']['MAX_PUMP_FREQUENCY']
PUMP_ON_TIME = config['FuelPumpControl']['PUMP_ON_TIME']

# ┌─────────────────────┐
# │ Emergency Handling  │
# └─────────────────────┘
FAILURE_STATE_RETRIES = config['EmergencyHandling']['FAILURE_STATE_RETRIES']
EMERGENCY_STOP_TIMER = config['EmergencyHandling']['EMERGENCY_STOP_TIMER']

# ┌─────────────────────┐
# │ Startup Settings    │
# └─────────────────────┘
STARTUP_TIME_LIMIT = config['StartupSettings']['STARTUP_TIME_LIMIT']
GLOW_PLUG_HEAT_UP_TIME = config['StartupSettings']['GLOW_PLUG_HEAT_UP_TIME']
INITIAL_FAN_SPEED_PERCENTAGE = config['StartupSettings']['INITIAL_FAN_SPEED_PERCENTAGE']

# ┌─────────────────────┐
# │ Shutdown Settings   │
# └─────────────────────┘
SHUTDOWN_TIME_LIMIT = config['ShutdownSettings']['SHUTDOWN_TIME_LIMIT']
COOLDOWN_MIN_TIME = config['ShutdownSettings']['COOLDOWN_MIN_TIME']
EXHAUST_SHUTDOWN_TEMP = config['ShutdownSettings']['EXHAUST_SHUTDOWN_TEMP']

# ┌─────────────────────┐
# │ Flame-out Detection │
# └─────────────────────┘
EXHAUST_TEMP_HISTORY_LENGTH = config['FlameOutDetection']['EXHAUST_TEMP_HISTORY_LENGTH']
MIN_TEMP_DELTA = config['FlameOutDetection']['MIN_TEMP_DELTA']

# ┌─────────────────────┐
# │ Logging Level       │
# └─────────────────────┘
LOG_LEVEL = config['LoggingLevel']['LOG_LEVEL']

# ┌─────────────────────┐
# │ Global Variables    │
# └─────────────────────┘
pump_frequency = 0
startup_attempts = 0
startup_successful = True
current_state = 'OFF'
emergency_reason = None
output_temp = 0
exhaust_temp = 0
heartbeat = utime.time()
fan_speed_percentage = 0
fan_rpm = 0

# ┌─────────────────────┐
# │ Pin Assignments     │
# └─────────────────────┘

# Fuel Control
FUEL_PIN = machine.Pin(5, machine.Pin.OUT)
FUEL_PIN.off()  # Initialize to OFF

# Air Control
AIR_PIN = machine.Pin(23, machine.Pin.OUT)
air_pwm = machine.PWM(AIR_PIN)
air_pwm.freq(15000)
air_pwm.duty(0)  # Initialize to OFF

# Glow Plug Control
GLOW_PIN = machine.Pin(21, machine.Pin.OUT)
GLOW_PIN.off()  # Initialize to OFF

# Water Control
if IS_WATER_HEATER:
    WATER_PIN = machine.Pin(19, machine.Pin.OUT)
    WATER_PIN.off()  # Initialize to OFF

if HAS_SECOND_PUMP:
    WATER_SECONDARY_PIN = machine.Pin(18, machine.Pin.OUT)
    WATER_SECONDARY_PIN.off()  # Initialize to OFF

# Fan RPM Sensor
if FAN_RPM_SENSOR:
    FAN_RPM_PIN = machine.Pin(22, machine.Pin.IN, machine.Pin.PULL_UP)

# Switch Control
SWITCH_PIN = machine.Pin(33, machine.Pin.IN, machine.Pin.PULL_UP)

# ADC for Temp Sensor
OUTPUT_TEMP_ADC = machine.ADC(machine.Pin(32))
OUTPUT_TEMP_ADC.atten(machine.ADC.ATTN_11DB)

EXHAUST_TEMP_ADC = machine.ADC(machine.Pin(34))
EXHAUST_TEMP_ADC.atten(machine.ADC.ATTN_11DB)
