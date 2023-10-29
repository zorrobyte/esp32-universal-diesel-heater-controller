import config
from logic import startup, shutdown, control


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
            if config.startup_attempts >= 3:
                shutdown.shut_down()
                return 'FAILURE', None
            return 'STARTING', None

    if current_state == 'RUNNING':
        if output_temp > config.TARGET_TEMP + 10:
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
        if output_temp < config.TARGET_TEMP - 10 and switch_value == 0:
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
