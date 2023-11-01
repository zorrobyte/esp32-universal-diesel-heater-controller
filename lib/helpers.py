# Common helper functions
import config


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
            speed_percentage = max(0, min(speed_percentage, 100))  # Limit to 0-100

            # Scale the speed_percentage taking into account the FAN_START_PERCENTAGE
            scaled_speed = config.FAN_START_PERCENTAGE + (
                    speed_percentage * (config.MAX_FAN_PERCENTAGE - config.FAN_START_PERCENTAGE) / 100)

        config.fan_speed_percentage = scaled_speed

        # Calculate the fan duty and set it
        fan_duty = int((config.fan_speed_percentage / 100) * config.FAN_MAX_DUTY)
        config.air_pwm.duty(fan_duty)
