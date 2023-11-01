import machine
import utime

# ┌─────────────────────┐
# │ General Settings    │
# └─────────────────────┘
USE_WIFI = False  # Enable or disable Wi-Fi functionality.
USE_MQTT = False  # Enable or disable MQTT functionality.
IS_WATER_HEATER = False  # Set to True if this device is controlling a water or coolant heater.
HAS_SECOND_PUMP = False  # Set to True if there is a secondary water pump in the system.
IS_SIMULATION = False  # Set to True if you wish to simulate without sensors, etc connected

# ┌─────────────────────┐
# │ Network Settings    │
# └─────────────────────┘
SSID = 'SSID'  # SSID of the WiFi network to connect to
PASSWORD = 'PASSWORD'  # Password of the WiFi network
MQTT_SERVER = '10.0.0.137'  # Address of the MQTT broker
MQTT_CLIENT_ID = 'esp32_oshw_controller'  # MQTT client ID
MQTT_USERNAME = 'USERNAME'  # MQTT username
MQTT_PASSWORD = 'PASSWORD'  # MQTT password

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
# Remember to use a matching resistor in your voltage divider, we assume it is for calculations
OUTPUT_SENSOR_TYPE = 'NTC_50k'
OUTPUT_SENSOR_BETA = 3950  # BETA value for the output temperature sensor, typically found in the datasheet.
EXHAUST_SENSOR_TYPE = 'PTC_1k'
EXHAUST_SENSOR_BETA = 3000  # BETA value for the exhaust temperature sensor, typically found in the datasheet.

# ┌─────────────────────┐
# │ Device Control      │
# └─────────────────────┘

# ── Temperature Control ──────────────────────────────
TARGET_TEMP = 22.0  # Target temperature to maintain in C.
CONTROL_MAX_DELTA = 20  # Maximum temperature delta for control logic in C.

# ── Fan Control ──────────────────────────────────────
FAN_RPM_SENSOR = False  # If using a hall effect sensor for fan RPM (recommended)
# Assuming two magnets on your fan blade. File an issue on GH if you know of one
# with a single magnet or more than two. Yes, hydronics have them check on the other
# side of the fan shaft.
# Else, you can use "dumb" non-feedback fan control based on percentage of
# maximum PWM cycle by guessing values. Note that 100% on percentage mode (non-RPM) is
# VERY FAST, faster than your heater has run ever likely, and can smoke wires, etc
# since the fan may pull 10Amps+! Note that non-RPM based control is inherently
# more dangerous than RPM control as if the fan stops or gets slower over time
# (due to dust in bearing, etc), no one will know and can cause nasty things like
# massive CO2 production due to improper air/fuel or even a fire
MIN_FAN_RPM = 2000  # Minimum fan RPM
MAX_FAN_RPM = 5000  # Maximum fan RPM
FAN_MAX_DUTY = 1023  # Maximum duty cycle for the fan's PWM signal
# PWM scaling for non-linear fan behavior
if FAN_RPM_SENSOR:
    FAN_START_PERCENTAGE = 0  # Not used in RPM mode
    MIN_FAN_PERCENTAGE = 1  # Don't change
    MAX_FAN_PERCENTAGE = 100  # Don't change
else:
    FAN_START_PERCENTAGE = 40  # Start percentage for scaling
    MIN_FAN_PERCENTAGE = 20  # Minimum fan speed as percentage of max speed
    MAX_FAN_PERCENTAGE = 80  # Maximum fan speed as percentage of max speed

# ── Fuel Pump Control ───────────────────────────────
MIN_PUMP_FREQUENCY = 1.0  # Minimum frequency of the water pump in Hz
MAX_PUMP_FREQUENCY = 5.0  # Maximum frequency of the water pump in Hz
PUMP_ON_TIME = 0.02  # Duration the pump is on during each pulse, in seconds

