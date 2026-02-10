#include "sensors.h"
Adafruit_ADS1115 ads;

bool ads_available = false;  
unsigned long last_ads_check = 0;
unsigned long ads_check_interval = 5000;  
float last_voltage_reading = -999.0;  
unsigned long last_voltage_change = 0;

int stuck_reading_count = 0;
CurrentMovingAverageFilter picohydroCurrentFilter;
CurrentMovingAverageFilter batteryInCurrentFilter;
CurrentMovingAverageFilter batteryOutCurrentFilter;
CurrentMovingAverageFilter::CurrentMovingAverageFilter() {
  readIndex = 0;
  sum = 0.0;
  bufferFilled = false;
  zeroOffset = 0.0;
  autoCalibrationEnabled = true;
  calibrationSum = 0.0;
  calibrationCount = 0;
  stableReadingsCount = 0;
  lastReading = 0.0;
  isCalibrating = false;
  lastCalibrationTime = 0;
  for (int i = 0; i < CURRENT_FILTER_WINDOW_SIZE; i++) {
    readings[i] = 0.0;
  }
}

float CurrentMovingAverageFilter::addReading(float newReading) {
  if (autoCalibrationEnabled) {
    performAutoCalibration(newReading);
  }
  float correctedReading = newReading - zeroOffset;
  sum -= readings[readIndex];
  readings[readIndex] = correctedReading;
  sum += correctedReading;
  readIndex = (readIndex + 1) % CURRENT_FILTER_WINDOW_SIZE;
  if (readIndex == 0 && !bufferFilled) {
    bufferFilled = true;
  }
  int divisor = bufferFilled ? CURRENT_FILTER_WINDOW_SIZE : readIndex + 1;
  return sum / divisor;
}

float CurrentMovingAverageFilter::getCurrentAverage() {
  int divisor = bufferFilled ? CURRENT_FILTER_WINDOW_SIZE : readIndex;
  return (divisor > 0) ? sum / divisor : 0.0;
}

void CurrentMovingAverageFilter::reset() {
  readIndex = 0;
  sum = 0.0;
  bufferFilled = false;
  calibrationSum = 0.0;
  calibrationCount = 0;
  stableReadingsCount = 0;
  isCalibrating = false;
  for (int i = 0; i < CURRENT_FILTER_WINDOW_SIZE; i++) {
    readings[i] = 0.0;
  }
}

void CurrentMovingAverageFilter::performAutoCalibration(float rawReading) {
  if (abs(rawReading - lastReading) < 0.01) { 
    if (abs(rawReading) < ZERO_CURRENT_THRESHOLD) { 
      stableReadingsCount++;
      if (stableReadingsCount >= STABLE_READINGS_REQUIRED && !isCalibrating) {
        startCalibration();
      }
      if (isCalibrating) {
        calibrationSum += rawReading;
        calibrationCount++;
        if (calibrationCount >= CALIBRATION_SAMPLES) {
          completeCalibration();
        }
      }
    } else {
      resetCalibration();
    }
  } else {
    resetCalibration();
  }
  lastReading = rawReading;
}

void CurrentMovingAverageFilter::startCalibration() {
  isCalibrating = true;
  calibrationSum = 0.0;
  calibrationCount = 0;
  lastCalibrationTime = millis();
}

void CurrentMovingAverageFilter::completeCalibration() {
  if (calibrationCount > 0) {
    float newZeroOffset = calibrationSum / calibrationCount;
    zeroOffset = newZeroOffset;
    lastCalibrationTime = millis();
  }
  resetCalibration();
}

void CurrentMovingAverageFilter::resetCalibration() {
  isCalibrating = false;
  stableReadingsCount = 0;
  calibrationSum = 0.0;
  calibrationCount = 0;
}

void CurrentMovingAverageFilter::enableAutoCalibration() {
  autoCalibrationEnabled = true;
}

void CurrentMovingAverageFilter::disableAutoCalibration() {
  autoCalibrationEnabled = false;
}

bool CurrentMovingAverageFilter::isAutoCalibrationEnabled() {
  return autoCalibrationEnabled;
}

float CurrentMovingAverageFilter::getZeroOffset() {
  return zeroOffset;
}

void CurrentMovingAverageFilter::setZeroOffset(float offset) {
  zeroOffset = offset;
}

