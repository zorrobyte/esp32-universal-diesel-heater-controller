import machine
import time
import _thread
import config
from logic import networking, tempSensors, states, emergencyStop

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


def pulse_fuel_thread():
    while True:
        current_time = time.time()
        if current_time - config.heartbeat > 10:  # No heartbeat for the last 10 seconds
            config.FUEL_PIN.off()
            log("Heartbeat missing, fuel pump turned off.")
        elif config.pump_frequency > 0:
            period = 1.0 / config.pump_frequency
            off_time = period - config.PUMP_ON_TIME
            config.FUEL_PIN.on()
            time.sleep(config.PUMP_ON_TIME)
            config.FUEL_PIN.off()
            time.sleep(off_time)
        else:
            config.FUEL_PIN.off()  # Ensure the pump is off if frequency is zero
            time.sleep(0.1)


def emergency_stop_thread():
    while True:
        wdt.feed()
        current_time = time.time()

        # Check for a missing heartbeat
        if current_time - config.heartbeat > 10:  # No heartbeat for the last 10 seconds
            emergencyStop.emergency_stop("No heartbeat detected")

        # Read and check exhaust temperature
        exhaust_temp = tempSensors.read_exhaust_temp()
        if exhaust_temp > config.EXHAUST_SAFE_TEMP:
            emergencyStop.emergency_stop("Exhaust temperature exceeded safe limit")

        # Read and check output temperature
        output_temp = tempSensors.read_output_temp()
        if output_temp > config.OUTPUT_SAFE_TEMP:
            emergencyStop.emergency_stop("Output temperature exceeded safe limit")

        time.sleep(1)  # Check every second


_thread.start_new_thread(emergency_stop_thread, ())
_thread.start_new_thread(pulse_fuel_thread, ())


def main():
    while True:
        config.heartbeat = time.time()
        networking.run_networking()

        config.output_temp = tempSensors.read_output_temp()
        config.exhaust_temp = tempSensors.read_exhaust_temp()
        current_switch_value = config.SWITCH_PIN.value()

        # Handle state transitions
        config.current_state, config.emergency_reason = states.handle_state(
            config.current_state,
            current_switch_value,
            config.exhaust_temp,
            config.output_temp
        )

        log(f"Current state: {config.current_state}")
        if config.emergency_reason:
            log(f"Emergency reason: {config.emergency_reason}")

        time.sleep(1)


if __name__ == "__main__":
    boot_reason = get_reset_reason()
    log(f"Reset/Boot Reason was: {boot_reason}")
    main()
