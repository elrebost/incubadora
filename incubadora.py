"""
DHT22: Humidity and temperature sensor
    Humidity must be in [50-60]% 
    Temperature must be in [37-38] Celsius
    # DHT22: +-0.5 Celsius sensibility. Sampling rate: 1 every 2 seconds
    # DHT22: Adafruit AM2302 module 
    # pip3 install --install-option="--force-pi" Adafruit_DHT
    # https://pimylifeup.com/raspberry-pi-humidity-sensor-dht22/
    # DHT22 library is available at
    # https://github.com/danjperron/PicoDHT22
    # DHT11: +- 2.0 Celsius sensibility. Sampling rate: 1 every second
    # Micropython library dht.DHT11
Screen: 0.91 inch OLED display module white/blue
    OLED 128X32 LCD LED Display SSD1306 12864 0.91 IIC i2C (SDA + SCL 3.3v)
    At PI Zero edit config.txt and uncomment
    dtparam=i2c_arm=on
    dtoverlay=i2c1,pins_2_3
    More info at:
    https://forums.raspberrypi.com/viewtopic.php?t=316627

    On python3 (pip install luma.oled)
    https://github.com/rm-hull/luma.oled
    On MicroPython
    https://docs.micropython.org/en/latest/esp8266/tutorial/ssd1306.html
Relay: Any
"""
import os
import sys
import logging
import time
import datetime
import RPi.GPIO as GPIO
import Adafruit_DHT
from influxdb_client import InfluxDBClient, Point, WritePrecision, WriteOptions
from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import ImageFont
from dotenv import load_dotenv, find_dotenv

logging.basicConfig(format='%(asctime)s - %(name)s - %(message)s', level=logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
#logger = logging.getLogger(__name__)
logger = logging.getLogger('incubadora')
logger.addHandler(handler)
logger.info(f"Starting {__file__}")

load_dotenv(find_dotenv())

#capicua-pl
INFLUX_HOST = os.getenv('INFLUX_HOST')
INFLUX_ORG = os.getenv('INFLUX_ORG')
INFLUX_TOKEN = os.getenv('INFLUX_TOKEN')
INFLUX_BUCKET = os.getenv('INFLUX_BUCKET')

if not INFLUX_HOST or not INFLUX_ORG or not INFLUX_TOKEN or not INFLUX_BUCKET:
   logger.error('Cannot load env values')
   sys.exit(1)
else:
    logger.info(f"Logging to influx host {INFLUX_HOST}")

DHT_SENSOR = Adafruit_DHT.AM2302
TARGET_TEMPERATURE = 37.7
TARGET_HUMIDITY = 50
SAMPLING_RATE = 6
BEEP_TIME = 0.5
FONT_PATH= f"{os.path.dirname(os.path.abspath(__file__))}/fonts/Arial.ttf"
FONT_SIZE = 28

query = 'from(bucket: "incubadora")\
 range(start: -1m)\
 filter(fn: (r) => r._measurement == "incubadora_pollets")\
 filter(fn: (r) => r._field == "temperature")'

#Define the PINs to use
RELAY_PIN = 23 #GPIO 23 pin 16
DHT_PIN = 24 #GPIO 24 pin 18
BUZZER_PIN = 25 #GPIO 25 pin 22
#led_PIN = 21 #GPIO 21 pin 40

#Setup the PINs
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT)
GPIO.setup(DHT_PIN, GPIO.IN)
GPIO.setup(BUZZER_PIN, GPIO.OUT)
#GPIO.setup(led_PIN, GPIO.OUT)

#def do_nothing(obj):
#    pass

# To test the power set led to on
#GPIO.output(led_PIN, GPIO.HIGH)

def do_beep(t):
    GPIO.output(BUZZER_PIN, GPIO.HIGH)
    time.sleep(t)
    GPIO.output(BUZZER_PIN, GPIO.LOW)

# Prepare the influx client
influx_client = InfluxDBClient(url=INFLUX_HOST, token=INFLUX_TOKEN, org=INFLUX_ORG, debug=False)
#influx_write_api = influx_client.write_api(SYNCHRONOUS)

influx_write_api = influx_client.write_api(write_options=WriteOptions(batch_size=500,
                                                             flush_interval=10_000,
                                                             jitter_interval=2_000,
                                                             retry_interval=5_000,
                                                             max_retries=5,
                                                             max_retry_delay=30_000,
                                                             exponential_base=2))
influx_query_api = influx_client.query_api()

#Load the  Font
font = ImageFont.truetype(FONT_PATH,FONT_SIZE)

#Prepare the i2c and setup the ssd1306
serial = i2c(port=1, address=0x3C)
device = ssd1306(serial, rotate=0)
#device.cleanup = do_nothing

device.clear()
with canvas(device) as draw:
    draw.text((0, 0), "Iniciant", fill="white", font=font)
    draw.text((0, 35), "test ...", fill="white", font=font)

logger.debug("Testing relay for 3 seconds.")
# Test the relay is working
for i in range(0,3):
    print(f"Relay test #{i}")
    GPIO.output(RELAY_PIN, GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output(RELAY_PIN, GPIO.LOW)
    do_beep(BEEP_TIME)
    time.sleep(0.5)

while True:
    # Read humidity and temperature 
    humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
   
    if not humidity or not temperature:
        print("ERROR: Cannot read the humidity or the temperature")
        logger.error("Cannot read the humidity or the temperature")
        continue
    
    temperature = round(temperature,2)
    humidity = round(humidity,2)
    utc_datetime = datetime.datetime.utcnow()
    data = {"measurement": "incubadora_pollets", "tags": 
            {"location": "incubadora_casa"}, "fields": {
                "temperature": temperature, "humidity": humidity},
            "time": utc_datetime}
    logger.debug(f"Sending data (humidity={humidity} temp={temperature} at {utc_datetime}) to influxdb at {INFLUX_HOST}")
    influx_write_api.write(INFLUX_BUCKET, INFLUX_ORG, [data])

    # Enable relay to raise the temperature
    if temperature < TARGET_TEMPERATURE:
        print("Enabling the relay")
        logger.info("Enabling the relay")
        GPIO.output(RELAY_PIN, GPIO.HIGH)
        do_beep(BEEP_TIME)
    else:
        print("Disabling the relay")
        logger.info("Disabling the relay")
        GPIO.output(RELAY_PIN, GPIO.LOW)
    
    # Show the temperature and the humidity got
    temp_str = f"{temperature:0.1f} C"
    humidity_str = f"{humidity:0.1f} %"
    logger.debug(f"T={temp_str} H={humidity_str}")
    
    # Show at the display the temperature and the humidity got
    logger.debug("Updating the canvas LCD")
    device.clear()
    with canvas(device) as draw:
        draw.text((0, 0), temp_str, fill="white",font=font)
        draw.text((0, 35), humidity_str, fill="white",font=font)
    
    #Wait the sampling rate
    time.sleep(SAMPLING_RATE)