bool CurrentMovingAverageFilter::isCurrentlyCalibrating() {
  return isCalibrating;
}
unsigned long CurrentMovingAverageFilter::getLastCalibrationTime() {
  return lastCalibrationTime;
}

void CurrentMovingAverageFilter::triggerManualCalibration() {
  resetCalibration();
  startCalibration();
}

void initializeADS1115() {
  Serial.println("Initializing ADS1115 (MANDATORY)...");
  initializeCurrentFilters();
  Wire.beginTransmission(ADS1115_ADDRESS);
  byte error = Wire.endTransmission();
  if (error == 0) {
    Serial.println("I2C device found at 0x48");
  } else {
    Serial.print("I2C error code: ");
    Serial.println(error);
  }
  if (ads.begin(ADS1115_ADDRESS)) {
    ads.setGain(ADS_GAIN);  
    ads_available = true;
    Serial.println("ADS1115 initialized successfully");
    Serial.println("Current filters initialized with auto-calibration enabled");
  } else {
    Serial.println("ERROR: ADS1115 initialization failed!");
    ads_available = false;
  }
  last_ads_check = millis();
}

bool checkADS1115Connection() {
  Wire.setTimeout(100); 
  Wire.beginTransmission(ADS1115_ADDRESS);
  byte error = Wire.endTransmission();
  Wire.setTimeout(1000);
  return (error == 0);
}

void recoverADS1115() {
  unsigned long current_time = millis();
  if (current_time - last_ads_check >= ads_check_interval) {
    if (!ads_available) {
      Serial.println("Attempting ADS1115 recovery...");
      Wire.begin();
      delay(100);
      if (checkADS1115Connection()) {
        if (ads.begin(ADS1115_ADDRESS)) {
          ads.setGain(ADS_GAIN);
          ads_available = true;
          Serial.println("ADS1115 recovery successful!");
        } else {
          Serial.println("ADS1115 recovery failed - begin() failed");
        }
      } else {
        Serial.println("ADS1115 recovery failed - I2C communication failed");
      }
    } else {
      static int verification_skip_count = 0;
      verification_skip_count++;
      if (verification_skip_count >= 5) {
        if (!checkADS1115Connection()) {
          Serial.println("ADS1115 connection lost! Marking as unavailable.");
          ads_available = false;
        }
        verification_skip_count = 0;
      }
    }
    last_ads_check = current_time;
  }
}

SensorData readSensors() {
  SensorData data;
  recoverADS1115();
  if (ads_available) {
    data.picohydro_voltage = readADSVoltageWithCorrection(ADS_PICOHYDRO_VOLTAGE_CHANNEL, VD_35V_RATIO);
    data.picohydro_current = readADSCorrectedCurrentWithFilter(ADS_PICOHYDRO_CURRENT_CHANNEL, PICOHYDRO_CURRENT_ZERO, PICOHYDRO_CURRENT_SENSITIVITY, picohydroCurrentFilter);
    data.battery_in_current = readADSCorrectedCurrentWithFilter(ADS_BATTERY_IN_CHANNEL, BATTERY_IN_CURRENT_ZERO, BATTERY_IN_CURRENT_SENSITIVITY, batteryInCurrentFilter);
    data.battery_out_current = readADSCorrectedCurrentWithFilter(ADS_BATTERY_OUT_CHANNEL, BATTERY_OUT_CURRENT_ZERO, BATTERY_OUT_CURRENT_SENSITIVITY, batteryOutCurrentFilter);
    static unsigned long last_info_print = 0;
    unsigned long current_time = millis();
    if (current_time - last_info_print >= 10000) {
      if (data.picohydro_voltage == 0.0 && data.picohydro_current == 0.0 && 
          data.battery_in_current == 0.0 && data.battery_out_current == 0.0) {
        Serial.println("INFO: All sensor readings are 0 - sensors may not be connected");
        Serial.println("INFO: This is normal if probes/sensors are not yet installed");
      }
      last_info_print = current_time;
    }
  } else {
    data.picohydro_voltage = 0.0;
    data.picohydro_current = 0.0;
    data.battery_in_current = 0.0;
    data.battery_out_current = 0.0;
    static unsigned long last_ads_warning = 0;
    unsigned long current_time = millis();
    if (current_time - last_ads_warning >= 15000) {
      Serial.println("WARNING: ADS1115 not available - check I2C connections");
      Serial.println("WARNING: All sensor readings forced to 0");
      last_ads_warning = current_time;
    }
  }
  return data;
}

