import machine
import math
import time
import _thread


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

# Configuration #
USE_WIFI = False  # Both Wifi and MQTT not working at this time, hangs
USE_MQTT = False
IS_WATER_HEATER = True  # Set this to True if this is a Water/Coolant heater
IS_SIMULATION = True  # If running simulation, skip some lengthy checks
TARGET_TEMP = 60.0
EXHAUST_SAFE_TEMP = 100  # TODO FIND REAL VALUE
OUTPUT_SAFE_TEMP = 90  # TODO FIND REAL VALUE
EXHAUST_SHUTDOWN_TEMP = 40.0
# WiFi Credentials
SSID = "MYSSID"
PASSWORD = "PASSWORD"
# MQTT Server
MQTT_SERVER = "10.0.0.137"
MQTT_CLIENT_ID = "esp32_heater"
SET_TEMP_TOPIC = "heater/set_temp"
SENSOR_VALUES_TOPIC = "heater/sensor_values"
COMMAND_TOPIC = "heater/command"

if USE_WIFI:
    import network

if USE_MQTT:
    from umqtt.simple import MQTTClient

# Pin Definitions
AIR_PIN = machine.Pin(23, machine.Pin.OUT)
FUEL_PIN = machine.Pin(22, machine.Pin.OUT)
GLOW_PIN = machine.Pin(21, machine.Pin.OUT)
if IS_WATER_HEATER:
    WATER_PIN = machine.Pin(19, machine.Pin.OUT)
SWITCH_PIN = machine.Pin(33, machine.Pin.IN, machine.Pin.PULL_UP)

# Initialize ADC for output and exhaust temperature
OUTPUT_TEMP_ADC = machine.ADC(machine.Pin(32))  # Changed to a valid ADC pin
OUTPUT_TEMP_ADC.atten(machine.ADC.ATTN_11DB)  # Corrected: Full range: 3.3v
EXHAUST_TEMP_ADC = machine.ADC(machine.Pin(34))  # Changed to a valid ADC pin
EXHAUST_TEMP_ADC.atten(machine.ADC.ATTN_11DB)  # Corrected: Full range: 3.3v

# Initialize PWM for air
air_pwm = machine.PWM(AIR_PIN)
air_pwm.freq(1000)

# Initialize Fuel, Glow, and Water Mosfets
fuel_mosfet = FUEL_PIN
glow_mosfet = GLOW_PIN
if IS_WATER_HEATER:
    water_mosfet = WATER_PIN

# Initialize Switch Pin
switch_pin = SWITCH_PIN

# Constants
BETA = 3950  # Beta value for the thermistor

# Global variables
pump_frequency = 0  # Hz of the fuel pump, MUST be a global as it's ran in another thread
startup_attempts = 0  # Counter for failed startup attempts
startup_successful = True  # Flag to indicate if startup was successful
failure_mode = False  # Flag to indicate if the system is in failure mode

air_pwm.duty(0)  # Ensure the fan isn't initially on after init


def pulse_fuel_thread():
    global pump_frequency
    while True:
        if pump_frequency > 0:
            period = 1.0 / pump_frequency
            on_time = 0.02
            off_time = period - on_time
            fuel_mosfet.on()
            time.sleep(on_time)
            fuel_mosfet.off()
            time.sleep(off_time)
            print("PULSE!", pump_frequency)
        else:
            time.sleep(0.1)


_thread.start_new_thread(pulse_fuel_thread, ())


def read_output_temp():
    try:
        analog_value = OUTPUT_TEMP_ADC.read()
        resistance = 1 / (4095.0 / analog_value - 1)
        celsius = 1 / (math.log(resistance) / BETA + 1.0 / 298.15) - 273.15
        # print("Output Temperature in Celsius:", celsius)
        return celsius
    except Exception as e:
        print("An error occurred while reading the output temperature sensor:", str(e))
        return 999


def read_exhaust_temp():
    try:
        analog_value = EXHAUST_TEMP_ADC.read()
        resistance = 1 / (4095.0 / analog_value - 1)
        celsius = 1 / (math.log(resistance) / BETA + 1.0 / 298.15) - 273.15
        # print("Exhaust Temperature in Celsius:", celsius)
        return celsius
    except Exception as e:
        print("An error occurred while reading the exhaust temperature sensor:", str(e))
        return 999


def control_air_and_fuel(output_temp, exhaust_temp):
    #  TODO IMPLEMENT FLAME OUT BASED ON exhaust_temp
    global pump_frequency
    max_delta = 20
    min_fan_percentage = 20
    max_fan_percentage = 100
    min_pump_frequency = 1
    max_pump_frequency = 5

    delta = TARGET_TEMP - output_temp
    fan_speed_percentage = min(max((delta / max_delta) * 100, min_fan_percentage), max_fan_percentage)
    fan_duty = int((fan_speed_percentage / 100) * 1023)
    pump_frequency = min(max((delta / max_delta) * max_pump_frequency, min_pump_frequency), max_pump_frequency)

    air_pwm.duty(fan_duty)
    if IS_WATER_HEATER:
        water_mosfet.on()
    glow_mosfet.off()


if USE_WIFI:
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)


    def connect_wifi():
        if not wlan.isconnected():
            print('Connecting to WiFi...')
            wlan.connect(SSID, PASSWORD)
            while not wlan.isconnected():
                time.sleep(1)
            print('WiFi connected!')

