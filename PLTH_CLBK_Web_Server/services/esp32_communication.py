#!/usr/bin/env python3
"""
ESP32 Communication Module
Handles communication with ESP32 for solar panel, battery, and environmental sensors
PZEM sensors removed as requested
"""

import json
import logging
import threading
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any

import serial
import serial.tools.list_ports

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SensorData:
    """Data structure for ESP32 sensor readings matching slave program output"""
    # Solar panel sensors
    solar_voltage: float = 0.0
    solar_current: float = 0.0
    
    # Battery sensors
    battery_voltage: float = 0.0
    
    # Environmental sensors
    temperature: float = 0.0
    humidity: float = 0.0
    tma_value: float = 0.0  # Water level sensor
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for JSON serialization"""
        return {
            'solar_voltage': self.solar_voltage,
            'solar_current': self.solar_current,
            'battery_voltage': self.battery_voltage,
            'temperature': self.temperature,
            'humidity': self.humidity,
            'tma_value': self.tma_value
        }

class ESP32Controller:
    """ESP32 controller for non-PZEM sensors"""
    
    def __init__(self, esp32_port: str = "/dev/ttyUSB0", esp32_baudrate: int = 115200):
        self.esp32_port = esp32_port
        self.esp32_baudrate = esp32_baudrate
        self.esp32_connection = None
        self.is_monitoring = False
        self.sensor_data = SensorData()
        self.data_lock = threading.Lock()
        
    def connect(self) -> bool:
        """Connect to ESP32"""
        try:
            # Find ESP32 port automatically if default doesn't work
            if not self._test_port(self.esp32_port):
                found_port = self._find_esp32_port()
                if found_port:
                    self.esp32_port = found_port
                else:
                    logger.error("No ESP32 found on any port")
                    return False
            
            self.esp32_connection = serial.Serial(
                port=self.esp32_port,
                baudrate=self.esp32_baudrate,
                timeout=0.5
            )
            
            logger.info(f"Connected to ESP32 on {self.esp32_port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to ESP32: {e}")
            return False
    
    def _test_port(self, port: str) -> bool:
        """Test if port is available"""
        try:
            test_serial = serial.Serial(port, self.esp32_baudrate, timeout=1)
            test_serial.close()
            return True
        except:
            return False
    
    def _find_esp32_port(self) -> Optional[str]:
        """Find ESP32 port automatically"""
        possible_ports = ['/dev/ttyUSB0', '/dev/ttyUSB1', 'COM3', 'COM4', 'COM5', 'COM6']
        
        for port in possible_ports:
            if self._test_port(port):
                logger.info(f"Found potential ESP32 at {port}")
                return port
                
        # Also check system detected ports
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if 'USB' in port.description or 'ESP32' in port.description:
                if self._test_port(port.device):
                    return port.device
                    
        return None
    
    @property
    def is_connected(self) -> bool:
        """Check if ESP32 is connected"""
        return self.esp32_connection is not None and self.esp32_connection.is_open
    
    def start_monitoring(self):
        """Start sensor monitoring thread"""
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        monitor_thread = threading.Thread(target=self._monitor_sensors, daemon=True)
        monitor_thread.start()
        logger.info("ESP32 sensor monitoring started")
    
    def stop_monitoring(self):
        """Stop sensor monitoring"""
        self.is_monitoring = False
        logger.info("ESP32 sensor monitoring stopped")
    
    def _monitor_sensors(self):
        """Monitor sensors in background thread with optimized timing"""
        buffer = ""
        
        while self.is_monitoring and self.is_connected:
            try:
                # Read available data without clearing buffer
                if self.esp32_connection.in_waiting > 0:
                    new_data = self.esp32_connection.read(self.esp32_connection.in_waiting)
                    
                    try:
                        decoded_data = new_data.decode('utf-8', errors='ignore')
                        buffer += decoded_data
                        
                        # Process complete lines
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            line = line.strip()
                            
                            if line and line.startswith('{'):
                                try:
                                    data = json.loads(line)
                                    
                                    with self.data_lock:
                                        # Update sensor data efficiently
                                        self.sensor_data.solar_voltage = float(data.get('solar_voltage', 0.0))
                                        self.sensor_data.solar_current = float(data.get('solar_current', 0.0))
                                        self.sensor_data.battery_voltage = float(data.get('battery_voltage', 0.0))
                                        self.sensor_data.temperature = float(data.get('temperature', 0.0))
                                        self.sensor_data.humidity = float(data.get('humidity', 0.0))
                                        self.sensor_data.tma_value = float(data.get('tma_value', 0.0))
                                
                                except json.JSONDecodeError:
                                    continue  # Skip invalid JSON, don't log every error
                                except (KeyError, ValueError):
                                    continue  # Skip parsing errors
                    
                    except UnicodeDecodeError:
                        continue  # Skip decode errors
                
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error monitoring ESP32 sensors: {e}")
                time.sleep(1.0)
    
    def get_data(self) -> Optional[SensorData]:
        """Get current sensor data with minimal overhead"""
        if not self.is_connected:
            return None
        
        self.data_lock.acquire()
        try:
            # Return reference to current data without creating new object
            return self.sensor_data
        finally:
            self.data_lock.release()
    
    def disconnect(self):
        """Disconnect from ESP32"""
        self.stop_monitoring()
        if self.esp32_connection:
            try:
                self.esp32_connection.close()
                logger.info("Disconnected from ESP32")
            except:
                pass
            finally:
                self.esp32_connection = None

# Test function
def test_esp32_controller():
    """Test ESP32 controller functionality"""
    controller = ESP32Controller()
    
    if controller.connect():
        print("ESP32 connected successfully")
        controller.start_monitoring()
        
        try:
            for i in range(10):
                data = controller.get_data()
                if data:
                    print(f"Sensor data: {data.to_dict()}")
                time.sleep(2)
        finally:
            controller.disconnect()
    else:
        print("Failed to connect to ESP32")

if __name__ == "__main__":
    test_esp32_controller()
