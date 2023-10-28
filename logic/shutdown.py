import config
import time
from logic import tempSensors, emergencyStop


def shut_down():
    print("Shutting Down")
    step = 0
    cooldown_start_time = None
    shutdown_start_time = time.time()  # Record the time when the shutdown process starts

    while True:
        config.heartbeat = time.time()  # Update heartbeat

        # Check if the shutdown process is taking too long (more than 5 minutes)
        if time.time() - shutdown_start_time > 300:
            emergencyStop.emergency_stop("Shutdown took too long")
            return

        if step == 0:
            print("Stopping fuel supply...")
            config.pump_frequency = 0  # Stop the fuel pump
            step += 1

        elif step == 1:

            if cooldown_start_time is None:
                print("Activating glow plug and fan for purging and cooling...")
                config.air_pwm.duty(1023)  # Run fan at 100% to purge system
                config.GLOW_PIN.on()  # Glow plug on to help purge
                cooldown_start_time = time.time()

            current_exhaust_temp = tempSensors.read_exhaust_temp()
            elapsed_time = time.time() - cooldown_start_time

            print(
                f"Cooling down... Elapsed Time: {elapsed_time}s, Target Exhaust Temp: {config.EXHAUST_SHUTDOWN_TEMP}°C, Current Exhaust Temp: {current_exhaust_temp}°C")

            if elapsed_time >= 30 and current_exhaust_temp <= config.EXHAUST_SHUTDOWN_TEMP:
                step += 1

        elif step == 2:
            print("Turning off electrical components...")
            config.air_pwm.duty(0)  # Turn off the fan
            config.GLOW_PIN.off()  # Turn off the glow plug
            if config.IS_WATER_HEATER:
                config.WATER_PIN.off()  # Turn off the water mosfet if it's a water heater
            if config.HAS_SECOND_PUMP:
                config.WATER_SECONDARY_PIN.off()
            print("Finished Shutting Down")
            break

        time.sleep(1)  # Sleep for a short while before the next iteration
