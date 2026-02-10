#!/usr/bin/env python3
"""
Optimasi kinerja untuk aplikasi monitoring
"""
import os
import re

def optimize_app_performance():
    """Mengoptimalkan kinerja aplikasi dengan menghapus debug code dan logging yang tidak perlu"""
    
    print("🚀 Starting performance optimization...")
    print("=" * 50)
    
    # Read app.py
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_lines = len(content.splitlines())
    
    # Optimizations to apply
    optimizations = [

        (r'print\(f?"\[INFO\].*?\n', ''),
        (r'print\(f?"\[OK\].*?\n', ''),
        (r'print\(f?"\[WARNING\].*?\n', ''),
        (r'print\(f?"\[ERROR\].*?\n', ''),
        

        (r'import traceback\s*\n', ''),
        (r'traceback\.print_exc\(\)\s*\n', ''),
        

        (r'level=logging\.INFO', 'level=logging.WARNING'),
        

        (r'app\.logger\.debug\(.*?\)\s*\n', ''),
        

        (r'app\.logger\.error\(f?"Error.*?\n', ''),
    ]
    
    changes_made = []
    
    for pattern, replacement in optimizations:
        matches = re.findall(pattern, content)
        if matches:
            content = re.sub(pattern, replacement, content)
            changes_made.append(f"Removed {len(matches)} debug/logging statements")
    

    # Reduce database health check interval for production
    content = re.sub(r'check_interval=60', 'check_interval=300', content)  # 5 minutes instead of 1
    changes_made.append("Increased database health check interval to 5 minutes")
    
    # Optimize cache settings
    content = re.sub(r'history_duration=30\.0', 'history_duration=60.0', content)
    changes_made.append("Increased history duration to 60 seconds")
    
    # Write optimized version
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    new_lines = len(content.splitlines())
    
    print("✅ Performance optimization completed!")
    print(f"   Original lines: {original_lines}")
    print(f"   New lines: {new_lines}")
    print(f"   Lines saved: {original_lines - new_lines}")
    
    if changes_made:
        print("\n📋 Changes made:")
        for change in changes_made:
            print(f"   - {change}")
    
    print("\n💡 Additional recommendations:")
    print("   - Set Flask debug=False in production")
    print("   - Use a proper WSGI server like Gunicorn")
    print("   - Consider using Redis for caching")
    print("   - Implement proper error monitoring")

def create_production_config():
    """Membuat file konfigurasi khusus untuk produksi"""
    
    production_config = '''"""
Production configuration untuk aplikasi monitoring
"""
import os

class ProductionConfig:
    """Konfigurasi untuk environment produksi"""
    
    # Flask settings
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
    
    # Database settings
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///data/sensor_data.db')
    DB_POOL_SIZE = 10
    DB_POOL_TIMEOUT = 30
    
    # Logging settings
    LOG_LEVEL = 'WARNING'
    LOG_FILE = 'app.log'
    MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    
    # Performance settings
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
    
    # Sensor settings
    SENSOR_UPDATE_INTERVAL = 2.0  # Slower for production
    SENSOR_HISTORY_DURATION = 120.0  # 2 minutes
    DB_RECORD_INTERVAL = 300  # 5 minutes
    
    # Health monitoring
    DB_HEALTH_CHECK_INTERVAL = 600  # 10 minutes
    
    # Security settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

class DevelopmentConfig:
    """Konfigurasi untuk environment development"""
    
    DEBUG = True
    TESTING = False
    LOG_LEVEL = 'DEBUG'
    SENSOR_UPDATE_INTERVAL = 1.0
    SENSOR_HISTORY_DURATION = 30.0
    DB_RECORD_INTERVAL = 60
    DB_HEALTH_CHECK_INTERVAL = 30

# Export berdasarkan environment
config = ProductionConfig() if os.environ.get('FLASK_ENV') == 'production' else DevelopmentConfig()
'''
    
    with open('production_config.py', 'w', encoding='utf-8') as f:
        f.write(production_config)
    
    print("✅ Created production_config.py")

if __name__ == "__main__":
    print("🚨 PERFORMANCE OPTIMIZATION WARNING:")
    print("This will modify your app.py file to optimize for production.")
    print("Make sure you have a backup of your current app.py file.")
    
    confirm = input("\nDo you want to proceed with optimization? (y/N): ").lower().strip()
    
    if confirm in ['y', 'yes']:
        optimize_app_performance()
        create_production_config()
    else:
        print("❌ Optimization cancelled.")
