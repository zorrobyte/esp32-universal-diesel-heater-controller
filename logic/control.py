import config


def log(message, level=1):
    if config.LOG_LEVEL >= level:
        print(f"[Control] {message}")


def control_air_and_fuel(output_temp, exhaust_temp):
    log("Performing air and fuel control...")

    # TODO: IMPLEMENT FLAME OUT BASED ON exhaust_temp
    max_delta = config.CONTROL_MAX_DELTA  # Moved to config

    delta = config.TARGET_TEMP - output_temp
    fan_speed_percentage = min(max((delta / max_delta) * 100, config.MIN_FAN_PERCENTAGE), config.MAX_FAN_PERCENTAGE)
    fan_duty = int((fan_speed_percentage / 100) * config.FAN_MAX_DUTY)  # Use max duty from config
    config.pump_frequency = min(max((delta / max_delta) * config.MAX_PUMP_FREQUENCY, config.MIN_PUMP_FREQUENCY),
                                config.MAX_PUMP_FREQUENCY)

    config.air_pwm.duty(fan_duty)
    log(f"Fan speed set to {fan_speed_percentage}%")

    if config.IS_WATER_HEATER:
        config.WATER_PIN.on()
        log("Water heating enabled.")

    if config.HAS_SECOND_PUMP:
        config.WATER_SECONDARY_PIN.on()
        log("Secondary water pump enabled.")

    config.GLOW_PIN.off()
    log("Glow pin turned off.")
