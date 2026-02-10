#!/usr/bin/env python3
"""
Script deployment untuk production environment
"""
import os
import sys
import subprocess
import shutil

def check_requirements():
    """Cek apakah semua requirements terpenuhi"""
    print("🔍 Checking requirements...")
    
    required_files = [
        'app.py',
        'config.py',
        'requirements.txt',
        'database/db_manager.py',
        'database/data_recorder.py',
        'services/dummy_sensors.py',
        'static/',
        'templates/'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print("❌ Missing required files:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    
    print("✅ All required files found")
    return True

def create_production_structure():
    """Buat struktur folder untuk produksi"""
    print("📁 Creating production structure...")
    
    # Buat folder logs jika belum ada
    if not os.path.exists('logs'):
        os.makedirs('logs')
        print("✅ Created logs directory")
    
    # Buat folder backups jika belum ada
    if not os.path.exists('backups'):
        os.makedirs('backups')
        print("✅ Created backups directory")
    
    # Buat folder untuk production config
    if not os.path.exists('config'):
        os.makedirs('config')
        print("✅ Created config directory")
    
    return True

def install_dependencies():
    """Install dependencies untuk production"""
    print("📦 Installing dependencies...")
    
    try:
        # Install production dependencies
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                      check=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        return False

def configure_production():
    """Konfigurasi untuk production environment"""
    print("⚙️ Configuring production environment...")
    
    # Set environment variables
    os.environ['FLASK_ENV'] = 'production'
    os.environ['PYTHONPATH'] = os.getcwd()
    
    # Buat production config file
    production_config = '''
# Production Environment Configuration
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Flask configuration
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-super-secret-key-change-this-in-production')
DEBUG = False
TESTING = False

# Database configuration
DATABASE_PATH = BASE_DIR / 'data' / 'sensor_data.db'
DATABASE_URL = f'sqlite:///{DATABASE_PATH}'

# Logging configuration
LOG_LEVEL = 'WARNING'
LOG_DIR = BASE_DIR / 'logs'
LOG_FILE = LOG_DIR / 'app.log'
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# Performance settings
CACHE_TYPE = 'simple'
CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
SENSOR_UPDATE_INTERVAL = 2.0  # seconds
DB_RECORD_INTERVAL = 300  # 5 minutes
DB_HEALTH_CHECK_INTERVAL = 600  # 10 minutes

# Security settings
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
WTF_CSRF_ENABLED = True
'''
    
    with open('config/production.py', 'w') as f:
        f.write(production_config)
    
    print("✅ Production configuration created")
    return True

def create_startup_script():
    """Buat script untuk menjalankan aplikasi"""
    print("🚀 Creating startup script...")
    
    # Windows batch script
    windows_script = '''@echo off
echo Starting Hybrid Power Monitoring System...
echo.

REM Set environment variables
set FLASK_ENV=production
set PYTHONPATH=%CD%

REM Create data directory if not exists
if not exist "data" mkdir data
if not exist "logs" mkdir logs

REM Check Python version
python --version
echo.

REM Start the application
echo Starting Flask application...
python app.py

pause
'''
    
    with open('start_production.bat', 'w') as f:
        f.write(windows_script)
    
    # Linux/Mac shell script
    linux_script = '''#!/bin/bash
echo "Starting Hybrid Power Monitoring System..."
echo ""

# Set environment variables
export FLASK_ENV=production
export PYTHONPATH=$(pwd)

# Create directories if not exist
mkdir -p data logs backups

# Check Python version
python3 --version
echo ""

# Start the application
echo "Starting Flask application..."
python3 app.py
'''
    
    with open('start_production.sh', 'w') as f:
        f.write(linux_script)
    
    # Make shell script executable
    try:
        os.chmod('start_production.sh', 0o755)
    except:
        pass  # Ignore on Windows
    
    print("✅ Startup scripts created")
    return True

def create_service_files():
    """Buat file service untuk systemd (Linux)"""
    print("🔧 Creating service files...")
    
    service_file = f'''[Unit]
Description=Hybrid Power Monitoring System
After=network.target

[Service]
Type=simple
User=monitoring
WorkingDirectory={os.getcwd()}
Environment=FLASK_ENV=production
Environment=PYTHONPATH={os.getcwd()}
ExecStart=/usr/bin/python3 app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
'''
    
    with open('config/monitoring.service', 'w') as f:
        f.write(service_file)
    
    print("✅ Service file created at config/monitoring.service")
    print("   To install: sudo cp config/monitoring.service /etc/systemd/system/")
    print("   To enable: sudo systemctl enable monitoring")
    print("   To start: sudo systemctl start monitoring")
    return True

def optimize_for_production():
    """Optimasi aplikasi untuk production"""
    print("🔧 Optimizing for production...")
    
    # Baca app.py dan lakukan optimasi
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Ganti debug mode
    content = content.replace('debug=True', 'debug=False')
    content = content.replace('use_reloader=False', 'use_reloader=False')
    
    # Optimalkan logging
    content = content.replace('level=logging.INFO', 'level=logging.WARNING')
    
    # Simpan perubahan
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Application optimized for production")
    return True

def run_deployment():
    """Jalankan proses deployment lengkap"""
    print("🚀 PRODUCTION DEPLOYMENT")
    print("=" * 50)
    
    # Check requirements
    if not check_requirements():
        print("❌ Requirements check failed")
        return False
    
    # Create production structure
    if not create_production_structure():
        print("❌ Failed to create production structure")
        return False
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        return False
    
    # Configure production
    if not configure_production():
        print("❌ Failed to configure production")
        return False
    
    # Create startup scripts
    if not create_startup_script():
        print("❌ Failed to create startup scripts")
        return False
    
    # Create service files
    if not create_service_files():
        print("❌ Failed to create service files")
        return False
    
    # Optimize for production
    if not optimize_for_production():
        print("❌ Failed to optimize for production")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!")
    print("\n📋 Next steps:")
    print("   1. Review production configuration in config/production.py")
    print("   2. Set your SECRET_KEY environment variable")
    print("   3. Run application with: python app.py")
    print("   4. Or use startup scripts: start_production.bat (Windows) or ./start_production.sh (Linux)")
    print("   5. For systemd service: Copy config/monitoring.service to /etc/systemd/system/")
    print("\n🔒 Security reminders:")
    print("   - Change SECRET_KEY in production")
    print("   - Set up proper firewall rules")
    print("   - Use HTTPS in production")
    print("   - Regular backup of database")
    print("\n💡 Production tips:")
    print("   - Monitor logs in logs/ directory")
    print("   - Use nginx as reverse proxy")
    print("   - Set up monitoring and alerting")
    print("   - Regular database backups")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--auto':
        # Auto deployment without confirmation
        run_deployment()
    else:
        # Ask for confirmation
        print("🚨 PRODUCTION DEPLOYMENT WARNING:")
        print("This will configure your application for production environment.")
        print("Make sure you have backed up your current configuration.")
        
        confirm = input("\nDo you want to proceed with deployment? (y/N): ").lower().strip()
        
        if confirm in ['y', 'yes']:
            run_deployment()
        else:
            print("❌ Deployment cancelled.")
