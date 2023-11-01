"""
####################################################################
#                          WARNING                                 #
####################################################################
# This code is provided "AS IS" without warranty of any kind.      #
# Use of this code in any form acknowledges your acceptance of     #
# these terms.                                                     #
#                                                                  #
# This code has NOT been tested in real-world scenarios.           #
# Improper usage, lack of understanding, or any combination        #
# thereof can result in significant property damage, injury,       #
# loss of life, or worse.                                          #
# Specifically, this code is related to controlling heating        #
# elements and systems, and there's a very real risk that it       #
# can BURN YOUR SHIT DOWN.                                         #
#                                                                  #
# By using, distributing, or even reading this code, you agree     #
# to assume all responsibility and risk associated with it.        #
# The author(s), contributors, and distributors of this code       #
# will NOT be held liable for any damages, injuries, or other      #
# consequences you may face as a result of using or attempting     #
# to use this code.                                                #
#                                                                  #
# Always approach such systems with caution. Ensure you understand #
# the code, the systems involved, and the potential risks.         #
# If you're unsure, DO NOT use the code.                           #
#                                                                  #
# Stay safe and think before you act.                              #
####################################################################
"""

import config
import utime
import json
import network
from umqtt.simple import MQTTClient

# Initialize global variables
wlan = None
mqtt_client = None
wifi_initialized = False
mqtt_initialized = False


# Initialize WiFi
def init_wifi():
    global wlan
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)


# Initialize MQTT with authentication
def init_mqtt():
    global mqtt_client
    mqtt_client = MQTTClient(config.MQTT_CLIENT_ID, config.MQTT_SERVER, user=config.MQTT_USERNAME,
                             password=config.MQTT_PASSWORD)


# Connect to WiFi
def connect_wifi():
    if wlan and not wlan.isconnected():
        print('Attempting WiFi connection...')
        wlan.connect(config.SSID, config.PASSWORD)
        while not wlan.isconnected():
            utime.sleep(1)
        print(f'WiFi connected! IP Address: {wlan.ifconfig()[0]}')


# Connect to MQTT
def connect_mqtt():
    global mqtt_client
    if not mqtt_client:
        init_mqtt()
    try:
        print('Attempting MQTT connection...')
        mqtt_client.connect()
        print('MQTT connected!')
    except Exception as e:
        print(f'Failed to connect to MQTT: {e}')
        mqtt_client = None  # Reset client to None to attempt re-initialization later


# MQTT Callback
# Add these new attributes to the payload in publish_sensor_values()
def publish_sensor_values():
    global mqtt_client
    if mqtt_client:
        payload = {
            "output_temp": config.output_temp,
            "exhaust_temp": config.exhaust_temp,
            "current_state": config.current_state,
            "fan_speed_percentage": config.fan_speed_percentage,
            "pump_frequency": config.pump_frequency,
            "startup_attempts": config.startup_attempts,
            "emergency_reason": config.emergency_reason,
            "heartbeat": config.heartbeat,
            "startup_successful": config.startup_successful
        }
        mqtt_client.publish(config.SENSOR_VALUES_TOPIC, json.dumps(payload))


# Extend mqtt_callback() to handle new settings
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
    elif topic == "set/exhaust_safe_temp":
        config.EXHAUST_SAFE_TEMP = float(msg)
    elif topic == "set/output_safe_temp":
        config.OUTPUT_SAFE_TEMP = float(msg)
    elif topic == "set/min_fan_percentage":
        config.MIN_FAN_PERCENTAGE = int(msg)
    elif topic == "set/max_fan_percentage":
        config.MAX_FAN_PERCENTAGE = int(msg)
    elif topic == "set/min_pump_frequency":
        config.MIN_PUMP_FREQUENCY = int(msg)
    elif topic == "set/max_pump_frequency":
        config.MAX_PUMP_FREQUENCY = int(msg)
    elif topic == "set/log_level":
        config.LOG_LEVEL = int(msg)
    elif topic == "set/startup_time_limit":
        config.STARTUP_TIME_LIMIT = int(msg)
    elif topic == "set/shutdown_time_limit":
        config.SHUTDOWN_TIME_LIMIT = int(msg)
    elif topic == "set/control_max_delta":
        config.CONTROL_MAX_DELTA = float(msg)
    elif topic == "set/emergency_stop_timer":
        config.EMERGENCY_STOP_TIMER = int(msg)


# Main function for networking
def run_networking():
    global wifi_initialized, mqtt_initialized, wlan, mqtt_client
    if config.USE_WIFI and not wifi_initialized:
        init_wifi()
        wifi_initialized = True
    if config.USE_MQTT and not mqtt_initialized:
        init_mqtt()
        mqtt_initialized = True

    if wlan and not wlan.isconnected():  # Check wlan is not None
        connect_wifi()
    if wlan and wlan.isconnected():  # Check wlan is not None
        if mqtt_client is None:
            connect_mqtt()
        if mqtt_client:  # Make sure mqtt_client is not None
            try:
                mqtt_client.set_callback(mqtt_callback)
                mqtt_client.subscribe(config.SET_TEMP_TOPIC)
                mqtt_client.subscribe(config.COMMAND_TOPIC)
                mqtt_client.check_msg()
                publish_sensor_values()
            except Exception as e:
                print(f'Failed in MQTT operation: {e}')
                mqtt_client = None  # Reset client to None to attempt re-initialization later

    utime.sleep(0.1)  # Add sleep to avoid CPU hogging
