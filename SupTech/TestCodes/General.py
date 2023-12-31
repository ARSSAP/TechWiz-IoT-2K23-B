import Adafruit_DHT
import time
from pymongo import MongoClient

DHT_SENSOR = Adafruit_DHT.DHT11
DHT_PIN = 24

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client["sensor_data"]
collection = db["dht11_data"]

while True:
    humidity, temperature = Adafruit_DHT.read(DHT_SENSOR, DHT_PIN)

    if humidity is not None and temperature is not None:
        data = {
            "timestamp": time.time(),
            "temperature": temperature,
            "humidity": humidity
        }
        collection.insert_one(data)
        print("Data uploaded to MongoDB")
    else:
        print("Failed to retrieve data from DHT11 sensor")

    time.sleep(2)

client.close()