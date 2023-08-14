import schedule
import random
import time
import logging
import digitalio
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_dht
import board
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import adafruit_character_lcd.character_lcd_i2c as character_lcd
import busio

# Set up logging
logging.basicConfig(level=logging.INFO)



# Configuration values
CONFIG = {
    'local_token': 'ajCjWngMkTYbvEVn7tE4NadkysKi2tQMMSZDHAdQurLWB83WrW4_QMrx29FHFEtrBMHSElvAnIYEx9ZBBPyc3A==',
    'local_org': 'aptech_kor',
    'local_url': 'http://localhost:8086',
    'local_bucket': 'smart_farm_bucket',
    'remote_token': '8ov6t2pEF6pv-ONbjtBVcRlUKlHLGPvLkL7Pad97le-BRT-V-XO0JHz2yZKYzJEyquUUQWajVA--CnLUFh2GmA==',
    'remote_org': 'aptech_kor',
    'remote_url': 'http://ec2-3-89-246-231.compute-1.amazonaws.com:8086/',
    'remote_bucket': 'smart_farm_bucket',
    'dht_pin': board.D4,
    'relay_pin': board.D16,
    'buzzer_pin': board.D18,
    'temp_threshold': 30,
    'humidity_threshold': 40,
    'soil_moisture_thresholds': (50, 90),
    'motor_on_duration_max': 5 * 60,
    'water_level_read_interval': 3,
    # 'other_sensors_read_interval': 3 * 60,
    'other_sensors_read_interval': 3,
    'slope': -0.0171,
    'intercept': 7.64,
    'lcd_columns': 16,
    'lcd_rows': 2,
    'lcd_i2c_address': 0x48,
    'DRY_SOIL_READING': 26000,
    'WET_SOIL_READING': 20000,
    'low_threshold': 0,
    'medium_threshold': 9000,
    'high_threshold': 15000,

}

