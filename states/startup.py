####################################################################
#                          WARNING                                 #
####################################################################
# This code is provided "AS IS" without warranty of any kind.      #
# Use of this code in any form acknowledges your acceptance of     #
# these terms.                                                     #
#                                                                  #
# This code has NOT been tested in real-world scenarios.           #
# Improper usage, lack of understanding, or any combination        #
# thereof can result in significant property damage, injury,       #
# loss of life, or worse.                                          #
# Specifically, this code is related to controlling heating        #
# elements and systems, and there's a very real risk that it       #
# can BURN YOUR SHIT DOWN.                                         #
#                                                                  #
# By using, distributing, or even reading this code, you agree     #
# to assume all responsibility and risk associated with it.        #
# The author(s), contributors, and distributors of this code       #
# will NOT be held liable for any damages, injuries, or other      #
# consequences you may face as a result of using or attempting     #
# to use this code.                                                #
#                                                                  #
# Always approach such systems with caution. Ensure you understand #
# the code, the systems involved, and the potential risks.         #
# If you're unsure, DO NOT use the code.                           #
#                                                                  #
# Stay safe and think before you act.                              #
####################################################################

import hardwareConfig as config
import utime
import main
from lib import helpers


def state_message(state, message):
    print(f"[Current Startup Procedure: - {state}] {message}")


def start_up():
    state = "WARMING_GLOW_PLUG"
    step = 1
    exhaust_temps = []
    initial_exhaust_temp = None
    last_time_checked = utime.time()
    if config.IS_SIMULATION:
        glow_plug_heat_up_end_time = last_time_checked + 1
    else:
        glow_plug_heat_up_end_time = last_time_checked + 60
    startup_start_time = last_time_checked
    startup_time_limit = 300  # 5 minutes in seconds

    while True:
        current_time = utime.time()
        config.heartbeat = utime.ticks_ms()
        main.wdt.feed()

        if current_time - startup_start_time > startup_time_limit:
            state_message("TIMEOUT", "Startup took too long. Changing state to STOPPING.")
            config.startup_successful = False
            return

        if state == "WARMING_GLOW_PLUG":
            state_message(state, "Initializing system...")
            config.startup_successful = False  # Assume startup will fail
            initial_exhaust_temp = config.exhaust_temp
            if initial_exhaust_temp > 100:
                state_message(state, "Initial exhaust temperature too high. Stopping...")
                config.startup_successful = False
                return
            helpers.set_fan_percentage(config.FAN_START_PERCENTAGE)
            config.GLOW_PIN.on()
            if config.IS_WATER_HEATER:
                config.WATER_PIN.on()
            if config.HAS_SECOND_PUMP:
                config.WATER_SECONDARY_PIN.on()
            state_message(state, f"Fan: {config.fan_speed_percentage}%, Glow plug: On")
            state = "INITIAL_FUELING"

        elif state == "INITIAL_FUELING":
            # state_message(state, "Waiting for glow plug to heat up...")
            if current_time >= glow_plug_heat_up_end_time:
                config.pump_frequency = config.MIN_PUMP_FREQUENCY
                state_message(state, f"Fuel Pump: {config.pump_frequency} Hz")
                state = "RAMPING_UP"
                last_time_checked = current_time
                exhaust_temps = []

        elif state == "RAMPING_UP":
            if current_time - last_time_checked >= 1:
                last_time_checked = current_time
                exhaust_temps.append(config.exhaust_temp)

                if len(exhaust_temps) >= 20:
                    avg_exhaust_temp = sum(exhaust_temps) / len(exhaust_temps)
                    state_message(state, f"Average Exhaust Temp at step {step}: {avg_exhaust_temp}C")

                    if avg_exhaust_temp >= 100:
                        state_message("COMPLETED", "Reached target exhaust temperature. Startup Procedure Completed.")
                        config.startup_successful = True
                        config.startup_attempts = 0
                        config.GLOW_PIN.off()
                        return

                    elif initial_exhaust_temp + 5 < avg_exhaust_temp:
                        config.fan_speed_percentage = min(config.fan_speed_percentage + 20, 100)
                        helpers.set_fan_percentage(config.fan_speed_percentage)
                        config.pump_frequency = min(config.pump_frequency + 1, config.MAX_PUMP_FREQUENCY)
                        state_message(state,
                                      f"Step {step} successful. Fan: {config.fan_speed_percentage}%, Fuel Pump: {config.pump_frequency} Hz")
                        initial_exhaust_temp = avg_exhaust_temp
                        step += 1

                        if step > 5:
                            state_message("COMPLETED", "Startup Procedure Completed")
                            config.startup_successful = True
                            config.startup_attempts = 0
                            return

                        exhaust_temps = []
                    else:
                        state_message(state, "Temperature not rising as expected. Changing state to STOPPING.")
                        config.current_state = 'STOPPING'
                        config.startup_attempts += 1
                        return
