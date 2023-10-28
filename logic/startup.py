import config
import time
from logic import tempSensors, shutdown

def start_up():
    step = 0
    initial_exhaust_temp = None
    fan_speed_percentage = 20
    config.pump_frequency = 1
    glow_plug_heat_time = 0
    exhaust_check_time = 0
    exhaust_temps = []

    while True:
        config.heartbeat = time.time()  # Update heartbeat

        if step == 0:
            print("Starting up...")
            # Initial setup
            initial_exhaust_temp = tempSensors.read_exhaust_temp()
            # Initialize fan and fuel pump
            fan_duty = int((fan_speed_percentage / 100) * 1023)
            config.air_pwm.duty(fan_duty)
            config.GLOW_PIN.on()
            glow_plug_heat_time = time.time()
            step += 1

        elif step == 1:
            print("Heating glow plug...")
            # Check if 30 seconds have passed for the glow plug to heat
            if time.time() - glow_plug_heat_time >= 30:
                step += 1

        elif step == 2:
            print("Initializing fuel pump...")
            # Start fuel pump with initial frequency
            config.pump_frequency = 1
            exhaust_check_time = time.time()
            step += 1

        elif step == 3:
            print("Checking exhaust temperature...")
            # Record exhaust temperature for 20 seconds
            if time.time() - exhaust_check_time < 20:
                exhaust_temps.append(tempSensors.read_exhaust_temp())
            else:
                avg_exhaust_temp = sum(exhaust_temps) / len(exhaust_temps)
                print(f"Average Exhaust Temp: {avg_exhaust_temp}°C")

                if avg_exhaust_temp > initial_exhaust_temp:
                    print("Exhaust temperature rising.")
                    # Increase fan speed and fuel pump frequency
                    fan_speed_percentage = min(fan_speed_percentage + 20, 100)
                    fan_duty = int((fan_speed_percentage / 100) * 1023)
                    config.air_pwm.duty(fan_duty)

                    config.pump_frequency = min(config.pump_frequency + 1, 5)
                    initial_exhaust_temp = avg_exhaust_temp  # Update for the next round
                    exhaust_temps = []  # Clear recorded temperatures
                    exhaust_check_time = time.time()  # Reset the timer
                else:
                    print("Temperature not rising as expected. Stopping fueling.")
                    config.current_state = 'STOPPING'
                    config.startup_attempts += 1  # Increment the failed attempts counter
                    return

        elif step == 4:
            print("Startup Procedure Completed")
            config.startup_successful = True  # Set the flag to true as startup was successful
            config.startup_attempts = 0  # Reset the failed attempts counter
            break

        time.sleep(1)  # Sleep for a short while before the next iteration
