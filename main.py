import machine
import time
import _thread
import config
from logic import networking, tempSensors, states


# Initialize the WDT with a 10-second timeout
# wdt = machine.WDT(id=0, timeout=60000)  # 60 seconds

def get_reset_reason():
    reset_reason = machine.reset_cause()
    if reset_reason == machine.PWRON_RESET:
        print("Reboot was because of Power-On!")
    elif reset_reason == machine.WDT_RESET:
        print("Reboot was because of WDT!")
    return reset_reason


boot_reason = get_reset_reason()


def pulse_fuel_thread():
    #  TODO: Add some sort of heartbeat so if
    # the main thread fucks off, the pump stops
    while True:
        if config.pump_frequency > 0:
            period = 1.0 / config.pump_frequency
            config.PUMP_ON_TIME = 0.02
            off_time = period - config.PUMP_ON_TIME
            config.FUEL_PIN.on()
            time.sleep(config.PUMP_ON_TIME)
            config.FUEL_PIN.off()
            time.sleep(off_time)
            # print("PULSE!", config.pump_frequency, "Hz") #  uncomment if you want a debug when it pulses
        else:
            time.sleep(0.1)


_thread.start_new_thread(pulse_fuel_thread, ())


def main():

    while True:
        # Uncomment the following line if you're using a Watchdog Timer
        # wdt.feed()

        networking.run_networking()

        config.output_temp = tempSensors.read_output_temp()
        config.exhaust_temp = tempSensors.read_exhaust_temp()
        current_switch_value = config.SWITCH_PIN.value()

        if config.current_state == 'INIT':
            config.current_state, emergency_reason = states.init()

        elif config.current_state == 'OFF':
            config.current_state = states.off(current_switch_value)

        elif config.current_state == 'STARTING':
            config.current_state = states.starting()

        elif config.current_state == 'RUNNING':
            config.current_state, emergency_reason = states.running(current_switch_value, exhaust_temp, config.output_temp)

        elif config.current_state == 'STOPPING':
            config.current_state, emergency_reason = states.stopping()

        elif config.current_state == 'STANDBY':
            config.current_state = states.standby(config.output_temp, current_switch_value)

        elif config.current_state == 'FAILURE':
            config.current_state = states.failure(current_switch_value)

        elif config.current_state == 'EMERGENCY_STOP':
            config.current_state, emergency_reason = states.emergency_stop(current_switch_value)

        print(f"Current state: {config.current_state}")
        if config.emergency_reason:
            print(f"Emergency reason: {config.emergency_reason}")

        time.sleep(1)


if __name__ == "__main__":
    print("Reset/Boot Reason was:", boot_reason)
    main()
