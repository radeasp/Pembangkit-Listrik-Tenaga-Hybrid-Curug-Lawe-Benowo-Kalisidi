#include "sensors.h"
float temperature = 0;
float humidity = 0;
float tma_value = 0;  
float solar_voltage = 0;   
float solar_current = 0;   
float battery_voltage = 0; 
bool ads1115_detected = false;  
const float battery_cal_voltage[] = {0, 1.01, 2.02, 3.01, 4, 5, 6, 7.027, 8, 9.012, 10, 11.01, 12.03, 13, 14, 15.014, 16.09, 17.017, 18, 19, 20, 21, 22, 23, 24.01, 25.07};
const float battery_cal_adc[] = {3.299, 3.299, 3.28, 3.231, 3.166, 3.073, 2.96, 2.83, 2.687, 2.529, 2.357, 2.176, 1.981, 1.788, 1.577, 1.363, 1.144, 0.919, 0.694, 0.467, 0.265, 0.211, 0.191, 0.18, 0.173, 0.166};
const int battery_cal_points = 26;
const float solar_cal_voltage[] = {0, 1, 2.01, 3.01, 4.01, 5.01, 6.01, 7.05, 8.051, 9.01, 10, 11.03, 12, 13.02, 14, 15.01, 16.01, 17.03, 18.02, 19.02, 21.01, 22.02, 23, 24.02, 25.05, 26.01, 27.01, 28.03, 29.04, 30.02, 31.02, 32.03, 33.03, 34.01, 35.01, 36.04, 37.05, 38.01, 39.01, 40, 41.057, 42.03, 43, 44.02, 45, 46.034, 47.019, 48.06, 49.047, 50.011};
const float solar_cal_adc[] = {3.277, 3.27, 3.269, 3.261, 3.248, 3.229, 3.207, 3.176, 3.148, 3.118, 3.063, 3.024, 2.976, 2.933, 2.878, 2.817, 2.761, 2.693, 2.626, 2.559, 2.483, 2.379, 2.341, 2.262, 2.162, 2.058, 2.014, 1.93, 1.881, 1.801, 1.663, 1.573, 1.479, 1.386, 1.291, 1.195, 1.094, 1.036, 0.901, 0.805, 0.707, 0.601, 0.502, 0.409, 0.316, 0.254, 0.225, 0.21, 0.191, 0.183};
const int solar_cal_points = 50;

DHT dht(DHT22_PIN, DHT22_TYPE);
ADS1115 ads(0x48);  
float interpolate(float adc_voltage, const float* cal_adc, const float* cal_voltage, int points) {
  if (adc_voltage >= cal_adc[0]) {
    return cal_voltage[0];  
  }
  if (adc_voltage <= cal_adc[points-1]) {
    return cal_voltage[points-1];  
  }
  for (int i = 0; i < points-1; i++) {
    if (adc_voltage <= cal_adc[i] && adc_voltage >= cal_adc[i+1]) {
      float adc_diff = cal_adc[i] - cal_adc[i+1];
      float volt_diff = cal_voltage[i+1] - cal_voltage[i];
      float ratio = (cal_adc[i] - adc_voltage) / adc_diff;
      return cal_voltage[i] + (ratio * volt_diff);
    }
  }
  return 0.0;  
}

void initializeSensors() {
  if (debug_mode) {
    scanI2CDevices();
  }
  dht.begin();
  if (debug_mode) Serial.println("DHT22 sensor initialized");
  if (ads.begin()) {
    Wire.beginTransmission(0x48);
    if (Wire.endTransmission() == 0) {
      ads1115_detected = true;
      ads.setGain(1);  
      if (debug_mode) Serial.println("ADS1115 ADC initialized at address 0x48");
    } else {
      if (debug_mode) Serial.println("Warning: ADS1115 address 0x48 not responding");
    }
  } else {
    if (debug_mode) Serial.println("Warning: ADS1115 initialization failed");
  }
}

