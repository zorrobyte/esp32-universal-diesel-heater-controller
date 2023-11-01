import utime
import config
import machine

# Initialize global variables
rpm_interrupt_count = 0
last_measurement_time = 0


# Interrupt handler function for the Hall Effect sensor
def rpm_interrupt_handler(pin):
    global rpm_interrupt_count
    rpm_interrupt_count += 1


# Initialize the interrupt for the Hall Effect Sensor
config.FAN_RPM_PIN.irq(trigger=machine.Pin.IRQ_RISING, handler=rpm_interrupt_handler)


class PIDController:
    def __init__(self, kp, ki, kd):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.prev_error = 0
        self.integral = 0

    def calculate(self, setpoint, current_value):
        error = setpoint - current_value
        self.integral += error
        derivative = error - self.prev_error

        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        self.prev_error = error

        return output


def set_fan_duty_cycle(duty_cycle):
    # Clip the duty cycle within the allowed range
    duty_cycle = max(0, min(duty_cycle, config.FAN_MAX_DUTY))
    config.air_pwm.duty(duty_cycle)


def fan_control_thread():
    pid = PIDController(kp=1.0, ki=0.1, kd=0.01)  # Initialize your PID controller with appropriate constants

    global rpm_interrupt_count, last_measurement_time

    while True:
        # Read current RPM from sensor
        current_time = utime.ticks_ms()
        elapsed_time = utime.ticks_diff(current_time, last_measurement_time) / 1000.0  # Convert to seconds
        current_rpm = (rpm_interrupt_count / 2) / (elapsed_time / 60)
        rpm_interrupt_count = 0
        last_measurement_time = current_time

        # Write the current RPM to config
        config.fan_rpm = current_rpm

        # Calculate target RPM based on config.fan_speed_percentage
        target_rpm = config.MIN_FAN_RPM + (
                config.fan_speed_percentage * (config.MAX_FAN_RPM - config.MIN_FAN_RPM) / 100)

        # Calculate the PID output
        pid_output = pid.calculate(target_rpm, current_rpm)

        # Calculate the new duty cycle
        new_duty_cycle = int((pid_output / 100) * config.FAN_MAX_DUTY)

        # Use the PID output to set the fan speed
        set_fan_duty_cycle(new_duty_cycle)

        # Sleep for a bit before the next iteration
        utime.sleep(0.2)  # 200 ms
