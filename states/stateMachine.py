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
from states import startup, shutdown, control


def log(message, level=2):
    if config.LOG_LEVEL >= level:
        print(message)


def handle_state(current_state, switch_value, exhaust_temp, output_temp):
    emergency_reason = None

    # When we are in OFF and the switch is OFF, we stay in OFF
    if current_state == 'OFF':
        if switch_value == 1:
            config.startup_attempts = 0
            return 'OFF', None
        else:
            return 'STARTING', None

    # When starting is successful, we transition into RUNNING
    if current_state == 'STARTING':
        startup.start_up()
        if config.startup_successful:
            config.startup_attempts = 0
            return 'RUNNING', None
        else:
            config.startup_attempts += 1
            if config.startup_attempts >= config.FAILURE_STATE_RETRIES:
                shutdown.shut_down()
                return 'FAILURE', None
            return 'STARTING', None

    if current_state == 'RUNNING':
        if output_temp > config.TARGET_TEMP + 2:
            shutdown.shut_down()
            return 'STANDBY', None
        elif switch_value == 1:
            config.startup_attempts = 0
            shutdown.shut_down()
            return 'OFF', None
        else:
            flame_status = control.control_air_and_fuel(output_temp, exhaust_temp)
            if flame_status == "FLAME_OUT":
                shutdown.shut_down()
                config.startup_attempts += 1
                return 'STARTING', None
            return 'RUNNING', None

    # When in STANDBY and the temps drops 10C under the set state, we transition from STANDBY to STARTING, then RUNNING
    if current_state == 'STANDBY':
        if output_temp < config.TARGET_TEMP - 2 and switch_value == 0:
            return 'STARTING', None
        elif switch_value == 1:
            config.startup_attempts = 0
            return 'OFF', None
        return 'STANDBY', None

    # When in FAILURE, the user can switch off and back on to start over
    if current_state == 'FAILURE':
        if switch_value == 1:
            config.startup_attempts = 0
            return 'OFF', None
        return 'FAILURE', None

    return current_state, emergency_reason
