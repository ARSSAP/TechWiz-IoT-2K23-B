import picamera
import time

with picamera.PiCamera() as camera:
    camera.resolution = (640, 480)  # Set the resolution
    camera.start_preview()
    time.sleep(2)  # Warm-up time
    camera.capture('image.jpg')  # Capture an image and save it
    camera.stop_preview()
