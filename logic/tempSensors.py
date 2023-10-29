import math
import config

# Predefined R0, and T0 values for common thermistors
common_thermistors = {
    'NTC_10k': {'R0': 10000, 'T0': 298.15},
    'NTC_50k': {'R0': 50000, 'T0': 298.15},
    'NTC_100k': {'R0': 100000, 'T0': 298.15},
    'PTC_500': {'R0': 500, 'T0': 298.15},
    'PTC_1k': {'R0': 1000, 'T0': 298.15},
    'PTC_2.3k': {'R0': 2300, 'T0': 298.15},
}


def log(message, level=1):
    if config.LOG_LEVEL >= level:
        print(f"[Sensor] {message}")


def read_temp(analog_value, sensor_type, sensor_beta):
    try:
        if analog_value == 4095:
            log("Warning: ADC max value reached, can't calculate resistance")
            return 999

        resistance = 10000 * (analog_value / (4095 - analog_value))
        params = common_thermistors.get(sensor_type, {})

        if not params:
            log("Invalid sensor type specified")
            return 999

        R0 = params['R0']
        T0 = params['T0']
        BETA = sensor_beta

        temperature_k = 1 / (
                math.log(resistance / R0) / BETA + 1 / T0
        ) if 'NTC' in sensor_type else 1 / (
                1 / T0 + (1 / BETA) * math.log(resistance / R0)
        )

        return temperature_k - 273.15
    except Exception as e:
        log(f"An error occurred while reading the temperature sensor: {e}")
        return 999


ot = 20


def read_output_temp():
    global ot
    if config.IS_SIMULATION:
        ot = ot + 1
        return min(ot, 50)
    else:
        return read_temp(
            config.OUTPUT_TEMP_ADC.read(),
            config.OUTPUT_SENSOR_TYPE,
            config.OUTPUT_SENSOR_BETA
        )


et = 20


def read_exhaust_temp():
    global et
    if config.IS_SIMULATION:
        et = et + 1
        return min(et, 119)
    else:
        return read_temp(
            config.EXHAUST_TEMP_ADC.read(),
            config.EXHAUST_SENSOR_TYPE,
            config.EXHAUST_SENSOR_BETA
        )
