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
from machine import Timer, reset


def log(message, level=1):
    if config.LOG_LEVEL >= level:
        print(f"[Emergency Stop] {message}")


def turn_off_pumps(timer):
    config.air_pwm.duty(0)
    log("Fan turned off after 10 minutes.")

    if config.IS_WATER_HEATER:
        config.WATER_PIN.off()
        log("Water pump turned off after 10 minutes.")

    if config.HAS_SECOND_PUMP:
        config.WATER_SECONDARY_PIN.off()
        log("Secondary water pump turned off after 10 minutes.")

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
        if config.IS_WATER_HEATER:
            config.WATER_PIN.on()
        if config.HAS_SECOND_PUMP:
            config.WATER_SECONDARY_PIN.on()
        config.air_pwm.duty(config.FAN_MAX_DUTY)
        config.pump_frequency = 0
        log("All pins and frequencies set to safe states. Please reboot to continue.")
