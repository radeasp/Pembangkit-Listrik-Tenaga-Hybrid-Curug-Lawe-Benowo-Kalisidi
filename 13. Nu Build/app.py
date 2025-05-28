from flask import Flask, render_template, jsonify, request
from datetime import datetime
from services import dummy_sensors, sensors_communication

app = Flask(__name__)

# Initialize and start sensor simulation
dummy_sensors.start_sensor_simulation(update_interval=1.0, history_duration=30.0)

# Tambahkan variable untuk tracking sumber data aktif
current_data_source = 'dummy'

# Routes
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

@app.route('/dump_load')
def dump_load():
    """Halaman Dump Load"""
    return render_template('dump_load.html', 
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
    """Halaman Pengaturan Sistem"""
    return render_template('settings.html', 
                          location_left="Bendungan PLTPH Daerah Irigasi Sidopangus",
                          location_right="Kawasan Wisata Curug Lawe Benowo Kalisidi",
                          current_time=datetime.now().strftime("%H:%M:%S"),
                          current_date=datetime.now().strftime("%A, %d %B, %Y"))

@app.route('/api/sensor-mode', methods=['GET', 'POST'])
def sensor_mode():
    global current_data_source
    
    if request.method == 'POST':
        data = request.get_json()
        new_mode = data.get('mode')
        
        if new_mode in ['dummy', 'real']:
            try:
                if new_mode == 'real':
                    sensors_communication.start_sensor_monitoring()
                    dummy_sensors.stop_simulation()
                else:
                    dummy_sensors.start_simulation()
                    sensors_communication.stop_sensor_monitoring()
                
                current_data_source = new_mode
                return jsonify({
                    'success': True,
                    'current_mode': current_data_source,
                    'message': f'Switched to {new_mode} mode'
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': str(e)
                }), 500
    
    # GET request - return current status
    return jsonify({
        'current_mode': current_data_source,
        'available_modes': {
            'dummy': True,
            'real': sensors_communication.SENSORS_AVAILABLE
        },
        'connection_status': {
            'real_sensors_detail': {
                'raspberry_pi': sensors_communication.SENSORS_AVAILABLE,
                'stm32': sensors_communication.SENSORS_AVAILABLE
            }
        }
    })

# Modifikasi endpoint data untuk menggunakan sumber yang aktif
@app.route('/api/data')
def get_data():
    """API endpoint untuk semua data sensor"""
    if current_data_source == 'real':
        data = sensors_communication.get_sensor_data()
    else:
        data = dummy_sensors.get_sensor_data()
    
    data['timestamp'] = datetime.now().strftime("%H:%M:%S")
    return jsonify(data)

@app.route('/api/data/<module>')
def get_module_data(module):
    """API endpoint untuk data sensor tertentu"""
    if current_data_source == 'real':
        module_data = sensors_communication.get_module_data(module)
    else:
        module_data = dummy_sensors.get_module_data(module)
    
    if module_data:
        data = {module: module_data}
        data['timestamp'] = datetime.now().strftime("%H:%M:%S")
        return jsonify(data)
    else:
        return jsonify({'error': 'Module not found'}), 404

@app.route('/api/history/<module>')
def get_history(module):
    """API endpoint untuk mendapatkan history data sensor tertentu"""
    history = dummy_sensors.get_history(module)
    
    if module in history:
        return jsonify({
            'history': history[module],
            'status': 'success'
        })
    return jsonify({'error': 'Module not found'}), 404

@app.route('/api/history')
def get_all_history():
    """API endpoint untuk mendapatkan semua history data"""
    history = dummy_sensors.get_history()
    return jsonify({
        'history': history,
        'status': 'success'
    })

@app.route('/api/sensor-info')
def get_sensor_info():
    """API endpoint untuk mendapatkan informasi konfigurasi sensor"""
    info = dummy_sensors.get_sensor_info()
    return jsonify({
        'sensor_info': info,
        'status': 'success'
    })

@app.route('/api/sensor-info/<module>')
def get_module_sensor_info(module):
    """API endpoint untuk mendapatkan informasi konfigurasi sensor modul tertentu"""
    info = dummy_sensors.get_module_info(module)
    
    if info:
        return jsonify({
            'module': module,
            'sensor_info': info,
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
    return jsonify({
        'simulation_running': dummy_sensors.is_running,
        'modules': list(dummy_sensors.sensor_ranges.keys()),
        'update_interval': getattr(dummy_sensors, 'update_interval', 1.0),
        'history_duration': getattr(dummy_sensors, 'history_duration', 30.0),
        'timestamp': datetime.now().isoformat()
    })

# Cleanup when app shuts down
def cleanup():
    """Cleanup function to stop sensor simulation"""
    dummy_sensors.stop_simulation()

import atexit
atexit.register(cleanup)

if __name__ == '__main__':
    try:
        app.run(debug=True, extra_files=['static/js/realtime.js', 'dummy_sensors.py'])
    except KeyboardInterrupt:
        print("\nShutting down...")
        cleanup()