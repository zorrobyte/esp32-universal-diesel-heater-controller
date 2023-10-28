import config
import time
from logic import tempSensors, emergencyStop


def start_up():
    print("Starting up the diesel parking heater.")
    startup_start_time = time.time()
    startup_time_limit = 600  # 10 minutes in seconds
    exhaust_temps = []  # To store exhaust temperatures for averaging

    # Initialize variables to keep track of time
    last_glow_plug_heat_time = None
    last_exhaust_check_time = None

    # Initialize the system
    fan_duty = int((20 / 100) * 1023)
    config.air_pwm.duty(fan_duty)
    config.GLOW_PIN.on()
    print("System initialized.")

    # Start the process
    while True:
        current_time = time.time()
        config.heartbeat = current_time

        if current_time - startup_start_time > startup_time_limit:
            print("Startup took too long. Triggering emergency stop.")
            emergencyStop.emergency_stop("Startup took too long")
            return

        # Heat the glow plug
        if last_glow_plug_heat_time is None:
            last_glow_plug_heat_time = current_time
            print("Heating the glow plug.")
        elif current_time - last_glow_plug_heat_time < 30:
            continue

        # Initialize the fuel pump
        print("Initializing the fuel pump.")
        config.pump_frequency = 1

        # Check exhaust temperature and adjust if needed
        if last_exhaust_check_time is None:
            last_exhaust_check_time = current_time
        elif current_time - last_exhaust_check_time < 20:
            exhaust_temps.append(tempSensors.read_exhaust_temp())
        else:
            avg_exhaust_temp = sum(exhaust_temps) / len(exhaust_temps)
            print(f"Average exhaust temperature: {avg_exhaust_temp}°C.")
            min_temp_rise = 5.0 if avg_exhaust_temp < 50 else 3.0

            if avg_exhaust_temp > min_temp_rise:
                fan_speed_percentage = 40
                fan_duty = int((fan_speed_percentage / 100) * 1023)
                config.air_pwm.duty(fan_duty)
                config.pump_frequency = min(config.pump_frequency + 1, 5)
                print("Adjusting fan speed and pump frequency.")
                exhaust_temps = []  # Reset the list
                last_exhaust_check_time = current_time

            if avg_exhaust_temp >= 150:
                print("Startup successful.")
                config.startup_successful = True
                config.startup_attempts = 0
                break

            if avg_exhaust_temp < min_temp_rise:
                print("Temperature not rising as expected. Stopping.")
                config.current_state = 'STOPPING'
                config.startup_attempts += 1
                return
