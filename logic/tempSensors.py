import math
import config


def log(message, level=2):
    if config.LOG_LEVEL >= level:
        print(message)


# Predefined R0, and T0 values for common thermistors
common_thermistors = {
    'NTC_10k': {'R0': 10000, 'T0': 298.15},
    'NTC_50k': {'R0': 50000, 'T0': 298.15},
    'NTC_100k': {'R0': 100000, 'T0': 298.15},
    'PTC_500': {'R0': 500, 'T0': 298.15},
    'PTC_1k': {'R0': 1000, 'T0': 298.15},
    'PTC_2.3k': {'R0': 2300, 'T0': 298.15},
}


def read_temp(analog_value, sensor_type, sensor_beta):
    try:
        if analog_value == 4095:
            log("Warning: ADC max value reached, can't calculate resistance", level=1)
            return 999
        else:
            resistance = 10000 * (analog_value / (4095 - analog_value))

        params = common_thermistors.get(sensor_type)
        if params:
            R0 = params['R0']
            T0 = params['T0']
            BETA = sensor_beta
        else:
            log("Invalid sensor type specified", level=1)
            return 999

        if 'NTC' in sensor_type:
            temperature_k = 1 / (math.log(resistance / R0) / BETA + 1 / T0)
        elif 'PTC' in sensor_type:
            temperature_k = 1 / (1 / T0 + (1 / BETA) * math.log(resistance / R0))
        else:
            log("Invalid sensor type specified", level=1)
            return 999

        celsius = temperature_k - 273.15
        return celsius
    except Exception as e:
        log(f"An error occurred while reading the temperature sensor: {str(e)}", level=1)
        return 999


def read_output_temp():
    analog_value = config.OUTPUT_TEMP_ADC.read()
    return read_temp(analog_value, config.OUTPUT_SENSOR_TYPE, config.OUTPUT_SENSOR_BETA)


def read_exhaust_temp():
    analog_value = config.EXHAUST_TEMP_ADC.read()
    return read_temp(analog_value, config.EXHAUST_SENSOR_TYPE, config.EXHAUST_SENSOR_BETA)
