import config

# Initialize a list to store the last N exhaust temperatures
exhaust_temp_history = []


def log(message, level=1):
    if config.LOG_LEVEL >= level:
        print(f"[Control] {message}")


def calculate_fan_duty(target_temp, output_temp, max_delta, max_duty, min_percentage, max_percentage):
    delta = target_temp - output_temp
    fan_speed_percentage = min(max((delta / max_delta) * 100, min_percentage), max_percentage)
    fan_duty = int((fan_speed_percentage / 100) * max_duty)
    return fan_duty, fan_speed_percentage


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

    fan_duty, fan_speed_percentage = calculate_fan_duty(
        config.TARGET_TEMP, output_temp, config.CONTROL_MAX_DELTA,
        config.FAN_MAX_DUTY, config.MIN_FAN_PERCENTAGE, config.MAX_FAN_PERCENTAGE
    )

    pump_frequency = calculate_pump_frequency(
        config.TARGET_TEMP, output_temp, config.CONTROL_MAX_DELTA,
        config.MAX_PUMP_FREQUENCY, config.MIN_PUMP_FREQUENCY
    )

    # Update global variables
    config.air_pwm.duty(fan_duty)
    config.pump_frequency = pump_frequency

    log(f"Fan speed: {fan_speed_percentage}%, Pump frequency: {pump_frequency} Hz")

    # Additional hardware controls
    if not config.IS_WATER_HEATER:
        config.WATER_PIN.on()
        log("Water heating enabled.")

    if not config.HAS_SECOND_PUMP:
        config.WATER_SECONDARY_PIN.on()
        log("Secondary water pump enabled.")