float readADSVoltage(int channel, float divider_ratio) {
  if (!ads_available) return 0.0;
  Wire.setTimeout(50); 
  Wire.beginTransmission(ADS1115_ADDRESS);
  if (Wire.endTransmission() != 0) {
    Wire.setTimeout(1000); 
    static int i2c_fail_count = 0;
    i2c_fail_count++;
    if (i2c_fail_count >= 5) { 
      ads_available = false;
      Serial.println("ERROR: ADS1115 I2C communication failed repeatedly");
      i2c_fail_count = 0;
    }
    return 0.0;
  }
  unsigned long start_time = millis();
  int16_t adc_value = ads.readADC_SingleEnded(channel);
  unsigned long read_time = millis() - start_time;
  Wire.setTimeout(1000);
  if (read_time > 500) { 
    Serial.print("CRITICAL: ADC read hang detected: ");
    Serial.print(read_time);
    Serial.println("ms - possible system crash");
    ads_available = false; 
    return 0.0;
  }
  if (adc_value == -32768 || adc_value == 32767) {
    static int invalid_reading_count = 0;
    invalid_reading_count++;
    if (invalid_reading_count >= 10) { 
      Serial.println("WARNING: Persistent invalid ADC readings - possible ADS issue");
      ads_available = false;
      invalid_reading_count = 0;
    }
    return 0.0; 
  }
  float voltage = ((float)adc_value * ADS_VREF) / 32768.0;
  float result = voltage * divider_ratio;
  if (isnan(result) || isinf(result)) {
    Serial.println("ERROR: NaN/Inf voltage calculation - ADS communication problem");
    ads_available = false; 
    return 0.0;
  }
  if (result < 0.0 || result > 50.0) {
    return 0.0; 
  }
  return result;
}

float readADSVoltageWithCorrection(int channel, float divider_ratio) {
  if (!ads_available) return 0.0;
  float raw_voltage = readADSVoltage(channel, divider_ratio);
  float corrected_voltage = VOLTAGE_CORRECTION_SLOPE * raw_voltage + VOLTAGE_CORRECTION_OFFSET;
  if (corrected_voltage < 0.0 || corrected_voltage > 50.0 || isnan(corrected_voltage) || isinf(corrected_voltage)) {
    Serial.print("ERROR: Corrected voltage out of range: ");
    Serial.print(corrected_voltage);
    Serial.print("V (raw: ");
    Serial.print(raw_voltage);
    Serial.println("V)");
    return 0.0;
  }
  return corrected_voltage;
}

float readADSCalibratedCurrent(int channel, float zero_voltage, float sensitivity) {
  if (!ads_available) return 0.0;
  Wire.setTimeout(50); 
  Wire.beginTransmission(ADS1115_ADDRESS);
  if (Wire.endTransmission() != 0) {
    Wire.setTimeout(1000); 
    static int i2c_fail_count = 0;
    i2c_fail_count++;
    if (i2c_fail_count >= 5) {
      ads_available = false;
      Serial.println("ERROR: ADS1115 I2C communication failed repeatedly during current read");
      i2c_fail_count = 0;
    }
    return 0.0;
  }
  unsigned long start_time = millis();
  int16_t adc_value = ads.readADC_SingleEnded(channel);
  unsigned long read_time = millis() - start_time;
  Wire.setTimeout(1000);
  if (read_time > 500) {
    Serial.print("CRITICAL: ADC current read hang detected: ");
    Serial.print(read_time);
    Serial.println("ms - possible system crash");
    ads_available = false;
    return 0.0;
  }
  if (adc_value == -32768 || adc_value == 32767) {
    static int invalid_reading_count = 0;
    invalid_reading_count++;
    if (invalid_reading_count >= 10) {
      Serial.println("WARNING: Persistent invalid ADC readings during current measurement");
      ads_available = false;
      invalid_reading_count = 0;
    }
    return 0.0;
  }
  float voltage = ((float)adc_value * ADS_VREF) / 32768.0;
  float current = (voltage - zero_voltage) / sensitivity;
  if (isnan(current) || isinf(current)) {
    Serial.println("ERROR: NaN/Inf current calculation - ADS communication problem");
    ads_available = false; 
    return 0.0;
  }
  if (current < -100.0 || current > 100.0) {
    return 0.0; 
  }
  return current;
}

