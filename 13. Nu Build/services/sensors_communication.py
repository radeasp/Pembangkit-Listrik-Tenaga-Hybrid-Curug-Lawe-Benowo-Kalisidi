#!/usr/bin/env python3
import time
import json
import threading
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
import queue
import copy

# Import the actual sensor communication modules
try:
    from rpio_communication import SensorReader
    from stm32_communication import STM32Controller, SensorData as STM32SensorData
    SENSORS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import sensor modules: {e}")
    print("Running in mock mode for development")
    SensorReader = None
    STM32Controller = None
    STM32SensorData = None
    SENSORS_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CombinedSensorData:
    """Combined data structure for all sensor readings"""
    # Timestamp
    timestamp: float = 0.0
    datetime_str: str = ""
    
    # Pico Hydro Generator (from both RPi and STM32)
    picohydro_voltage: float = 0.0      # STM32
    picohydro_current: float = 0.0      # STM32
    picohydro_rpm: float = 0.0          # RPi
    picohydro_charging_current: float = 0.0  # STM32
    
    # Solar Panel Generator (from both RPi and STM32)
    solar_voltage: float = 0.0          # STM32
    solar_current: float = 0.0          # STM32
    lighting: float = 0.0               # RPi (ambient light)
    
    # Battery System (from STM32)
    battery_voltage: float = 0.0        # STM32
    battery_input_current: float = 0.0  # STM32 (battery_in_current)
    battery_output_current: float = 0.0 # STM32 (battery_out_current)
    
    # Load/Beban (from RPi)
    dc_input_current: float = 0.0       # Calculated from battery output
    ac_output_voltage: float = 0.0      # RPi
    ac_output_current: float = 0.0      # RPi
    
    # Dump Load (from STM32)
    dumpload_voltage: float = 0.0       # STM32
    dumpload_current: float = 0.0       # STM32
    
    # Environment (from RPi)
    temperature: float = 0.0            # RPi
    humidity: float = 0.0               # RPi
    pressure: float = 0.0               # RPi
    tma_value: float = 0.0              # RPi (water level)
    rain_status: bool = False           # RPi
    
    # PID Controller Parameters (from STM32)
    setpoint: float = 0.0               # STM32
    kp: float = 0.0                     # STM32
    ki: float = 0.0                     # STM32
    kd: float = 0.0                     # STM32
    pwm_output: int = 0                 # STM32
    pid_error: float = 0.0              # Calculated
    
    # System Status
    rpi_sensors_active: bool = False
    stm32_controller_active: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    def to_grouped_dict(self) -> Dict[str, Dict[str, Any]]:
        """Convert to grouped dictionary matching dummy_sensor format"""
        return {
            'picohydro_generator': {
                'picohydro_voltage': self.picohydro_voltage,
                'picohydro_current': self.picohydro_current,
                'picohydro_rpm': self.picohydro_rpm,
            },
            'solar_panel_generator': {
                'solar_voltage': self.solar_voltage,
                'solar_current': self.solar_current,
                'lighting': self.lighting
            },
            'baterai': {
                'battery_voltage': self.battery_voltage,
                'battery_input_current': self.battery_input_current,
                'battery_output_current': self.battery_output_current,
            },
            'beban': {
                'battery_voltage': self.battery_voltage,
                'dc_input_current': self.dc_input_current,
                'ac_output_voltage': self.ac_output_voltage,
                'ac_output_current': self.ac_output_current,
            },
            'dump_load': {
                'picohydro_voltage': self.picohydro_voltage,
                'picohydro_charging_current': self.picohydro_charging_current,
                'dumpload_voltage': self.dumpload_voltage,
                'dumpload_current': self.dumpload_current,
            },
            'environment': {
                'temperature': self.temperature,
                'humidity': self.humidity,
                'pressure': self.pressure,
                'tma_value': self.tma_value,
                'rain_status': float(self.rain_status),
            },
            'pid_controller': {
                'setpoint': self.setpoint,
                'kp': self.kp,
                'ki': self.ki,
                'kd': self.kd,
                'pwm_output': self.pwm_output,
                'pid_error': self.pid_error,
            }
        }

