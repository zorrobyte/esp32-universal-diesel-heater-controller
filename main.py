import machine
import time
import network
from umqtt.simple import MQTTClient

# Constants
TARGET_TEMP = 60.0  # target temperature in Celsius
EXHAUST_SAFE_TEMP = 120.0  # safety threshold in Celsius
EXHAUST_SHUTDOWN_TEMP = 37.8  # 100°F in Celsius
BURN_CHAMBER_SAFE_TEMP = 150.0  # Temperature to ensure stable combustion in Celsius

# WiFi Credentials
SSID = "MYSSID"
PASSWORD = "PASSWORD"

# MQTT Server
MQTT_SERVER = "10.0.0.137"
MQTT_CLIENT_ID = "esp32_heater"
SET_TEMP_TOPIC = "heater/set_temp"
SENSOR_VALUES_TOPIC = "heater/sensor_values"
COMMAND_TOPIC = "heater/command"

# Pin Definitions
AIR_PIN = 5
FUEL_PIN = 6
GLOW_PIN = 7
WATER_PIN = 8
WATER_TEMP_SENSOR_PIN = 12
EXHAUST_TEMP_SENSOR_PIN = 13
FAN_SPEED_SENSOR_PIN = 14
SWITCH_PIN = 15  # Single pole switch pin

# Initialize pins
air_mosfet = machine.Pin(AIR_PIN, machine.Pin.OUT)
fuel_mosfet = machine.Pin(FUEL_PIN, machine.Pin.OUT)
glow_mosfet = machine.Pin(GLOW_PIN, machine.Pin.OUT)
water_mosfet = machine.Pin(WATER_PIN, machine.Pin.OUT)
switch_pin = machine.Pin(SWITCH_PIN, machine.Pin.IN, machine.Pin.PULL_UP)

# Initialize DS18B20 temperature sensors
from ds18x20 import DS18X20
from onewire import OneWire

ow_water = OneWire(machine.Pin(WATER_TEMP_SENSOR_PIN))
ow_exhaust = OneWire(machine.Pin(EXHAUST_TEMP_SENSOR_PIN))
temp_sensor_water = DS18X20(ow_water)
temp_sensor_exhaust = DS18X20(ow_exhaust)


def read_water_temp():
    roms = temp_sensor_water.scan()
    temp_sensor_water.convert_temp()
    time.sleep_ms(750)
    return temp_sensor_water.read_temp(roms[0])


def read_exhaust_temp():
    roms = temp_sensor_exhaust.scan()
    temp_sensor_exhaust.convert_temp()
    time.sleep_ms(750)
    return temp_sensor_exhaust.read_temp(roms[0])


def linear_interp(x, x0, x1, y0, y1):
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def control_air_and_fuel(temp):
    delta = TARGET_TEMP - temp
    max_delta = 20

    normalized_delta = min(max(delta / max_delta, 0), 1)

    fan_voltage = linear_interp(normalized_delta, 0, 1, 2000, 5000)
    pump_frequency = linear_interp(normalized_delta, 0, 1, 1, 5)

    if fan_voltage > 3500:
        air_mosfet.on()
    else:
        air_mosfet.off()

    if pump_frequency > 3:
        fuel_mosfet.on()
    else:
        fuel_mosfet.off()


# Initialize WiFi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)


def connect_wifi():
    if not wlan.isconnected():
        print('Connecting to WiFi...')
        wlan.connect(SSID, PASSWORD)
        while not wlan.isconnected():
            time.sleep(1)
        print('WiFi connected!')


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
    water_mosfet.on()
    glow_mosfet.on()
    while read_exhaust_temp() < BURN_CHAMBER_SAFE_TEMP:
        time.sleep(5)
    glow_mosfet.off()
    air_mosfet.on()
    fuel_mosfet.on()


def shut_down():
    fuel_mosfet.off()
    air_mosfet.off()
    glow_mosfet.on()
    time.sleep(60)
    glow_mosfet.off()
    while read_exhaust_temp() > EXHAUST_SHUTDOWN_TEMP:
        air_mosfet.on()
        time.sleep(5)
    air_mosfet.off()
    water_mosfet.off()


def main():
    system_running = False
    connect_wifi()
    connect_mqtt()

    while True:
        try:
            if not wlan.isconnected():
                connect_wifi()

            mqtt_client.check_msg()
            publish_sensor_values()

            water_temp = read_water_temp()
            exhaust_temp = read_exhaust_temp()

            if exhaust_temp > EXHAUST_SAFE_TEMP and system_running:
                shut_down()
                system_running = False

            if switch_pin.value() == 0 and not system_running:  # Assuming active-low switch
                start_up()
                system_running = True
            elif switch_pin.value() == 1 and system_running:
                shut_down()
                system_running = False

            if system_running:
                control_air_and_fuel(water_temp)

            time.sleep(10)

        except Exception as e:
            print("Error:", e)
            print("Attempting to reconnect...")
            time.sleep(10)
            connect_wifi()
            connect_mqtt()


if __name__ == "__main__":
    main()