float readADSCalibratedCurrentWithFilter(int channel, float zero_voltage, float sensitivity, CurrentMovingAverageFilter& filter) {
  if (!ads_available) return 0.0;
  Wire.setTimeout(50); 
  Wire.beginTransmission(ADS1115_ADDRESS);
  if (Wire.endTransmission() != 0) {
    Wire.setTimeout(1000); 
    static int i2c_fail_count = 0;
    i2c_fail_count++;
    if (i2c_fail_count >= 5) {
      ads_available = false;
      Serial.println("ERROR: ADS1115 I2C communication failed repeatedly during filtered current read");
      i2c_fail_count = 0;
    }
    return 0.0;
  }
  unsigned long start_time = millis();
  int16_t adc_value = ads.readADC_SingleEnded(channel);
  unsigned long read_time = millis() - start_time;
  Wire.setTimeout(1000);
  if (read_time > 500) {
    Serial.print("CRITICAL: ADC filtered current read hang detected: ");
    Serial.print(read_time);
    Serial.println("ms - possible system crash");
    ads_available = false;
    return 0.0;
  }
  if (adc_value == -32768 || adc_value == 32767) {
    static int invalid_reading_count = 0;
    invalid_reading_count++;
    if (invalid_reading_count >= 10) {
      Serial.println("WARNING: Persistent invalid ADC readings during filtered current measurement");
      ads_available = false;
      invalid_reading_count = 0;
    }
    return 0.0;
  }
  float voltage = ((float)adc_value * ADS_VREF) / 32768.0;
  float current = (voltage - zero_voltage) / sensitivity;
  if (isnan(current) || isinf(current)) {
    Serial.println("ERROR: NaN/Inf filtered current calculation - ADS communication problem");
    ads_available = false; 
    return 0.0;
  }
  if (current < -100.0 || current > 100.0) {
    return 0.0; 
  }
  float filtered_current = filter.addReading(current);
  return filtered_current;
}

float readADSCorrectedCurrentWithFilter(int channel, float zero_voltage, float sensitivity, CurrentMovingAverageFilter& filter) {
  if (!ads_available) return 0.0;
  float raw_current = readADSCalibratedCurrentWithFilter(channel, zero_voltage, sensitivity, filter);
  if (channel == ADS_PICOHYDRO_CURRENT_CHANNEL) {
    float corrected_current = PICOHYDRO_CURRENT_CORRECTION_SLOPE * raw_current + PICOHYDRO_CURRENT_CORRECTION_OFFSET;
    if (isnan(corrected_current) || isinf(corrected_current)) {
      Serial.print("ERROR: Corrected picohydro current calculation error: ");
      Serial.print(corrected_current);
      Serial.print("A (raw: ");
      Serial.print(raw_current);
      Serial.println("A)");
      return 0.0;
    }
    if (corrected_current < -25.0 || corrected_current > 25.0) {
      return 0.0;
    }
    return corrected_current;
  } else if (channel == ADS_BATTERY_OUT_CHANNEL) {
    float corrected_current = BATTERY_OUT_CURRENT_CORRECTION_SLOPE * raw_current + BATTERY_OUT_CURRENT_CORRECTION_OFFSET;
    if (isnan(corrected_current) || isinf(corrected_current)) {
      Serial.print("ERROR: Corrected battery out current calculation error: ");
      Serial.print(corrected_current);
      Serial.print("A (raw: ");
      Serial.print(raw_current);
      Serial.println("A)");
      return 0.0;
    }
    if (corrected_current < -60.0 || corrected_current > 60.0) {
      return 0.0;
    }
    return corrected_current;
  } else if (channel == ADS_BATTERY_IN_CHANNEL) {
    float corrected_current = BATTERY_IN_CURRENT_CORRECTION_SLOPE * raw_current + BATTERY_IN_CURRENT_CORRECTION_OFFSET;
    if (isnan(corrected_current) || isinf(corrected_current)) {
      Serial.print("ERROR: Corrected battery in current calculation error: ");
      Serial.print(corrected_current);
      Serial.print("A (raw: ");
      Serial.print(raw_current);
      Serial.println("A)");
      return 0.0;
    }
    if (corrected_current < -25.0 || corrected_current > 25.0) {
      return 0.0;
    }
    return corrected_current;
  } else {
    return raw_current;
  }
}

