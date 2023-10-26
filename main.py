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
USE_WIFI = False
USE_MQTT = False
IS_WATER_HEATER = True  # Set this to True if this is a Water/Coolant heater
TARGET_TEMP = 60.0
EXHAUST_SAFE_TEMP = 75.0
EXHAUST_SHUTDOWN_TEMP = 40.0
BURN_CHAMBER_SAFE_TEMP = 150.0
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

# Variable init
cycle_counter = 0
pump_frequency = 0


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


def control_air_and_fuel(temp, exhaust_temp):
    global cycle_counter, pump_frequency
    max_delta = 20
    min_fan_percentage = 20
    max_fan_percentage = 100
    min_pump_frequency = 1
    max_pump_frequency = 5

    delta = TARGET_TEMP - temp
    fan_speed_percentage = min(max((delta / max_delta) * 100, min_fan_percentage), max_fan_percentage)
    fan_duty = int((fan_speed_percentage / 100) * 1023)
    pump_frequency = min(max((delta / max_delta) * max_pump_frequency, min_pump_frequency), max_pump_frequency)

    air_pwm.duty(fan_duty)
    if IS_WATER_HEATER:
        water_mosfet.on()
    glow_mosfet.off()

    cycle_counter += 1

    if cycle_counter >= 1000:
        print("========================================")
        print("          SYSTEM STATUS                ")
        print("========================================")
        print(f"  Fan Speed: {fan_speed_percentage:>4}% (Duty Cycle: {fan_duty:>4})      ")
        print(f"  Pump Frequency: {pump_frequency:>4} Hz                           ")
        print(f"  Target Temp: {TARGET_TEMP:>6.2f}°C")
        print(f"  Current Temp: {temp:>6.2f}°C")
        print(f"  Temperature Delta: {delta:>6.2f}°C                            ")
        print(f"  Exhaust Temp: {exhaust_temp:>6.2f}°C                            ")
        print("========================================")
        cycle_counter = 0


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
    global pump_frequency
    print("Starting Up")
    fan_speed_percentage = 20  # Initial fan speed
    fan_duty = int((fan_speed_percentage / 100) * 1023)
    air_pwm.duty(fan_duty)
    print(f"Fan: {fan_speed_percentage}%")
    glow_mosfet.on()
    if IS_WATER_HEATER:
        water_mosfet.on()
    print("Glow plug: On")
    print("Wait 60 seconds for glow plug to heat up")
    time.sleep(5)  # simulating a shorter time, TODO: change this to actual delay
    initial_exhaust_temp = read_exhaust_temp()
    print(f"Initial Exhaust Temp: {initial_exhaust_temp}°C")
    pump_frequency = 1  # Initial pump frequency
    print(f"Fuel Pump: {pump_frequency} Hz")

    # Waiting 15 seconds after initial fueling
    time.sleep(15)

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
            return
    print("Startup Procedure Completed")




def shut_down():
    global pump_frequency
    print("Shutting Down")
    pump_frequency = 0
    if IS_WATER_HEATER:
        water_mosfet.on()
    air_pwm.duty(1023)
    glow_mosfet.on()
    while read_exhaust_temp() > EXHAUST_SHUTDOWN_TEMP:
        air_pwm.duty(1023)
        print("Waiting for cooldown, exhaust temp is:", read_exhaust_temp())
        time.sleep(5)
    air_pwm.duty(0)
    if IS_WATER_HEATER:
        water_mosfet.off()
    glow_mosfet.off()
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
    global pump_frequency
    system_running = False

    while True:
        # wdt.feed()
        if USE_WIFI:
            try:
                if not wlan.isconnected():
                    connect_wifi()
            except Exception as e:
                print("Error with WiFi:", e)
        if USE_MQTT:
            try:
                mqtt_client.check_msg()
                publish_sensor_values()
            except Exception as e:
                print("Error with MQTT:", e)
                try:
                    connect_mqtt()
                except Exception as e:
                    print("Error reconnecting to MQTT:", e)

        output_temp = read_output_temp()
        exhaust_temp = read_exhaust_temp()

        # Main control logic
        if exhaust_temp > EXHAUST_SAFE_TEMP:
            system_running = False
            emergency_stop("high exhaust temperature")

        if output_temp > TARGET_TEMP + 15:
            system_running = False
            emergency_stop("high output temperature")

        if switch_pin.value() == 0 and not system_running:
            start_up()
            system_running = True
        elif switch_pin.value() == 1 and system_running:
            shut_down()
            system_running = False

        if system_running:
            control_air_and_fuel(output_temp, exhaust_temp)

if __name__ == "__main__":
    print("Reset/Boot Reason was:", boot_reason)
    main()
