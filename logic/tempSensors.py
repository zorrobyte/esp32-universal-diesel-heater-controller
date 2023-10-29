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


# Global variables for simulation
simulated_output_temp = 20  # Simulated output temperature
simulated_exhaust_temp = 20  # Simulated exhaust temperature
output_temp_ramp_direction = 1  # 1 for ramping up, -1 for ramping down


# Read simulated output temperature
def read_output_temp():
    global simulated_output_temp, output_temp_ramp_direction
    if config.IS_SIMULATION:
        if config.current_state == 'RUNNING':
            if simulated_output_temp >= 80:
                output_temp_ramp_direction = -1  # Change direction to ramp down
            elif simulated_output_temp <= 50:
                output_temp_ramp_direction = 1  # Change direction to ramp up

            simulated_output_temp += output_temp_ramp_direction  # Increment or decrement based on direction
        else:
            simulated_output_temp = 20  # Reset to 20 for other states
        return simulated_output_temp
    else:
        return read_temp(
            config.OUTPUT_TEMP_ADC.read(),
            config.OUTPUT_SENSOR_TYPE,
            config.OUTPUT_SENSOR_BETA
        )


# Read simulated exhaust temperature
def read_exhaust_temp():
    global simulated_exhaust_temp
    if config.IS_SIMULATION:
        if config.current_state == 'STARTING':
            simulated_exhaust_temp = min(simulated_exhaust_temp + 1, 120)
        elif config.current_state == 'RUNNING':
            simulated_exhaust_temp = 120
        elif config.current_state == 'STOPPING':
            simulated_exhaust_temp = max(simulated_exhaust_temp - 1, 20)
        else:
            simulated_exhaust_temp = 20  # Reset to 20 for other states
        return simulated_exhaust_temp
    else:
        return read_temp(
            config.EXHAUST_TEMP_ADC.read(),
            config.EXHAUST_SENSOR_TYPE,
            config.EXHAUST_SENSOR_BETA
        )
