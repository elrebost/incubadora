Some python scripts to use with a Raspberry PI Zero to manage a bird incubator.
## Hardware:
- Raspberry PI Zero.
- DHT22: Humidity and temperature sensor
- Screen: 0.91 inch OLED display module white/blue
- Relay module to enable/disable a Lamp used to add temperature

## Software:
- Python3
- Infuxdb2 server to report the measured data

## Some hardware details:
**DHT22: Humidity and temperature sensor**
- **Humidity** must be in **[50-60]%**
- **Temperature** must be in **[37-38] Celsius**
- **DHT22**: +-0.5 Celsius sensibility. Sampling rate: 1 every 2 seconds
	- DHT22: Adafruit AM2302 module 
	- pip3 install --install-option="--force-pi" Adafruit_DHT
	- https://pimylifeup.com/raspberry-pi-humidity-sensor-dht22/
	- DHT22 library is available at
	- https://github.com/danjperron/PicoDHT22
- **DHT11**: +- 2.0 Celsius sensibility. Sampling rate: 1 every second
	- Micropython library dht.DHT11

**Screen: 0.91 inch OLED display module white/blue**
OLED 128X32 LCD LED Display SSD1306 12864 0.91 IIC i2C (SDA + SCL 3.3v)
At the PI Zero edit config.txt and commentout or add these 2 lines to enable I2C at pins 2 (SDA) and 3 (SCL):
	dtparam=i2c_arm=on
	dtoverlay=i2c1,pins_2_3

More info at:
https://forums.raspberrypi.com/viewtopic.php?t=316627

At a Raspberry PI:
- python3 (pip install luma.oled)
	- https://github.com/rm-hull/luma.oled

At PI Pico
- MicroPython
	- https://docs.micropython.org/en/latest/esp8266/tutorial/ssd1306.html

**How it works**
Every 2 seconds we read the temperature and humidity values.
If we need more temperature
then 
	we enable the relay to set the lamp to ON for heating
else 
	we set the lamp to OFF.
We save the measurements to the influxdb.

## Systemd
The script must run as a service under systemd
Create the file /etc/systemd/system/incubadora.service
	[Unit]
	Description=Incubadora monitor
	Wants=network-online.target
	After=network-online.target
	
	[Service]
	User=mau
	ExecStart=/home/mau/scripts/incubadora/start.sh
	Restart=on-failure

	[Install]
	WantedBy=multi-user.target

### And enable and start the service:
	sudo systemctl daemon-reload
	sudo systemctl start incubadora.service
	sudo systemctl status incubadora.service
	sudo systemctl enable incubadora.service
