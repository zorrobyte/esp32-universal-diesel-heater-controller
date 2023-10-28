import config


def emergency_stop(reason):
    while True:
        config.current_state = 'EMERGENCY_STOP'
        config.GLOW_PIN.off()
        config.FUEL_PIN.off()
        config.air_pwm.duty(1023)
        config.pump_frequency = 0
        if config.IS_WATER_HEATER:
            config.WATER_PIN.on()
        if config.HAS_SECOND_PUMP:
            config.WATER_SECONDARY_PIN.on()
        print(f"Emergency stop triggered due to {reason}. Please reboot to continue.")
