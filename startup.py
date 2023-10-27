import config
import time
import shutdown
import tempSensors


def start_up():
    print("Starting Up")
    fan_speed_percentage = 20  # Initial fan speed
    fan_duty = int((fan_speed_percentage / 100) * 1023)
    config.air_pwm.duty(fan_duty)
    print(f"Fan: {fan_speed_percentage}%")
    config.GLOW_PIN.on()
    if config.IS_WATER_HEATER:
        config.WATER_PIN.on()
    if config.HAS_SECOND_PUMP:
        config.WATER_SECONDARY_PIN.on()
    print("Glow plug: On")
    print("Wait 60 seconds for glow plug to heat up")
    time.sleep(60)  # TODO Find actual delay
    initial_exhaust_temp = tempSensors.read_exhaust_temp()
    print(f"Initial Exhaust Temp: {initial_exhaust_temp}°C")
    config.pump_frequency = 1  # Initial pump frequency
    print(f"Fuel Pump: {config.pump_frequency} Hz")

    # Initially assume startup will fail
    config.startup_successful = False

    for step in range(1, 6):  # 5 steps
        exhaust_temps = []

        # Record exhaust temperature over the next 20 seconds
        for _ in range(20):
            time.sleep(1)  # Wait for 1 second
            exhaust_temps.append(tempSensors.read_exhaust_temp())

        avg_exhaust_temp = sum(exhaust_temps) / len(exhaust_temps)
        print(f"Average Exhaust Temp at step {step}: {avg_exhaust_temp}°C")

        if avg_exhaust_temp > initial_exhaust_temp:
            # Increase in temperature, increase fan and fuel frequency
            fan_speed_percentage += 20
            if fan_speed_percentage > 100:
                fan_speed_percentage = 100
            fan_duty = int((fan_speed_percentage / 100) * 1023)
            config.air_pwm.duty(fan_duty)

            config.pump_frequency += 1
            if config.pump_frequency > 5:
                config.pump_frequency = 5

            print(f"Step {step} successful. Increasing Fan to {fan_speed_percentage}% and Fuel Pump to {config.pump_frequency} Hz")

            # Update the initial_exhaust_temp for next comparison
            initial_exhaust_temp = avg_exhaust_temp
        else:
            # Temperature not increasing or decreasing, shut down
            print("Temperature not rising as expected. Stopping fueling.")
            shutdown.shut_down()
            config.startup_attempts += 1  # Increment the failed attempts counter
            return

    print("Startup Procedure Completed")
    config.startup_successful = True  # Set the flag to true as startup was successful
    config.startup_attempts = 0  # Reset the failed attempts counter
