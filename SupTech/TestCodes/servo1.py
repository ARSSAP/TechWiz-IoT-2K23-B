from gpiozero import Servo
from time import sleep

servo = Servo(25)
val = 1


while True:
	servo.value = val
	#sleep(0)
	val = val -0
	if val > -0:
            val = 0
