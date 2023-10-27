import config
import math

# Constants for 50k NTC thermistor
BETA_NTC_50k = 3950  # Placeholder value; you should calibrate this for more accuracy
R0_NTC_50k = 50000.0  # 50k ohms
T0_NTC_50k = 298.15  # 25C in Kelvin


def read_output_temp():
    try:
        analog_value = config.OUTPUT_TEMP_ADC.read()
        resistance = 1 / (4095.0 / analog_value - 1)

        # Calculate temperature using the simplified B parameter equation for NTC
        temperature_k = 1 / (math.log(resistance / R0_NTC_50k) / BETA_NTC_50k + 1 / T0_NTC_50k)

        # Convert temperature to Celsius
        celsius = temperature_k - 273.15
        if config.IS_SIMULATION:
            if config.current_state == 'STARTING':
                return 10
            else:
                return 60
        else:
            return celsius
    except Exception as e:
        print("An error occurred while reading the output temperature sensor:", str(e))
        return 999


# Constants for 1K PTC thermistor (HCalory Coolant Heater)
BETA_PTC_1K = 3000  # Placeholder value; you should calibrate this for more accuracy
R0_PTC_1K = 1000.0  # 1k ohms
T0_PTC_1K = 298.15  # 25C in Kelvin


def read_exhaust_temp():
    try:
        analog_value = config.EXHAUST_TEMP_ADC.read()
        resistance = 1 / (4095.0 / analog_value - 1)

        # Calculate temperature using the simplified B parameter equation for PTC
        temperature_k = 1 / (1 / T0_PTC_1K + (1 / BETA_PTC_1K) * math.log(resistance / R0_PTC_1K))

        # Convert temperature to Celsius
        celsius = temperature_k - 273.15
        if config.IS_SIMULATION:
            return 60
        else:
            return celsius
    except Exception as e:
        print("An error occurred while reading the exhaust temperature sensor:", str(e))
        return 999
