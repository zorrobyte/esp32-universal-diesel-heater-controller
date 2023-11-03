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

import machine
import _thread
import config
import utime
from machine import Timer
from states import stateMachine, emergencyStop
from lib import sensors, networking, fanPID
import webserver

# Initialize the WDT with a 10-second timeout
wdt = machine.WDT(id=0, timeout=10000)  # 10 seconds


def log(message, level=2):
    if config.LOG_LEVEL >= level:
        print(message)


def get_reset_reason():
    reset_reason = machine.reset_cause()
    if reset_reason == machine.PWRON_RESET:
        print("Reboot was because of Power-On!")
    elif reset_reason == machine.WDT_RESET:
        print("Reboot was because of WDT!")
    return reset_reason


pulse_timer = Timer(0)
last_pulse_time = 0
off_timer = Timer(1)


def turn_off_pump(_):
    config.FUEL_PIN.off()


def pulse_fuel_callback(_):
    global last_pulse_time
    current_time = utime.ticks_ms()

    if utime.ticks_diff(current_time, config.heartbeat) > 10000:
        config.FUEL_PIN.off()
        log("Heartbeat missing, fuel pump turned off.")
    elif config.pump_frequency > 0:
        period = 1000.0 / config.pump_frequency

        if utime.ticks_diff(current_time, last_pulse_time) >= period:
            last_pulse_time = current_time
            config.FUEL_PIN.on()
            off_timer.init(period=int(config.PUMP_ON_TIME * 1000), mode=Timer.ONE_SHOT, callback=turn_off_pump)
    else:
        config.FUEL_PIN.off()


pulse_timer.init(period=100, mode=Timer.PERIODIC, callback=pulse_fuel_callback)


def emergency_stop_thread():
    while True:
        wdt.feed()
        current_time = utime.ticks_ms()  # Use ticks_ms to get the current time in milliseconds

        if utime.ticks_diff(current_time, config.heartbeat) > 10000:  # Compare in milliseconds (10 seconds = 10000 ms)
            emergencyStop.emergency_stop("No heartbeat detected")

        utime.sleep(1)


def run_networking_thread():
    while True:
        networking.run_networking()
        utime.sleep(5)


def main():
    while True:
        config.heartbeat = utime.ticks_ms()

        config.output_temp = sensors.read_output_temp()
        config.exhaust_temp = sensors.read_exhaust_temp()
        current_switch_value = config.SWITCH_PIN.value()

        config.current_state, config.emergency_reason = stateMachine.handle_state(
            config.current_state,
            current_switch_value,
            config.exhaust_temp,
            config.output_temp
        )

        log(f"Current state: {config.current_state}")
        if config.emergency_reason:
            log(f"Emergency reason: {config.emergency_reason}")

        utime.sleep(1)


if __name__ == "__main__":
    boot_reason = get_reset_reason()
    log(f"Reset/Boot Reason was: {boot_reason}")
    _thread.start_new_thread(emergency_stop_thread, ())
    _thread.start_new_thread(run_networking_thread, ())
    if config.FAN_RPM_SENSOR:
        _thread.start_new_thread(fanPID.fan_control_thread, ())
    if config.USE_WEBSERVER:
        _thread.start_new_thread(webserver.web_server(), ())
    main()
