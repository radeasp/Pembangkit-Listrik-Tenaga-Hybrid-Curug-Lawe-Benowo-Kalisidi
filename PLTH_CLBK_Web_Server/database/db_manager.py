import sqlite3
import os
import json
import logging
import time
from datetime import datetime, timedelta
from threading import Lock
import threading
from collections import deque
import pickle
import tempfile

class DatabaseManager:
    """SQLite Database Manager for sensor data storage"""
    
    def __init__(self, db_path="sensor_data.db"):
        """Initialize database connection"""
        self.db_path = db_path
        self.lock = Lock()
        self.logger = logging.getLogger(__name__)
        
        # Initialize cache system
        cache_file = os.path.join(os.path.dirname(db_path), '.sensor_cache.pkl')
        self.cache = DatabaseCache(max_size=500, cache_file=cache_file)
        
        # Performance monitoring
        self.operation_stats = {
            'successful_writes': 0,
            'failed_writes': 0,
            'cache_fallbacks': 0,
            'last_success': None,
            'last_failure': None
        }
        
        # Initialize database tables if they don't exist
        self._init_db()
        
    def _init_db(self):
        """Initialize database tables if they don't exist"""
        try:
            # Check directory permissions and create if needed
            db_dir = os.path.dirname(self.db_path)
            if not os.path.exists(db_dir):
                try:
                    os.makedirs(db_dir, mode=0o755, exist_ok=True)
                    self.logger.info(f"Created database directory: {db_dir}")
                except OSError as e:
                    self.logger.error(f"Failed to create database directory {db_dir}: {e}")
                    raise
            
            # Check directory write permissions
            if not os.access(db_dir, os.W_OK):
                self.logger.error(f"No write permission for database directory: {db_dir}")
                # Try to fix permissions
                try:
                    os.chmod(db_dir, 0o755)
                    self.logger.info(f"Fixed permissions for database directory: {db_dir}")
                except OSError as e:
                    self.logger.error(f"Failed to fix directory permissions: {e}")
                    raise
            
            if os.path.exists(self.db_path):
                if not os.access(self.db_path, os.W_OK):
                    self.logger.warning(f"Database file is not writable: {self.db_path}")
                    try:
                        os.chmod(self.db_path, 0o644)
                        self.logger.info(f"Fixed permissions for database file: {self.db_path}")
                    except OSError as e:
                        self.logger.error(f"Failed to fix database file permissions: {e}")
                        raise
            
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS sensor_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    module TEXT NOT NULL,
                    data_source TEXT NOT NULL,
                    data JSON NOT NULL
                )
                ''')
                
                # Create indexes to improve query performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON sensor_readings(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_module ON sensor_readings(module)')
                
                # Create a summary table for aggregated data
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    module TEXT NOT NULL,
                    min_values JSON,
                    max_values JSON,
                    avg_values JSON,
                    samples_count INTEGER
                )
                ''')
                
                cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_date_module ON daily_summaries(date, module)')
                
                conn.commit()
                self.logger.info("Database initialized successfully")
                
        except sqlite3.Error as e:
            self.logger.error(f"Database initialization error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error during database initialization: {e}")
            
    def store_sensor_data(self, module, data, data_source='unknown'):
        """Store sensor data in the database with enhanced retry and cache fallback
        
        Args:
            module (str): The module/sensor name
            data (dict): The sensor data to store
            data_source (str): The source of data (real/dummy)
        """
        max_retries = 3
        retry_delay = 0.1  # Start with 100ms delay
        
        for attempt in range(max_retries):
            try:
                if os.path.exists(self.db_path) and not os.access(self.db_path, os.W_OK):
                    self._auto_fix_permissions()
                
                timestamp = datetime.now().isoformat()
                

                timeout = 2.0 if attempt == 0 else 1.0
                
                with self.lock, sqlite3.connect(self.db_path, timeout=timeout) as conn:
                    if attempt == 0:
                        try:
                            conn.execute("PRAGMA journal_mode=WAL")
                            conn.execute("PRAGMA synchronous=NORMAL")
                        except sqlite3.OperationalError:
                            pass
                    
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO sensor_readings (timestamp, module, data_source, data) VALUES (?, ?, ?, ?)",
                        (timestamp, module, data_source, json.dumps(data))
                    )
                    conn.commit()
                    
                    # Update stats
                    self.operation_stats['successful_writes'] += 1
                    self.operation_stats['last_success'] = timestamp
                    
                    # Try to flush cache if successful
                    if len(self.cache.cache) > 0:
                        flushed = self.cache.flush_to_database(self)
                        if flushed > 0:
                            self.logger.info(f"Flushed {flushed} cached entries to database")
                    
                    return True
                    
            except sqlite3.OperationalError as e:
                error_msg = str(e).lower()
                if "readonly database" in error_msg or "locked" in error_msg:
                    if attempt < max_retries - 1:
                        self.logger.warning(f"Database operation failed (attempt {attempt + 1}), retrying: {e}")
                        self._auto_fix_permissions()
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        self.logger.error(f"Database is read-only or locked after {max_retries} attempts, using cache fallback")
                        break
                else:
                    self.logger.error(f"SQLite operational error: {e}")
                    break
                    
            except sqlite3.Error as e:
                self.logger.error(f"SQLite error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                break
                
            except Exception as e:
                self.logger.error(f"Unexpected error storing sensor data: {e}")
                break
        
        # If database failed, use cache as fallback
        self.operation_stats['failed_writes'] += 1
        self.operation_stats['cache_fallbacks'] += 1
        self.operation_stats['last_failure'] = datetime.now().isoformat()
        
        if self.cache.add_data(module, data, data_source):
            self.logger.info(f"Data stored in cache fallback for module: {module}")
            return True
        else:
            self.logger.error(f"Both database and cache storage failed for module: {module}")
            return False
    
    def _auto_fix_permissions(self):
        """Automatically attempt to fix file permissions"""
        try:
            # Fix database file permissions
            if os.path.exists(self.db_path):
                current_mode = os.stat(self.db_path).st_mode
                if not (current_mode & 0o200):  # Check if write bit is missing
                    os.chmod(self.db_path, 0o644)
                    self.logger.info(f"Auto-fixed database file permissions: {self.db_path}")
            
            db_dir = os.path.dirname(self.db_path)
            if os.path.exists(db_dir):
                current_mode = os.stat(db_dir).st_mode
                if not (current_mode & 0o200):  # Check if write bit is missing
                    os.chmod(db_dir, 0o755)
                    self.logger.info(f"Auto-fixed directory permissions: {db_dir}")
                    
        except Exception as e:
            self.logger.debug(f"Auto-fix permissions failed: {e}")
            
    def store_all_sensors_data(self, all_data, data_source='unknown'):
        """Store data from all sensors
        
        Args:
            all_data (dict): Dictionary with module names as keys and sensor data as values
            data_source (str): The source of data (real/dummy)
        """
        success = True
        timestamp = datetime.now()
        
        excluded_keys = ['timestamp', 'data_source']
        
        for module, data in all_data.items():
            if module not in excluded_keys and isinstance(data, dict):
                if not self.store_sensor_data(module, data, data_source):
                    success = False
                    
        return success
        
    # Query cache for optimization
    _query_cache = {}
    _cache_ttl = 30  # 30 seconds cache validity
    
    def get_sensor_data(self, module=None, start_time=None, end_time=None, limit=1000):
        """Retrieve sensor data from the database
        
        Args:
            module (str, optional): Filter by module name
            start_time (str, optional): Start time in ISO format
            end_time (str, optional): End time in ISO format
            limit (int, optional): Maximum number of records to return
            
        Returns:
            list: List of sensor readings as dictionaries
        """
        # Create cache key from parameters
        cache_key = f"data_{module}_{start_time}_{end_time}_{limit}"
        current_time = time.time()
        
        # Check if we have a valid cached result
        if cache_key in self._query_cache:
            cache_entry = self._query_cache[cache_key]
            if current_time - cache_entry['timestamp'] < self._cache_ttl:
                self.logger.debug(f"Using cached result for query {cache_key}")
                return cache_entry['data']
        
        # Set a reasonable limit to prevent excessive memory usage
        if limit > 5000:
            limit = 5000
        
        query = "SELECT timestamp, module, data_source, data FROM sensor_readings"
        params = []
        conditions = []
        
        if module:
            conditions.append("LOWER(module) = LOWER(?)")
            params.append(module)
            
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time)
            
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time)
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        try:

            with self.lock, sqlite3.connect(self.db_path, timeout=5.0) as conn:
                conn.row_factory = sqlite3.Row  # Return rows as dictionaries
                cursor = conn.cursor()
                
                cursor.execute("PRAGMA temp_store = MEMORY")
                cursor.execute("PRAGMA journal_mode = WAL")
                cursor.execute("PRAGMA synchronous = NORMAL")
                
                cursor.execute(query, params)
                
                results = []
                for row in cursor.fetchall():
                    record = {
                        "timestamp": row['timestamp'],
                        "module": row['module'],
                        "data_source": row['data_source'],
                        "data": json.loads(row['data'])
                    }
                    results.append(record)
                
                # Store in cache
                self._query_cache[cache_key] = {
                    'timestamp': current_time,
                    'data': results
                }
                
                # Clean up old cache entries
                if len(self._query_cache) > 10:
                    old_keys = []
                    for k, v in self._query_cache.items():
                        if current_time - v['timestamp'] > self._cache_ttl:
                            old_keys.append(k)
                    
                    for k in old_keys:
                        del self._query_cache[k]
                
                return results
                
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving sensor data: {e}")
            return []
            
    def get_daily_summary(self, date=None, module=None):
        """Get daily summary statistics for sensor data
        
        Args:
            date (str, optional): Date in YYYY-MM-DD format
            module (str, optional): Filter by module name
            
        Returns:
            list: List of daily summaries
        """
        query = "SELECT date, module, min_values, max_values, avg_values, samples_count FROM daily_summaries"
        params = []
        conditions = []
        
        if date:
            conditions.append("date = ?")
            params.append(date)
            
        if module:
            conditions.append("LOWER(module) = LOWER(?)")
            params.append(module)
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)
                
                results = []
                for row in cursor.fetchall():
                    record = {
                        "date": row['date'],
                        "module": row['module'],
                        "min_values": json.loads(row['min_values']),
                        "max_values": json.loads(row['max_values']),
                        "avg_values": json.loads(row['avg_values']),
                        "samples_count": row['samples_count']
                    }
                    results.append(record)
                    
                return results
                
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving daily summaries: {e}")
            return []
            
    def generate_daily_summary(self, date=None):
        """Generate summary statistics for a given date
        
        Args:
            date (str, optional): Date in YYYY-MM-DD format, defaults to yesterday
            
        Returns:
            bool: Success status
        """
        if not date:
            # Default to yesterday
            date = (datetime.now().date() - timedelta(days=1)).isoformat()
            
        start_time = f"{date}T00:00:00"
        end_time = f"{date}T23:59:59"
        
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get all modules that have data for this date
                cursor.execute(
                    "SELECT DISTINCT module FROM sensor_readings WHERE timestamp BETWEEN ? AND ?",
                    (start_time, end_time)
                )
                
                modules = [row['module'] for row in cursor.fetchall()]
                
                for module in modules:
                    # Get all readings for this module and date
                    cursor.execute(
                        "SELECT data FROM sensor_readings WHERE module = ? AND timestamp BETWEEN ? AND ?",
                        (module, start_time, end_time)
                    )
                    
                    readings = [json.loads(row['data']) for row in cursor.fetchall()]
                    
                    if not readings:
                        continue
                        
                    # Combine all readings keys
                    all_keys = set()
                    for reading in readings:
                        all_keys.update(reading.keys())
                        
                    # Calculate min, max, avg for numeric values
                    min_values = {}
                    max_values = {}
                    sum_values = {}
                    count_values = {}
                    
                    for reading in readings:
                        for key in all_keys:
                            if key in reading and isinstance(reading[key], (int, float)):
                                value = reading[key]
                                
                                if key not in min_values or value < min_values[key]:
                                    min_values[key] = value
                                    
                                if key not in max_values or value > max_values[key]:
                                    max_values[key] = value
                                    
                                sum_values[key] = sum_values.get(key, 0) + value
                                count_values[key] = count_values.get(key, 0) + 1
                                
                    # Calculate averages
                    avg_values = {
                        key: sum_values[key] / count_values[key]
                        for key in sum_values
                    }
                    
                    # Store summary in database
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO daily_summaries 
                        (date, module, min_values, max_values, avg_values, samples_count)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            date, 
                            module, 
                            json.dumps(min_values),
                            json.dumps(max_values),
                            json.dumps(avg_values),
                            len(readings)
                        )
                    )
                    
                conn.commit()
                return True
                
        except sqlite3.Error as e:
            self.logger.error(f"Error generating daily summary: {e}")
            return False
            
    def cleanup_old_data(self, days_to_keep=30):
        """Remove data older than the specified number of days
        
        Args:
            days_to_keep (int): Number of days of data to retain
            
        Returns:
            int: Number of records deleted
        """
        cutoff_date = (datetime.now().date() - timedelta(days=days_to_keep)).isoformat()
        cutoff_time = f"{cutoff_date}T00:00:00"
        
        try:
            with self.lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM sensor_readings WHERE timestamp < ?",
                    (cutoff_time,)
                )
                deleted_count = cursor.rowcount
                conn.commit()
                
                self.logger.info(f"Cleaned up {deleted_count} old sensor readings")
                return deleted_count
                
        except sqlite3.Error as e:
            self.logger.error(f"Error cleaning up old data: {e}")
            return 0

    def get_performance_stats(self):
        """Get database performance statistics"""
        cache_stats = self.cache.get_stats()
        
        return {
            'database_stats': self.operation_stats,
            'cache_stats': cache_stats,
            'health_status': self._get_health_status()
        }
    
    def _get_health_status(self):
        """Determine database health status"""
        recent_failures = self.operation_stats['failed_writes']
        recent_successes = self.operation_stats['successful_writes']
        cache_fallbacks = self.operation_stats['cache_fallbacks']
        
        if recent_successes > 0 and recent_failures == 0:
            return 'healthy'
        elif cache_fallbacks > 0 and recent_failures > recent_successes:
            return 'degraded'
        elif recent_failures > 0:
            return 'warning'
        else:
            return 'unknown'
    
    def force_cache_flush(self):
        """Manually force flush cache to database"""
        if self.cache:
            return self.cache.flush_to_database(self)
        return 0

