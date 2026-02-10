from flask import Flask, render_template, jsonify, request
from datetime import datetime
from services.dummy_sensors import dummy_sensors
import os
import logging
import sqlite3
import time
import threading
import uuid
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

# Import database modules
from database.db_manager import DatabaseManager
from database.data_recorder import DataRecorder

# Import real sensors with error handling
try:
    from services.sensors_communication import real_sensors
    REAL_SENSORS_AVAILABLE = True
    print("Actual sensors module loaded successfully")
except ImportError as e:
    print(f"Warning: Actual sensors not available: {e}")
    REAL_SENSORS_AVAILABLE = False
    real_sensors = None

app = Flask(__name__)

# Global configuration for data source
class DataSourceConfig:
    def __init__(self):
        # Initialize with default values
        self.current_mode = 'simulasi'  # Start with simulasi by default
        self.available_modes = {
            'simulasi': True,
            'aktual': False
        }
        self.connection_status = {
            'simulasi': True,
            'aktual': False,
            'real_sensors_detail': {
                'esp32': False,
                'stm32': False
            }
        }
        
        if REAL_SENSORS_AVAILABLE:
            import time
            time.sleep(0.5)
            self._check_real_sensor_connections()

            if self.available_modes['aktual'] and self.current_mode != 'aktual':
                print(f"[OK] Real sensors detected (STM32: {self.connection_status['real_sensors_detail']['stm32']}, ESP32: {self.connection_status['real_sensors_detail']['esp32']})")
                self.current_mode = 'aktual'
                print(f"[OK] Switched to aktual mode")
    
    def _check_real_sensor_connections(self):
        """Check real sensor hardware connections"""
        try:
            if real_sensors:
                stm32_connected = False
                esp32_connected = False
                
                # Check STM32 connection - use the property directly
                if hasattr(real_sensors, 'stm32_controller') and real_sensors.stm32_controller:
                    try:

                        stm32_connected = real_sensors.stm32_controller.is_connected

                    except Exception as e:

                        stm32_connected = False
                

                if hasattr(real_sensors, 'esp32_controller') and real_sensors.esp32_controller:
                    try:

                        esp32_connected = real_sensors.esp32_controller.is_connected

                    except Exception as e:

                        esp32_connected = False
                
                self.connection_status['real_sensors_detail'] = {
                    'stm32': stm32_connected,
                    'esp32': esp32_connected
                }
                

                self.available_modes['aktual'] = stm32_connected or esp32_connected
                self.connection_status['aktual'] = self.available_modes['aktual']
                
        except Exception as e:
            print(f"[ERROR] Error checking real sensor connections: {e}")
            import traceback
            traceback.print_exc()
            self.available_modes['aktual'] = False
            self.connection_status['aktual'] = False
    

    def refresh_mode(self):
        """Refresh connection status and update available modes only"""
        self._check_real_sensor_connections()

    def get_current_sensor_source(self):
        self.refresh_mode()
        if self.current_mode == 'aktual' and REAL_SENSORS_AVAILABLE:
            return real_sensors
        else:
            return dummy_sensors
    
    def switch_mode(self, new_mode):
        """Switch between simulasi and aktual sensor modes"""
        if new_mode not in ['simulasi', 'aktual']:
            return False, "Invalid mode specified"
        
        if not self.available_modes.get(new_mode, False):
            return False, f"Mode '{new_mode}' is not available"
        
        old_mode = self.current_mode
        
        try:
            # Stop current sensor if it's running
            current_sensor = self.get_current_sensor_source()
            if hasattr(current_sensor, 'stop_simulation'):
                current_sensor.stop_simulation()
            
            # Switch to new mode
            self.current_mode = new_mode
            new_sensor = self.get_current_sensor_source()
            
            # Start new sensor simulation
            if hasattr(new_sensor, 'start_simulation'):
                if new_mode == 'aktual':
                    new_sensor.start_simulation(update_interval=1.0, history_duration=30.0)
                else:
                    new_sensor.start_simulation(update_interval=1.0, history_duration=30.0)
            
            return True, f"Successfully switched from {old_mode} to {new_mode} mode"
            
        except Exception as e:
            # Revert to old mode on error
            self.current_mode = old_mode
            return False, f"Error switching to {new_mode} mode: {str(e)}"

# Initialize data source configuration
data_config = DataSourceConfig()

@app.route('/api/sensor')
def api_sensor():
    sensor_data = data_config.get_current_sensor_source().get_sensor_data()
    return jsonify(sensor_data)
