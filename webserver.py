import network
import socket
import re
import machine

# 1. Set the ESP32 to work as an Access Point:

# Configure Access Point
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid='esp32-diesel-ecu', password='794759876')

# Define HTML page template
HTML_PAGE = """
<html>
<head>
    <title>ESP32 Configuration</title>
</head>
<body>
    <h1>ESP32 Configuration</h1>
    <form action="/set" method="post">
        {}
        <input type="submit" value="Save">
    </form>
    <form action="/restart" method="post"> <!-- Added restart form -->
        <input type="submit" value="Restart ESP32">
    </form>
</body>
</html>
"""


# 2. Implement functions to handle the web server:

# Read the config.py file and identify lines with uppercase parameters
def read_config_params():
    params = {}
    with open('config.py', 'r') as f:
        for line in f:
            match = re.match(r'(\w+)\s*=\s*(.*)', line)
            if match:
                key, value = match.groups()
                if key.isupper():
                    params[key] = value.strip()
    return params


# Generate the HTML page dynamically based on the parameters from config.py
def generate_html_page(params):
    input_fields = ""
    for key, value in params.items():
        if value.lower() == 'true' or value.lower() == 'false':
            checked = 'checked' if value.lower() == 'true' else ''
            input_fields += '{}: <input type="checkbox" name="{}" {}><br>'.format(key, key, checked)
        else:
            input_fields += '{}: <input type="text" name="{}" value="{}"><br>'.format(key, key, value)
    return HTML_PAGE.format(input_fields)


# Handle the POST data and modify the config.py file
def handle_post_data(data):
    params = read_config_params()
    # Parse the POST data using regex
    for key in params.keys():
        match = re.search(r'{}=(\w+)'.format(key), data)
        if match:
            value = match.group(1)
            if value == 'on':
                value = 'True'
            elif value == 'off':
                value = 'False'
            params[key] = value

    # Update config.py with modified values
    with open('config.py', 'r') as f:
        lines = f.readlines()

    with open('config.py', 'w') as f:
        for line in lines:
            match = re.match(r'(\w+)\s*=\s*(.*)', line)
            if match and match.group(1) in params:
                f.write("{} = {}\n".format(match.group(1), params[match.group(1)]))
            else:
                f.write(line)


# Web server function
def web_server():
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)

    while True:
        conn, addr = s.accept()
        request = conn.recv(1024)
        request = str(request, 'utf-8')

        if request.startswith('POST'):
            if "/restart" in request:  # <-- Handle restart request
                response = "HTTP/1.1 200 OK\r\n\r\nRestarting..."
                conn.sendall(response.encode('utf-8'))
                conn.close()
                machine.reset()  # <-- Restart the ESP32
            else:
                # Handle POST request (save configuration)
                post_data = request.split('\r\n\r\n')[-1]
                handle_post_data(post_data)
                # Send a response to the client indicating success
                response = "HTTP/1.1 200 OK\r\n\r\nSaved successfully!"
                conn.sendall(response.encode('utf-8'))
        else:
            params = read_config_params()
            html_page = generate_html_page(params)
            conn.sendall(html_page.encode('utf-8'))

        conn.close()


# Start the web server
web_server()
