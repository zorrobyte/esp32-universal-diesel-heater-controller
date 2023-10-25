import machine
import time
from ds18x20 import DS18X20
from onewire import OneWire

# Initialize the WDT with a 10-second timeout
#wdt = machine.WDT(id=0, timeout=60000)  # 60 seconds

# Function to get the reset reason
def get_reset_reason():
    reset_reason = machine.reset_cause()
    if reset_reason == machine.PWRON_RESET:
        print("Reboot was because of Power-On!")
    elif reset_reason == machine.WDT_RESET:
        print("Reboot was because of WDT!")
    return reset_reason


# Check the boot reason right at the beginning
boot_reason = get_reset_reason()

# Configuration #
USE_WIFI = False
USE_MQTT = False
TARGET_TEMP = 60.0
EXHAUST_SAFE_TEMP = 120.0
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
WATER_PIN = machine.Pin(19, machine.Pin.OUT)

# Analog Input, Digital I/O
FAN_SPEED_SENSOR_PIN = machine.Pin(32, machine.Pin.IN)  # You can change this to machine.Pin.OUT based on your use-case
SWITCH_PIN = machine.Pin(33, machine.Pin.IN)  # Using internal pull-up

# Initialize pins
air_pwm = machine.PWM(AIR_PIN)
air_pwm.freq(1000)  # Note, this has nothing to do with the duty cycle
# but is the frequency it's pulsed. The duty cycle
# will end up being the same
fuel_mosfet = machine.Pin(FUEL_PIN, machine.Pin.OUT)
glow_mosfet = machine.Pin(GLOW_PIN, machine.Pin.OUT)
water_mosfet = machine.Pin(WATER_PIN, machine.Pin.OUT)
switch_pin = machine.Pin(SWITCH_PIN, machine.Pin.IN, machine.Pin.PULL_UP)

# Initialize a Timer for the fuel pump pulsing
fuel_timer = machine.Timer(0)


def pulse_fuel():
    fuel_mosfet.on()
    time.sleep_ms(20)
    fuel_mosfet.off()


# Initialize DS18B20 temperature sensors
ow_water = OneWire(machine.Pin(18))
ow_exhaust = OneWire(machine.Pin(14))
temp_sensor_water = DS18X20(ow_water)
temp_sensor_exhaust = DS18X20(ow_exhaust)


def read_water_temp():
    try:
        roms = temp_sensor_water.scan()
        temp_sensor_water.convert_temp()
        time.sleep_ms(750)
        return temp_sensor_water.read_temp(roms[0])
    except Exception as e:
        #print("An error occurred while reading the water temperature sensor:", str(e))
        return 90  # Return None or some default value

def read_exhaust_temp():
    try:
        roms = temp_sensor_exhaust.scan()
        temp_sensor_exhaust.convert_temp()
        time.sleep_ms(750)
        return temp_sensor_exhaust.read_temp(roms[0])
    except Exception as e:
        #print("An error occurred while reading the exhaust temperature sensor:", str(e))
        return 100  # Return None or some default value



def linear_interp(x, x0, x1, y0, y1):
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


# Initialize a counter variable outside of the function, so it retains its value between calls
cycle_counter = 0


def control_air_and_fuel(temp):
    global cycle_counter  # Declare the counter as global so we can modify it

    # Tuning parameters
    max_delta = 20  # Maximum temperature difference considered for control
    min_fan_percentage = 20  # Minimum fan speed in percentage
    max_fan_percentage = 100  # Maximum fan speed in percentage
    min_pump_frequency = 1  # Minimum pump frequency in Hz
    max_pump_frequency = 5  # Maximum pump frequency in Hz

    # Calculate the temperature difference from the target
    delta = TARGET_TEMP - temp

    # Calculate fan speed as a percentage, within the range [min_fan_percentage, max_fan_percentage]
    fan_speed_percentage = min(max((delta / max_delta) * 100, min_fan_percentage), max_fan_percentage)

    # Convert the fan speed percentage to a PWM duty cycle between 0 and 1023
    fan_duty = int((fan_speed_percentage / 100) * 1023)

    # Calculate pump frequency, within the range [min_pump_frequency, max_pump_frequency]
    pump_frequency = min(max((delta / max_delta) * max_pump_frequency, min_pump_frequency), max_pump_frequency)

    # Update fan speed
    air_pwm.duty(fan_duty)

    # Update fuel pump frequency
    if pump_frequency > 0:
        fuel_timer.init(period=int(1000 / pump_frequency), mode=machine.Timer.PERIODIC, callback=pulse_fuel)
    else:
        fuel_timer.deinit()

    # Increment the cycle counter
    cycle_counter += 1

    # Print information every 1000 cycles
    if cycle_counter >= 1000:
        print("========================================")
        print("          SYSTEM STATUS                ")
        print("========================================")
        print(f"  Fan Speed: {fan_speed_percentage:>4}% (Duty Cycle: {fan_duty:>4})      ")
        print(f"  Pump Frequency: {pump_frequency:>4} Hz                           ")
        print(f"  Target Temp: {TARGET_TEMP:>6.2f}°C")
        print(f"  Current Temp: {temp:>6.2f}°C")
        print(f"  Temperature Delta: {delta:>6.2f}°C                            ")
        print("========================================")

        cycle_counter = 0  # Reset the counter

# Initialize WiFi
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
        mqtt_client.set_callback(mqtt_callback)
        mqtt_client.connect()
        mqtt_client.subscribe(SET_TEMP_TOPIC)
        mqtt_client.subscribe(COMMAND_TOPIC)
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
        water_temp = read_water_temp()
        exhaust_temp = read_exhaust_temp()
        payload = {
            "water_temp": water_temp,
            "exhaust_temp": exhaust_temp
        }
        mqtt_client.publish(SENSOR_VALUES_TOPIC, str(payload))


def start_up():
    print("Starting Up")
    water_mosfet.on()
    glow_mosfet.on()
    while read_exhaust_temp() < BURN_CHAMBER_SAFE_TEMP:
        print("Waiting for startup, exhaust temp is:", read_exhaust_temp())
        time.sleep(5)
    glow_mosfet.off()
    air_pwm.duty(1023)
    fuel_timer.init(period=int(1000 / 5), mode=machine.Timer.PERIODIC, callback=pulse_fuel)


def shut_down():
    print("Shutting Down")
    fuel_timer.deinit()
    air_pwm.duty(0)
    glow_mosfet.on()
    time.sleep(60)
    glow_mosfet.off()
    while read_exhaust_temp() > EXHAUST_SHUTDOWN_TEMP:
        air_pwm.duty(1023)
        print("Waiting for cooldown, exhaust temp is:", read_exhaust_temp())
        time.sleep(5)
    air_pwm.duty(0)
    water_mosfet.off()


def main():
    system_running = True

    while True:
        #wdt.feed()
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

        water_temp = read_water_temp()
        exhaust_temp = read_exhaust_temp()
        if exhaust_temp > EXHAUST_SAFE_TEMP and system_running:
            shut_down()
            system_running = False

        #if switch_pin.value() == 0 and not system_running:
        #    start_up()
        #    system_running = True
        #elif switch_pin.value() == 1 and system_running:
        #    shut_down()
        #    system_running = False

        if system_running:
            control_air_and_fuel(water_temp)



if __name__ == "__main__":
    print("Reset/Boot Reason was:", boot_reason)
    main()