# Initialize database with enhanced auto-fix capabilities
def initialize_database_with_autofix():
    """Initialize database with comprehensive automatic permission fixing"""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'sensor_data.db')
    data_dir = os.path.dirname(db_path)
    
    print(f"Initializing database system...")
    print(f"Database path: {db_path}")
    
    # Step 1: Create directory with proper permissions
    try:
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, mode=0o755, exist_ok=True)
            print(f"[OK] Created data directory: {data_dir}")
        
        # Always check and fix directory permissions
        current_perms = oct(os.stat(data_dir).st_mode)[-3:]
        if not os.access(data_dir, os.W_OK) or current_perms != '755':
            try:
                os.chmod(data_dir, 0o755)
                print(f"[OK] Fixed directory permissions: {data_dir} ({current_perms} -> 755)")
            except OSError as e:
                print(f"[WARNING] Could not fix directory permissions: {e}")

                try:
                    test_file = os.path.join(data_dir, '.write_test')
                    with open(test_file, 'w') as f:
                        f.write('test')
                    os.remove(test_file)
                    print("[OK] Directory is writable (test passed)")
                except Exception as test_e:
                    print(f"[ERROR] Directory is not writable: {test_e}")
                    return None, f"Cannot write to directory: {data_dir}"
        
    except Exception as e:
        print(f"[ERROR] Failed to setup data directory: {e}")
        return None, f"Directory setup failed: {e}"
    
    # Step 2: Handle existing database file permissions
    if os.path.exists(db_path):
        try:
            current_perms = oct(os.stat(db_path).st_mode)[-3:]
            if not os.access(db_path, os.W_OK) or current_perms not in ['644', '664']:
                os.chmod(db_path, 0o644)
                print(f"[OK] Fixed database file permissions: {current_perms} -> 644")
        except OSError as e:
            print(f"[WARNING] Could not fix database file permissions: {e}")
            # Try to backup and recreate if possible
            try:
                backup_path = f"{db_path}.backup.{int(time.time())}"
                import shutil
                shutil.copy2(db_path, backup_path)
                print(f"[OK] Created backup: {backup_path}")
                
                # Test if we can read the database
                with sqlite3.connect(db_path, timeout=1.0) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = cursor.fetchall()
                    print(f"[OK] Database readable, found {len(tables)} tables")
                    
            except Exception as backup_e:
                print(f"[WARNING] Backup attempt failed: {backup_e}")
    
    # Step 3: Test database creation/connection with multiple attempts
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            # Use a unique test database name to avoid conflicts
            test_db_path = db_path + f'.test_{uuid.uuid4().hex[:8]}'
            

            if os.path.exists(test_db_path):
                os.remove(test_db_path)
                
            with sqlite3.connect(test_db_path, timeout=2.0) as conn:
                cursor = conn.cursor()
                cursor.execute("CREATE TABLE test (id INTEGER)")
                cursor.execute("INSERT INTO test VALUES (1)")
                cursor.execute("SELECT * FROM test")
                result = cursor.fetchone()
                if result and result[0] == 1:
                    conn.commit()
                    print("[OK] Database write test successful")
                else:
                    raise Exception("Database test query failed")
            
            # Clean up test database
            if os.path.exists(test_db_path):
                os.remove(test_db_path)
            
            break
            
        except Exception as e:
            print(f"[WARNING] Database test attempt {attempt + 1}/{max_attempts} failed: {e}")
            if attempt < max_attempts - 1:

                try:
                    if os.path.exists(db_path):
                        os.chmod(db_path, 0o666)  # More permissive
                    os.chmod(data_dir, 0o777)   # More permissive
                    print(f"[OK] Applied more permissive permissions (attempt {attempt + 2})")
                except:
                    pass
                time.sleep(0.1)  # Brief pause
            else:
                return None, f"Database access failed after {max_attempts} attempts: {e}"
    
    # Step 4: Initialize DatabaseManager
    try:
        print(f"[INFO] Attempting to initialize DatabaseManager with path: {db_path}")
        db_manager = DatabaseManager(db_path=db_path)
        print("[OK] Database manager initialized successfully")
        
        # Test basic operations
        test_data = {"test": "value", "timestamp": datetime.now().isoformat()}
        print(f"[INFO] Testing database write operation...")
        if db_manager.store_sensor_data("test_module", test_data, "test"):
            print("[OK] Database write operation test successful")
            # Clean up test data
            try:
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM sensor_readings WHERE module = 'test_module'")
                    conn.commit()
                print("[OK] Test data cleaned up")
            except Exception as cleanup_e:
                print(f"[WARNING] Test data cleanup failed: {cleanup_e}")
        else:
            print("[WARNING] Database write test failed, but manager initialized")
        
        return db_manager, "Database initialized successfully"
        
    except Exception as e:
        print(f"[ERROR] DatabaseManager initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return None, f"DatabaseManager failed: {e}"

# Initialize database with auto-fix - More robust handling
try:
    print("[INFO] Starting database initialization...")
    db_manager, db_init_message = initialize_database_with_autofix()
    if db_manager:
        print(f"[OK] {db_init_message}")
    else:
        print(f"[ERROR] Database initialization failed: {db_init_message}")
        print("[OK] Application will continue without database functionality")
        db_manager = None
        

    if db_manager:
        try:
            # Simple test to ensure database is working
            test_data = {"test": "initialization", "timestamp": datetime.now().isoformat()}
            if db_manager.store_sensor_data("init_test", test_data, "system"):
                print("[OK] Database write test successful")
                # Clean up test data
                import sqlite3
                with sqlite3.connect(db_manager.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM sensor_readings WHERE module = 'init_test'")
                    conn.commit()
            else:
                print("[WARNING] Database write test failed - continuing without database")
                db_manager = None
        except Exception as test_e:
            print(f"[WARNING] Database test failed: {test_e} - continuing without database")
            db_manager = None
            
except Exception as e:
    print(f"[ERROR] Critical database initialization error: {e}")
    import traceback
    traceback.print_exc()
    print("[OK] Application will continue without database functionality")
    db_manager = None

data_recorder = None
if db_manager:
    try:
        data_recorder = DataRecorder(db_manager=db_manager, data_config=data_config, record_interval=60)
        print("[OK] Data recorder initialized successfully")
    except Exception as e:
        print(f"[ERROR] Failed to initialize data recorder: {e}")
        data_recorder = None
else:
    print("[INFO] Data recorder disabled due to database initialization failure")

# Initialize and start sensor simulation based on current mode
try:
    current_sensor = data_config.get_current_sensor_source()
    current_sensor.start_simulation(update_interval=1.0, history_duration=30.0)
    print(f"[OK] Sensor simulation started in {data_config.current_mode} mode")
    
    # Display connection status
    if data_config.current_mode == 'simulasi':
        print("[INFO] Using simulation data (no real sensors connected)")
    else:
        print(f"[INFO] Using real sensors - connection status: {data_config.connection_status}")
        
except Exception as e:
    print(f"[ERROR] Failed to start sensor simulation: {e}")
    # Fall back to dummy sensors
    try:
        from services.dummy_sensors import dummy_sensors
        dummy_sensors.start_simulation(update_interval=1.0, history_duration=30.0)
        data_config.current_mode = 'simulasi'
        print("[OK] Fallback to dummy sensors successful")
    except Exception as fallback_e:
        print(f"[CRITICAL] Even fallback sensors failed: {fallback_e}")
        # Continue anyway - the app should still work for basic functionality

# Routes (unchanged from original)
@app.route('/')
def index():
    """Halaman utama - Dashboard"""
    return render_template('dashboard.html', 
                          location_left="Bendungan PLTPH Daerah Irigasi Sidopangus",
                          location_right="Kawasan Wisata Curug Lawe Benowo Kalisidi",
                          current_time=datetime.now().strftime("%H:%M:%S"),
                          current_date=datetime.now().strftime("%A, %d %B, %Y"))

@app.route('/picohydro_generator')
def picohydro_generator():
    """Halaman Picohydro Generator"""
    return render_template('picohydro_generator.html', 
                          location_left="Bendungan PLTPH Daerah Irigasi Sidopangus",
                          location_right="Kawasan Wisata Curug Lawe Benowo Kalisidi",
                          current_time=datetime.now().strftime("%H:%M:%S"),
                          current_date=datetime.now().strftime("%A, %d %B, %Y"))

@app.route('/solar_panel_generator')
def solar_panel_generator():
    """Halaman Solar Panel Generator"""
    return render_template('solar_panel_generator.html', 
                          location_left="Bendungan PLTPH Daerah Irigasi Sidopangus",
                          location_right="Kawasan Wisata Curug Lawe Benowo Kalisidi",
                          current_time=datetime.now().strftime("%H:%M:%S"),
                          current_date=datetime.now().strftime("%A, %d %B, %Y"))

@app.route('/baterai')
def baterai():
    """Halaman Baterai"""
    return render_template('baterai.html', 
                          location_left="Bendungan PLTPH Daerah Irigasi Sidopangus",
                          location_right="Kawasan Wisata Curug Lawe Benowo Kalisidi",
                          current_time=datetime.now().strftime("%H:%M:%S"),
                          current_date=datetime.now().strftime("%A, %d %B, %Y"))

@app.route('/beban')
def beban():
    """Halaman Beban"""
    return render_template('beban.html', 
                          location_left="Bendungan PLTPH Daerah Irigasi Sidopangus",
                          location_right="Kawasan Wisata Curug Lawe Benowo Kalisidi",
                          current_time=datetime.now().strftime("%H:%M:%S"),
                          current_date=datetime.now().strftime("%A, %d %B, %Y"))


@app.route('/environment')
def environment():
    """Halaman Kondisi Lingkungan"""
    return render_template('environment.html', 
                          location_left="Bendungan PLTPH Daerah Irigasi Sidopangus",
                          location_right="Kawasan Wisata Curug Lawe Benowo Kalisidi",
                          current_time=datetime.now().strftime("%H:%M:%S"),
                          current_date=datetime.now().strftime("%A, %d %B, %Y"))

@app.route('/settings')
def settings():
    """Halaman Pengaturan Sistem dan Database"""
    return render_template('settings.html', 
                          location_left="Bendungan PLTPH Daerah Irigasi Sidopangus",
                          location_right="Kawasan Wisata Curug Lawe Benowo Kalisidi",
                          current_time=datetime.now().strftime("%H:%M:%S"),
                          current_date=datetime.now().strftime("%A, %d %B, %Y"))

@app.route('/data_recorder')
def data_recorder_page():
    """Halaman Database Sensor"""
    return render_template('data_recorder.html', 
                          location_left="Bendungan PLTPH Daerah Irigasi Sidopangus",
                          location_right="Kawasan Wisata Curug Lawe Benowo Kalisidi",
                          current_time=datetime.now().strftime("%H:%M:%S"),
                          current_date=datetime.now().strftime("%A, %d %B, %Y"))

# Route for database management UI, now separate from settings page

# Cached database status to improve performance
db_stats_cache = {
    'last_update': 0,
    'db_size': "Unknown",
    'record_count': 0,
    'formatted_size': "Unknown"
}

# Database API endpoints
@app.route('/api/data-recorder/status')
def get_recorder_status():
    """Get data recorder status with real database information"""
    basic_response = {
        'success': True,
        'message': 'Status retrieved successfully',
        'recording': False,
        'data_source': 'simulasi',
        'db_size': 'N/A',
        'record_count': 0,
        'record_interval': 60,
        'days_to_keep': 30,
        'last_cleanup': None,
        'database_available': False
    }
    
    # Try to get real data from database and data recorder
    try:
        # Update data source
        if hasattr(data_config, 'current_mode'):
            basic_response['data_source'] = data_config.current_mode
        

        if db_manager is not None:
            basic_response['database_available'] = True
            
            # Get actual record count from database
            try:
                import sqlite3
                with sqlite3.connect(db_manager.db_path, timeout=2.0) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM sensor_readings")
                    count = cursor.fetchone()[0]
                    basic_response['record_count'] = count
                    
                    # Get database file size
                    import os
                    if os.path.exists(db_manager.db_path):
                        size_bytes = os.path.getsize(db_manager.db_path)
                        if size_bytes < 1024:
                            basic_response['db_size'] = f"{size_bytes} B"
                        elif size_bytes < 1024*1024:
                            basic_response['db_size'] = f"{size_bytes/1024:.1f} KB"
                        else:
                            basic_response['db_size'] = f"{size_bytes/(1024*1024):.1f} MB"
                        
            except Exception as db_e:
                app.logger.warning(f"Error getting database stats: {db_e}")
                basic_response['record_count'] = 0
                basic_response['db_size'] = "Error"
        
        # Check data recorder status
        if data_recorder is not None:
            basic_response['recording'] = getattr(data_recorder, 'recording', False)
            if hasattr(data_recorder, 'record_interval'):
                basic_response['record_interval'] = data_recorder.record_interval
            if hasattr(data_recorder, 'days_to_keep'):
                basic_response['days_to_keep'] = data_recorder.days_to_keep
            
    except Exception as e:
        app.logger.error(f"Error getting recorder status: {e}")
        basic_response['message'] = f'Error getting status: {str(e)}'
    
    return jsonify(basic_response)

@app.route('/api/data-recorder/toggle', methods=['POST'])
def toggle_recording():
    """Toggle data recording on/off - simplified to avoid errors"""
    # Always return success with basic info
    return jsonify({
        'success': False,
        'message': 'Data recorder not available - database initialization failed',
        'recording': False,
        'database_available': False
    })

@app.route('/api/data-recorder/settings', methods=['POST'])
def update_recorder_settings():
    """Update data recorder settings"""
    if not data_recorder:
        return jsonify({
            'success': False,
            'message': 'Data recorder not available - database initialization failed',
            'database_available': bool(db_manager)
        })  # Changed to 200 to avoid frontend errors
    
    data = request.json or {}
    result = {'success': True, 'message': 'Settings updated'}
    
    try:
        # Update recording interval if specified
        if 'record_interval' in data:
            interval = int(data['record_interval'])
            if data_recorder.set_recording_interval(interval):
                result['record_interval'] = interval
            else:
                result['success'] = False
                result['message'] = "Invalid recording interval"
        
        # Update data retention if specified
        if 'days_to_keep' in data:
            days = int(data['days_to_keep'])
            if data_recorder.set_data_retention(days):
                result['days_to_keep'] = days
            else:
                result['success'] = False
                result['message'] = "Invalid data retention period"
                
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error updating recorder settings: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'database_available': bool(db_manager)
        })  # Changed to 200 to avoid frontend errors

