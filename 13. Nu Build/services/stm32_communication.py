#!/usr/bin/env python3
"""
STM32 PLTH Controller - Raspberry Pi Interface
Communicates with STM32 controller for Pico Hydro, Solar, Battery monitoring and control
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
    solar_voltage: float = 0.0
    solar_current: float = 0.0
    dumpload_voltage: float = 0.0
    dumpload_current: float = 0.0
    picohydro_charging_current: float = 0.0
    battery_voltage: float = 0.0
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
            'solar_voltage': self.solar_voltage,
            'solar_current': self.solar_current,
            'dumpload_voltage': self.dumpload_voltage,
            'dumpload_current': self.dumpload_current,
            'picohydro_charging_current': self.picohydro_charging_current,
            'battery_voltage': self.battery_voltage,
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
    """Main controller class for STM32 communication"""
    
    def __init__(self, port: str = '/dev/ttyUSB0', baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn: Optional[serial.Serial] = None
        self.running = False
        self.data_queue = queue.Queue()
        self.latest_data: Optional[SensorData] = None
        self.data_lock = threading.Lock()
        
        # PID Parameters for sending updates
        self.current_setpoint = 14.4
        self.current_kp = 1.0
        self.current_ki = 0.1
        self.current_kd = 0.05
        
    def connect(self) -> bool:
        """Establish serial connection to STM32"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1,
                write_timeout=1
            )
            time.sleep(2)  # Wait for connection to stabilize
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
        while self.running:
            try:
                if self.serial_conn.in_waiting > 0:
                    line = self.serial_conn.readline().decode('utf-8').strip()
                    if line:
                        self._process_received_data(line)
                time.sleep(0.01)  # Small delay to prevent CPU overload
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(1)
    
    def _process_received_data(self, line: str):
        """Process received JSON data from STM32"""
        try:
            # Try to parse as JSON
            data_dict = json.loads(line)
            
            # Create SensorData object
            sensor_data = SensorData(
                picohydro_voltage=data_dict.get('picohydro_voltage', 0.0),
                picohydro_current=data_dict.get('picohydro_current', 0.0),
                solar_voltage=data_dict.get('solar_voltage', 0.0),
                solar_current=data_dict.get('solar_current', 0.0),
                dumpload_voltage=data_dict.get('dumpload_voltage', 0.0),
                dumpload_current=data_dict.get('dumpload_current', 0.0),
                picohydro_charging_current=data_dict.get('picohydro_charging_current', 0.0),
                battery_voltage=data_dict.get('battery_voltage', 0.0),
                battery_in_current=data_dict.get('battery_in_current', 0.0),
                battery_out_current=data_dict.get('battery_out_current', 0.0),
                setpoint=data_dict.get('setpoint', 0.0),
                kp=data_dict.get('kp', 0.0),
                ki=data_dict.get('ki', 0.0),
                kd=data_dict.get('kd', 0.0),
                pwm_output=data_dict.get('pwm_output', 0),
                timestamp=data_dict.get('timestamp', 0)
            )
            
            # Update latest data with thread safety
            with self.data_lock:
                self.latest_data = sensor_data
            
            # Add to queue for processing
            try:
                self.data_queue.put_nowait(sensor_data)
            except queue.Full:
                # Remove oldest item if queue is full
                try:
                    self.data_queue.get_nowait()
                    self.data_queue.put_nowait(sensor_data)
                except queue.Empty:
                    pass
            
            logger.debug(f"Received sensor data: Battery={sensor_data.battery_voltage:.2f}V, "
                        f"Picohydro={sensor_data.picohydro_voltage:.2f}V, "
                        f"PWM={sensor_data.pwm_output}")
                        
        except json.JSONDecodeError:
            # Handle non-JSON debug output from STM32
            if "ADC READINGS" in line or "VOLTAGE SENSORS" in line or "CURRENT SENSORS" in line:
                logger.debug(f"STM32 Debug: {line}")
            else:
                logger.warning(f"Received non-JSON data: {line}")
        except Exception as e:
            logger.error(f"Error processing received data: {e}")
    
    def send_pid_parameters(self, setpoint: float = None, kp: float = None, 
                          ki: float = None, kd: float = None) -> bool:
        """Send PID parameters to STM32"""
        if not self.serial_conn or not self.serial_conn.is_open:
            logger.error("Serial connection not established")
            return False
        
        try:
            # Create parameter update dictionary
            params = {}
            if setpoint is not None:
                params['setpoint'] = setpoint
                self.current_setpoint = setpoint
            if kp is not None:
                params['kp'] = kp
                self.current_kp = kp
            if ki is not None:
                params['ki'] = ki
                self.current_ki = ki
            if kd is not None:
                params['kd'] = kd
                self.current_kd = kd
            
            if not params:
                logger.warning("No parameters to send")
                return False
            
            # Send JSON command
            json_command = json.dumps(params)
            self.serial_conn.write((json_command + '\n').encode('utf-8'))
            
            logger.info(f"Sent PID parameters: {params}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending PID parameters: {e}")
            return False
    
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
    
    print(f"🔋 POWER SOURCES:")
    print(f"   Pico Hydro    : {data.picohydro_voltage:6.2f} V  |  {data.picohydro_current:6.2f} A")
    print(f"   Solar Panel   : {data.solar_voltage:6.2f} V  |  {data.solar_current:6.2f} A")
    print(f"   Charging Curr : {data.picohydro_charging_current:6.2f} A")
    
    print(f"\n🔋 BATTERY SYSTEM:")
    print(f"   Battery Volt  : {data.battery_voltage:6.2f} V")
    print(f"   Battery In    : {data.battery_in_current:6.2f} A")
    print(f"   Battery Out   : {data.battery_out_current:6.2f} A")
    
    print(f"\n⚡ DUMP LOAD:")
    print(f"   Dump Load     : {data.dumpload_voltage:6.2f} V  |  {data.dumpload_current:6.2f} A")
    
    print(f"\n🎛️  PID CONTROL:")
    print(f"   Setpoint      : {data.setpoint:6.2f} V")
    print(f"   Error         : {data.setpoint - data.picohydro_voltage:6.2f} V")
    print(f"   PWM Output    : {data.pwm_output:3d}/255 ({(data.pwm_output/255)*100:5.1f}%)")
    print(f"   PID Params    : Kp={data.kp:5.2f}, Ki={data.ki:5.2f}, Kd={data.kd:5.2f}")
    
    # Calculate power values
    pico_power = data.picohydro_voltage * data.picohydro_current
    solar_power = data.solar_voltage * data.solar_current
    dump_power = data.dumpload_voltage * data.dumpload_current
    battery_power_in = data.battery_voltage * data.battery_in_current
    battery_power_out = data.battery_voltage * data.battery_out_current
    
    print(f"\n⚡ POWER CALCULATIONS:")
    print(f"   Pico Hydro    : {pico_power:6.2f} W")
    print(f"   Solar Panel   : {solar_power:6.2f} W")
    print(f"   Dump Load     : {dump_power:6.2f} W")
    print(f"   Battery In    : {battery_power_in:6.2f} W")
    print(f"   Battery Out   : {battery_power_out:6.2f} W")
    print(f"   Net Battery   : {battery_power_in - battery_power_out:6.2f} W")

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
            elif cmd.startswith('set'):
                handle_set_command(controller, cmd)
            elif cmd.startswith('debug'):
                handle_debug_command(controller, cmd)
            elif cmd == 'save':
                controller.save_data_to_file()
            elif cmd == 'help':
                print("Available commands: data, set, debug, save, quit")
            else:
                print("Unknown command. Type 'help' for available commands.")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

