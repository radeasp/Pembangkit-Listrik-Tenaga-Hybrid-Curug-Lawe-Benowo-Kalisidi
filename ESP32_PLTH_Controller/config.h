#ifndef CONFIG_H
#define CONFIG_H

#include <WiFi.h>
#include <Wire.h>
#include <DHT.h>
#include <ArduinoJson.h>
#include <ADS1X15.h>

#define DHT22_PIN 13
#define DHT22_TYPE DHT22
#define HCSR04_TRIG 18
#define HCSR04_ECHO 19
#define LED_BUILTIN 2
#define I2C_SDA 21
#define I2C_SCL 22
#define ADS1115_ADDRESS 0x48
#define CURRENT_VOLTAGE_DIVIDER_RATIO (1.0 / 1.549)
#define SOLAR_CURRENT_CORRECTION_SLOPE   0.968207f
#define SOLAR_CURRENT_CORRECTION_OFFSET  -0.247602f
#define SOLAR_CURRENT_ZERO 1.638  
#define SOLAR_CURRENT_SENSITIVITY (0.1 / 1.549)

const unsigned long LED_BLINK_DURATION = 100;
const unsigned long MASTER_TIMEOUT = 5000;
const unsigned long LED_IDLE_INTERVAL = 3000;
const unsigned long LED_COMM_INTERVAL = 1000;
extern float temperature;
extern float humidity;
extern float tma_value;
extern float solar_voltage;
extern float solar_current;
extern float battery_voltage;
extern bool json_output_mode;
extern bool debug_mode;
extern bool serial_monitor_active;
extern bool plotter_mode;
extern bool quick_view_mode;
extern bool recording_active;
extern unsigned long recording_start_time;
extern unsigned long recording_duration;
extern unsigned long last_recording_sample;
extern unsigned long last_serial_output;
extern float current_zero_voltage;
extern float current_sensitivity;
extern bool current_calibrated;
extern float current_zero_threshold;
extern float current_divider_ratio;
extern bool ads1115_detected;
extern bool led_state;
extern unsigned long led_toggle_time;
extern bool data_transfer_active;
extern bool master_connected;
extern unsigned long last_data_request_time;
extern String last_json_data;
extern bool data_changed;

float interpolate(float adc_voltage, const float* cal_adc, const float* cal_voltage, int points);
#endif

