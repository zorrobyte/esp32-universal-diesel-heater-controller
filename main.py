import machine
import time
import _thread
import config
from machine import Timer
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


pulse_timer = Timer(0)  # Use the first hardware timer

last_pulse_time = 0

# Additional hardware timer for turning off the pump
off_timer = Timer(1)


def turn_off_pump(_):
    config.FUEL_PIN.off()


def pulse_fuel_callback(_):
    global last_pulse_time
    current_time = time.time()
    if current_time - config.heartbeat > 10:  # No heartbeat for the last 10 seconds
        config.FUEL_PIN.off()
        log("Heartbeat missing, fuel pump turned off.")
    elif config.pump_frequency > 0:
        period = 1.0 / config.pump_frequency
        if current_time - last_pulse_time >= period:
            last_pulse_time = current_time
            config.FUEL_PIN.on()
            off_timer.init(period=int(config.PUMP_ON_TIME * 1000), mode=Timer.ONE_SHOT, callback=turn_off_pump)
    else:
        config.FUEL_PIN.off()  # Ensure the pump is off if frequency is zero


# Initialize the timer to call pulse_fuel_callback every 100 milliseconds
pulse_timer.init(period=100, mode=Timer.PERIODIC, callback=pulse_fuel_callback)


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


def run_networking_thread():
    while True:
        networking.run_networking()
        time.sleep(1)  # Adjust sleep time as needed



def main():
    while True:
        config.heartbeat = time.time()

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
    _thread.start_new_thread(emergency_stop_thread, ())
    _thread.start_new_thread(run_networking_thread, ())
    main()
