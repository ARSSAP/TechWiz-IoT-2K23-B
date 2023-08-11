import RPi.GPIO as GPIO
import time

# Set up GPIO mode
GPIO.setmode(GPIO.BCM)

# Define the GPIO pin to which the sensor is connected
sensor_pin = 24

# Set the GPIO pin as an input
GPIO.setup(sensor_pin, GPIO.IN)

try:
    while True:
        # Read sensor data
        sensor_value = GPIO.input(sensor_pin)
        
        # Print the sensor value
        if sensor_value == GPIO.HIGH:
            print("Water Detected")
        else:
            print("No Water")
        
        time.sleep(1)
        
except KeyboardInterrupt:
    # Clean up GPIO on Ctrl+C exit
    GPIO.cleanup()
