# ┌─────────────────────┐
# │  General Settings   │
# └─────────────────────┘
USE_WIFI = False  # Use Wi-Fi (not functional yet)
USE_MQTT = False  # Use MQTT (not functional yet)
IS_WATER_HEATER = True  # True if controlling a Water/Coolant Heater
HAS_SECOND_PUMP = True  # True if driving a second water pump
IS_SIMULATION = True  # True to run in simulation mode

# ┌─────────────────────┐
# │  Safety Limits      │
# └─────────────────────┘
EXHAUST_SAFE_TEMP = 100  # Max safe temp for exhaust (°C)
OUTPUT_SAFE_TEMP = 90  # Max safe temp for output (°C)
EXHAUST_SHUTDOWN_TEMP = 40.0  # Exhaust shutdown temp (°C)

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
# │  Device Control     │
# └─────────────────────┘
TARGET_TEMP = 60.0  # Target temp (°C)
MIN_FAN_PERCENTAGE = 20  # Min fan speed (%)
MAX_FAN_PERCENTAGE = 100  # Max fan speed (%)
MIN_PUMP_FREQUENCY = 1  # Min pump freq (Hz)
MAX_PUMP_FREQUENCY = 5  # Max pump freq (Hz)
PUMP_ON_TIME = 0.02  # Pump on time per pulse (s)
