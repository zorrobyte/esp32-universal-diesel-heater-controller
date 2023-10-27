import config
import time
from logic import tempSensors

def shut_down():
    print("Shutting Down")
    config.pump_frequency = 0  # Stop the fuel pump
    if config.IS_WATER_HEATER:
        config.WATER_PIN.on()  # If it's a water heater, turn the water mosfet on
    if config.HAS_SECOND_PUMP:
        config.WATER_SECONDARY_PIN.on()

    # If startup was not successful, run the fan at 100% for 30 seconds
    if not config.startup_successful:
        print("Startup failed. Running fan at 100% for 30 seconds to purge.")
        config.air_pwm.duty(1023)  # 100% fan speed
        config.GLOW_PIN.on()  # Glow plug on to help purge
        if config.IS_SIMULATION:
            time.sleep(5)
        else:
            time.sleep(30)  # Run the fan for 30 seconds
        config.GLOW_PIN.off()

    config.air_pwm.duty(1023)  # Set fan to 100% for normal shutdown as well
    config.GLOW_PIN.on()  # Turn on the glow plug

    while tempSensors.read_exhaust_temp() > config.EXHAUST_SHUTDOWN_TEMP:
        config.air_pwm.duty(1023)  # Maintain 100% fan speed
        print("Waiting for cooldown, exhaust temp is:", tempSensors.read_exhaust_temp())
        time.sleep(5)  # Wait for 5 seconds before checking again

    config.air_pwm.duty(0)  # Turn off the fan
    if config.IS_WATER_HEATER:
        config.WATER_PIN.off()  # Turn off the water mosfet if it's a water heater
    if config.HAS_SECOND_PUMP:
        config.WATER_SECONDARY_PIN.off()
    config.GLOW_PIN.off()  # Turn off the glow plug

    print("Finished Shutting Down")
