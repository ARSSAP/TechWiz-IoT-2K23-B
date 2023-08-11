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
        #sensor_value = GPIO.input(sensor_pin)
        sensor_value = 100
        # Print the sensor value
        print("Sensor Value:", sensor_value)
        
        time.sleep(1)
        
except KeyboardInterrupt:
    # Clean up GPIO on Ctrl+C exit
    GPIO.cleanup()
