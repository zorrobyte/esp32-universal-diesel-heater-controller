import network
import socket
import machine
import json
import utime


def unquote_plus(string):
    # Replace '+' with ' ' and decode percent-encoded characters
    string = string.replace('+', ' ')
    parts = string.split('%')
    if len(parts) > 1:
        string = parts[0]
        for item in parts[1:]:
            try:
                if len(item) >= 2:
                    string += chr(int(item[:2], 16)) + item[2:]
                else:
                    string += '%' + item
            except ValueError:
                string += '%' + item
    return string


# Define HTML escape function
def escape_html(text):
    html_escape_table = {
        "&": "&amp;",
        '"': "&quot;",
        "'": "&apos;",
        ">": "&gt;",
        "<": "&lt;",
    }
    return "".join(html_escape_table.get(c, c) for c in text)


# Configure Access Point
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid='esp32-diesel-ecu', password='794759876')

# HTML page template
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ESP32 Configuration</title>
    <style>
        body {
            font-family: 'Arial', sans-serif;
            background-color: #f7f7f7;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .container {
            background-color: #fff;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            width: 100%;
            max-width: 500px;
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 20px;
        }
        form {
            display: grid;
            gap: 10px;
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            color: #555;
        }
        input[type="text"], input[type="password"], input[type="number"], select {
            width: 100%;
            padding: 10px;
            margin-bottom: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            box-sizing: border-box;
        }
        input[type="submit"] {
            padding: 10px 15px;
            border: none;
            border-radius: 5px;
            background-color: #007bff;
            color: white;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        input[type="submit"]:hover {
            background-color: #0056b3;
        }
        .restart-btn {
            background-color: #dc3545;
        }
        .restart-btn:hover {
            background-color: #c82333;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>ESP32 Configuration</h1>
        <form action="/set" method="post">
            {} <!-- Form fields will be injected here -->
            <input type="submit" value="Save">
        </form>
        <form action="/restart" method="post">
            <input type="submit" value="Restart ESP32" class="restart-btn">
        </form>
    </div>
</body>
</html>
"""


# Read config.json and return as dictionary
def read_config_params():
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except OSError:
        return {}


# Generate HTML page based on config.json
def generate_html_page(params):
    input_fields = ""
    for section, settings in params.items():
        input_fields += f"<h2>{escape_html(section)}</h2>"
        for key, value in settings.items():
            safe_key = escape_html(key)
            safe_value = escape_html(str(value))
            input_fields += f'{safe_key}: <input type="text" name="{section}.{safe_key}" value="{safe_value}"><br>'
    return HTML_PAGE.format(input_fields)


# Custom pretty-print function for JSON-like dictionaries
def pretty_print_json(data, indent=4, level=0):
    if not isinstance(data, dict):  # if the data is not a dictionary, just return it as a string
        return str(data)
    items = []
    for key, value in data.items():
        items.append(' ' * (level * indent) + f'"{key}": ' + (
            pretty_print_json(value, indent, level + 1) if isinstance(value, dict) else json.dumps(value)))
    return "{\n" + ",\n".join(items) + "\n" + ' ' * (level - 1) * indent + "}"


# Handle POST data and update config.json
def handle_post_data(data):
    params = read_config_params()

    # Parse POST data
    lines = data.split('&')
    for line in lines:
        section_key_value = line.split('=')
        if len(section_key_value) == 2:
            section_key, value = map(unquote_plus, section_key_value)
            section, key = section_key.split('.')
            if value.lower() in ('true', 'on'):
                value = True
            elif value.lower() == 'off':
                value = False
            else:
                try:
                    value = float(value) if '.' in value else int(value)
                except ValueError:
                    pass  # If not a number, leave as string
            if section in params and key in params[section]:
                params[section][key] = value

    # Write updated parameters back to config.json with custom pretty-printing
    with open('config.json', 'w') as f:
        f.write(pretty_print_json(params))


# Web server function
def web_server():
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(1)

    while True:
        conn, addr = s.accept()
        request = conn.recv(1024)
        request_str = str(request, 'utf-8')

        if request_str.startswith('POST'):
            post_data = request_str.split('\r\n\r\n')[-1]
            if "/restart" in request_str:
                conn.sendall("HTTP/1.1 200 OK\r\n\r\nRestarting...".encode('utf-8'))
                conn.close()
                utime.sleep(1)  # Delay to ensure the response is sent before resetting
                machine.reset()
            else:
                handle_post_data(post_data)
                conn.sendall("HTTP/1.1 200 OK\r\n\r\nSaved successfully!".encode('utf-8'))
        else:
            params = read_config_params()
            html_page = generate_html_page(params)
            conn.sendall(html_page.encode('utf-8'))

        conn.close()


# Start the web server
web_server()
