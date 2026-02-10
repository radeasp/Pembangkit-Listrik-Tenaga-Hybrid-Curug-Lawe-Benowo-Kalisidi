#!/usr/bin/env python3
"""
STM32 PLTH Controller - Raspberry Pi Interface
Communicates with STM32 controller for Picohydro, Solar Panel, Battery monitoring and control
"""

import serial
import json
import time
import threading
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, Any
import queue
import argparse
import platform
import sys


# Fallback config import for port and baudrate
try:
    from config import get_stm32_port, get_stm32_baudrate
except ImportError:
    print("config.py not found, using default serial port and baudrate for STM32")
    def get_stm32_port():
        return "/dev/ttyACM0"
    def get_stm32_baudrate():
        return 115200

# Import select hanya untuk sistem Unix/Linux
if platform.system() != 'Windows':
    import select

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stm32_plth_controller.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class SensorData:
    """Data structure to hold all sensor readings"""
    picohydro_voltage: float = 0.0
    picohydro_current: float = 0.0

    picohydro_charging_current: float = 0.0

    battery_in_current: float = 0.0
    battery_out_current: float = 0.0
    setpoint: float = 0.0
    kp: float = 0.0
    ki: float = 0.0
    kd: float = 0.0
    pwm_output: int = 0
    timestamp: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'picohydro_voltage': self.picohydro_voltage,
            'picohydro_current': self.picohydro_current,

            'picohydro_charging_current': self.picohydro_charging_current,

            'battery_in_current': self.battery_in_current,
            'battery_out_current': self.battery_out_current,
            'setpoint': self.setpoint,
            'kp': self.kp,
            'ki': self.ki,
            'kd': self.kd,
            'pwm_output': self.pwm_output,
            'timestamp': self.timestamp,
            'received_at': datetime.now().isoformat()
        }

