import threading
import time
import logging
from datetime import datetime, timedelta

class DataRecorder:
    """
    A class to record sensor data to the database at regular intervals.
    """
    
    def __init__(self, db_manager, data_config, record_interval=60, cleanup_interval=86400):
        """Initialize data recorder
        
        Args:
            db_manager: Database manager instance
            data_config: Data source configuration
            record_interval (int): Recording interval in seconds (default: 60s)
            cleanup_interval (int): Database cleanup interval in seconds (default: 24h)
        """
        self.db_manager = db_manager
        self.data_config = data_config
        self.record_interval = record_interval
        self.cleanup_interval = cleanup_interval
        self.logger = logging.getLogger(__name__)
        
        self.recording = False
        self.recording_thread = None
        self.last_cleanup = datetime.now()
        self.days_to_keep = 30  # Default: keep 30 days of data
        
    def start_recording(self):
        """Start recording data at regular intervals"""
        if self.recording:
            return False
            
        self.recording = True
        self.recording_thread = threading.Thread(target=self._record_loop, daemon=True)
        self.recording_thread.start()
        self.logger.info(f"Data recording started with interval: {self.record_interval}s")
        return True
        
    def stop_recording(self):
        """Stop recording data"""
        if not self.recording:
            return False
            
        self.recording = False
        if self.recording_thread:
            self.recording_thread.join(timeout=2.0)
            self.recording_thread = None
            
        self.logger.info("Data recording stopped")
        return True
        
    def set_recording_interval(self, interval):
        """Change the recording interval
        
        Args:
            interval (int): New interval in seconds (must be ≥ 1)
            
        Returns:
            bool: Success status
        """
        if interval < 1:
            return False
            
        self.record_interval = interval
        self.logger.info(f"Recording interval changed to {interval}s")
        return True
        
    def set_data_retention(self, days):
        """Set how many days of data to keep
        
        Args:
            days (int): Number of days to keep data for
            
        Returns:
            bool: Success status
        """
        if days < 1:
            return False
            
        self.days_to_keep = days
        self.logger.info(f"Data retention set to {days} days")
        return True
        
    def _record_loop(self):
        """Background thread for recording data"""
        while self.recording:
            try:
                # Get current sensor data
                sensor = self.data_config.get_current_sensor_source()
                all_data = sensor.get_sensor_data()
                
                # Store in database
                self.db_manager.store_all_sensors_data(
                    all_data, 
                    data_source=self.data_config.current_mode
                )
                

                now = datetime.now()
                if (now - self.last_cleanup).total_seconds() >= self.cleanup_interval:
                    self.db_manager.cleanup_old_data(days_to_keep=self.days_to_keep)
                    self.db_manager.generate_daily_summary()
                    self.last_cleanup = now
                    
            except Exception as e:
                self.logger.error(f"Error in data recording: {e}")
                
            # Sleep until next recording
            time.sleep(self.record_interval)
            
    def generate_summary(self, date=None):
        """Generate summary for a specific date
        
        Args:
            date (str, optional): Date in YYYY-MM-DD format
            
        Returns:
            bool: Success status
        """
        return self.db_manager.generate_daily_summary(date)
        
    def get_status(self):
        """Get current status of the data recorder
        
        Returns:
            dict: Status information
        """
        try:
            last_cleanup_iso = self.last_cleanup.isoformat() if self.last_cleanup else None
            next_cleanup_iso = (self.last_cleanup + timedelta(seconds=self.cleanup_interval)).isoformat() if self.last_cleanup else None
            
            return {
                'recording': self.recording,
                'record_interval': self.record_interval,
                'days_to_keep': self.days_to_keep,
                'last_cleanup': last_cleanup_iso,
                'next_cleanup': next_cleanup_iso
            }
        except Exception as e:
            self.logger.error(f"Error getting recorder status: {e}")
            return {
                'recording': False,
                'record_interval': 60,
                'days_to_keep': 30,
                'last_cleanup': None,
                'next_cleanup': None,
                'error': str(e)
            }
