import config
from logic import startup, shutdown, control, emergencyStop


def log(message, level=2):
    if config.LOG_LEVEL >= level:
        print(message)


def handle_state(current_state, switch_value, exhaust_temp, output_temp):
    emergency_reason = None
    next_state = current_state  # Default to staying in the current state

    # State transition rules
    allowed_transitions = {
        'INIT': ['OFF', 'INIT'],
        'OFF': ['STANDBY', 'STARTING', 'FAILURE', 'OFF'],
        'STARTING': ['RUNNING', 'STOPPING', 'STARTING'],
        'RUNNING': ['STOPPING', 'RUNNING'],
        'STOPPING': ['OFF', 'STANDBY', 'STOPPING'],
        'STANDBY': ['STARTING', 'OFF', 'STANDBY'],
        'FAILURE': ['OFF', 'FAILURE'],
        'EMERGENCY_STOP': ['EMERGENCY_STOP']
    }

    if current_state == 'INIT':
        next_state, emergency_reason = init()

    elif current_state == 'OFF':
        next_state, emergency_reason = off(switch_value)

    elif current_state == 'STARTING':
        next_state, emergency_reason = starting()

    elif current_state == 'RUNNING':
        next_state, emergency_reason = running(switch_value, exhaust_temp, output_temp)

    elif current_state == 'STOPPING':
        next_state, emergency_reason = stopping()

    elif current_state == 'STANDBY':
        next_state, emergency_reason = standby(output_temp, switch_value)

    elif current_state == 'FAILURE':
        next_state, emergency_reason = failure()

    elif current_state == 'EMERGENCY_STOP':
        next_state, emergency_reason = emergency_stop()

    # Enforce allowed transitions
    if next_state not in allowed_transitions.get(current_state, []):
        log(f"Invalid transition from {current_state} to {next_state}. Keeping current state.", level=0)
        next_state = current_state

    if current_state != next_state:
        log(f"Transitioning from {current_state} to {next_state}", level=2)

    return next_state, emergency_reason



def init():
    return 'OFF', None


def off(current_switch_value):
    if current_switch_value == 0:
        if config.output_temp > config.TARGET_TEMP + 10:
            return 'STANDBY', None
        elif config.startup_attempts < 3:
            return 'STARTING', None
        else:
            return 'FAILURE', None
    elif current_switch_value == 1:
        config.startup_attempts = 0
        if config.IS_WATER_HEATER:
            config.WATER_PIN.off()
        if config.HAS_SECOND_PUMP:
            config.WATER_SECONDARY_PIN.off()
        return 'OFF', None


def starting():
    startup.start_up()
    if config.startup_successful:
        return 'RUNNING', None
    else:
        config.startup_attempts += 1
        return 'STOPPING', None


def running(current_switch_value, exhaust_temp, output_temp):
    if current_switch_value == 1:
        return 'STOPPING', None
    elif output_temp > config.TARGET_TEMP + 10:
        return 'STANDBY', None
    else:
        flame_out = control.control_air_and_fuel(output_temp, exhaust_temp)
        if flame_out == "FLAME_OUT":
            log("Flame out detected. Transitioning to OFF state.", level=0)
            config.startup_attempts += 1  # Increment startup attempts as the flame went out
            return 'OFF', None
        return 'RUNNING', None


def stopping():
    shutdown.shut_down()
    return 'OFF', None


def standby(output_temp, current_switch_value):
    if output_temp < config.TARGET_TEMP - 10:
        return 'STARTING', None
    elif current_switch_value == 1:
        return 'OFF', None
    else:
        shutdown.shut_down()
        if config.IS_WATER_HEATER:
            config.WATER_PIN.on()
        if config.HAS_SECOND_PUMP:
            config.WATER_SECONDARY_PIN.on()
        return 'STANDBY', None


def failure():
    print("Max startup attempts reached. Switch off and on to restart.")
    return 'OFF', None


def emergency_stop():
    emergencyStop.emergency_stop(config.emergency_reason)
    return 'EMERGENCY_STOP', config.emergency_reason
