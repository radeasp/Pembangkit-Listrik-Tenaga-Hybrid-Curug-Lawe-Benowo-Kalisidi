#!/usr/bin/env python3
"""
Multi-Sensor Reader for Raspberry Pi 4B+
Reads data from multiple sensors for hydro power monitoring system
"""

import time
import threading
import serial
import smbus2
import RPi.GPIO as GPIO
from datetime import datetime

# GPIO pin assignments
KY003_PIN = 18      # Hall Effect sensor (digital input)
DHT11_PIN = 24      # DHT11 sensor (digital I/O)
HCSR04_TRIG = 23    # Ultrasonic sensor trigger
HCSR04_ECHO = 25    # Ultrasonic sensor echo
RAIN_PIN = 22       # Rain sensor (digital input)

# I2C addresses
BH1750_ADDR = 0x23  # Light sensor
BMP280_ADDR = 0x76  # Pressure sensor

# UART settings for PZEM-004T (menggunakan hardware UART)
PZEM_UART_PORT = '/dev/ttyS0'  # Hardware UART (GPIO 14-TX, GPIO 15-RX)
PZEM_BAUDRATE = 9600

class SensorReader:
    def __init__(self):
        # Initialize GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Setup GPIO pins
        GPIO.setup(KY003_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(DHT11_PIN, GPIO.OUT)
        GPIO.setup(HCSR04_TRIG, GPIO.OUT)
        GPIO.setup(HCSR04_ECHO, GPIO.IN)
        GPIO.setup(RAIN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Initialize I2C
        self.i2c = smbus2.SMBus(1)
        
        # Initialize UART for PZEM
        try:
            self.pzem_serial = serial.Serial(PZEM_UART_PORT, PZEM_BAUDRATE, timeout=1)
        except:
            print("Warning: PZEM-004T UART connection failed")
            self.pzem_serial = None
        
        # Sensor variables
        self.picohydro_rpm = 0
        self.lighting = 0
        self.ac_output_voltage = 0
        self.ac_output_current = 0
        self.temperature = 0
        self.humidity = 0
        self.pressure = 0
        self.tma_value = 0  # Water level in cm
        self.rain_status = False
        
        # RPM calculation variables
        self.pulse_count = 0
        self.last_rpm_time = time.time()
        
        # Setup interrupt for hall effect sensor
        GPIO.add_event_detect(KY003_PIN, GPIO.FALLING, callback=self.hall_pulse_callback, bouncetime=50)
        
        # Initialize sensors
        self.init_bh1750()
        self.init_bmp280()
        
    def hall_pulse_callback(self, channel):
        """Callback for hall effect sensor pulse counting"""
        self.pulse_count += 1
    
    def read_picohydro_rpm(self):
        """Calculate RPM from hall effect sensor pulses"""
        current_time = time.time()
        time_diff = current_time - self.last_rpm_time
        
        if time_diff >= 1.0:  # Calculate RPM every second
            # Assuming 1 magnet per revolution
            self.picohydro_rpm = (self.pulse_count * 60) / time_diff
            self.pulse_count = 0
            self.last_rpm_time = current_time
    
    def init_bh1750(self):
        """Initialize BH1750 light sensor"""
        try:
            # Power on and set continuous high resolution mode
            self.i2c.write_byte(BH1750_ADDR, 0x01)  # Power on
            time.sleep(0.01)
            self.i2c.write_byte(BH1750_ADDR, 0x10)  # Continuous high resolution mode
            time.sleep(0.12)
        except:
            print("Warning: BH1750 initialization failed")
    
    def read_lighting(self):
        """Read light intensity from BH1750 sensor"""
        try:
            data = self.i2c.read_i2c_block_data(BH1750_ADDR, 0x00, 2)
            self.lighting = (data[0] << 8 | data[1]) / 1.2
        except:
            self.lighting = 0
    
    def init_bmp280(self):
        """Initialize BMP280 pressure sensor"""
        try:
            # Read calibration data
            cal_data = self.i2c.read_i2c_block_data(BMP280_ADDR, 0x88, 24)
            
            # Parse calibration coefficients
            self.dig_T1 = cal_data[1] << 8 | cal_data[0]
            self.dig_T2 = self.to_signed16(cal_data[3] << 8 | cal_data[2])
            self.dig_T3 = self.to_signed16(cal_data[5] << 8 | cal_data[4])
            
            self.dig_P1 = cal_data[7] << 8 | cal_data[6]
            self.dig_P2 = self.to_signed16(cal_data[9] << 8 | cal_data[8])
            self.dig_P3 = self.to_signed16(cal_data[11] << 8 | cal_data[10])
            self.dig_P4 = self.to_signed16(cal_data[13] << 8 | cal_data[12])
            self.dig_P5 = self.to_signed16(cal_data[15] << 8 | cal_data[14])
            self.dig_P6 = self.to_signed16(cal_data[17] << 8 | cal_data[16])
            self.dig_P7 = self.to_signed16(cal_data[19] << 8 | cal_data[18])
            self.dig_P8 = self.to_signed16(cal_data[21] << 8 | cal_data[20])
            self.dig_P9 = self.to_signed16(cal_data[23] << 8 | cal_data[22])
            
            # Set sensor configuration
            self.i2c.write_byte_data(BMP280_ADDR, 0xF4, 0x27)  # Temp and pressure oversampling
            self.i2c.write_byte_data(BMP280_ADDR, 0xF5, 0xA0)  # Configuration
        except:
            print("Warning: BMP280 initialization failed")
    
    def to_signed16(self, val):
        """Convert unsigned 16-bit to signed"""
        return val - 65536 if val > 32767 else val
    
    def read_pressure(self):
        """Read pressure from BMP280 sensor"""
        try:
            # Read raw data
            data = self.i2c.read_i2c_block_data(BMP280_ADDR, 0xF7, 6)
            
            adc_P = (data[0] << 16 | data[1] << 8 | data[2]) >> 4
            adc_T = (data[3] << 16 | data[4] << 8 | data[5]) >> 4
            
            # Temperature compensation
            var1 = (adc_T / 16384.0 - self.dig_T1 / 1024.0) * self.dig_T2
            var2 = ((adc_T / 131072.0 - self.dig_T1 / 8192.0) * 
                    (adc_T / 131072.0 - self.dig_T1 / 8192.0)) * self.dig_T3
            t_fine = var1 + var2
            
            # Pressure compensation
            var1 = (t_fine / 2.0) - 64000.0
            var2 = var1 * var1 * self.dig_P6 / 32768.0
            var2 = var2 + var1 * self.dig_P5 * 2.0
            var2 = (var2 / 4.0) + (self.dig_P4 * 65536.0)
            var1 = (self.dig_P3 * var1 * var1 / 524288.0 + self.dig_P2 * var1) / 524288.0
            var1 = (1.0 + var1 / 32768.0) * self.dig_P1
            
            if var1 == 0:
                self.pressure = 0
            else:
                pressure = 1048576.0 - adc_P
                pressure = (pressure - (var2 / 4096.0)) * 6250.0 / var1
                var1 = self.dig_P9 * pressure * pressure / 2147483648.0
                var2 = pressure * self.dig_P8 / 32768.0
                pressure = pressure + (var1 + var2 + self.dig_P7) / 16.0
                self.pressure = pressure / 100.0  # Convert to hPa
        except:
            self.pressure = 0
    
    def read_pzem_data(self):
        """Read voltage and current from PZEM-004T sensor"""
        if not self.pzem_serial:
            return
        
        try:
            # PZEM-004T command to read all data
            command = bytes([0x01, 0x04, 0x00, 0x00, 0x00, 0x0A, 0x70, 0x0D])
            self.pzem_serial.write(command)
            time.sleep(0.1)
            
            response = self.pzem_serial.read(25)
            if len(response) >= 25:
                # Parse voltage (bytes 3-4)
                self.ac_output_voltage = ((response[3] << 8) | response[4]) / 10.0
                
                # Parse current (bytes 7-10)
                self.ac_output_current = (((response[7] << 24) | (response[8] << 16) | 
                                         (response[9] << 8) | response[10]) / 1000.0)
        except:
            self.ac_output_voltage = 0
            self.ac_output_current = 0
    
    def read_dht11(self):
        """Read temperature and humidity from DHT11 sensor"""
        try:
            # Send start signal
            GPIO.setup(DHT11_PIN, GPIO.OUT)
            GPIO.output(DHT11_PIN, GPIO.HIGH)
            time.sleep(0.25)
            GPIO.output(DHT11_PIN, GPIO.LOW)
            time.sleep(0.02)
            GPIO.output(DHT11_PIN, GPIO.HIGH)
            
            # Switch to input mode
            GPIO.setup(DHT11_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # Read data
            data = []
            timeout_count = 0
            
            # Wait for sensor response
            while GPIO.input(DHT11_PIN) == GPIO.HIGH:
                timeout_count += 1
                if timeout_count > 100:
                    return
                time.sleep(0.00001)
            
            # Read 40 bits of data
            for i in range(40):
                bit_start = time.time()
                while GPIO.input(DHT11_PIN) == GPIO.LOW:
                    if time.time() - bit_start > 0.001:
                        return
                
                bit_start = time.time()
                while GPIO.input(DHT11_PIN) == GPIO.HIGH:
                    if time.time() - bit_start > 0.001:
                        return
                
                if (time.time() - bit_start) > 0.00004:
                    data.append(1)
                else:
                    data.append(0)
            
            # Convert bits to bytes
            humidity_bit = data[0:8]
            humidity_point_bit = data[8:16]
            temperature_bit = data[16:24]
            temperature_point_bit = data[24:32]
            check_bit = data[32:40]
            
            humidity_data = 0
            for bit in humidity_bit:
                humidity_data = (humidity_data << 1) | bit
                
            temperature_data = 0
            for bit in temperature_bit:
                temperature_data = (temperature_data << 1) | bit
            
            self.humidity = humidity_data
            self.temperature = temperature_data
            
        except:
            self.temperature = 0
            self.humidity = 0
    
    def read_hcsr04(self):
        """Read water level using HC-SR04 ultrasonic sensor"""
        try:
            # Send trigger pulse
            GPIO.output(HCSR04_TRIG, GPIO.HIGH)
            time.sleep(0.00001)
            GPIO.output(HCSR04_TRIG, GPIO.LOW)
            
            # Measure echo duration
            start_time = time.time()
            while GPIO.input(HCSR04_ECHO) == GPIO.LOW:
                if time.time() - start_time > 0.1:
                    return
                start_time = time.time()
            
            end_time = time.time()
            while GPIO.input(HCSR04_ECHO) == GPIO.HIGH:
                if time.time() - start_time > 0.1:
                    return
                end_time = time.time()
            
            # Calculate distance
            duration = end_time - start_time
            distance = (duration * 34300) / 2  # Speed of sound: 343 m/s
            
            # Convert to water level (sensor is 100cm above channel bottom)
            water_level = 100 - distance
            self.tma_value = max(0, water_level)  # Ensure non-negative value
            
        except:
            self.tma_value = 0
    
    def read_rain_status(self):
        """Read rain sensor status"""
        try:
            # Rain sensor typically outputs LOW when rain is detected
            self.rain_status = not GPIO.input(RAIN_PIN)
        except:
            self.rain_status = False
    
    def read_all_sensors(self):
        """Read all sensors with optimized timing"""
        # Fast sensors (digital/interrupt based)
        self.read_picohydro_rpm()
        self.read_rain_status()
        
        # Medium speed sensors (I2C)
        self.read_lighting()
        self.read_pressure()
        
        # Slower sensors (require timing delays)
        self.read_hcsr04()
        
        # UART sensor (moderate speed)
        self.read_pzem_data()
        
        # Slowest sensor (DHT11 - requires 2+ seconds between reads)
        # Only read DHT11 every 3rd cycle to avoid timing issues
        if not hasattr(self, 'dht_counter'):
            self.dht_counter = 0
        self.dht_counter += 1
        if self.dht_counter >= 3:
            self.read_dht11()
            self.dht_counter = 0
    
    def print_sensor_data(self):
        """Print all sensor readings"""
        print(f"\n=== Sensor Readings - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
        print(f"Hydro RPM (picohydro_rpm): {self.picohydro_rpm:.2f} RPM")
        print(f"Light Level (lighting): {self.lighting:.2f} Lux")
        print(f"AC Output Voltage (ac_output_voltage): {self.ac_output_voltage:.1f} V")
        print(f"AC Output Current (ac_output_current): {self.ac_output_current:.3f} A")
        print(f"Temperature (temperature): {self.temperature}°C")
        print(f"Humidity (humidity): {self.humidity}%")
        print(f"Pressure (pressure): {self.pressure:.2f} hPa")
        print(f"Water Level (tma_value): {self.tma_value:.1f} cm")
        print(f"Rain Status (rain_status): {'Rain Detected' if self.rain_status else 'No Rain'}")
        print("=" * 60)
    
    def cleanup(self):
        """Clean up GPIO and close connections"""
        GPIO.cleanup()
        if self.pzem_serial:
            self.pzem_serial.close()

def main():
    sensor_reader = SensorReader()
    
    try:
        print("Multi-Sensor Reader Started")
        print("Press Ctrl+C to stop")
        
        while True:
            start_time = time.time()
            sensor_reader.read_all_sensors()
            sensor_reader.print_sensor_data()
            
            # Ensure consistent 1-second intervals
            execution_time = time.time() - start_time
            sleep_time = max(0, 1.0 - execution_time)
            time.sleep(sleep_time)
            
            # Print timing info every 10 cycles for monitoring
            if not hasattr(sensor_reader, 'cycle_count'):
                sensor_reader.cycle_count = 0
            sensor_reader.cycle_count += 1
            if sensor_reader.cycle_count % 10 == 0:
                print(f"Execution time: {execution_time:.3f}s, Sleep: {sleep_time:.3f}s")
            
    except KeyboardInterrupt:
        print("\nStopping sensor reader...")
    finally:
        sensor_reader.cleanup()

if __name__ == "__main__":
    main()
