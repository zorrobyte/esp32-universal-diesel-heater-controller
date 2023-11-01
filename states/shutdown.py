"""
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
"""

import config
import utime
from lib import helpers


def log(message, level=2):
    if config.LOG_LEVEL >= level:
        print(f"[Shutdown] {message}")


def shut_down():
    log("Shutting Down")
    step = 0
    config.current_state = 'STOPPING'
    cooldown_start_time = None
    shutdown_start_time = utime.time()

    while True:
        config.heartbeat = utime.ticks_ms()
        config.exhaust_temp = config.exhaust_temp
        if utime.time() - shutdown_start_time > config.SHUTDOWN_TIME_LIMIT:
            log("Shutdown took too long, triggering emergency stop.")
            return

        if step == 0:
            log("Stopping fuel supply...")
            config.pump_frequency = 0
            step += 1

        elif step == 1:
            if cooldown_start_time is None:
                log("Activating glow plug and fan for purging and cooling...")
                helpers.set_fan_percentage(config.MAX_FAN_PERCENTAGE)
                config.GLOW_PIN.on()
                cooldown_start_time = utime.time()

            current_exhaust_temp = config.exhaust_temp
            elapsed_time = utime.time() - cooldown_start_time

            log(
                f"Cooling down... Elapsed Time: {elapsed_time}s, Target Exhaust Temp: {config.EXHAUST_SHUTDOWN_TEMP}C, Current Exhaust Temp: {current_exhaust_temp}C")

            if elapsed_time >= config.COOLDOWN_MIN_TIME and current_exhaust_temp <= config.EXHAUST_SHUTDOWN_TEMP:
                step += 1

        elif step == 2:
            log("Turning off electrical components...")
            helpers.set_fan_percentage(0)
            config.GLOW_PIN.off()
            if config.IS_WATER_HEATER:
                config.WATER_PIN.off()
            if config.HAS_SECOND_PUMP:
                config.WATER_SECONDARY_PIN.off()
            log("Finished Shutting Down")
            break

        utime.sleep(1)
