import machine
import math
import time
import _thread
import config
import startup
import shutdown


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

if config.USE_WIFI:
    import network

if config.USE_MQTT:
    from umqtt.simple import MQTTClient


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

# Constants for 50k NTC thermistor
BETA_NTC_50k = 3950  # Placeholder value; you should calibrate this for more accuracy
R0_NTC_50k = 50000.0  # 50k ohms
T0_NTC_50k = 298.15  # 25C in Kelvin


def read_output_temp():
    try:
        analog_value = config.OUTPUT_TEMP_ADC.read()
        resistance = 1 / (4095.0 / analog_value - 1)

        # Calculate temperature using the simplified B parameter equation for NTC
        temperature_k = 1 / (math.log(resistance / R0_NTC_50k) / BETA_NTC_50k + 1 / T0_NTC_50k)

        # Convert temperature to Celsius
        celsius = temperature_k - 273.15
        if config.IS_SIMULATION:
            return 60
        else:
            return celsius
    except Exception as e:
        print("An error occurred while reading the output temperature sensor:", str(e))
        return 999


# Constants for 1K PTC thermistor (HCalory Coolant Heater)
BETA_PTC_1K = 3000  # Placeholder value; you should calibrate this for more accuracy
R0_PTC_1K = 1000.0  # 1k ohms
T0_PTC_1K = 298.15  # 25C in Kelvin


def read_exhaust_temp():
    try:
        analog_value = config.EXHAUST_TEMP_ADC.read()
        resistance = 1 / (4095.0 / analog_value - 1)

        # Calculate temperature using the simplified B parameter equation for PTC
        temperature_k = 1 / (1 / T0_PTC_1K + (1 / BETA_PTC_1K) * math.log(resistance / R0_PTC_1K))

        # Convert temperature to Celsius
        celsius = temperature_k - 273.15
        if config.IS_SIMULATION:
            return 60
        else:
            return celsius
    except Exception as e:
        print("An error occurred while reading the exhaust temperature sensor:", str(e))
        return 999


def control_air_and_fuel(output_temp, exhaust_temp):
    #  TODO IMPLEMENT FLAME OUT BASED ON exhaust_temp
    max_delta = 20

    delta = config.TARGET_TEMP - output_temp
    fan_speed_percentage = min(max((delta / max_delta) * 100, config.MIN_FAN_PERCENTAGE), config.MAX_FAN_PERCENTAGE)
    fan_duty = int((fan_speed_percentage / 100) * 1023)
    config.pump_frequency = min(max((delta / max_delta) * config.MAX_PUMP_FREQUENCY, config.MIN_PUMP_FREQUENCY),
                         config.MAX_PUMP_FREQUENCY)

    config.air_pwm.duty(fan_duty)
    if config.IS_WATER_HEATER:
        config.WATER_PIN.on()
    if config.HAS_SECOND_PUMP:
        config.WATER_SECONDARY_PIN.on()
    config.GLOW_PIN.off()


if config.USE_WIFI:
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)


    def connect_wifi():
        if not wlan.isconnected():
            print('Connecting to WiFi...')
            wlan.connect(config.SSID, config.PASSWORD)
            while not wlan.isconnected():
                time.sleep(1)
            print('WiFi connected!')

if config.USE_MQTT:
    mqtt_client = None


    def connect_mqtt():
        global mqtt_client
        print("Connecting to MQTT...")
        mqtt_client = MQTTClient(config.MQTT_CLIENT_ID, config.MQTT_SERVER)
        mqtt_client.connect()
        print("Connected to MQTT!")


    def mqtt_callback(topic, msg):
        topic = topic.decode('utf-8')
        msg = msg.decode('utf-8')
        if topic == config.SET_TEMP_TOPIC:
            config.TARGET_TEMP = float(msg)
        elif topic == config.COMMAND_TOPIC:
            if msg == "start":
                startup.start_up()
            elif msg == "stop":
                shutdown.shut_down()


    def publish_sensor_values():
        output_temp = read_output_temp()
        exhaust_temp = read_exhaust_temp()
        payload = {
            "output_temp": output_temp,
            "exhaust_temp": exhaust_temp
        }
        mqtt_client.publish(config.SENSOR_VALUES_TOPIC, str(payload))


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

        # Handle WiFi and MQTT
        if config.USE_WIFI and not wlan.isconnected():
            try:
                connect_wifi()
            except Exception as e:
                print(f"Error with WiFi: {e}")
                emergency_reason = "WiFi Connection Failure"

        if config.USE_MQTT:
            try:
                mqtt_client.check_msg()
                publish_sensor_values()
            except Exception as e:
                print(f"Error with MQTT: {e}")
                emergency_reason = "MQTT Connection Failure"
                try:
                    connect_mqtt()
                except Exception as e:
                    print(f"Error reconnecting to MQTT: {e}")

        output_temp = read_output_temp()
        exhaust_temp = read_exhaust_temp()
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
                control_air_and_fuel(output_temp, exhaust_temp)

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