# ── Emergency Handling ───────────────────────────────
EMERGENCY_STOP_TIMER = 600000  # Time after emergency stop triggered until system reboot, in ms
# Note that this needs more thought and could be DANGEROUS and/or could damage your heater. The
# reason I included it is that sometimes things like gelled up diesel killing a fuel pump is better than
# thousands of dollars of water damage due to busted pipes or dead pets due to the cold.
# Obviously, if you hit an ESTOP, something has gone pretty wrong, or something is misconfigured,
# or my code sucks.
# Again, use your judgement and critical thinking skills and I accept NO liability
# if your shit burns down, and/or worse.
# On a personal note, if you have pets in your caravan/van/RV/etc, get a temp sensor that can
# text you/alert you if something goes wrong. Something like an SMS/Text device would be best
# as you don't have to rely on an Internet of Shit device and their servers/app and if you want
# to be really safe, get a standalone heater, like propane, with a thermostat set to 50F or something.
# Existing RVs with propane furnaces make this easy, just set a low thermostat temp as a backup.
# Don't think that because it worked the last 100 times that the one time you rely on it, it
# won't break, especially for some DIY'd electronics and some code you found on GitHub.


# ┌─────────────────────┐
# │ Startup Settings    │
# └─────────────────────┘
STARTUP_TIME_LIMIT = 300  # Maximum time allowed for startup, in seconds.
GLOW_PLUG_HEAT_UP_TIME = 60  # Time for the glow plug to heat up, in seconds.
INITIAL_FAN_SPEED_PERCENTAGE = 20  # Initial fan speed as a percentage of the maximum speed.
# Note that the pump will be pulsed at MIN_PUMP_FREQUENCY also for the duration of initial startup.
# So the default here is 1hz/20% fan speed

# ┌─────────────────────┐
# │ Shutdown Settings   │
# └─────────────────────┘
SHUTDOWN_TIME_LIMIT = 300  # Maximum time allowed for shutdown, in seconds Exceeding this puts us in an EMERGENCY state.
COOLDOWN_MIN_TIME = 30  # Minimum time for the system to cool down, in seconds, regardless of temperature.
EXHAUST_SHUTDOWN_TEMP = 40.0  # Temperature at which we consider the heater cooled down in C.

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
MIN_TEMP_DELTA = 2.0

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

# Note: Be cautious when using ESP32 strapping pins for your components.
# Strapping pins are: GPIO 0, 2, 4, 5, 12, 15.

# ── Fuel Control ───────────────────────
# Strapping Pin: GPIO 5
FUEL_PIN = machine.Pin(5, machine.Pin.OUT)
FUEL_PIN.off()  # Initialize to OFF

# ── Air Control ────────────────────────
AIR_PIN = machine.Pin(23, machine.Pin.OUT)
air_pwm = machine.PWM(AIR_PIN)
air_pwm.freq(1000)
air_pwm.duty(0)  # Initialize to OFF

# ── Glow Plug Control ──────────────────
GLOW_PIN = machine.Pin(21, machine.Pin.OUT)
GLOW_PIN.off()  # Initialize to OFF

# ── Water Control ──────────────────────
if IS_WATER_HEATER:
    WATER_PIN = machine.Pin(19, machine.Pin.OUT)
    WATER_PIN.off()  # Initialize to OFF

if HAS_SECOND_PUMP:
    WATER_SECONDARY_PIN = machine.Pin(18, machine.Pin.OUT)
    WATER_SECONDARY_PIN.off()  # Initialize to OFF

# ── Fan RPM Sensor ─────────────────────
if FAN_RPM_SENSOR:
    FAN_RPM_PIN = machine.Pin(22, machine.Pin.IN, machine.Pin.PULL_UP)

# ── Switch Control ─────────────────────
SWITCH_PIN = machine.Pin(33, machine.Pin.IN, machine.Pin.PULL_UP)

# ── ADC for Temp Sensor ────────────────
OUTPUT_TEMP_ADC = machine.ADC(machine.Pin(32))
OUTPUT_TEMP_ADC.atten(machine.ADC.ATTN_11DB)

EXHAUST_TEMP_ADC = machine.ADC(machine.Pin(34))
EXHAUST_TEMP_ADC.atten(machine.ADC.ATTN_11DB)