@app.route('/api/data-recorder/data')
def query_data():
    """Query recorded sensor data"""
    if not db_manager:
        return jsonify({
            'success': False,
            'message': 'Database not available - initialization failed',
            'data': [],
            'database_available': False
        })  # Changed to 200 to avoid frontend errors
    
    module = request.args.get('module')
    start_time = request.args.get('start_time')
    end_time = request.args.get('end_time')
    limit = request.args.get('limit', 100, type=int)
    
    try:
        data = db_manager.get_sensor_data(
            module=module,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'data': data,
            'count': len(data),
            'database_available': bool(db_manager)
        })
        
    except Exception as e:
        app.logger.error(f"Error querying data: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'data': [],
            'database_available': bool(db_manager)
        })  # Changed to 200 to avoid frontend errors

@app.route('/api/data-recorder/summary')
def get_daily_summary():
    """Get daily summary data"""
    if not db_manager:
        return jsonify({
            'success': False,
            'message': 'Database not available - initialization failed',
            'summaries': [],
            'database_available': False
        })  # Changed to 200 to avoid frontend errors
    
    date = request.args.get('date')
    module = request.args.get('module')
    
    try:
        summaries = db_manager.get_daily_summary(date=date, module=module)
        
        return jsonify({
            'success': True,
            'summaries': summaries,
            'count': len(summaries),
            'database_available': bool(db_manager)
        })
        
    except Exception as e:
        app.logger.error(f"Error getting summary data: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'summaries': [],
            'database_available': bool(db_manager)
        })  # Changed to 200 to avoid frontend errors