class STM32Controller:
    def __init__(self, port: str = None, baudrate: int = None):
        self.port = port if port is not None else get_stm32_port()
        self.baudrate = baudrate if baudrate is not None else get_stm32_baudrate()
        self.serial_conn: Optional[serial.Serial] = None
        self.running = False
        self.data_queue = queue.Queue()
        self.latest_data: Optional[SensorData] = None
        self.data_lock = threading.Lock()
        
        # Buffer untuk menyimpan data yang tidak lengkap
        self.read_buffer = ""
        
    @property
    def is_connected(self):
        return self.serial_conn is not None and self.serial_conn.is_open

    def connect(self) -> bool:
        """Establish serial connection to STM32"""
        try:
            # Close the connection if it's already open
            if self.serial_conn and self.serial_conn.is_open:
                try:
                    self.serial_conn.close()
                except Exception:
                    pass
            
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.1,
                write_timeout=1
            )
            time.sleep(2)  # Wait for connection to stabilize
            
            # Clear any existing data in buffer
            try:
                self.serial_conn.reset_input_buffer()
                self.serial_conn.reset_output_buffer()
            except Exception as e:
                logger.warning(f"Could not reset STM32 buffers: {e}")
            
            # Initialize data tracking
            self.last_stm32_data_time = time.time()
            self.read_buffer = ""
            
            logger.info(f"Connected to STM32 on {self.port} at {self.baudrate} baud")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to STM32: {e}")
            return False
    
    def disconnect(self):
        """Close serial connection"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            logger.info("Disconnected from STM32")
    
    def start_monitoring(self):
        """Start the monitoring thread"""
        if not self.serial_conn or not self.serial_conn.is_open:
            logger.error("Serial connection not established")
            return False
        
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Started monitoring thread")
        return True
    
    def stop_monitoring(self):
        """Stop the monitoring thread"""
        self.running = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=5)
        logger.info("Stopped monitoring thread")
    
    def _monitor_loop(self):
        """Main monitoring loop running in separate thread"""
        # Pilih metode berdasarkan OS
        if platform.system() != 'Windows' and hasattr(select, 'select'):
            self._monitor_loop_select()
        else:
            self._monitor_loop_polling()
    
    def _process_buffer(self):
        """Process all complete lines in the buffer"""
        try:
            # Find all complete lines in the buffer
            lines = self.read_buffer.split('\n')
            
            # If the last element doesn't end with a newline, it's incomplete
            # Keep it in the buffer for next time
            if len(lines) > 0:
                self.read_buffer = lines.pop()
            
            # Process each complete line
            for line in lines:
                line = line.strip()
                if line:
                    self._process_received_data(line)
        except Exception as e:
            logger.error(f"Error processing buffer: {e}")
            # If there's an error, clear the buffer to prevent buildup of corrupted data
            self.read_buffer = ""

    def _monitor_loop_select(self):
        """Monitor loop menggunakan select (untuk Unix/Linux) - lebih efisien"""
        while self.running:
            try:
                if self.serial_conn is None or not self.serial_conn.is_open:
                    logger.error("STM32 connection lost, attempting to reconnect in 5 seconds")
                    time.sleep(5)
                    self.connect()
                    continue
                

                ready, _, _ = select.select([self.serial_conn], [], [], 0.5)
                
                if ready:
                    # Ada data tersedia, baca semua
                    available = self.serial_conn.in_waiting
                    if available > 0:
                        data = self.serial_conn.read(available).decode('utf-8', errors='ignore')
                        self.read_buffer += data
                    
                        # Process all complete lines
                        self._process_buffer()
                
            except (serial.SerialException, OSError) as e:
                logger.error(f"Serial error in monitoring loop (select): {e}")
                # Try to reconnect in case of serial error
                try:
                    if self.serial_conn and self.serial_conn.is_open:
                        self.serial_conn.close()
                except Exception:
                    pass
                time.sleep(5)
                self.connect()
            except Exception as e:
                logger.error(f"Error in monitoring loop (select): {e}")
                time.sleep(1)
    
    def _monitor_loop_polling(self):
        """Monitor loop menggunakan polling (untuk Windows atau fallback)"""
        while self.running:
            try:
                if self.serial_conn is None or not self.serial_conn.is_open:
                    logger.error("STM32 connection lost, attempting to reconnect in 5 seconds")
                    time.sleep(5)
                    self.connect()
                    continue
                
                # Cek apakah ada data yang tersedia
                available = self.serial_conn.in_waiting
                if available > 0:
                    # Baca semua data yang tersedia dalam buffer
                    data = self.serial_conn.read(available).decode('utf-8', errors='ignore')
                    self.read_buffer += data
                    
                    # Process all complete lines
                    self._process_buffer()
                    
                    # Jika masih ada data, sleep lebih singkat
                    time.sleep(0.1)  # 100 ms untuk tetap responsif jika ada data berkelanjutan
                else:
                    # Jika tidak ada data, sleep lebih lama untuk menghemat CPU
                    time.sleep(0.5)
                
            except (serial.SerialException, OSError) as e:
                logger.error(f"Serial error in monitoring loop (polling): {e}")
                # Try to reconnect in case of serial error
                try:
                    if self.serial_conn and self.serial_conn.is_open:
                        self.serial_conn.close()
                except Exception:
                    pass
                time.sleep(5)
                self.connect()
            except Exception as e:
                logger.error(f"Error in monitoring loop (polling): {e}")
                time.sleep(1)
    
    def _process_received_data(self, line: str):
        """Process received JSON data from STM32"""
        # Skip empty lines
        if not line or len(line.strip()) == 0:
            return
        try:
            # Skip debug lines yang jelas bukan JSON
            if any(keyword in line for keyword in ["===", "ADC READINGS", "VOLTAGE SENSORS", "CURRENT SENSORS", "PID CONTROL"]):
                logger.debug(f"STM32 Debug (skipped): {line}")
                return
            # Sanitize the line - check if it starts with { and ends with }
            if not line.startswith('{') or not line.endswith('}'):
                line_fixed = line[line.find('{'):line.rfind('}')+1]
                if not line_fixed or line_fixed == '{':
                    logger.debug(f"Skipping invalid JSON data: {line}")
                    return
                line = line_fixed
                logger.debug(f"Sanitized JSON: {line}")
            # Try to parse as JSON
            data_dict = json.loads(line)
            # Get current data or create new
            with self.data_lock:
                current_data = self.latest_data if self.latest_data else SensorData()
            # Check if we have all required fields
            required_fields = ['picohydro_voltage', 'picohydro_current']
            if not all(field in data_dict for field in required_fields):
                missing = [field for field in required_fields if field not in data_dict]
                logger.warning(f"Incomplete STM32 JSON data, missing fields: {missing}")
            # Create SensorData object, preserving previous values for missing fields
            sensor_data = SensorData(
                picohydro_voltage=data_dict.get('picohydro_voltage', current_data.picohydro_voltage),
                picohydro_current=data_dict.get('picohydro_current', current_data.picohydro_current),
                picohydro_charging_current=data_dict.get('picohydro_charging_current', current_data.picohydro_charging_current),

                battery_in_current=data_dict.get('battery_in_current', current_data.battery_in_current),
                battery_out_current=data_dict.get('battery_out_current', current_data.battery_out_current),
                setpoint=data_dict.get('setpoint', current_data.setpoint),
                kp=data_dict.get('kp', current_data.kp),
                ki=data_dict.get('ki', current_data.ki),
                kd=data_dict.get('kd', current_data.kd),
                pwm_output=data_dict.get('pwm_output', current_data.pwm_output),
                timestamp=data_dict.get('timestamp', int(time.time()))
            )
            # Update latest data with thread safety
            with self.data_lock:
                self.latest_data = sensor_data

                self.last_stm32_data_time = time.time()

            try:
                self.data_queue.put_nowait(sensor_data)
            except queue.Full:

                try:
                    self.data_queue.get_nowait()
                    self.data_queue.put_nowait(sensor_data)
                except queue.Empty:
                    pass
            logger.debug(f"Received sensor data: Picohydro={sensor_data.picohydro_voltage:.2f}V, PWM={sensor_data.pwm_output}")

        except json.JSONDecodeError:

            if "ADC READINGS" in line or "VOLTAGE SENSORS" in line or "CURRENT SENSORS" in line:
                logger.debug(f"STM32 Debug: {line}")
            else:
                logger.warning(f"Received non-JSON data: {line}")
        except Exception as e:
            logger.error(f"Error processing received data: {e}")
    
    def send_debug_command(self, command: str) -> bool:
        """Send debug commands to STM32"""
        valid_commands = ['DEBUG_ON', 'DEBUG_OFF', 'PLOTTER_MODE']
        
        if command not in valid_commands:
            logger.error(f"Invalid debug command: {command}")
            return False
        
        if not self.serial_conn or not self.serial_conn.is_open:
            logger.error("Serial connection not established")
            return False
        
        try:
            self.serial_conn.write((command + '\n').encode('utf-8'))
            logger.info(f"Sent debug command: {command}")
            return True
        except Exception as e:
            logger.error(f"Error sending debug command: {e}")
            return False
    
    def get_latest_data(self) -> Optional[SensorData]:
        """Get the latest sensor data (thread-safe)"""
        with self.data_lock:
            return self.latest_data
    
    def get_data_from_queue(self, timeout: float = 1.0) -> Optional[SensorData]:
        """Get sensor data from queue"""
        try:
            return self.data_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def save_data_to_file(self, filename: str = None):
        """Save current data to JSON file"""
        if filename is None:
            filename = f"sensor_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        data = self.get_latest_data()
        if data:
            try:
                with open(filename, 'w') as f:
                    json.dump(data.to_dict(), f, indent=2)
                logger.info(f"Data saved to {filename}")
            except Exception as e:
                logger.error(f"Error saving data to file: {e}")
        else:
            logger.warning("No data available to save")

def print_sensor_data(data: SensorData):
    """Pretty print sensor data"""
    print("\n" + "="*60)
    print(f"SENSOR DATA - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    print(f"POWER SOURCES:")
    print(f"   Picohydro      : {data.picohydro_voltage:6.2f} V  |  {data.picohydro_current:6.2f} A")
    print(f"   Solar Panel    : [MOVED TO ESP32 - Check ESP32 output]")
    print(f"   Picohydro Char : {data.picohydro_charging_current:6.2f} A")
    
    print(f"\nBATTERY SYSTEM:")
    print(f"   Battery Volt   : [MOVED TO ESP32 - Check ESP32 output]")
    print(f"   Battery In     : {data.battery_in_current:6.2f} A")
    print(f"   Battery Out    : {data.battery_out_current:6.2f} A")
    
    
    print(f"\nPID CONTROL:")
    print(f"   Setpoint       : {data.setpoint:6.2f} V")
    print(f"   Error          : {data.setpoint - data.picohydro_voltage:6.2f} V")
    print(f"   PWM Output     : {data.pwm_output:3d}/255 ({(data.pwm_output/255)*100:5.1f}%)")
    print(f"   PID Params     : Kp={data.kp:5.2f}, Ki={data.ki:5.2f}, Kd={data.kd:5.2f}")
    
def interactive_mode(controller: STM32Controller):
    """Interactive mode for manual control"""
    print("\n" + "="*60)
    print("INTERACTIVE MODE - STM32 PLTH Controller")
    print("="*60)
    print("Commands:")
    print("  data          - Show latest sensor data")
    print("  set <param>   - Set PID parameters (setpoint, kp, ki, kd)")
    print("  debug <cmd>   - Send debug command (on, off, plotter)")
    print("  save          - Save current data to file")
    print("  quit          - Exit interactive mode")
    print("="*60)
    
    while True:
        try:
            cmd = input("\nSTM32> ").strip().lower()
            
            if cmd == 'quit' or cmd == 'exit':
                break
            elif cmd == 'data':
                data = controller.get_latest_data()
                if data:
                    print_sensor_data(data)
                else:
                    print("No data available")
            elif cmd.startswith('debug'):
                handle_debug_command(controller, cmd)
            elif cmd == 'save':
                controller.save_data_to_file()
            elif cmd == 'help':
                print("Available commands: data, debug, save, quit")
            else:
                print("Unknown command. Type 'help' for available commands.")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

def handle_debug_command(controller: STM32Controller, cmd: str):
    """Handle debug commands"""
    parts = cmd.split()
    if len(parts) < 2:
        print("Usage: debug <command>")
        print("Commands: on, off, plotter")
        return
    
    debug_cmd = parts[1].upper()
    if debug_cmd == 'ON':
        controller.send_debug_command('DEBUG_ON')
    elif debug_cmd == 'OFF':
        controller.send_debug_command('DEBUG_OFF')
    elif debug_cmd == 'PLOTTER':
        controller.send_debug_command('PLOTTER_MODE')
    else:
        print("Invalid debug command. Use: on, off, plotter")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='STM32 PLTH Controller Interface')
    parser.add_argument('--port', default=None, help='Serial port (default: from config.py)')
    parser.add_argument('--baudrate', type=int, default=None, help='Baud rate (default: from config.py)')
    parser.add_argument('--interactive', action='store_true', help='Start in interactive mode')
    parser.add_argument('--monitor-only', action='store_true', help='Monitor only (no interactive mode)')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    args = parser.parse_args()
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Ambil port/baudrate dari config.py jika tidak diberikan via argumen
    port = args.port if args.port else get_stm32_port()
    baudrate = args.baudrate if args.baudrate else get_stm32_baudrate()
    controller = STM32Controller(port=port, baudrate=baudrate)
    
    try:
        # Connect to STM32
        if not controller.connect():
            logger.error("Failed to establish connection")
            return 1
        
        # Start monitoring
        if not controller.start_monitoring():
            logger.error("Failed to start monitoring")
            return 1
        
        print(f"Connected to STM32 on {args.port}")
        print("Monitoring sensor data...")
        
        if args.interactive:
            interactive_mode(controller)
        elif args.monitor_only:
            print("Press Ctrl+C to stop monitoring")
            try:
                while True:
                    data = controller.get_data_from_queue(timeout=5.0)
                    if data:
                        print_sensor_data(data)
                    else:
                        print("No data received in last 5 seconds...")
            except KeyboardInterrupt:
                pass
        else:
            # Default: show data for 30 seconds then enter interactive mode
            print("Monitoring for 30 seconds, then entering interactive mode...")
            end_time = time.time() + 30
            
            while time.time() < end_time:
                data = controller.get_data_from_queue(timeout=1.0)
                if data:
                    print_sensor_data(data)
                
            interactive_mode(controller)
    
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    finally:
        controller.stop_monitoring()
        controller.disconnect()
    
    return 0

if __name__ == "__main__":
    exit(main())