if USE_MQTT:
    mqtt_client = None


    def connect_mqtt():
        global mqtt_client
        print("Connecting to MQTT...")
        mqtt_client = MQTTClient(MQTT_CLIENT_ID, MQTT_SERVER)
        mqtt_client.connect()
        print("Connected to MQTT!")


    def mqtt_callback(topic, msg):
        global TARGET_TEMP
        topic = topic.decode('utf-8')
        msg = msg.decode('utf-8')
        if topic == SET_TEMP_TOPIC:
            TARGET_TEMP = float(msg)
        elif topic == COMMAND_TOPIC:
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
        mqtt_client.publish(SENSOR_VALUES_TOPIC, str(payload))


def start_up():
    global pump_frequency, startup_successful, startup_attempts
    print("Starting Up")
    if IS_SIMULATION:
        print("Startup Procedure Completed")
        startup_successful = True
        return
    fan_speed_percentage = 20  # Initial fan speed
    fan_duty = int((fan_speed_percentage / 100) * 1023)
    air_pwm.duty(fan_duty)
    print(f"Fan: {fan_speed_percentage}%")
    glow_mosfet.on()
    if IS_WATER_HEATER:
        water_mosfet.on()
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
            air_pwm.duty(fan_duty)

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
    if IS_WATER_HEATER:
        water_mosfet.on()  # If it's a water heater, turn the water mosfet on

    # If startup was not successful, run the fan at 100% for 30 seconds
    if not startup_successful:
        print("Startup failed. Running fan at 100% for 30 seconds to purge.")
        air_pwm.duty(1023)  # 100% fan speed
        glow_mosfet.on()  # Glow plug on to help purge
        if IS_SIMULATION:
            time.sleep(5)
        else:
            time.sleep(30)  # Run the fan for 30 seconds
        glow_mosfet.off()

    air_pwm.duty(1023)  # Set fan to 100% for normal shutdown as well
    glow_mosfet.on()  # Turn on the glow plug

    while read_exhaust_temp() > EXHAUST_SHUTDOWN_TEMP:
        air_pwm.duty(1023)  # Maintain 100% fan speed
        print("Waiting for cooldown, exhaust temp is:", read_exhaust_temp())
        time.sleep(5)  # Wait for 5 seconds before checking again

    air_pwm.duty(0)  # Turn off the fan
    if IS_WATER_HEATER:
        water_mosfet.off()  # Turn off the water mosfet if it's a water heater
    glow_mosfet.off()  # Turn off the glow plug

    print("Finished Shutting Down")


def emergency_stop(reason):
    global pump_frequency
    while True:
        glow_mosfet.off()
        fuel_mosfet.off()
        air_pwm.duty(1023)
        pump_frequency = 0
        if IS_WATER_HEATER:
            water_mosfet.on()
        print(f"Emergency stop triggered due to {reason}. Please reboot to continue.")
        time.sleep(30)


def main():
    global pump_frequency, startup_attempts, startup_successful
    states = ['INIT', 'OFF', 'STARTING', 'RUNNING', 'STANDBY', 'FAILURE', 'EMERGENCY_STOP']
    current_state = 'INIT'
    emergency_reason = None  # Variable to capture the reason for emergency stop

    while True:
        # Uncomment the following line if you're using a Watchdog Timer
        # wdt.feed()

        # Handle WiFi and MQTT
        if USE_WIFI and not wlan.isconnected():
            try:
                connect_wifi()
            except Exception as e:
                print(f"Error with WiFi: {e}")
                emergency_reason = "WiFi Connection Failure"

        if USE_MQTT:
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
        current_switch_value = switch_pin.value()

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
                if output_temp > TARGET_TEMP + 10:
                    current_state = 'STANDBY'
                elif startup_attempts < 3:
                    current_state = 'STARTING'
                else:
                    current_state = 'FAILURE'
            elif current_switch_value == 1:
                startup_attempts = 0  # Reset startup_attempts when switch is off
                current_state = 'OFF'
                if IS_WATER_HEATER:
                    water_mosfet.off()

        elif current_state == 'STARTING':
            start_up()
            if startup_successful:
                current_state = 'RUNNING'
            else:
                startup_attempts += 1
                current_state = 'OFF'

        elif current_state == 'RUNNING':
            if exhaust_temp > EXHAUST_SAFE_TEMP:
                emergency_reason = "High Exhaust Temperature"
                current_state = 'EMERGENCY_STOP'
            elif output_temp > OUTPUT_SAFE_TEMP:
                emergency_reason = "High Output Temperature"
                shut_down()
                current_state = 'EMERGENCY_STOP'
            elif output_temp > TARGET_TEMP + 10:
                shut_down()
                current_state = 'STANDBY'
            elif current_switch_value == 1:
                shut_down()
                current_state = 'OFF'
            else:
                control_air_and_fuel(output_temp, exhaust_temp)

        elif current_state == 'STANDBY':
            if output_temp < TARGET_TEMP - 10:
                current_state = 'STARTING'
            elif current_switch_value == 1:
                current_state = 'OFF'
            else:
                if IS_WATER_HEATER:
                    water_mosfet.on()

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
