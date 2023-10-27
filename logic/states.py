import config
import main
from logic import startup, shutdown, control, emergencyStop


def init():
    reset_reason = main.get_reset_reason()
    if reset_reason == 'Some Specific Reason':
        return 'EMERGENCY_STOP', "Unusual Reset Reason"
    else:
        return 'OFF', None


def off(current_switch_value):
    if current_switch_value == 0:
        if config.output_temp > config.TARGET_TEMP + 10:
            return 'STANDBY'
        elif config.startup_attempts < 3:
            return 'STARTING'
        else:
            return 'FAILURE'
    elif current_switch_value == 1:
        config.startup_attempts = 0
        if config.IS_WATER_HEATER:
            config.WATER_PIN.off()
        if config.HAS_SECOND_PUMP:
            config.WATER_SECONDARY_PIN.off()
        return 'OFF'


def starting():
    startup.start_up()
    if config.startup_successful:
        return 'RUNNING'
    else:
        config.startup_attempts += 1
        return 'OFF'


def running(current_switch_value, exhaust_temp, output_temp):
    if current_switch_value == 1:
        return 'STOPPING', None
    elif exhaust_temp > config.EXHAUST_SAFE_TEMP:
        return 'EMERGENCY_STOP', "High Exhaust Temperature"
    elif output_temp > config.OUTPUT_SAFE_TEMP:
        return 'EMERGENCY_STOP', "High Output Temperature"
    elif output_temp > config.TARGET_TEMP + 10:
        return 'STANDBY', None
    else:
        control.control_air_and_fuel(output_temp, exhaust_temp)
        return 'RUNNING', None


def stopping():
    shutdown.shut_down()
    return 'OFF', None


def standby(output_temp, current_switch_value):
    if output_temp < config.TARGET_TEMP - 10:
        return 'STARTING'
    elif current_switch_value == 1:
        return 'OFF'
    else:
        if config.IS_WATER_HEATER:
            config.WATER_PIN.on()
        if config.HAS_SECOND_PUMP:
            config.WATER_SECONDARY_PIN.on()
        return 'STANDBY'


def failure(current_switch_value):
    print("Max startup attempts reached. Switch off and on to restart.")
    if current_switch_value == 1:
        return 'OFF'


def emergency_stop(current_switch_value):
    emergencyStop.emergency_stop(config.emergency_reason)
    if current_switch_value == 1:
        return 'OFF', None
