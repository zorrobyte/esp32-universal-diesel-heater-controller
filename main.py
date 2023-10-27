import machine
import time
import _thread
import config
import tempSensors
import shutdown
import control
import startup
import networking


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


def emergency_stop(reason):
    while True:
        config.GLOW_PIN.off()
        config.FUEL_PIN.off()
        config.air_pwm.duty(1023)
        config.pump_frequency = 0
        if config.IS_WATER_HEATER:
            config.WATER_PIN.on()
        if config.HAS_SECOND_PUMP:
            config.WATER_SECONDARY_PIN.on()
        print(f"Emergency stop triggered due to {reason}. Please reboot to continue.")
        time.sleep(30)


def main():
    # states = ['INIT', 'OFF', 'STARTING', 'RUNNING', 'STANDBY', 'FAILURE', 'EMERGENCY_STOP']
    current_state = 'INIT'
    emergency_reason = None  # Variable to capture the reason for emergency stop

    while True:
        # Uncomment the following line if you're using a Watchdog Timer
        # wdt.feed()

        networking.run_networking()

        output_temp = tempSensors.read_output_temp()
        exhaust_temp = tempSensors.read_exhaust_temp()
        current_switch_value = config.SWITCH_PIN.value()

        # State transitions
        if current_state == 'INIT':
            reset_reason = get_reset_reason()
            if reset_reason == 'Some Specific Reason':
                emergency_reason = "Unusual Reset Reason"
                current_state = 'EMERGENCY_STOP'
            else:
                current_state = 'OFF'

        elif current_state == 'OFF':
            if current_switch_value == 0:
                if output_temp > config.TARGET_TEMP + 10:
                    current_state = 'STANDBY'
                elif config.startup_attempts < 3:
                    current_state = 'STARTING'
                else:
                    current_state = 'FAILURE'
            elif current_switch_value == 1:
                config.startup_attempts = 0  # Reset config.startup_attempts when switch is off
                current_state = 'OFF'
                if config.IS_WATER_HEATER:
                    config.WATER_PIN.off()
                if config.HAS_SECOND_PUMP:
                    config.WATER_SECONDARY_PIN.off()

        elif current_state == 'STARTING':
            startup.start_up()
            if config.startup_successful:
                current_state = 'RUNNING'
            else:
                config.startup_attempts += 1
                current_state = 'OFF'

        elif current_state == 'RUNNING':
            if exhaust_temp > config.EXHAUST_SAFE_TEMP:
                emergency_reason = "High Exhaust Temperature"
                current_state = 'EMERGENCY_STOP'
            elif output_temp > config.OUTPUT_SAFE_TEMP:
                emergency_reason = "High Output Temperature"
                shutdown.shut_down()
                current_state = 'EMERGENCY_STOP'
            elif output_temp > config.TARGET_TEMP + 10:
                shutdown.shut_down()
                current_state = 'STANDBY'
            elif current_switch_value == 1:
                shutdown.shut_down()
                current_state = 'OFF'
            else:
                control.control_air_and_fuel(output_temp, exhaust_temp)

        elif current_state == 'STANDBY':
            if output_temp < config.TARGET_TEMP - 10:
                current_state = 'STARTING'
            elif current_switch_value == 1:
                current_state = 'OFF'
            else:
                if config.IS_WATER_HEATER:
                    config.WATER_PIN.on()
                if config.HAS_SECOND_PUMP:
                    config.WATER_SECONDARY_PIN.on()

        elif current_state == 'FAILURE':
            print("Max startup attempts reached. Switch off and on to restart.")
            if current_switch_value == 1:
                current_state = 'OFF'

        elif current_state == 'EMERGENCY_STOP':
            emergency_stop(emergency_reason)
            if current_switch_value == 1:
                current_state = 'OFF'
                emergency_reason = None

        print(f"Current state: {current_state}")
        if emergency_reason:
            print(f"Emergency reason: {emergency_reason}")
        time.sleep(1)


if __name__ == "__main__":
    print("Reset/Boot Reason was:", boot_reason)
    main()
