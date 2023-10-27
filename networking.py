import config
import tempSensors
import startup
import time
import shutdown

if config.USE_WIFI:
    import network

if config.USE_MQTT:
    from umqtt.simple import MQTTClient

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
        output_temp = tempSensors.read_output_temp()
        exhaust_temp = tempSensors.read_exhaust_temp()
        payload = {
            "output_temp": output_temp,
            "exhaust_temp": exhaust_temp
        }
        mqtt_client.publish(config.SENSOR_VALUES_TOPIC, str(payload))


def run_networking():
    # Handle WiFi and MQTT
    if config.USE_WIFI and not wlan.isconnected():
        try:
            connect_wifi()
        except Exception as e:
            print(f"Error with WiFi: {e}")

    if config.USE_MQTT:
        try:
            mqtt_client.check_msg()
            publish_sensor_values()
        except Exception as e:
            print(f"Error with MQTT: {e}")
            try:
                connect_mqtt()
            except Exception as e:
                print(f"Error reconnecting to MQTT: {e}")