class SensorsManager:
    """Main class for managing sensors data from both RPi and STM32"""
    
    def __init__(self, stm32_port: str = '/dev/ttyUSB0', stm32_baudrate: int = 115200):
        self.stm32_port = stm32_port
        self.stm32_baudrate = stm32_baudrate
        
        # Initialize sensor interfaces
        self.rpi_sensor: Optional[Any] = None
        self.stm32_controller: Optional[Any] = None
        
        # Data storage
        self.current_data = CombinedSensorData()
        self.sensor_history: List[CombinedSensorData] = []
        self.history_lock = threading.Lock()
        
        # Control flags
        self.is_running = False
        self.update_thread = None
        self.history_duration = 300.0  # 5 minutes default
        self.update_interval = 1.0     # 1 second default
        
        # Connection status
        self.rpi_connected = False
        self.stm32_connected = False
        
    def initialize_sensors(self) -> bool:
        """Initialize both sensor interfaces"""
        success = True
        
        # Initialize RPi sensors
        if SensorReader:
            try:
                self.rpi_sensor = SensorReader()
                self.rpi_connected = True
                logger.info("Raspberry Pi sensors initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize RPi sensors: {e}")
                self.rpi_connected = False
                success = False
        else:
            logger.warning("SensorReader not available - running without RPi sensors")
            self.rpi_connected = False
        
        # Initialize STM32 controller
        if STM32Controller:
            try:
                self.stm32_controller = STM32Controller(
                    port=self.stm32_port, 
                    baudrate=self.stm32_baudrate
                )
                if self.stm32_controller.connect():
                    if self.stm32_controller.start_monitoring():
                        self.stm32_connected = True
                        logger.info("STM32 controller initialized successfully")
                    else:
                        logger.error("Failed to start STM32 monitoring")
                        success = False
                else:
                    logger.error("Failed to connect to STM32")
                    success = False
            except Exception as e:
                logger.error(f"Failed to initialize STM32 controller: {e}")
                self.stm32_connected = False
                success = False
        else:
            logger.warning("STM32Controller not available - running without STM32 data")
            self.stm32_connected = False
        
        return success
    
    def read_sensor_data(self) -> CombinedSensorData:
        """Read and combine data from all sensors"""
        data = CombinedSensorData()
        data.timestamp = time.time()
        data.datetime_str = datetime.now().isoformat()
        
        # Read RPi sensor data
        if self.rpi_sensor and self.rpi_connected:
            try:
                self.rpi_sensor.read_all_sensors()
                
                # Map RPi sensor data
                data.picohydro_rpm = self.rpi_sensor.picohydro_rpm
                data.lighting = self.rpi_sensor.lighting
                data.ac_output_voltage = self.rpi_sensor.ac_output_voltage
                data.ac_output_current = self.rpi_sensor.ac_output_current
                data.temperature = self.rpi_sensor.temperature
                data.humidity = self.rpi_sensor.humidity
                data.pressure = self.rpi_sensor.pressure
                data.tma_value = self.rpi_sensor.tma_value
                data.rain_status = self.rpi_sensor.rain_status
                
                data.rpi_sensors_active = True
                
            except Exception as e:
                logger.error(f"Error reading RPi sensors: {e}")
                data.rpi_sensors_active = False
        
        # Read STM32 controller data
        if self.stm32_controller and self.stm32_connected:
            try:
                stm32_data = self.stm32_controller.get_latest_data()
                if stm32_data:
                    # Map STM32 sensor data
                    data.picohydro_voltage = stm32_data.picohydro_voltage
                    data.picohydro_current = stm32_data.picohydro_current
                    data.picohydro_charging_current = stm32_data.picohydro_charging_current
                    data.solar_voltage = stm32_data.solar_voltage
                    data.solar_current = stm32_data.solar_current
                    data.battery_voltage = stm32_data.battery_voltage
                    data.battery_input_current = stm32_data.battery_in_current
                    data.battery_output_current = stm32_data.battery_out_current
                    data.dumpload_voltage = stm32_data.dumpload_voltage
                    data.dumpload_current = stm32_data.dumpload_current
                    
                    # PID Controller data
                    data.setpoint = stm32_data.setpoint
                    data.kp = stm32_data.kp
                    data.ki = stm32_data.ki
                    data.kd = stm32_data.kd
                    data.pwm_output = stm32_data.pwm_output
                    
                    # Calculate PID error
                    data.pid_error = data.setpoint - data.picohydro_voltage
                    
                    data.stm32_controller_active = True
                else:
                    data.stm32_controller_active = False
                    
            except Exception as e:
                logger.error(f"Error reading STM32 data: {e}")
                data.stm32_controller_active = False
        
        # Calculate derived values
        data.dc_input_current = data.battery_output_current  # Assuming DC load current = battery output
        
        return data
    
    def start_monitoring(self, update_interval: float = 1.0, history_duration: float = 300.0):
        """Start continuous sensor monitoring"""
        if self.is_running:
            logger.warning("Monitoring already running")
            return
        
        self.update_interval = update_interval
        self.history_duration = history_duration
        self.is_running = True
        
        def monitoring_loop():
            """Main monitoring loop"""
            while self.is_running:
                try:
                    # Read sensor data
                    new_data = self.read_sensor_data()
                    
                    # Update current data
                    self.current_data = new_data
                    
                    # Add to history with thread safety
                    with self.history_lock:
                        self.sensor_history.append(copy.deepcopy(new_data))
                        
                        # Keep only data within history duration
                        current_time = time.time()
                        self.sensor_history = [
                            entry for entry in self.sensor_history
                            if (current_time - entry.timestamp) <= self.history_duration
                        ]
                    
                    time.sleep(self.update_interval)
                    
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    time.sleep(self.update_interval)
        
        self.update_thread = threading.Thread(target=monitoring_loop, daemon=True)
        self.update_thread.start()
        
        logger.info(f"Sensor monitoring started (interval: {update_interval}s, history: {history_duration}s)")
    
    def stop_monitoring(self):
        """Stop sensor monitoring"""
        self.is_running = False
        if self.update_thread:
            self.update_thread.join(timeout=5)
        
        logger.info("Sensor monitoring stopped")
    
    def get_sensor_data(self) -> Dict[str, Dict[str, Any]]:
        """Get current sensor data in grouped format (compatible with dummy_sensor)"""
        return self.current_data.to_grouped_dict()
    
    def get_module_data(self, module: str) -> Dict[str, Any]:
        """Get current sensor data for specific module"""
        grouped_data = self.get_sensor_data()
        return grouped_data.get(module, {})
    
    def get_raw_data(self) -> CombinedSensorData:
        """Get current raw sensor data"""
        return copy.deepcopy(self.current_data)
    
    def get_history(self, module: str = None, limit: int = None) -> List[Dict[str, Any]]:
        """Get sensor history data"""
        with self.history_lock:
            history_data = []
            
            for entry in self.sensor_history:
                if module:
                    # Get specific module data
                    grouped = entry.to_grouped_dict()
                    if module in grouped:
                        history_entry = {
                            'timestamp': entry.timestamp,
                            'datetime_str': entry.datetime_str,
                            'data': grouped[module]
                        }
                        history_data.append(history_entry)
                else:
                    # Get all data
                    history_entry = {
                        'timestamp': entry.timestamp,
                        'datetime_str': entry.datetime_str,
                        'data': entry.to_grouped_dict()
                    }
                    history_data.append(history_entry)
            
            # Apply limit if specified
            if limit and limit > 0:
                history_data = history_data[-limit:]
            
            return history_data
    
    def clear_history(self):
        """Clear sensor history"""
        with self.history_lock:
            self.sensor_history.clear()
        logger.info("Sensor history cleared")
    
    def get_connection_status(self) -> Dict[str, bool]:
        """Get connection status of all sensor interfaces"""
        return {
            'rpi_sensors': self.rpi_connected and self.current_data.rpi_sensors_active,
            'stm32_controller': self.stm32_connected and self.current_data.stm32_controller_active
        }
    
    def send_pid_parameters(self, setpoint: float = None, kp: float = None, 
                          ki: float = None, kd: float = None) -> bool:
        """Send PID parameters to STM32 controller"""
        if not self.stm32_controller or not self.stm32_connected:
            logger.error("STM32 controller not connected")
            return False
        
        return self.stm32_controller.send_pid_parameters(
            setpoint=setpoint, kp=kp, ki=ki, kd=kd
        )
    
    def save_current_data(self, filename: str = None):
        """Save current sensor data to JSON file"""
        if filename is None:
            filename = f"sensor_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(self.current_data.to_dict(), f, indent=2)
            logger.info(f"Current data saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving data: {e}")
    
    def save_history(self, filename: str = None, module: str = None):
        """Save sensor history to JSON file"""
        if filename is None:
            filename = f"sensor_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            history_data = self.get_history(module=module)
            with open(filename, 'w') as f:
                json.dump(history_data, f, indent=2)
            logger.info(f"History data saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving history: {e}")
    
    def cleanup(self):
        """Clean up resources"""
        self.stop_monitoring()
        
        if self.rpi_sensor:
            try:
                self.rpi_sensor.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up RPi sensors: {e}")
        
        if self.stm32_controller:
            try:
                self.stm32_controller.stop_monitoring()
                self.stm32_controller.disconnect()
            except Exception as e:
                logger.error(f"Error cleaning up STM32 controller: {e}")
        
        logger.info("Sensor manager cleanup completed")

