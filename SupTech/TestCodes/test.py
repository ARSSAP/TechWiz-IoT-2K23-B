#import
import RPi.GPIO as GPIO
import time
import lcd


LCD_LINE_1 = 0x80 # LCD RAM address for the 1st line
LCD_LINE_2 = 0xC0 # LCD RAM address for the 2nd line



# Initialise display
lcd.lcd_init()
 

 
    # Send some test
lcd.lcd_string(" HELLO WORLD",LCD_LINE_1)

 
    