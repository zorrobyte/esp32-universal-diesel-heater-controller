import config
import utime
from logic import tempSensors
from lib import helpers


def log(message, level=2):
    if config.LOG_LEVEL >= level:
        print(f"[Shutdown] {message}")


def shut_down():
    log("Shutting Down")
    step = 0
    config.current_state = 'STOPPING'
    cooldown_start_time = None
    shutdown_start_time = utime.time()

    while True:
        config.heartbeat = utime.ticks_ms()
        config.exhaust_temp = tempSensors.read_exhaust_temp()
        if utime.time() - shutdown_start_time > config.SHUTDOWN_TIME_LIMIT:
            log("Shutdown took too long, triggering emergency stop.")
            return

        if step == 0:
            log("Stopping fuel supply...")
            config.pump_frequency = 0
            step += 1

        elif step == 1:
            if cooldown_start_time is None:
                log("Activating glow plug and fan for purging and cooling...")
                helpers.set_fan_percentage(config.MAX_FAN_PERCENTAGE)
                config.GLOW_PIN.on()
                cooldown_start_time = utime.time()

            current_exhaust_temp = config.exhaust_temp
            elapsed_time = utime.time() - cooldown_start_time

            log(
                f"Cooling down... Elapsed Time: {elapsed_time}s, Target Exhaust Temp: {config.EXHAUST_SHUTDOWN_TEMP}C, Current Exhaust Temp: {current_exhaust_temp}C")

            if elapsed_time >= config.COOLDOWN_MIN_TIME and current_exhaust_temp <= config.EXHAUST_SHUTDOWN_TEMP:
                step += 1

        elif step == 2:
            log("Turning off electrical components...")
            helpers.set_fan_percentage(0)
            config.GLOW_PIN.off()
            if config.IS_WATER_HEATER:
                config.WATER_PIN.off()
            if config.HAS_SECOND_PUMP:
                config.WATER_SECONDARY_PIN.off()
            log("Finished Shutting Down")
            break

        utime.sleep(1)
