#!/usr/bin/env python3
"""
Configuration file for STM32 PLTH Controller
Centralized configuration for all communication modules
"""

import platform
import os
import json

class SensorConfig:
    """Centralized configuration for sensor communication"""
    
    def __init__(self):
        self.default_config = {
            'stm32': {
                'port_linux': '/dev/ttyACM0',
                'port_windows': 'COM4',
                'baudrate': 115200
            },
            'esp32': {
                'usb_port_linux': '/dev/ttyUSB0',
                'usb_port_windows': 'COM12', 
                'baudrate': 115200
            },
            'platform': {
                'auto_detect': True,
                'force_platform': None
            },
            'logging': {
                'level': 'INFO',
                'file': 'stm32_plth_controller.log'
            }
        }
        
        # Load configuration from file if exists
        self.config_file = 'sensor_config.json'
        self.config = self.load_config()
        
        # Auto-detect platform if enabled
        if self.config['platform']['auto_detect']:
            self.current_platform = self.detect_platform()
        else:
            self.current_platform = self.config['platform']['force_platform'] or self.detect_platform()
    
    def detect_platform(self):
        """Auto-detect current platform"""
        system = platform.system().lower()
        if system == 'windows':
            return 'windows'
        elif system in ['linux', 'darwin']:  # Linux or macOS
            return 'linux'
        else:
            # Default fallback
            return 'linux'
    
    def load_config(self):
        """Load configuration from JSON file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                # Merge with defaults
                config = self.default_config.copy()
                config.update(loaded_config)
                return config
            except Exception as e:
                print(f"Warning: Could not load config file {self.config_file}: {e}")
                print("Using default configuration")
        
        return self.default_config.copy()
    
    def save_config(self):
        """Save current configuration to JSON file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            print(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False
    
    def get_stm32_port(self):
        """Get STM32 port based on current platform"""
        if self.current_platform == 'windows':
            return self.config['stm32']['port_windows']
        else:
            return self.config['stm32']['port_linux']
    
    def get_stm32_baudrate(self):
        """Get STM32 baudrate"""
        return self.config['stm32']['baudrate']
    
    def set_stm32_port(self, port, platform=None):
        """Set STM32 port for specific platform"""
        if platform is None:
            platform = self.current_platform
        
        if platform == 'windows':
            self.config['stm32']['port_windows'] = port
        else:
            self.config['stm32']['port_linux'] = port
    
    def set_stm32_baudrate(self, baudrate):
        """Set STM32 baudrate"""
        self.config['stm32']['baudrate'] = baudrate
    
    def get_esp32_port(self):
        """Get ESP32 USB port based on current platform"""
        if self.current_platform == 'windows':
            return self.config['esp32']['usb_port_windows']
        else:
            return self.config['esp32']['usb_port_linux']
    
    def get_esp32_baudrate(self):
        """Get ESP32 baudrate"""
        return self.config['esp32']['baudrate']
    
    def get_pzem_output_port(self):
        """Get PZEM output USB port based on current platform"""
        if self.current_platform == 'windows':
            return self.config['pzem']['output_usb_port_windows']
        else:
            return self.config['pzem']['output_usb_port_linux']
    
    def get_pzem_picohydro_port(self):
        """Get PZEM picohydro USB port based on current platform"""
        if self.current_platform == 'windows':
            return self.config['pzem']['picohydro_usb_port_windows']
        else:
            return self.config['pzem']['picohydro_usb_port_linux']
    
    def get_pzem_baudrate(self):
        """Get PZEM baudrate"""
        return self.config['pzem']['baudrate']

    def get_platform_info(self):
        """Get platform information"""
        return {
            'detected_platform': platform.system(),
            'current_platform': self.current_platform,
            'auto_detect': self.config['platform']['auto_detect'],
            'force_platform': self.config['platform']['force_platform']
        }
    
    def set_platform(self, platform_name, auto_detect=True):
        """Set platform configuration"""
        self.config['platform']['force_platform'] = platform_name
        self.config['platform']['auto_detect'] = auto_detect
        
        if not auto_detect and platform_name:
            self.current_platform = platform_name
        else:
            self.current_platform = self.detect_platform()

# Create global configuration instance
sensor_config = SensorConfig()

# Convenience functions
def get_stm32_port():
    """Get STM32 port for current platform"""
    return sensor_config.get_stm32_port()

def get_stm32_baudrate():
    """Get STM32 baudrate"""
    return sensor_config.get_stm32_baudrate()

def get_stm32_config():
    """Get complete STM32 configuration"""
    return {
        'port': sensor_config.get_stm32_port(),
        'baudrate': sensor_config.get_stm32_baudrate()
    }

def save_sensor_config():
    """Save sensor configuration to file"""
    return sensor_config.save_config()

def get_platform_info():
    """Get platform information"""
    return sensor_config.get_platform_info()

def get_esp32_port():
    """Get ESP32 USB port for current platform"""
    return sensor_config.get_esp32_port()

def get_esp32_baudrate():
    """Get ESP32 baudrate"""
    return sensor_config.get_esp32_baudrate()

def get_pzem_output_port():
    """Get PZEM output USB port for current platform"""
    return sensor_config.get_pzem_output_port()

def get_pzem_picohydro_port():
    """Get PZEM picohydro USB port for current platform"""
    return sensor_config.get_pzem_picohydro_port()

def get_pzem_baudrate():
    """Get PZEM baudrate"""
    return sensor_config.get_pzem_baudrate()

if __name__ == "__main__":
    # Test configuration
    print("STM32 Configuration Test")
    print("=" * 40)
    print(f"Detected platform: {platform.system()}")
    print(f"Current platform: {sensor_config.current_platform}")
    print(f"STM32 Port: {get_stm32_port()}")
    print(f"STM32 Baudrate: {get_stm32_baudrate()}")
    print(f"Complete config: {get_stm32_config()}")
    print("\nPlatform info:", get_platform_info())
    
    # Example: Save configuration
    print("\nSaving configuration...")
    save_sensor_config()