import config
import math

# Constants for 50k NTC thermistor
BETA_NTC_50k = 3950  # Placeholder value; you should calibrate this for more accuracy
R0_NTC_50k = 50000.0  # 50k ohms
T0_NTC_50k = 298.15  # 25C in Kelvin

simulated_output_temp = 10  # Initial simulated output temperature
output_temp_direction = 1  # 1 for increasing, -1 for decreasing


def read_output_temp():
    global simulated_output_temp, output_temp_direction

    if config.IS_SIMULATION:
        if config.current_state == 'STARTING':
            # Simulate a low temperature during startup
            simulated_output_temp = 10
            return simulated_output_temp
        elif config.current_state == 'RUNNING' or config.current_state == 'STANDBY':
            # Vary the temperature between 50°C and 80°C
            simulated_output_temp += output_temp_direction
            if simulated_output_temp > 80:
                simulated_output_temp = 80
                output_temp_direction = -1  # Start decreasing
            elif simulated_output_temp < 40:
                simulated_output_temp = 40
                output_temp_direction = 1  # Start increasing
            return simulated_output_temp
        else:
            # Return a stable temperature when not in 'STARTING' or 'RUNNING' state
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


# Constants for 1K PTC thermistor (HCalory Coolant Heater)
BETA_PTC_1K = 3000  # Placeholder value; you should calibrate this for more accuracy
R0_PTC_1K = 1000.0  # 1k ohms
T0_PTC_1K = 298.15  # 25C in Kelvin

simulated_exhaust_temp = 10
def read_exhaust_temp():
    global simulated_exhaust_temp
    if config.IS_SIMULATION:
        if config.current_state == 'STARTING':
            # Simulate temperature rising by 1 degree each time function is called
            simulated_exhaust_temp += 1.
            return simulated_exhaust_temp
        elif config.current_state == 'OFF':
            # Reset simulated temperature
            simulated_temp = 10
            return simulated_temp
        else:
            # Return a stable temperature when not in 'STARTING' state
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