class DatabaseCache:
    """In-memory cache and fallback storage for database operations"""
    
    def __init__(self, max_size=1000, cache_file=None):
        self.max_size = max_size
        self.cache = deque(maxlen=max_size)
        self.cache_lock = threading.Lock()
        self.cache_file = cache_file or os.path.join(tempfile.gettempdir(), 'sensor_cache.pkl')
        self.stats = {
            'hits': 0,
            'misses': 0,
            'fallback_writes': 0,
            'cache_flushes': 0
        }
        
        # Load existing cache if available
        self._load_cache()
    
    def add_data(self, module, data, data_source='unknown'):
        """Add sensor data to cache"""
        try:
            with self.cache_lock:
                entry = {
                    'timestamp': datetime.now().isoformat(),
                    'module': module,
                    'data_source': data_source,
                    'data': data
                }
                self.cache.append(entry)
                
                # Periodically save cache to disk
                if len(self.cache) % 50 == 0:  # Save every 50 entries
                    self._save_cache()
                    
            return True
        except Exception as e:
            logging.getLogger(__name__).error(f"Cache add failed: {e}")
            return False
    
    def get_recent_data(self, module=None, limit=100):
        """Get recent data from cache"""
        try:
            with self.cache_lock:
                if module:
                    filtered_data = [entry for entry in self.cache if entry['module'] == module]
                else:
                    filtered_data = list(self.cache)
                
                self.stats['hits'] += 1
                return filtered_data[-limit:] if limit else filtered_data
        except Exception as e:
            logging.getLogger(__name__).error(f"Cache read failed: {e}")
            self.stats['misses'] += 1
            return []
    
    def flush_to_database(self, db_manager):
        """Flush cached data to database when it becomes available"""
        if not db_manager:
            return 0
        
        flushed_count = 0
        try:
            with self.cache_lock:
                cache_copy = list(self.cache)
                
            for entry in cache_copy:
                if db_manager.store_sensor_data(
                    entry['module'], 
                    entry['data'], 
                    entry['data_source']
                ):
                    flushed_count += 1
                else:
                    break  # Stop if database fails
            
            if flushed_count > 0:
                with self.cache_lock:

                    for _ in range(min(flushed_count, len(self.cache))):
                        if self.cache:
                            self.cache.popleft()
                
                self.stats['cache_flushes'] += 1
                logging.getLogger(__name__).info(f"Flushed {flushed_count} entries from cache to database")
                
        except Exception as e:
            logging.getLogger(__name__).error(f"Cache flush failed: {e}")
        
        return flushed_count
    
    def _save_cache(self):
        """Save cache to disk"""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(list(self.cache), f)
        except Exception as e:
            logging.getLogger(__name__).debug(f"Cache save failed: {e}")
    
    def _load_cache(self):
        """Load cache from disk"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                    with self.cache_lock:
                        self.cache.extend(cached_data[-self.max_size:])
                logging.getLogger(__name__).info(f"Loaded {len(self.cache)} entries from cache file")
        except Exception as e:
            logging.getLogger(__name__).debug(f"Cache load failed: {e}")
    
    def get_stats(self):
        """Get cache statistics"""
        return {
            **self.stats,
            'cache_size': len(self.cache),
            'cache_max_size': self.max_size
        }