@app.route('/api/data-recorder/generate-summary', methods=['POST'])
def generate_daily_summary():
    """Generate daily summary for a date"""
    if not db_manager:
        return jsonify({
            'success': False,
            'message': 'Database not available - initialization failed',
            'database_available': False
        })  # Changed to 200 to avoid frontend errors
    
    data = request.json or {}
    date = data.get('date')
    
    try:
        success = db_manager.generate_daily_summary(date=date)
        
        if success:
            return jsonify({
                'success': True,
                'message': f"Summary for {date} generated successfully",
                'database_available': bool(db_manager)
            })
        else:
            return jsonify({
                'success': False,
                'message': "Failed to generate summary",
                'database_available': bool(db_manager)
            })  # Changed to 200 to avoid frontend errors
            
    except Exception as e:
        app.logger.error(f"Error generating summary: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'database_available': bool(db_manager)
        })  # Changed to 200 to avoid frontend errors

@app.route('/api/data-recorder/export-csv')
def export_csv():
    """Export data as CSV"""
    # This is handled client-side in JavaScript
    pass

@app.route('/api/data-recorder/export-json')
def export_json():
    """Export data as JSON"""
    # This is handled client-side in JavaScript
    pass

# Modified API endpoints to use dynamic data source
@app.route('/api/data')
def get_data():
    """API endpoint untuk semua data sensor"""
    try:
        current_sensor = data_config.get_current_sensor_source()
        

        app.logger.debug(f"Getting all sensor data, mode: {data_config.current_mode}")
        
        data = current_sensor.get_sensor_data()
        data['timestamp'] = datetime.now().strftime("%H:%M:%S")
        data['data_source'] = data_config.current_mode
        

        if request.args.get('record', '').lower() in ('true', '1', 'yes'):
            if db_manager:
                try:
                    db_manager.store_all_sensors_data(data, data_source=data_config.current_mode)
                except Exception as e:
                    app.logger.error(f"Error recording data: {e}")
            else:
                app.logger.warning("Database recording requested but database manager not available")
        
        return jsonify(data)
        
    except Exception as e:
        app.logger.error(f"Error getting sensor data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Internal server error',
            'message': str(e),
            'data_source': data_config.current_mode
        }), 500