class SmartFarm:
    def __init__(self, config):
        self.config = config
        self.temperature = 0
        self.humidity = 0
        self.ph = 0
        self.soil_moisture = 0
        self.water_level_value = 0
        self.water_level_status = ""
        self.motor_status = "OFF"
        
        # Set up local InfluxDB
        self.local_client = InfluxDBClient(url=self.config['local_url'], token=self.config['local_token'], org=self.config['local_org'])
        self.local_write_api = self.local_client.write_api(write_options=SYNCHRONOUS)

        # Set up remote InfluxDB
        self.remote_client = InfluxDBClient(url=self.config['remote_url'], token=self.config['remote_token'], org=self.config['remote_org'])
        self.remote_write_api = self.remote_client.write_api(write_options=SYNCHRONOUS)

        # DHT sensor
        self.dht = adafruit_dht.DHT11(self.config['dht_pin'], use_pulseio=False)

        # Relay pin
        self.relay_pin = digitalio.DigitalInOut(self.config['relay_pin'])
        self.relay_pin.direction = digitalio.Direction.OUTPUT
        self.relay_pin.value = False

        # Buzzer configuration
        self.buzzer_pin = digitalio.DigitalInOut(self.config['buzzer_pin'])
        self.buzzer_pin.direction = digitalio.Direction.OUTPUT
        self.buzzer_pin.value = False 

        # LCD configuration
        i2c = busio.I2C(board.SCL, board.SDA)
        self.lcd = character_lcd.Character_LCD_I2C(i2c, self.config['lcd_columns'], self.config['lcd_rows'], address=self.config['lcd_i2c_address'])
        self.lcd.clear()

         # Welcome message
        self.lcd.message = "Welcome!"
        time.sleep(2) # Display for 2 seconds

        # Project name
        self.lcd.clear()
        self.lcd.message = "TECHWIX 2023" # Replace with your project name
        time.sleep(2) # Display for 2 seconds

        # Loading animation
        self.lcd.clear()
        self.lcd.message = "Loading"
        for i in range(3):
            self.lcd.message = '.'
            time.sleep(1) # Display each dot for 1 second
        
        # Create the I2C bus and ADC object
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.ads = ADS.ADS1115(self.i2c)

        # Schedule jobs
        schedule.every(self.config['water_level_read_interval']).seconds.do(self.read_water_level_job)
        schedule.every(self.config['other_sensors_read_interval']).seconds.do(self.read_other_sensors_job)

    
    def update_lcd_display(self):
        if self.motor_status == "ON":
            display_text = "Watering...\nMotor: ON"
        else:
            display_text = "T:{} H:{} L:{}\nP:{} M:{}".format(self.temperature, self.humidity, self.water_level_status, self.ph, self.motor_status)

        self.lcd.message = display_text
    
    def read_dht11(self):
        try:
            return self.dht.temperature, self.dht.humidity
        except Exception as e:
            logging.error(f"Error reading DHT11: {e}")
            return None, None

    def read_soil_moisture_raw(self):
        try:
            chan = AnalogIn(self.ads, ADS.P2)
            value = chan.value
            # value = max(0, value)
            return value
        except Exception as e:
            logging.error(f"Error reading soil moisture: {e}")
            return None

    def map_value(self, x, in_min, in_max, out_min, out_max):
        return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

    def read_soil_moisture(self):
        raw_value = self.read_soil_moisture_raw()
        if raw_value is not None:
            calibrated_value = self.map_value(raw_value, self.config['DRY_SOIL_READING'], self.config['WET_SOIL_READING'], 0, 100)
            return round(calibrated_value,2)
        else:
            return None

    def read_ph(self):
        try:
            chan = AnalogIn(self.ads, ADS.P1)
            voltage = chan.voltage
            value = voltage * self.config['slope'] + self.config['intercept']
            return round(value,2)
        except Exception as e:
            logging.error(f"Error reading pH: {e}")
            return None

   
    def read_water_level(self):
        try:
            chan = AnalogIn(self.ads, ADS.P0)
            value = chan.value
            value = max(0, value)

            low_threshold = self.config['low_threshold']
            medium_threshold = self.config['medium_threshold']
            high_threshold = self.config['high_threshold']

            percentage = ((value - low_threshold) / (high_threshold - low_threshold)) * 100

            status = "low" if percentage <= 0 else "medium" if percentage < 40 else "high"
            return round(percentage, 2), status 
        except Exception as e:
            logging.error(f"Error reading water level: {e}")
            return None, None

    def control_motor_relay(self, status):
        self.relay_pin.value = status == "ON"

    def control_motor(self):
        # logging.info(f"Before control: Motor status: {self.motor_status}, Water level status: {self.water_level_status}, Soil moisture: {self.soil_moisture}")
     
        if self.water_level_status == "low" or self.soil_moisture > self.config['soil_moisture_thresholds'][1]:
            self.motor_status = "OFF"
        elif (self.temperature > self.config['temp_threshold'] or self.humidity < self.config['humidity_threshold'] or self.soil_moisture < self.config['soil_moisture_thresholds'][0]):
            self.motor_status = "ON"
        else:
            self.motor_status = "OFF"
        # logging.info(f"After control: Motor status: {self.motor_status}")
        self.control_motor_relay(self.motor_status)


    def read_water_level_job(self):
        self.water_level_value, self.water_level_status = self.read_water_level()
        self.soil_moisture = self.read_soil_moisture() or 0

        if self.water_level_status == "low":
            self.buzzer_pin.value = True # Turn buzzer ON
        else:
            self.buzzer_pin.value = False # Turn buzzer OFF

    def read_other_sensors_job(self):
        self.temperature, self.humidity = self.read_dht11()
        self.temperature = self.temperature  or 0
        self.humidity = self.humidity or 0

        self.ph = self.read_ph() or 0

    def run(self):

        # Initial readings
        self.temperature, self.humidity = self.read_dht11()
        self.temperature = self.temperature or 0
        self.humidity  = self.humidity  or 0

        self.ph = self.read_ph() or 0
        self.soil_moisture = self.read_soil_moisture() or 0
        self.water_level_value, self.water_level_status = self.read_water_level()

        while True:
            schedule.run_pending()
            self.control_motor()
            # Rest of the main loop code...
            logging.info(f"Temp: {self.temperature}, Humidity: {self.humidity}, pH: {self.ph}, Moisture: {self.soil_moisture}, Water_Level: {self.water_level_value}, Water_Level_Status: {self.water_level_status}, Motor_Status: {self.motor_status}")
            self.update_lcd_display()
            if self.motor_status == "ON":
                start_time = time.time()
                while self.soil_moisture < self.config['soil_moisture_thresholds'][1] and time.time() - start_time < self.config['motor_on_duration_max']:
                    self.soil_moisture = self.read_soil_moisture()
                    logging.info(f"Watering... Current soil moisture: {self.soil_moisture}")
                    time.sleep(30)
                elapsed_time = time.time() - start_time
                self.motor_status = "OFF"
                logging.info(f"Watering completed. Final soil moisture: {self.soil_moisture}")
                logging.info(f"Motor was ON for {elapsed_time} seconds")

            motor_status_value = 1 if self.motor_status == "ON" else 0

            p = Point("measurement_data").tag("location", "Karachi")\
                .field("temperature", self.temperature)\
                .field("humidity", self.humidity)\
                .field("ph", self.ph)\
                .field("soil_moisture", self.soil_moisture)\
                .field("water_level_value", self.water_level_value)\
                .field("water_level_status", self.water_level_status)\
                .field("motor_status", motor_status_value)
            
            
             # Write to local InfluxDB
            try:
                self.local_write_api.write(bucket=self.config['local_bucket'], org=self.config['local_org'], record=p)
            except Exception as e:
                print(f"Error writing to local InfluxDB: {e}")

            # # Write to remote InfluxDB
            # try:
            #     self.remote_write_api.write(bucket=self.config['remote_bucket'], org=self.config['remote_org'], record=p)
            # except Exception as e:
            #     print(f"Error writing to remote InfluxDB: {e}")

            time.sleep(1)


if __name__ == "__main__":
    smart_farm = SmartFarm(CONFIG)
    try:
        smart_farm.run()
    except KeyboardInterrupt:
        smart_farm.buzzer_pin.value = False
        smart_farm.relay_pin.value = False
    finally:
        smart_farm.buzzer_pin.value = False
        smart_farm.relay_pin.value = False
        