import random
import time
from datetime import datetime
from threading import Thread, Lock
from typing import Dict, Any, List

class DummySensors:
    def __init__(self):
        self.sensor_history = {}
        self.history_lock = Lock()
        self.is_running = False
        self.update_thread = None
        
        # Konfigurasi range untuk setiap sensor
        self.sensor_ranges = {
            'picohydro_generator': {
                'picohydro_voltage': {'min': 13.9, 'max': 14.1, 'unit': 'V'},
                'picohydro_current': {'min': 4.9, 'max': 5.1, 'unit': 'A'},
            },
            'solar_panel_generator': {
                'solar_voltage': {'min': 29.9, 'max': 30.1, 'unit': 'V'},
                'solar_current': {'min': 7.9, 'max': 8.1, 'unit': 'A'},
            },
            'baterai': {
                'battery_voltage': {'min': 11.9, 'max': 12.1, 'unit': 'V'},
                'battery_input_current': {'min': 7.9, 'max': 8.1, 'unit': 'A'},
                'battery_output_current': {'min': 39.9, 'max': 40.1, 'unit': 'A'},
            },
            'beban': {
                'battery_voltage': {'min': 11.9, 'max': 12.1, 'unit': 'V'},
                'dc_input_current': {'min': 39.9, 'max': 40.1, 'unit': 'A'},
            },
            'environment': {
                'temperature': {'min': 25.0, 'max': 35.0, 'unit': '°C'},
                'humidity': {'min': 60.0, 'max': 90.0, 'unit': '%'},
                'tma_value': {'min': 6.0, 'max': 8.0, 'unit': 'cm'},
            }
        }
    
    def generate_sensor_value(self, sensor_range: Dict[str, float]) -> float:
        """Generate random value within specified range"""
        return round(random.uniform(sensor_range['min'], sensor_range['max']), 2)
    
    def get_sensor_data(self) -> Dict[str, Dict[str, float]]:
        """Generate current sensor data for all modules"""
        data = {}
        
        for module, sensors in self.sensor_ranges.items():
            data[module] = {}
            for sensor_name, sensor_range in sensors.items():
                data[module][sensor_name] = self.generate_sensor_value(sensor_range)
        
        return data
    
    def get_module_data(self, module: str) -> Dict[str, float]:
        """Generate current sensor data for specific module"""
        if module in self.sensor_ranges:
            data = {}
            for sensor_name, sensor_range in self.sensor_ranges[module].items():
                data[sensor_name] = self.generate_sensor_value(sensor_range)
            return data
            return result
        return {}
    
    def get_sensor_info(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Get sensor configuration info including ranges and units"""
        return self.sensor_ranges
    
    def get_module_info(self, module: str) -> Dict[str, Dict[str, Any]]:
        """Get sensor configuration info for specific module"""
        return self.sensor_ranges.get(module, {})
    
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
                    print(f"Error in sensor simulation: {e}")
                    time.sleep(self.update_interval)
        
        self.update_thread = Thread(target=sensor_updater, daemon=True)
        self.update_thread.start()
        print(f"Sensor simulation started with {self.update_interval}s interval")
    
    def stop_simulation(self):
        """Stop sensor data simulation"""
        self.is_running = False
        if self.update_thread:
            self.update_thread.join(timeout=2)
        print("Sensor simulation stopped")
    
    def get_history(self, module: str = None) -> Dict[str, List[Dict]]:
        """Get sensor history data"""
        with self.history_lock:
            if module:
                return {module: self.sensor_history.get(module, [])}
            return dict(self.sensor_history)
    
    def clear_history(self, module: str = None):
        """Clear sensor history"""
        with self.history_lock:
            if module and module in self.sensor_history:
                self.sensor_history[module] = []
            else:
                self.sensor_history.clear()
    
    def add_custom_sensor(self, module: str, sensor_name: str, min_val: float, max_val: float, unit: str = ""):
        """Add custom sensor configuration"""
        if module not in self.sensor_ranges:
            self.sensor_ranges[module] = {}
        
        self.sensor_ranges[module][sensor_name] = {
            'min': min_val,
            'max': max_val,
            'unit': unit
        }
    
    def remove_sensor(self, module: str, sensor_name: str = None):
        """Remove sensor or entire module"""
        if sensor_name:
            if module in self.sensor_ranges and sensor_name in self.sensor_ranges[module]:
                del self.sensor_ranges[module][sensor_name]
        else:
            if module in self.sensor_ranges:
                del self.sensor_ranges[module]
    
    def update_sensor_range(self, module: str, sensor_name: str, min_val: float = None, max_val: float = None, unit: str = None):
        """Update sensor range configuration"""
        if module in self.sensor_ranges and sensor_name in self.sensor_ranges[module]:
            sensor_config = self.sensor_ranges[module][sensor_name]
            if min_val is not None:
                sensor_config['min'] = min_val
            if max_val is not None:
                sensor_config['max'] = max_val
            if unit is not None:
                sensor_config['unit'] = unit

# Create global instance
dummy_sensors = DummySensors()

# Convenience functions for backward compatibility
def get_sensor_data():
    """Get current sensor data (backward compatibility function)"""
    return dummy_sensors.get_sensor_data()

def start_sensor_simulation(update_interval=1.0):
    """Start sensor simulation (convenience function)"""
    dummy_sensors.start_simulation(update_interval)

def stop_sensor_simulation():
    """Stop sensor simulation (convenience function)"""
    dummy_sensors.stop_simulation()

def get_sensor_history():
    """Get all sensor history (convenience function)"""
    return dummy_sensors.get_history()

if __name__ == "__main__":
    # Test the simulator
    print("Testing Sensor Simulator...")
    
    # Test data generation
    data = dummy_sensors.get_sensor_data()
    print("Sample data:", data)
    
    # Test specific module
    battery_data = dummy_sensors.get_module_data('baterai')
    print("Battery data:", battery_data)
    
    # Test sensor info
    info = dummy_sensors.get_sensor_info()
    print("Sensor ranges:", info)
    
    # Test simulation
    dummy_sensors.start_simulation(0.5, 10)  # 0.5s interval, 10s history
    
    import time
    time.sleep(3)  # Let it run for 3 seconds
    
    history = dummy_sensors.get_history('baterai')
    print(f"Battery history entries: {len(history['baterai'])}")
    
    dummy_sensors.stop_simulation()
    print("Test completed!")
