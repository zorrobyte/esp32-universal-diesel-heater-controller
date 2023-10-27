import machine
import math
import time
import _thread
import config


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

# Global variables
pump_frequency = 0  # Hz of the fuel pump, MUST be a global as it's ran in another thread
startup_attempts = 0  # Counter for failed startup attempts
startup_successful = True  # Flag to indicate if startup was successful
failure_mode = False  # Flag to indicate if the system is in failure mode


def pulse_fuel_thread():
    #  TODO: Add some sort of heartbeat so if
    # the main thread fucks off, the pump stops
    global pump_frequency
    while True:
        if pump_frequency > 0:
            period = 1.0 / pump_frequency
            config.PUMP_ON_TIME = 0.02
            off_time = period - config.PUMP_ON_TIME
            config.FUEL_PIN.on()
            time.sleep(config.PUMP_ON_TIME)
            config.FUEL_PIN.off()
            time.sleep(off_time)
            # print("PULSE!", pump_frequency, "Hz") #  uncomment if you want a debug when it pulses
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
    global pump_frequency
    max_delta = 20

    delta = config.TARGET_TEMP - output_temp
    fan_speed_percentage = min(max((delta / max_delta) * 100, config.MIN_FAN_PERCENTAGE), config.MAX_FAN_PERCENTAGE)
    fan_duty = int((fan_speed_percentage / 100) * 1023)
    pump_frequency = min(max((delta / max_delta) * config.MAX_PUMP_FREQUENCY, config.MIN_PUMP_FREQUENCY),
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
                start_up()
            elif msg == "stop":
                shut_down()


    def publish_sensor_values():
        output_temp = read_output_temp()
        exhaust_temp = read_exhaust_temp()
        payload = {
            "output_temp": output_temp,
            "exhaust_temp": exhaust_temp
        }
        mqtt_client.publish(config.SENSOR_VALUES_TOPIC, str(payload))


def start_up():
    global pump_frequency, startup_successful, startup_attempts
    print("Starting Up")
    if config.IS_SIMULATION:
        print("Startup Procedure Completed")
        startup_successful = True
        return
    fan_speed_percentage = 20  # Initial fan speed
    fan_duty = int((fan_speed_percentage / 100) * 1023)
    config.air_pwm.duty(fan_duty)
    print(f"Fan: {fan_speed_percentage}%")
    config.GLOW_PIN.on()
    if config.IS_WATER_HEATER:
        config.WATER_PIN.on()
    if config.HAS_SECOND_PUMP:
        config.WATER_SECONDARY_PIN.on()
    print("Glow plug: On")
    print("Wait 60 seconds for glow plug to heat up")
    time.sleep(60)  # TODO Find actual delay
    initial_exhaust_temp = read_exhaust_temp()
    print(f"Initial Exhaust Temp: {initial_exhaust_temp}°C")
    pump_frequency = 1  # Initial pump frequency
    print(f"Fuel Pump: {pump_frequency} Hz")

    # Initially assume startup will fail
    startup_successful = False

    for step in range(1, 6):  # 5 steps
        exhaust_temps = []

        # Record exhaust temperature over the next 20 seconds
        for _ in range(20):
            time.sleep(1)  # Wait for 1 second
            exhaust_temps.append(read_exhaust_temp())

        avg_exhaust_temp = sum(exhaust_temps) / len(exhaust_temps)
        print(f"Average Exhaust Temp at step {step}: {avg_exhaust_temp}°C")

        if avg_exhaust_temp > initial_exhaust_temp:
            # Increase in temperature, increase fan and fuel frequency
            fan_speed_percentage += 20
            if fan_speed_percentage > 100:
                fan_speed_percentage = 100
            fan_duty = int((fan_speed_percentage / 100) * 1023)
            config.air_pwm.duty(fan_duty)

            pump_frequency += 1
            if pump_frequency > 5:
                pump_frequency = 5

            print(
                f"Step {step} successful. Increasing Fan to {fan_speed_percentage}% and Fuel Pump to {pump_frequency} Hz")

            # Update the initial_exhaust_temp for next comparison
            initial_exhaust_temp = avg_exhaust_temp
        else:
            # Temperature not increasing or decreasing, shut down
            print("Temperature not rising as expected. Stopping fueling.")
            shut_down()
            startup_attempts += 1  # Increment the failed attempts counter
            return

    print("Startup Procedure Completed")
    startup_successful = True  # Set the flag to true as startup was successful
    startup_attempts = 0  # Reset the failed attempts counter


def shut_down():
    global pump_frequency, startup_successful
    print("Shutting Down")
    pump_frequency = 0  # Stop the fuel pump
    if config.IS_WATER_HEATER:
        config.WATER_PIN.on()  # If it's a water heater, turn the water mosfet on
    if config.HAS_SECOND_PUMP:
        config.WATER_SECONDARY_PIN.on()

    # If startup was not successful, run the fan at 100% for 30 seconds
    if not startup_successful:
        print("Startup failed. Running fan at 100% for 30 seconds to purge.")
        config.air_pwm.duty(1023)  # 100% fan speed
        config.GLOW_PIN.on()  # Glow plug on to help purge
        if config.IS_SIMULATION:
            time.sleep(5)
        else:
            time.sleep(30)  # Run the fan for 30 seconds
        config.GLOW_PIN.off()

    config.air_pwm.duty(1023)  # Set fan to 100% for normal shutdown as well
    config.GLOW_PIN.on()  # Turn on the glow plug

    while read_exhaust_temp() > config.EXHAUST_SHUTDOWN_TEMP:
        config.air_pwm.duty(1023)  # Maintain 100% fan speed
        print("Waiting for cooldown, exhaust temp is:", read_exhaust_temp())
        time.sleep(5)  # Wait for 5 seconds before checking again

    config.air_pwm.duty(0)  # Turn off the fan
    if config.IS_WATER_HEATER:
        config.WATER_PIN.off()  # Turn off the water mosfet if it's a water heater
    if config.HAS_SECOND_PUMP:
        config.WATER_SECONDARY_PIN.off()
    config.GLOW_PIN.off()  # Turn off the glow plug

    print("Finished Shutting Down")


def emergency_stop(reason):
    global pump_frequency
    while True:
        config.GLOW_PIN.off()
        config.FUEL_PIN.off()
        config.air_pwm.duty(1023)
        pump_frequency = 0
        if config.IS_WATER_HEATER:
            config.WATER_PIN.on()
        if config.HAS_SECOND_PUMP:
            config.WATER_SECONDARY_PIN.on()
        print(f"Emergency stop triggered due to {reason}. Please reboot to continue.")
        time.sleep(30)


def main():
    global pump_frequency, startup_attempts, startup_successful
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
                elif startup_attempts < 3:
                    current_state = 'STARTING'
                else:
                    current_state = 'FAILURE'
            elif current_switch_value == 1:
                startup_attempts = 0  # Reset startup_attempts when switch is off
                current_state = 'OFF'
                if config.IS_WATER_HEATER:
                    config.WATER_PIN.off()
                if config.HAS_SECOND_PUMP:
                    config.WATER_SECONDARY_PIN.off()

        elif current_state == 'STARTING':
            start_up()
            if startup_successful:
                current_state = 'RUNNING'
            else:
                startup_attempts += 1
                current_state = 'OFF'

        elif current_state == 'RUNNING':
            if exhaust_temp > config.EXHAUST_SAFE_TEMP:
                emergency_reason = "High Exhaust Temperature"
                current_state = 'EMERGENCY_STOP'
            elif output_temp > config.OUTPUT_SAFE_TEMP:
                emergency_reason = "High Output Temperature"
                shut_down()
                current_state = 'EMERGENCY_STOP'
            elif output_temp > config.TARGET_TEMP + 10:
                shut_down()
                current_state = 'STANDBY'
            elif current_switch_value == 1:
                shut_down()
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
