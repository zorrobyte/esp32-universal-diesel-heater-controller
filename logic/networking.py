import config
import time
import json
from logic import tempSensors

# Initialize global variables
wlan = None
mqtt_client = None


# Initialize WiFi
def init_wifi():
    global wlan
    if config.USE_WIFI:
        import network
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)


# Initialize MQTT
def init_mqtt():
    global mqtt_client
    if config.USE_MQTT:
        from umqtt.simple import MQTTClient
        mqtt_client = MQTTClient(config.MQTT_CLIENT_ID, config.MQTT_SERVER)


# Connect to WiFi
def connect_wifi():
    if config.USE_WIFI and wlan and not wlan.isconnected():
        try:
            print('Connecting to WiFi...')
            wlan.connect(config.SSID, config.PASSWORD)
            while not wlan.isconnected():
                time.sleep(1)
            print('WiFi connected!')
        except Exception as e:
            print(f"Error with WiFi: {e}")


# Connect to MQTT
def connect_mqtt():
    if config.USE_MQTT and mqtt_client:
        try:
            print("Connecting to MQTT...")
            mqtt_client.connect()
            print("Connected to MQTT!")
        except Exception as e:
            print(f"Error connecting to MQTT: {e}")


# MQTT Callback
def mqtt_callback(topic, msg):
    topic = topic.decode('utf-8')
    msg = msg.decode('utf-8')
    if topic == config.SET_TEMP_TOPIC:
        config.TARGET_TEMP = float(msg)
    elif topic == config.COMMAND_TOPIC:
        if msg == "start":
            config.current_state = 'STARTING'
        elif msg == "stop":
            config.current_state = 'STOPPING'


# Publish Sensor Values to MQTT
def publish_sensor_values():
    if config.USE_MQTT and mqtt_client:
        try:
            output_temp = tempSensors.read_output_temp()
            exhaust_temp = tempSensors.read_exhaust_temp()
            payload = {
                "output_temp": output_temp,
                "exhaust_temp": exhaust_temp
            }
            mqtt_client.publish(config.SENSOR_VALUES_TOPIC, json.dumps(payload))
        except Exception as e:
            print(f"Error publishing to MQTT: {e}")


# Main function for networking
def run_networking():
    connect_wifi()

    if config.USE_MQTT and mqtt_client:
        try:
            mqtt_client.check_msg()
            publish_sensor_values()
        except Exception as e:
            print(f"Error with MQTT: {e}")
            connect_mqtt()


# Initialize WiFi and MQTT
init_wifi()
init_mqtt()
