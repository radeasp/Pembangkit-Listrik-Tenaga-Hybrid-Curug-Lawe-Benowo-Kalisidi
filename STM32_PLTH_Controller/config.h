#ifndef CONFIG_H
#define CONFIG_H
#define VD_35V_RATIO 6.992  
#define VOLTAGE_CORRECTION_SLOPE   0.988940f
#define VOLTAGE_CORRECTION_OFFSET  0.554445f
#define PICOHYDRO_CURRENT_CORRECTION_SLOPE   1.039789f
#define PICOHYDRO_CURRENT_CORRECTION_OFFSET  0.064061f
#define BATTERY_OUT_CURRENT_CORRECTION_SLOPE   0.962743f
#define BATTERY_OUT_CURRENT_CORRECTION_OFFSET  0.184946f
#define BATTERY_IN_CURRENT_CORRECTION_SLOPE   0.967366f
#define BATTERY_IN_CURRENT_CORRECTION_OFFSET  0.094310f
#include <ArduinoJson.h>
#include <Adafruit_ADS1X15.h>
#include <Wire.h>
#define PWM_PIN PA15                   
#define LED_BUILTIN PC13               
#define ADS1115_ADDRESS 0x48           
#define ADS_PICOHYDRO_VOLTAGE_CHANNEL 0    
#define ADS_PICOHYDRO_CURRENT_CHANNEL 1    
#define ADS_BATTERY_IN_CHANNEL 2           
#define ADS_BATTERY_OUT_CHANNEL 3          
#define ADS_RESOLUTION 32767.0         
#define ADS_VREF 6.144                 
#define ADS_GAIN GAIN_TWOTHIRDS        
#define PICOHYDRO_CURRENT_ZERO 2.535        
#define PICOHYDRO_CURRENT_SENSITIVITY 0.1   
#define BATTERY_IN_CURRENT_ZERO 2.564      
#define BATTERY_IN_CURRENT_SENSITIVITY 0.1  
#define BATTERY_OUT_CURRENT_ZERO 2.567     
#define BATTERY_OUT_CURRENT_SENSITIVITY 0.04  
#define CURRENT_FILTER_WINDOW_SIZE 15
#define ZERO_CURRENT_THRESHOLD 0.05         
#define CALIBRATION_SAMPLES 30              
#define STABLE_READINGS_REQUIRED 10         
extern bool usb_connected;
extern unsigned long last_data_send;
extern unsigned long last_serial_output;
extern unsigned long last_led_toggle;
extern bool led_state;
extern unsigned long led_blink_interval;
extern bool debug_mode;
extern bool serial_monitor_active;
extern Adafruit_ADS1115 ads;
extern bool ads_available;
extern unsigned long last_ads_check;
extern unsigned long ads_check_interval;
extern unsigned long last_watchdog_reset;
extern unsigned long watchdog_timeout;
extern float last_voltage_reading;
extern unsigned long last_voltage_change;
extern int stuck_reading_count;
extern bool recording_active;
extern unsigned long recording_start_time;
extern unsigned long recording_duration;
extern unsigned long last_recording_sample;
extern unsigned long recording_sample_interval;
extern String recording_type;
extern bool show_menu;
extern bool plotter_mode;
extern bool quick_view_mode;
extern bool command_mode;
extern String command_buffer;
#endif

