import config


def control_air_and_fuel(output_temp, exhaust_temp):
    #  TODO IMPLEMENT FLAME OUT BASED ON exhaust_temp
    max_delta = 20

    delta = config.TARGET_TEMP - output_temp
    fan_speed_percentage = min(max((delta / max_delta) * 100, config.MIN_FAN_PERCENTAGE), config.MAX_FAN_PERCENTAGE)
    fan_duty = int((fan_speed_percentage / 100) * 1023)
    config.pump_frequency = min(max((delta / max_delta) * config.MAX_PUMP_FREQUENCY, config.MIN_PUMP_FREQUENCY),
                                config.MAX_PUMP_FREQUENCY)

    config.air_pwm.duty(fan_duty)
    if config.IS_WATER_HEATER:
        config.WATER_PIN.on()
    if config.HAS_SECOND_PUMP:
        config.WATER_SECONDARY_PIN.on()
    config.GLOW_PIN.off()
