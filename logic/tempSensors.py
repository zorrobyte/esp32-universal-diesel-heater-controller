import config
import math

# Constants for 50k NTC thermistor
BETA_NTC_50k = 3950  # Placeholder value; you should calibrate this for more accuracy
R0_NTC_50k = 50000.0  # 50k ohms
T0_NTC_50k = 298.15  # 25C in Kelvin

simulated_output_temp = 10  # Initial simulated output temperature
simulated_temp_direction = 1  # 1 for increasing, -1 for decreasing


def read_output_temp():
    global simulated_output_temp, simulated_temp_direction

    if config.IS_SIMULATION:
        if config.current_state == 'STOPPING':
            simulated_output_temp = max(20, simulated_output_temp - 1)
            return simulated_output_temp
        elif config.current_state == 'STARTING':
            simulated_output_temp = 10
            return simulated_output_temp
        elif config.current_state == 'RUNNING' or config.current_state == 'STANDBY':
            simulated_output_temp += simulated_temp_direction
            if simulated_output_temp > 80:
                simulated_output_temp = 80
                simulated_temp_direction = -1  # Start decreasing
            elif simulated_output_temp < 40:
                simulated_output_temp = 40
                simulated_temp_direction = 1  # Start increasing
            return simulated_output_temp
        else:
            return 60
    else:
        try:
            analog_value = config.OUTPUT_TEMP_ADC.read()
            resistance = 1 / (4095.0 / analog_value - 1)
            # Calculate temperature using the simplified B parameter equation for NTC
            temperature_k = 1 / (math.log(resistance / R0_NTC_50k) / BETA_NTC_50k + 1 / T0_NTC_50k)
            # Convert temperature to Celsius
            celsius = temperature_k - 273.15
            return celsius
        except Exception as e:
            print("An error occurred while reading the output temperature sensor:", str(e))
            return 999


# Constants for 1K PTC thermistor
BETA_PTC_1K = 3000  # Placeholder value; you should calibrate this for more accuracy
R0_PTC_1K = 1000.0  # 1k ohms
T0_PTC_1K = 298.15  # 25C in Kelvin

simulated_exhaust_temp = 10  # Initial simulated exhaust temperature
simulated_stopping_state = True


def read_exhaust_temp():
    global simulated_exhaust_temp, simulated_stopping_state

    if config.IS_SIMULATION:
        if config.current_state == 'STOPPING':
            if simulated_stopping_state:
                simulated_exhaust_temp = 120  # Initialize to 120°C when first entering 'STOPPING' state
                simulated_stopping_state = False  # Reset the flag
            simulated_exhaust_temp = max(20, simulated_exhaust_temp - 1)
            return simulated_exhaust_temp
        elif config.current_state == 'STARTING':
            simulated_stopping_state = True  # Reset the flag for the next 'STOPPING' state
            simulated_exhaust_temp += 0.1
            return simulated_exhaust_temp
        elif config.current_state == 'OFF':
            simulated_stopping_state = True  # Reset the flag for the next 'STOPPING' state
            simulated_exhaust_temp = 10
            return simulated_exhaust_temp
        else:
            return 10
    else:
        try:
            analog_value = config.EXHAUST_TEMP_ADC.read()
            resistance = 1 / (4095.0 / analog_value - 1)
            # Calculate temperature using the simplified B parameter equation for PTC
            temperature_k = 1 / (1 / T0_PTC_1K + (1 / BETA_PTC_1K) * math.log(resistance / R0_PTC_1K))
            # Convert temperature to Celsius
            celsius = temperature_k - 273.15
            return celsius
        except Exception as e:
            print("An error occurred while reading the exhaust temperature sensor:", str(e))
            return 999