# Create global instance for backward compatibility
sensors_manager = SensorsManager()

# Convenience functions for backward compatibility with dummy_sensor interface
def get_sensor_data():
    """Get current sensor data (backward compatibility function)"""
    return sensors_manager.get_sensor_data()

def get_module_data(module: str):
    """Get module data (backward compatibility function)"""
    return sensors_manager.get_module_data(module)

def start_sensor_monitoring(update_interval: float = 1.0):
    """Start sensor monitoring (convenience function)"""
    if not sensors_manager.initialize_sensors():
        logger.warning("Some sensors failed to initialize")
    sensors_manager.start_monitoring(update_interval)

def stop_sensor_monitoring():
    """Stop sensor monitoring (convenience function)"""
    sensors_manager.stop_monitoring()

def get_sensor_history():
    """Get all sensor history (convenience function)"""
    return sensors_manager.get_history()

def send_pid_parameters(**kwargs):
    """Send PID parameters (convenience function)"""
    return sensors_manager.send_pid_parameters(**kwargs)

if __name__ == "__main__":
    """Test the sensors manager"""
    print("Testing Sensor Manager...")
    
    # Initialize
    manager = SensorsManager()
    
    try:
        # Test initialization
        print("Initializing sensors...")
        if manager.initialize_sensors():
            print("✓ Sensors initialized successfully")
        else:
            print("⚠ Some sensors failed to initialize")
        
        # Test single reading
        print("\nTesting single sensor reading...")
        data = manager.read_sensor_data()
        print(f"Sample data - Battery: {data.battery_voltage:.2f}V, Temp: {data.temperature}°C")
        
        # Test grouped data format
        grouped = manager.get_sensor_data()
        print(f"Grouped data modules: {list(grouped.keys())}")
        
        # Test monitoring
        print("\nStarting monitoring for 10 seconds...")
        manager.start_monitoring(update_interval=0.5, history_duration=30)
        
        time.sleep(10)
        
        # Check history
        history = manager.get_history(limit=5)
        print(f"History entries: {len(history)}")
        
        # Test PID parameter sending
        print("\nTesting PID parameter sending...")
        if manager.send_pid_parameters(setpoint=14.0, kp=1.5):
            print("✓ PID parameters sent successfully")
        else:
            print("⚠ Failed to send PID parameters")
        
        # Connection status
        status = manager.get_connection_status()
        print(f"Connection status: {status}")
        
        print("\nTest completed successfully!")
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Test error: {e}")
    finally:
        manager.cleanup()
        print("Cleanup completed")