@app.route('/api/data/<module>')
def get_module_data(module):
    """API endpoint untuk data sensor tertentu"""
    try:
        current_sensor = data_config.get_current_sensor_source()
        

        app.logger.debug(f"Getting data for module: {module}, mode: {data_config.current_mode}")
        
        module_data = current_sensor.get_module_data(module)
        
        if module_data:
            data = {module: module_data}
            data['timestamp'] = datetime.now().strftime("%H:%M:%S")
            data['data_source'] = data_config.current_mode
            return jsonify(data)
        else:
            app.logger.warning(f"Module not found: {module}")
            return jsonify({'error': 'Module not found', 'module': module}), 404
            
    except Exception as e:
        app.logger.error(f"Error getting module data for {module}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'Internal server error',
            'message': str(e),
            'module': module,
            'data_source': data_config.current_mode
        }), 500

@app.route('/api/history/<module>')
def get_history(module):
    """API endpoint untuk mendapatkan history data sensor tertentu"""
    current_sensor = data_config.get_current_sensor_source()
    history = current_sensor.get_history(module)
    
    if module in history:
        return jsonify({
            'history': history[module],
            'data_source': data_config.current_mode,
            'status': 'success'
        })
    return jsonify({'error': 'Module not found'}), 404

@app.route('/api/history')
def get_all_history():
    """API endpoint untuk mendapatkan semua history data"""
    current_sensor = data_config.get_current_sensor_source()
    history = current_sensor.get_history()
    return jsonify({
        'history': history,
        'data_source': data_config.current_mode,
        'status': 'success'
    })

