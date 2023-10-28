import config
import main
from machine import Timer, reset


def turn_off_pumps(timer):
    config.air_pwm.duty(1023)
    if config.IS_WATER_HEATER:
        config.WATER_PIN.on()
    if config.HAS_SECOND_PUMP:
        config.WATER_SECONDARY_PIN.on()
    print("Air and water pumps turned off after 10 minutes.")
    timer.deinit()  # Stop the timer
    print("Performing hard reset...")
    reset()  # Perform a hard reset


def emergency_stop(reason):
    # Create a timer that will call `turn_off_pumps` after 10 minutes
    pump_timer = Timer(-1)
    pump_timer.init(period=600000, mode=Timer.ONE_SHOT, callback=turn_off_pumps)

    while True:
        main.wdt.feed()
        config.current_state = 'EMERGENCY_STOP'
        config.GLOW_PIN.off()
        config.FUEL_PIN.off()
        config.pump_frequency = 0
        print(f"Emergency stop triggered due to {reason}. Please reboot to continue.")
