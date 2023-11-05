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

# Common helper functions
import hardwareConfig as config


def set_fan_percentage(speed_percentage):
    """
    Set the fan speed according to the given percentage.

    :param speed_percentage: The speed percentage for the fan.
    """
    if config.FAN_RPM_SENSOR:
        # Directly set the fan speed percentage for RPM control
        config.fan_speed_percentage = speed_percentage
    else:
        # Special case: 0% should equal 0% output
        if speed_percentage == 0:
            scaled_speed = 0
        else:
            # Ensure speed_percentage is within limits defined in config
            speed_percentage = max(config.MIN_FAN_PERCENTAGE, min(speed_percentage, config.MAX_FAN_PERCENTAGE))  # Limit to 0-100

            # Scale the speed_percentage taking into account the FAN_START_PERCENTAGE
            scaled_speed = config.FAN_START_PERCENTAGE + (
                    speed_percentage * (config.MAX_FAN_PERCENTAGE - config.FAN_START_PERCENTAGE) / 100)

        config.fan_speed_percentage = scaled_speed

        # Calculate the fan duty and set it
        fan_duty = int((config.fan_speed_percentage / 100) * config.FAN_MAX_DUTY)
        config.air_pwm.duty(fan_duty)
