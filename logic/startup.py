import config
import time
from logic import tempSensors, emergencyStop


def start_up():
    step = 0
    initial_exhaust_temp = None
    fan_speed_percentage = 20
    config.pump_frequency = 1
    glow_plug_heat_time = 0
    exhaust_check_time = 0
    exhaust_temps = []
    avg_exhaust_temp = None  # Initialize to None

    # Startup time limit (10 minutes)
    startup_start_time = time.time()
    startup_time_limit = 600  # 10 minutes in seconds

    while True:
        config.heartbeat = time.time()

        # Check if the startup process is taking too long
        if time.time() - startup_start_time > startup_time_limit:
            emergencyStop.emergency_stop("Startup took too long")
            return

        if step == 0:
            print("Starting up...")
            initial_exhaust_temp = tempSensors.read_exhaust_temp()
            fan_duty = int((fan_speed_percentage / 100) * 1023)
            config.air_pwm.duty(fan_duty)
            config.GLOW_PIN.on()
            glow_plug_heat_time = time.time()

            step += 1

        elif step == 1:
            print("Heating glow plug...")
            # If the initial temperature is below freezing, allow more time for the glow plug to heat
            glow_plug_target_time = 30 if initial_exhaust_temp >= 0 else 60
            if time.time() - glow_plug_heat_time >= glow_plug_target_time:
                step += 1

        elif step == 2:
            print("Initializing fuel pump...")
            config.pump_frequency = 1
            exhaust_check_time = time.time()
            step += 1

        elif step == 3:
            print("Checking exhaust temperature...")
            if time.time() - exhaust_check_time < 20:
                exhaust_temps.append(tempSensors.read_exhaust_temp())
            else:
                avg_exhaust_temp = sum(exhaust_temps) / len(exhaust_temps)
                print(f"Average Exhaust Temp: {avg_exhaust_temp}°C")

                # Dynamic adjustment of min_temp_rise based on current average temperature
                min_temp_rise = 5.0 if avg_exhaust_temp < 50 else 3.0

                if avg_exhaust_temp > initial_exhaust_temp + min_temp_rise:
                    fan_speed_percentage = min(fan_speed_percentage + 20, 100)
                    fan_duty = int((fan_speed_percentage / 100) * 1023)
                    config.air_pwm.duty(fan_duty)
                    config.pump_frequency = min(config.pump_frequency + 1, 5)
                    initial_exhaust_temp = avg_exhaust_temp
                    exhaust_temps = []
                    exhaust_check_time = time.time()
                else:
                    print("Temperature not rising as expected. Stopping fueling.")
                    config.current_state = 'STOPPING'
                    config.startup_attempts += 1
                    return

        elif step == 4:
            if avg_exhaust_temp and avg_exhaust_temp >= 150:
                print("Startup Procedure Completed")
                config.startup_successful = True
                config.startup_attempts = 0
                break
            else:
                print(f"Startup failed, exhaust temperature is too low: {avg_exhaust_temp}°C")
                config.current_state = 'STOPPING'
                config.startup_attempts += 1
                return

        time.sleep(1)
