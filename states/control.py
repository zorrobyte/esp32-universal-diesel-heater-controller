import config
from lib import helpers

# Initialize a list to store the last N exhaust temperatures
exhaust_temp_history = []


def log(message, level=1):
    if config.LOG_LEVEL >= level:
        print(f"[Control] {message}")


def calculate_pump_frequency(target_temp, output_temp, max_delta, max_frequency, min_frequency):
    delta = target_temp - output_temp
    pump_frequency = min(max((delta / max_delta) * max_frequency, min_frequency), max_frequency)
    return pump_frequency


def control_air_and_fuel(output_temp, exhaust_temp):
    log("Performing air and fuel control...")

    # Update the exhaust temperature history
    exhaust_temp_history.append(exhaust_temp)

    # Manually enforce maximum length
    while len(exhaust_temp_history) > config.EXHAUST_TEMP_HISTORY_LENGTH:
        exhaust_temp_history.pop(0)

    # Check for decreasing exhaust temperature over the last N readings
    if len(exhaust_temp_history) == config.EXHAUST_TEMP_HISTORY_LENGTH:
        if all(earlier - later > config.MIN_TEMP_DELTA for earlier, later in
               zip(exhaust_temp_history, exhaust_temp_history[1:])):
            log("Flame out detected based on decreasing exhaust temperature. Exiting...", level=0)
            return "FLAME_OUT"

    # Calculate the fan speed percentage based on temperature delta
    delta = config.TARGET_TEMP - output_temp
    config.fan_speed_percentage = min(max((delta / config.CONTROL_MAX_DELTA) * 100, config.MIN_FAN_PERCENTAGE),
                                      config.MAX_FAN_PERCENTAGE)

    # Use the helper function to set the fan speed
    helpers.set_fan_percentage(config.fan_speed_percentage)

    pump_frequency = calculate_pump_frequency(
        config.TARGET_TEMP, output_temp, config.CONTROL_MAX_DELTA,
        config.MAX_PUMP_FREQUENCY, config.MIN_PUMP_FREQUENCY
    )

    # Update global variables
    config.pump_frequency = pump_frequency

    log(f"Fan speed: {config.fan_speed_percentage}%, Pump frequency: {pump_frequency} Hz, Exhaust Temp: {config.exhaust_temp}, Output Temp: {config.output_temp}")

    # Additional hardware controls
    if config.IS_WATER_HEATER:
        config.WATER_PIN.on()

    if config.HAS_SECOND_PUMP:
        config.WATER_SECONDARY_PIN.on()