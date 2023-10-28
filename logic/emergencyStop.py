import config
from machine import Timer, reset


def log(message, level=1):
    if config.LOG_LEVEL >= level:
        print(f"[Emergency Stop] {message}")


def turn_off_pumps(timer):
    config.air_pwm.duty(config.FAN_MAX_DUTY)
    log("Air pump turned off after 10 minutes.")

    if config.IS_WATER_HEATER:
        config.WATER_PIN.on()
        log("Water pump turned on after 10 minutes.")

    if config.HAS_SECOND_PUMP:
        config.WATER_SECONDARY_PIN.on()
        log("Secondary water pump turned on after 10 minutes.")

    timer.deinit()  # Stop the timer
    log("Performing hard reset...")
    reset()  # Perform a hard reset


def emergency_stop(reason):
    log(f"Triggered due to {reason}. Initiating emergency stop sequence.")

    # Create a timer that will call `turn_off_pumps` after 10 minutes
    pump_timer = Timer(-1)
    pump_timer.init(period=config.EMERGENCY_STOP_TIMER, mode=Timer.ONE_SHOT, callback=turn_off_pumps)

    while True:
        config.current_state = 'EMERGENCY_STOP'
        config.GLOW_PIN.off()
        config.FUEL_PIN.off()
        config.pump_frequency = 0
        log("All pins and frequencies set to safe states. Please reboot to continue.")