void initializeCurrentFilters() {
  Serial.println("Initializing current moving average filters...");
  picohydroCurrentFilter.reset();
  batteryInCurrentFilter.reset();
  batteryOutCurrentFilter.reset();
  picohydroCurrentFilter.enableAutoCalibration();
  batteryInCurrentFilter.enableAutoCalibration();
  batteryOutCurrentFilter.enableAutoCalibration();
  Serial.print("Filter window size: ");
  Serial.println(CURRENT_FILTER_WINDOW_SIZE);
  Serial.println("Auto-calibration enabled for all current sensors");
}

void resetCurrentFilters() {
  picohydroCurrentFilter.reset();
  batteryInCurrentFilter.reset();
  batteryOutCurrentFilter.reset();
  Serial.println("All current filters reset");
}

float getFilteredPicohydroCurrent() {
  return picohydroCurrentFilter.getCurrentAverage();
}

float getFilteredBatteryInCurrent() {
  return batteryInCurrentFilter.getCurrentAverage();
}

float getFilteredBatteryOutCurrent() {
  return batteryOutCurrentFilter.getCurrentAverage();
}

int16_t getRawADCValue(int channel) {
  if (!ads_available) return -32768;
  return ads.readADC_SingleEnded(channel);
}

void printRawADCValues() {
  if (!ads_available) {
    Serial.println("ADS1115 not available - cannot read raw values");
    return;
  }
  Serial.println("\n=== RAW ADC DEBUG VALUES ===");
  for (int i = 0; i < 4; i++) {
    int16_t raw_value = getRawADCValue(i);
    float voltage = ((float)raw_value * ADS_VREF) / 32768.0;
    Serial.print("Channel "); Serial.print(i); Serial.print(": ");
    Serial.print("Raw="); Serial.print(raw_value);
    Serial.print(", Voltage="); Serial.print(voltage, 4); Serial.println("V");
  }
  Serial.println("============================\n");
}

void printCurrentFilterStatus() {
  Serial.println("\n=== CURRENT FILTER STATUS ===");
  Serial.print("Picohydro Current Filter - Auto Cal: ");
  Serial.print(picohydroCurrentFilter.isAutoCalibrationEnabled() ? "ON" : "OFF");
  Serial.print(", Zero Offset: ");
  Serial.print(picohydroCurrentFilter.getZeroOffset(), 4);
  Serial.print("A, Calibrating: ");
  Serial.println(picohydroCurrentFilter.isCurrentlyCalibrating() ? "YES" : "NO");
  Serial.print("Battery In Current Filter - Auto Cal: ");
  Serial.print(batteryInCurrentFilter.isAutoCalibrationEnabled() ? "ON" : "OFF");
  Serial.print(", Zero Offset: ");
  Serial.print(batteryInCurrentFilter.getZeroOffset(), 4);
  Serial.print("A, Calibrating: ");
  Serial.println(batteryInCurrentFilter.isCurrentlyCalibrating() ? "YES" : "NO");
  Serial.print("Battery Out Current Filter - Auto Cal: ");
  Serial.print(batteryOutCurrentFilter.isAutoCalibrationEnabled() ? "ON" : "OFF");
  Serial.print(", Zero Offset: ");
  Serial.print(batteryOutCurrentFilter.getZeroOffset(), 4);
  Serial.print("A, Calibrating: ");
  Serial.println(batteryOutCurrentFilter.isCurrentlyCalibrating() ? "YES" : "NO");
  Serial.print("Filter Window Size: ");
  Serial.println(CURRENT_FILTER_WINDOW_SIZE);
  Serial.println("==============================\n");
}

bool detectStuckValues(SensorData& data) {
  return false; 
}

void forceSystemReset() {
  Serial.println("=== FORCE SYSTEM RESET ===");
  analogWrite(PWM_PIN, 0);
  Wire.end();
  delay(500); 
  Wire.begin();
  Wire.setClock(100000); 
  delay(200);
  ads_available = false;
  initializeADS1115();
  last_voltage_reading = -999.0;
  last_voltage_change = 0;
  stuck_reading_count = 0;
  Serial.println("System reset completed");
}