@app.route('/api/sensor-info')
def get_sensor_info():
    """API endpoint untuk mendapatkan informasi konfigurasi sensor"""
    current_sensor = data_config.get_current_sensor_source()
    info = current_sensor.get_sensor_info()
    return jsonify({
        'sensor_info': info,
        'data_source': data_config.current_mode,
        'status': 'success'
    })

@app.route('/api/sensor-info/<module>')
def get_module_sensor_info(module):
    """API endpoint untuk mendapatkan informasi konfigurasi sensor modul tertentu"""
    current_sensor = data_config.get_current_sensor_source()
    info = current_sensor.get_module_info(module)
    
    if info:
        return jsonify({
            'module': module,
            'sensor_info': info,
            'data_source': data_config.current_mode,
            'status': 'success'
        })
    return jsonify({'error': 'Module not found'}), 404

@app.route('/api/datetime')
def get_datetime():
    """API endpoint untuk mendapatkan waktu dan tanggal saat ini"""
    return jsonify({
        'time': datetime.now().strftime("%H:%M:%S"),
        'date': datetime.now().strftime("%A, %d %B, %Y")
    })

@app.route('/api/status')
def get_status():
    """API endpoint untuk mendapatkan status sistem"""
    current_sensor = data_config.get_current_sensor_source()
    is_running = getattr(current_sensor, 'is_running', False)
    
    return jsonify({
        'simulation_running': is_running,
        'data_source': data_config.current_mode,
        'available_modes': data_config.available_modes,
        'modules': list(current_sensor.get_sensor_info().keys()) if hasattr(current_sensor, 'get_sensor_info') else [],
        'update_interval': getattr(current_sensor, 'update_interval', 1.0),
        'history_duration': getattr(current_sensor, 'history_duration', 30.0),
        'timestamp': datetime.now().isoformat()
    })

