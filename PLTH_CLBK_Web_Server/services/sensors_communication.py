#!/usr/bin/env python3
"""
Actual Sensors Interface - STM32 and ESP32 sensor data
Handles communication with both microcontrollers
"""

import time
import threading
import logging
import json
import serial
import sys
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from threading import Lock


# Fallback config import for port and baudrate
try:
    from config import (
        get_stm32_port, get_stm32_baudrate
    )
except ImportError:
    print("config.py not found, using default serial port and baudrate for STM32")
    def get_stm32_port():
        return "/dev/ttyACM0"
    def get_stm32_baudrate():
        return 115200

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from stm32_communication import STM32Controller, SensorData
    STM32_AVAILABLE = True
except ImportError as e:
    print(f"Warning: STM32 communication not available: {e}")
    STM32_AVAILABLE = False

try:
    from esp32_communication import ESP32Controller
    ESP32_AVAILABLE = True
except ImportError as e:
    print(f"Warning: ESP32 communication not available: {e}")
    ESP32_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealSensors:
    def __init__(self):
        self.sensor_history = {}
        self.history_lock = Lock()
        self.is_running = False
        self.update_threads = []

        stm32_port = get_stm32_port()
        stm32_baudrate = get_stm32_baudrate()

        # Tambahkan ESP32 port dan baudrate
        try:
            from config import get_esp32_port, get_esp32_baudrate
            esp32_port = get_esp32_port()
            esp32_baudrate = get_esp32_baudrate()
        except ImportError:
            esp32_port = "/dev/ttyUSB0"  # default ESP32 port
            esp32_baudrate = 115200      # default ESP32 baudrate

        self.stm32_controller = None
        if STM32_AVAILABLE:
            try:
                self.stm32_controller = STM32Controller(port=stm32_port, baudrate=stm32_baudrate)
                if self.stm32_controller.connect():
                    self.stm32_controller.start_monitoring()
                    logger.info("STM32 controller connected and monitoring started")
                else:
                    logger.error("Failed to connect to STM32")
                    self.stm32_controller = None
            except Exception as e:
                logger.error(f"Error initializing STM32 controller: {e}")
                self.stm32_controller = None

        # Tambahkan ESP32 controller
        self.esp32_controller = None
        if ESP32_AVAILABLE:
            try:
                self.esp32_controller = ESP32Controller(esp32_port=esp32_port, esp32_baudrate=esp32_baudrate)
                if self.esp32_controller.connect():
                    self.esp32_controller.start_monitoring()
                    logger.info("ESP32 controller connected and monitoring started")
                else:
                    logger.error("Failed to connect to ESP32")
                    self.esp32_controller = None
            except Exception as e:
                logger.error(f"Error initializing ESP32 controller: {e}")
                self.esp32_controller = None

        self._current_data = {}
        self._data_lock = Lock()
        
        self._fast_sensors_data = {}
        self._medium_sensors_data = {}
        self._slow_sensors_data = {}
        
        self._fast_lock = Lock()
        self._medium_lock = Lock()
        self._slow_lock = Lock()
        
        self._pv_data = {}
        self._batt_data = {}
        self._load_data = {}
        self._env_data = {}

    def _get_stm32_data(self) -> Dict[str, Dict[str, float]]:
        """Get data from STM32 controller"""
        if not self.stm32_controller:
            return {}
            

        try:
            if not self.stm32_controller.is_connected:
                return {}
        except:
            return {}
        
        try:

            data = None
            

            if hasattr(self.stm32_controller, 'get_latest_data'):
                data = self.stm32_controller.get_latest_data()
                

                if data is None and hasattr(self.stm32_controller, 'get_data_from_queue'):
                    try:
                        data = self.stm32_controller.get_data_from_queue(timeout=0.5)
                    except:
                        pass
                        

            elif hasattr(self.stm32_controller, 'get_latest_readings'):
                data = self.stm32_controller.get_latest_readings()
            
            if data:
                return self._map_stm32_data(data)
                
        except Exception as e:
            logger.error(f"Error getting STM32 data: {e}")
        
        return {}
    
    def _map_stm32_data(self, stm32_data: 'SensorData') -> Dict[str, Dict[str, float]]:
        """Map STM32 data to module format"""
        mapped_data = {}
        
        # Picohydro Generator - from STM32
        mapped_data['picohydro_generator'] = {
            'picohydro_voltage': float(getattr(stm32_data, 'picohydro_voltage', 0.0)),
            'picohydro_current': float(getattr(stm32_data, 'picohydro_current', 0.0))
        }
        
        # Battery - STM32 provides current data
        mapped_data['baterai'] = {
            'battery_voltage': 0.0,  # Will be overridden by ESP32
            'battery_input_current': float(getattr(stm32_data, 'battery_in_current', 0.0)),
            'battery_output_current': float(getattr(stm32_data, 'battery_out_current', 0.0))
        }
        
        # Load/Beban - using battery output current as load current
        mapped_data['beban'] = {
            'battery_voltage': 0.0,  # Will be overridden by ESP32
            'dc_input_current': float(getattr(stm32_data, 'battery_out_current', 0.0))
        }
        
        return mapped_data

    def _get_esp32_data(self) -> Dict[str, Dict[str, float]]:
        """Get data from ESP32 controller"""
        if not self.esp32_controller:
            return {}
            

        try:
            if not self.esp32_controller.is_connected:
                return {}
        except:
            return {}
        
        try:
            esp32_data = self.esp32_controller.get_data()
            if not esp32_data:
                return {}
            
            # Map ESP32 sensor data to module structure
            mapped_data = {}
            
            # Solar Panel Generator data (from ESP32)
            mapped_data['solar_panel_generator'] = {
                'solar_voltage': getattr(esp32_data, 'solar_voltage', 0.0),
                'solar_current': getattr(esp32_data, 'solar_current', 0.0)
            }
            
            # Battery data (from ESP32)
            if hasattr(esp32_data, 'battery_voltage'):
                if 'baterai' not in mapped_data:
                    mapped_data['baterai'] = {}
                mapped_data['baterai']['battery_voltage'] = esp32_data.battery_voltage
            
            # Environment data (from ESP32) - including tma_value
            env_data = {}
            if hasattr(esp32_data, 'temperature'):
                env_data['temperature'] = esp32_data.temperature
            if hasattr(esp32_data, 'humidity'):
                env_data['humidity'] = esp32_data.humidity
            if hasattr(esp32_data, 'tma_value'):
                env_data['tma_value'] = esp32_data.tma_value
            
            if env_data:
                mapped_data['environment'] = env_data
            
            return mapped_data
            
        except Exception as e:
            logger.error(f"Error getting ESP32 data: {e}")
            return {}

    def get_sensor_data(self) -> Dict[str, Dict[str, float]]:
        """Get current sensor data for all modules"""
        stm32_data = self._get_stm32_data()
        esp32_data = self._get_esp32_data()

        # Start with STM32 data
        data = stm32_data.copy()

        # Merge ESP32 data, updating existing modules or adding new ones
        for module, values in esp32_data.items():
            if module in data:
                data[module].update(values)
            else:
                data[module] = values

        # Ensure solar panel data always present
        if 'solar_panel_generator' not in data:
            data['solar_panel_generator'] = {'solar_voltage': 0.0, 'solar_current': 0.0, 'solar_power': 0.0}
        else:
            for key in ['solar_voltage', 'solar_current', 'solar_power']:
                if key not in data['solar_panel_generator']:
                    data['solar_panel_generator'][key] = 0.0

        # Ensure battery voltage always present
        if 'baterai' not in data:
            data['baterai'] = {'battery_voltage': 0.0, 'battery_input_current': 0.0, 'battery_output_current': 0.0, 'battery_net_current': 0.0}
        else:
            if 'battery_voltage' not in data['baterai']:
                data['baterai']['battery_voltage'] = 0.0
            if 'battery_input_current' not in data['baterai']:
                data['baterai']['battery_input_current'] = 0.0
            if 'battery_output_current' not in data['baterai']:
                data['baterai']['battery_output_current'] = 0.0
            # Calculate net current
            data['baterai']['battery_net_current'] = data['baterai'].get('battery_input_current', 0.0) - data['baterai'].get('battery_output_current', 0.0)

        # Ensure beban data always present
        if 'beban' not in data:
            data['beban'] = {'battery_voltage': 0.0, 'dc_input_current': 0.0, 'dc_input_power': 0.0}
        else:
            if 'dc_input_current' not in data['beban']:
                data['beban']['dc_input_current'] = 0.0
        
        # Always sync beban battery_voltage with baterai battery_voltage
        data['beban']['battery_voltage'] = data['baterai'].get('battery_voltage', 0.0)
        
        # Calculate dc_input_power
        data['beban']['dc_input_power'] = data['beban'].get('battery_voltage', 0.0) * data['beban'].get('dc_input_current', 0.0)

        # Ensure environment data always present
        if 'environment' not in data:
            data['environment'] = {'temperature': 0.0, 'humidity': 0.0, 'tma_value': 0.0}
        else:
            for key in ['temperature', 'humidity', 'tma_value']:
                if key not in data['environment']:
                    data['environment'][key] = 0.0

        # Calculate derived powers if missing
        if 'picohydro_generator' in data:
            data['picohydro_generator']['picohydro_power'] = data['picohydro_generator'].get('picohydro_voltage', 0.0) * data['picohydro_generator'].get('picohydro_current', 0.0)
        if 'solar_panel_generator' in data:
            data['solar_panel_generator']['solar_power'] = data['solar_panel_generator'].get('solar_voltage', 0.0) * data['solar_panel_generator'].get('solar_current', 0.0)

        return data

    def get_module_data(self, module: str) -> Dict[str, float]:
        """Get current sensor data for specific module"""
        data = self.get_sensor_data()
        return data.get(module, {})

    def get_sensor_info(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Get sensor configuration info including ranges and units"""
        return {
            'picohydro_generator': {
                'picohydro_voltage': {'min': 13.0, 'max': 15.0, 'unit': 'V'},
                'picohydro_current': {'min': 0.0, 'max': 10.0, 'unit': 'A'}
            },
            'solar_panel_generator': {
                'solar_voltage': {'min': 25.0, 'max': 35.0, 'unit': 'V'},
                'solar_current': {'min': 0.0, 'max': 15.0, 'unit': 'A'}
            },
            'baterai': {
                'battery_voltage': {'min': 10.0, 'max': 14.5, 'unit': 'V'},
                'battery_input_current': {'min': 0.0, 'max': 20.0, 'unit': 'A'},
                'battery_output_current': {'min': 0.0, 'max': 50.0, 'unit': 'A'}
            },
            'beban': {
                'battery_voltage': {'min': 10.0, 'max': 14.5, 'unit': 'V'},
                'dc_input_current': {'min': 0.0, 'max': 50.0, 'unit': 'A'}
            },
            'environment': {
                'temperature': {'min': 20.0, 'max': 40.0, 'unit': '°C'},
                'humidity': {'min': 50.0, 'max': 100.0, 'unit': '%'},
                'tma_value': {'min': 0.0, 'max': 20.0, 'unit': 'cm'},
            }
        }

    def get_module_info(self, module: str) -> Dict[str, Dict[str, Any]]:
        """Get sensor configuration info for specific module"""
        return self.get_sensor_info().get(module, {})

    def start_simulation(self, update_interval: float = 1.0, history_duration: float = 30.0):
        """Start sensor data simulation with automatic history management"""
        if self.is_running:
            return
        
        self.is_running = True
        self.update_interval = update_interval
        self.history_duration = history_duration
        
        def sensor_updater():
            while self.is_running:
                try:
                    with self.history_lock:
                        data = self.get_sensor_data()
                        timestamp = datetime.now().timestamp()
                        
                        for module, values in data.items():
                            if module not in self.sensor_history:
                                self.sensor_history[module] = []
                            
                            # Add new data
                            self.sensor_history[module].append({
                                'timestamp': timestamp,
                                'data': values
                            })
                            
                            # Keep only data within history duration
                            self.sensor_history[module] = [
                                entry for entry in self.sensor_history[module] 
                                if (timestamp - entry['timestamp']) <= self.history_duration
                            ]
                    
                    time.sleep(self.update_interval)
                    
                except Exception as e:
                    logger.error(f"Error in sensor monitoring: {e}")
                    time.sleep(self.update_interval)
        
        self.update_thread = threading.Thread(target=sensor_updater, daemon=True)
        self.update_thread.start()
        logger.info(f"Sensor monitoring started with {self.update_interval}s interval")

    def stop_simulation(self):
        """Stop sensor data monitoring"""
        self.is_running = False
        if hasattr(self, 'update_thread'):
            self.update_thread.join(timeout=2)
        logger.info("Sensor monitoring stopped")

    def get_history(self, module: str = None) -> Dict[str, List[Dict]]:
        """Get sensor history data"""
        with self.history_lock:
            if module:
                return {module: self.sensor_history.get(module, [])}
            return dict(self.sensor_history)

    def is_connected(self) -> bool:
        """Check if any sensor is connected"""
        stm32_connected = False
        esp32_connected = False
        
        # Check STM32 (property)
        if self.stm32_controller:
            try:
                stm32_connected = bool(self.stm32_controller.is_connected)
            except:
                stm32_connected = False
        
        # Check ESP32 (property)
        if self.esp32_controller:
            try:
                esp32_connected = bool(self.esp32_controller.is_connected)
            except:
                esp32_connected = False
                
        return stm32_connected or esp32_connected
    
    def get_connection_status(self) -> Dict[str, bool]:
        """Get connection status for all sensors"""
        stm32_connected = False
        esp32_connected = False
        
        # Check STM32 (property)
        if self.stm32_controller:
            try:
                stm32_connected = bool(self.stm32_controller.is_connected)
            except:
                stm32_connected = False
        
        # Check ESP32 (property)
        if self.esp32_controller:
            try:
                esp32_connected = bool(self.esp32_controller.is_connected)
            except:
                esp32_connected = False
                
        return {
            'stm32': stm32_connected,
            'esp32': esp32_connected
        }

    def cleanup(self):
        """Cleanup resources"""
        self.stop_simulation()
        if self.stm32_controller:
            try:
                self.stm32_controller.disconnect()
            except:
                pass
        if self.esp32_controller:
            try:
                self.esp32_controller.disconnect()
            except:
                pass

# Create the global real_sensors instance
real_sensors = RealSensors()

# Main function for standalone testing
def main():
    """Main function for testing sensor communication"""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Test sensor communication')
    parser.add_argument('--interval', type=float, default=1.0, help='Update interval in seconds')
    parser.add_argument('--duration', type=int, default=30, help='Test duration in seconds')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    args = parser.parse_args()
    
    print("="*60)
    print("SENSOR COMMUNICATION TEST")
    print("="*60)
    
    # Check connections
    print("\nChecking sensor connections...")
    connection_status = real_sensors.get_connection_status()
    
    for sensor, connected in connection_status.items():
        status = "CONNECTED" if connected else "NOT CONNECTED"
        print(f"  {sensor.upper()}: {status}")
    
    if not real_sensors.is_connected():
        print("\n[ERROR] No sensors connected. Exiting...")
        return 1
    
    print(f"\n[OK] Starting sensor monitoring (interval: {args.interval}s, duration: {args.duration}s)")
    
    # Start monitoring
    real_sensors.start_simulation(update_interval=args.interval, history_duration=30.0)
    
    # Monitor for specified duration
    start_time = time.time()
    last_display = 0
    
    try:
        while (time.time() - start_time) < args.duration:
            current_time = time.time()
            
            # Display data every interval
            if (current_time - last_display) >= args.interval:
                data = real_sensors.get_sensor_data()
                
                if data:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Sensor Data:")
                    
                    for module, values in data.items():
                        if values:
                            print(f"  {module}:")
                            for param, value in values.items():
                                if isinstance(value, float):
                                    print(f"    {param}: {value:.2f}")
                                else:
                                    print(f"    {param}: {value}")
                    
                    if args.verbose:
                        # Show raw data from controllers
                        if real_sensors.stm32_controller and real_sensors.stm32_controller.is_connected:
                            stm32_data = real_sensors.stm32_controller.get_latest_data()
                            if stm32_data:
                                print("\n  [STM32 Raw Data]:")
                                print(f"    Picohydro: {stm32_data.picohydro_voltage:.2f}V, {stm32_data.picohydro_current:.2f}A")
                                print(f"    Battery: In={stm32_data.battery_in_current:.2f}A, Out={stm32_data.battery_out_current:.2f}A")
                                print(f"    PID: SP={stm32_data.setpoint:.2f}, PWM={stm32_data.pwm_output}")
                        
                        if real_sensors.esp32_controller and real_sensors.esp32_controller.is_connected:
                            esp32_data = real_sensors.esp32_controller.get_data()
                            if esp32_data:
                                print("\n  [ESP32 Raw Data]:")
                                print(f"    Solar: {esp32_data.solar_voltage:.2f}V, {esp32_data.solar_current:.2f}A")
                                print(f"    Battery: {esp32_data.battery_voltage:.2f}V")
                                print(f"    Environment: {esp32_data.temperature:.1f}°C, {esp32_data.humidity:.1f}%, TMA={esp32_data.tma_value:.1f}")
                else:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] No data available")
                
                last_display = current_time
            
            time.sleep(0.1)  # Small sleep to prevent CPU hogging
            
    except KeyboardInterrupt:
        print("\n\n[INFO] Interrupted by user")
    
    # Stop monitoring
    print("\n[INFO] Stopping sensor monitoring...")
    real_sensors.stop_simulation()
    

    print("[INFO] Cleaning up...")
    real_sensors.cleanup()
    
    print("\n[OK] Test completed")
    return 0

if __name__ == "__main__":
    sys.exit(main())