def handle_set_command(controller: STM32Controller, cmd: str):
    """Handle set parameter commands"""
    parts = cmd.split()
    if len(parts) < 3:
        print("Usage: set <parameter> <value>")
        print("Parameters: setpoint, kp, ki, kd")
        return
    
    param = parts[1]
    try:
        value = float(parts[2])
    except ValueError:
        print("Invalid value. Please enter a number.")
        return
    
    if param == 'setpoint':
        controller.send_pid_parameters(setpoint=value)
    elif param == 'kp':
        controller.send_pid_parameters(kp=value)
    elif param == 'ki':
        controller.send_pid_parameters(ki=value)
    elif param == 'kd':
        controller.send_pid_parameters(kd=value)
    else:
        print("Invalid parameter. Use: setpoint, kp, ki, kd")

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
    parser.add_argument('--port', default='/dev/ttyUSB0', help='Serial port (default: /dev/ttyUSB0)')
    parser.add_argument('--baudrate', type=int, default=115200, help='Baud rate (default: 115200)')
    parser.add_argument('--interactive', action='store_true', help='Start in interactive mode')
    parser.add_argument('--monitor-only', action='store_true', help='Monitor only (no interactive mode)')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Create controller
    controller = STM32Controller(port=args.port, baudrate=args.baudrate)
    
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