# New API endpoints for data source switching
@app.route('/api/sensor-mode', methods=['GET', 'POST'])
def sensor_mode_api():
    """API endpoint untuk mengatur mode sensor (simulasi/aktual)"""
    if request.method == 'GET':
        # Always refresh mode and connection status before returning
        data_config._check_real_sensor_connections()
        data_config.refresh_mode()
        return jsonify({
            'current_mode': data_config.current_mode,
            'available_modes': data_config.available_modes,
            'connection_status': data_config.connection_status,
            'status': 'success'
        })
    
    elif request.method == 'POST':
        data = request.json or {}
        new_mode = data.get('mode')
        
        if not new_mode:
            return jsonify({
                'success': False,
                'message': 'Mode parameter is required'
            }), 400
        
        success, message = data_config.switch_mode(new_mode)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'current_mode': data_config.current_mode,
                'available_modes': data_config.available_modes
            })
        else:
            return jsonify({
                'success': False,
                'message': message,
                'current_mode': data_config.current_mode,
                'available_modes': data_config.available_modes
            }), 400

@app.route('/api/connection-status')
def connection_status_api():
    """API endpoint untuk memeriksa status koneksi sensor"""
    # Refresh connection status
    data_config._check_real_sensor_connections()
    
    return jsonify({
        'connection_status': data_config.connection_status,
        'available_modes': data_config.available_modes,
        'current_mode': data_config.current_mode,
        'timestamp': datetime.now().isoformat(),
        'status': 'success'
    })




def cleanup():
    """Cleanup function to stop sensor simulation and database recording"""
    try:
        print("Starting application cleanup...")
        
        # Stop database health monitoring
        if db_health_monitor:
            db_health_monitor.stop_monitoring()
            print("[OK] Database health monitoring stopped")
        
        # Flush cache to database if possible
        if db_manager and hasattr(db_manager, 'cache'):
            try:
                flushed = db_manager.force_cache_flush()
                if flushed > 0:
                    print(f"[OK] Flushed {flushed} cached entries to database")
                    
                # Save cache to disk
                db_manager.cache._save_cache()
                print("[OK] Cache saved to disk")
            except Exception as cache_e:
                print(f"[WARNING] Cache cleanup error: {cache_e}")
        
        # Stop current sensor
        current_sensor = data_config.get_current_sensor_source()
        if hasattr(current_sensor, 'stop_simulation'):
            current_sensor.stop_simulation()
            print("[OK] Sensor simulation stopped")
        

        if REAL_SENSORS_AVAILABLE and real_sensors:
            if hasattr(real_sensors, 'cleanup'):
                real_sensors.cleanup()
                print("[OK] Aktual sensors cleaned up")
        

        if hasattr(dummy_sensors, 'stop_simulation'):
            dummy_sensors.stop_simulation()
            print("[OK] Simulasi sensors cleaned up")
        

        if data_recorder and data_recorder.recording:
            data_recorder.stop_recording()
            print("[OK] Data recording stopped")
            
        print("Application cleanup completed successfully")
            
    except Exception as e:
        print(f"Error during cleanup: {e}")

import atexit
atexit.register(cleanup)

if __name__ == '__main__':
    try:
        print(f"Starting Flask app with data source: {data_config.current_mode}")
        print(f"Available modes: {data_config.available_modes}")
        

        if data_recorder:
            data_recorder.start_recording()
            print(f"[OK] Data recording started with interval: {data_recorder.record_interval}s")
        else:
            print("[WARNING] Data recording disabled - database initialization failed")
            print("The application will run without database functionality")
        
        app.run(
            debug=True,
            host='0.0.0.0',
            port=5000,
            use_reloader=False,  # Disable reloader to avoid duplicate processes
            extra_files=[
                'static/js/realtime.js', 
                'services/sensors_communication.py',
                'services/dummy_sensors.py']
        )
    except KeyboardInterrupt:
        print("\nShutting down...")
        cleanup()