void scanI2CDevices() {
  byte error, address;
  int nDevices;
  Serial.println("Scanning I2C devices...");
  nDevices = 0;
  for(address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    error = Wire.endTransmission();
    if (error == 0) {
      Serial.print("I2C device found at address 0x");
      if (address < 16) Serial.print("0");
      Serial.print(address, HEX);
      if (address == 0x48) {
        Serial.print(" (ADS1115 ADC - ID: 0x48)");
        ads1115_detected = true;
      }
      Serial.println();
      nDevices++;
    }
  }
  if (nDevices == 0) {
    Serial.println("No I2C devices found");
  } else {
    Serial.println("I2C scan complete");
    if (ads1115_detected) {
      Serial.println("ADS1115 at address 0x48 confirmed");
    }
  }
}

void readAllSensors() {
  
  readDHT22();           
  readHCSR04();          
  readSolarPanel();      
  readBatteryVoltage();  
  if (debug_mode) {
    Serial.println("All sensors read at " + String(millis()/1000) + "s");
  }
}

void readDHT22() {
  
  float temp = dht.readTemperature();
  float hum = dht.readHumidity();
  if (!isnan(temp) && !isnan(hum)) {
    temperature = temp;
    humidity = hum;
  } else {
    if (debug_mode) Serial.println("DHT22 reading error - keeping previous values");
  }
}

void readHCSR04() {
  
  digitalWrite(HCSR04_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(HCSR04_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(HCSR04_TRIG, LOW);
  unsigned long duration = pulseIn(HCSR04_ECHO, HIGH, 30000); 
  if (duration > 0) {
    float distance = duration * 0.034 / 2;
    float water_level = 80 - distance;
    tma_value = max(0.0f, water_level);  
  } else {
    if (debug_mode) Serial.println("HC-SR04 timeout - keeping previous value");
  }
}

void readSolarPanel() {
  
  if (ads1115_detected) {
    int16_t voltage_raw = ads.readADC(0);
    float voltage_ads = (voltage_raw * 4.096) / 32768.0;
    solar_voltage = interpolate(voltage_ads, solar_cal_adc, solar_cal_voltage, solar_cal_points);
    int16_t current_raw = ads.readADC(1);
    float current_voltage = (current_raw * 4.096) / 32768.0;
    float voltage_difference = current_voltage - SOLAR_CURRENT_ZERO;
    float raw_current_ampere = voltage_difference / SOLAR_CURRENT_SENSITIVITY;
    float corrected_current = SOLAR_CURRENT_CORRECTION_SLOPE * raw_current_ampere + SOLAR_CURRENT_CORRECTION_OFFSET;
    if (abs(corrected_current) < current_zero_threshold) {
      corrected_current = 0.0;
    }
    if (corrected_current < 0) {
      corrected_current = 0.0;
    }
    solar_current = corrected_current;
    if (debug_mode) {
      Serial.print("Solar Debug - ADC: "); Serial.print(voltage_ads, 3);
      Serial.print("V, Voltage: "); Serial.print(solar_voltage, 2);
      Serial.print("V, Current Raw: "); Serial.print(raw_current_ampere, 3);
      Serial.print("A, Current Corrected: "); Serial.print(solar_current, 3);
      Serial.println("A");
    }
  } else {
    solar_voltage = 0;
    solar_current = 0;
    if (debug_mode) Serial.println("ADS1115 not detected - solar panel readings set to 0");
  }
}

void readBatteryVoltage() {
  
  if (ads1115_detected) {
    int16_t voltage_raw = ads.readADC(3);
    float voltage_ads = (voltage_raw * 4.096) / 32768.0;
    battery_voltage = interpolate(voltage_ads, battery_cal_adc, battery_cal_voltage, battery_cal_points);
    if (debug_mode) {
      Serial.print("🔋 Battery Debug - ADC: "); Serial.print(voltage_ads, 3);
      Serial.print("V, Voltage: "); Serial.print(battery_voltage, 2);
      Serial.println("V");
    }
  } else {
    battery_voltage = 0;
    if (debug_mode) Serial.println("ADS1115 not detected - battery voltage set to 0");
  }
}

