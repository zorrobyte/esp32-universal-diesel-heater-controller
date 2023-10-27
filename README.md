# ESP32 Heater Controller

This project provides a controller for a heater system based on the ESP32 platform. It uses MQTT for remote communication, allowing the user to set the desired temperature and receive sensor readings. The controller also has safety measures in place to ensure the system operates within safe temperature ranges.

> :warning: **Note**: This code is currently **untested** and **broken**. Even when at the state of working, use with caution and test in a safe environment before deploying.

## :fire: Liability Disclaimer :fire:

**WARNING:** This code is provided "AS IS" without warranty of any kind. Use of this code in any form acknowledges your acceptance of these terms.

This code has **NOT** been tested in real-world scenarios. Improper usage, lack of understanding, or any combination thereof can result in significant property damage, injury, or even loss of life. Specifically, this code is related to controlling heating elements and systems, and there's a very real risk that it can **BURN YOUR SHIT DOWN**.

By using, distributing, or even reading this code, you agree to assume all responsibility and risk associated with it. The author(s), contributors, and distributors of this code will **NOT** be held liable for any damages, injuries, or other consequences you may face as a result of using or attempting to use this code.

Always approach such systems with caution. Ensure you understand the code, the systems involved, and the potential risks. If you're unsure, **DO NOT** use the code.

Stay safe and think before you act.

## Simulator
You can fuck around with this project in the [ESP32 simulator](https://wokwi.com/projects/379601065746814977)
Press play then mess with the switches and temp sensors
Toggle IS_SIMULATION False if you'd like and manually simulate startup of a diesel heater (hint, increase exhaust temp during startup between each step)

## Features:

- **Remote control via MQTT**:
  - Set target temperature
  - Start or stop the heater
  - Receive water and exhaust temperature readings
- **Temperature-based control** of air and fuel to regulate heating.
- **Safety shutdown** based on exhaust temperature.
- **Start-up and shutdown routines** to ensure safe operation.
- **Reconnect mechanisms** for WiFi and MQTT in case of disconnection.

## Hardware Requirements:

- ESP32 board (Up to change depending on ADC accuracy issues)
- DS18X20 temperature sensors (for water/body temp and exhaust) - depends on what most heaters have in them
- MOSFETs for controlling air, fuel, glow plug, and water pump
- Single pole switch for manual start/stop

## Software Dependencies:

- `machine` for hardware interfacing
- `time` for delays and timing
- `network` for WiFi communication
- `umqtt.simple` for MQTT communication
- `ds18x20` and `onewire` for DS18X20 temperature sensor interfacing

## Setup:

1. Connect the ESP32 board and other hardware components according to the pin definitions in the code (will be basing hardware on Webastardo)
2. Replace `MYSSID` and `PASSWORD` in the code with your WiFi SSID and password.
3. Set the `MQTT_SERVER` variable to your MQTT broker's IP address (need to make this optional)
4. Flash the script onto your ESP32.

## Usage:

- The system will automatically try to connect to the specified WiFi network and MQTT broker upon startup.
- Use the MQTT topics `heater/set_temp` and `heater/command` to set the target temperature and send start/stop commands, respectively.
- The system will publish sensor readings to the `heater/sensor_values` topic at regular intervals.
- If the exhaust temperature exceeds the safety threshold, the system will automatically shut down.
- The onboard switch can be used for manual start/stop control.

## Future Improvements/Ideas/Random notes:

- Possibly implement a PID controller for more accurate temperature control.
- Add support for more sensors and actuators, make things configurable.
- Improve error handling and system resilience.
- Possibly use an external ADC chip like the DS1232/ADS1234 to get around ESP32 ADC noise issues
- Would be nice to have some sort of air/fuel autotune
- Eventually would be nice to have a custom/own board that's universal use friendly, such as with screw wire terminals

## License
[See LICENSE.md](./LICENSE.md)

So many hobbiest software and hardware developers absolutely **RAGE** when their work is borrowed/stolen (ironically, the open source ones seem to be the loudest) and it's never personally made sense to me. I'm not here to make a business out of this and I get pleasure out of dicking around in my shop. When I was a teen, I received death threats from some incel german kid around updating game mod code for Arma 2 to Arma 3 (a shooter game) that had clearly been licensed under Apache, and a project I had previously contributed to. It set in my mind that I'd never be like that and betray the ethos of Open Source for such licensed projects.

I spent countless hours designing and implementing a steering angle sensor for the Openpilot self driving community and never saw a dime out of it. Now that project and other hardware is being made in China and sold online, in people's cars. I'm genuinely flattered that I did something that people find useful and no amount of angst would have changed that outcome. If I make a good enough product, people will generally want to buy it from me anyway as most people want to support the creators and developers and if they don't, it's not like they would of bought it from me regardless (think how absurd it is for companies to report "losses" due to piracy, were these "customers" going to buy it at the end of the day)?

So truly, do what the fuck you want. Sell it on Etsy, rename it and say it's yours. I truly don't care. It's just not on me if you burn your house/van/hicendia down or get sued. Otherwise, we'll continue to see awesome projects go closed source which hurts everybody.