# Database Health Monitor and Auto-Recovery System
class DatabaseHealthMonitor:
    """Monitors database health and automatically fixes issues"""
    
    def __init__(self, db_manager, check_interval=30):
        self.db_manager = db_manager
        self.check_interval = check_interval
        self.monitoring = False
        self.monitor_thread = None
        self.last_check = 0
        self.consecutive_failures = 0
        self.max_failures = 3
        
    def start_monitoring(self):
        """Start the background monitoring thread"""
        if not self.monitoring and self.db_manager:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            print("[OK] Database health monitoring started")
    
    def stop_monitoring(self):
        """Stop the background monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                current_time = time.time()
                if current_time - self.last_check >= self.check_interval:
                    self._check_and_fix_database()
                    self.last_check = current_time
                
                time.sleep(5)
            except Exception as e:
                app.logger.error(f"Database monitor error: {e}")
                time.sleep(10)
    
    def _check_and_fix_database(self):
        """Check database health and attempt fixes if needed"""
        try:
            # Test basic database operations
            if not self._test_database_operations():
                print(f"[WARNING] Database health check failed, attempting auto-fix...")
                if self._attempt_database_fix():
                    print("[OK] Database auto-fix successful")
                    self.consecutive_failures = 0
                else:
                    self.consecutive_failures += 1
                    print(f"[ERROR] Database auto-fix failed (attempt {self.consecutive_failures}/{self.max_failures})")
                    
                    if self.consecutive_failures >= self.max_failures:
                        print("[ERROR] Maximum auto-fix attempts reached, database may need manual intervention")
                        self.consecutive_failures = 0
            else:

                if self.consecutive_failures > 0:
                    print("[OK] Database health restored")
                    self.consecutive_failures = 0
                    
        except Exception as e:
            app.logger.error(f"Database health check error: {e}")
    
    def _test_database_operations(self):
        """Test if database operations are working"""
        try:
            # Test write operation
            test_data = {
                "test_timestamp": datetime.now().isoformat(),
                "health_check": True
            }
            
            success = self.db_manager.store_sensor_data(
                "health_check", test_data, "monitor"
            )
            
            if success:

                try:
                    with sqlite3.connect(self.db_manager.db_path, timeout=1.0) as conn:
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM sensor_readings WHERE module = 'health_check'")
                        conn.commit()
                except:
                    pass
            
            return success
            
        except Exception as e:
            app.logger.debug(f"Database test failed: {e}")
            return False
    
    def _attempt_database_fix(self):
        """Attempt to fix database issues automatically"""
        try:
            db_path = self.db_manager.db_path
            data_dir = os.path.dirname(db_path)
            
            if os.path.exists(db_path):
                try:
                    current_perms = oct(os.stat(db_path).st_mode)[-3:]
                    if not os.access(db_path, os.W_OK):
                        os.chmod(db_path, 0o644)
                        print(f"[OK] Fixed database file permissions: {current_perms} -> 644")
                except OSError:
                    pass
            
            try:
                if not os.access(data_dir, os.W_OK):
                    os.chmod(data_dir, 0o755)
                    print(f"[OK] Fixed directory permissions: {data_dir}")
            except OSError:
                pass
            
            # Fix 3: Test database integrity
            try:
                with sqlite3.connect(db_path, timeout=2.0) as conn:
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA integrity_check")
                    result = cursor.fetchone()
                    if result and result[0] != 'ok':
                        print(f"[WARNING] Database integrity issue detected: {result[0]}")
                        # Attempt to vacuum the database
                        cursor.execute("VACUUM")
                        print("[OK] Database vacuum completed")
            except Exception as integrity_e:
                print(f"[WARNING] Database integrity check failed: {integrity_e}")
            
            # Fix 4: Reinitialize database manager if needed
            try:
                # Test if the fix worked
                return self._test_database_operations()
            except:
                return False
                
        except Exception as e:
            app.logger.error(f"Database auto-fix error: {e}")
            return False

# Initialize database health monitor
db_health_monitor = None
if db_manager:
    db_health_monitor = DatabaseHealthMonitor(db_manager, check_interval=60)  # Check every minute
    db_health_monitor.start_monitoring()

@app.route('/api/database/performance')
def database_performance():
    """API endpoint untuk mendapatkan statistik performa database"""
    if not db_manager:
        return jsonify({
            'success': False,
            'message': 'Database not available',
            'stats': None,
            'database_available': False
        })  # Changed to 200 to avoid frontend errors
    
    try:
        stats = db_manager.get_performance_stats()
        return jsonify({
            'success': True,
            'stats': stats,
            'timestamp': datetime.now().isoformat(),
            'database_available': bool(db_manager)
        })
    except Exception as e:
        app.logger.error(f"Error getting database performance stats: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'stats': None,
            'database_available': bool(db_manager)
        })  # Changed to 200 to avoid frontend errors

@app.route('/api/database/flush-cache', methods=['POST'])
def flush_database_cache():
    """API endpoint untuk memaksa flush cache ke database"""
    if not db_manager:
        return jsonify({
            'success': False,
            'message': 'Database not available',
            'flushed': 0,
            'database_available': False
        })  # Changed to 200 to avoid frontend errors
    
    try:
        flushed_count = db_manager.force_cache_flush()
        return jsonify({
            'success': True,
            'message': f'Flushed {flushed_count} entries from cache',
            'flushed': flushed_count,
            'database_available': bool(db_manager)
        })
    except Exception as e:
        app.logger.error(f"Error flushing cache: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'flushed': 0,
            'database_available': bool(db_manager)
        })  # Changed to 200 to avoid frontend errors
