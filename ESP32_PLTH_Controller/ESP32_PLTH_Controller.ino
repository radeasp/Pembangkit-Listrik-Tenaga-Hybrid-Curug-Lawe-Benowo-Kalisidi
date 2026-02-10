#include "config.h"
#include "sensors.h"
#include "communication.h"
#include "utilities.h"
#include "serial_commands.h"

#define CURRENT_FILTER_WINDOW_SIZE 31
#define ZERO_CURRENT_THRESHOLD 0.05
#define CALIBRATION_SAMPLES 50
#define STABLE_READINGS_REQUIRED 20

class CurrentMovingAverageFilter {
private:
  float readings[CURRENT_FILTER_WINDOW_SIZE];
  int readIndex;
  float sum;
  bool bufferFilled;
  float zeroOffset;
  bool autoCalibrationEnabled;
  float calibrationSum;
  int calibrationCount;
  int stableReadingsCount;
  float lastReading;
  bool isCalibrating;
  unsigned long lastCalibrationTime;

public:
  CurrentMovingAverageFilter() {
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

  float addReading(float newReading) {
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

  float getCurrentAverage() {
    int divisor = bufferFilled ? CURRENT_FILTER_WINDOW_SIZE : readIndex;
    return (divisor > 0) ? sum / divisor : 0.0;
  }

  void reset() {
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
  
private:
  void performAutoCalibration(float rawReading) {
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
  void startCalibration() {
    isCalibrating = true;
    calibrationSum = 0.0;
    calibrationCount = 0;
    lastCalibrationTime = millis();
  }
  void completeCalibration() {
    if (calibrationCount > 0) {
      float newZeroOffset = calibrationSum / calibrationCount;
      zeroOffset = newZeroOffset;
      lastCalibrationTime = millis();
    }
    resetCalibration();
  }
  void resetCalibration() {
    isCalibrating = false;
    stableReadingsCount = 0;
    calibrationSum = 0.0;
    calibrationCount = 0;
  }
public:
  void enableAutoCalibration() {
    autoCalibrationEnabled = true;
  }
  void disableAutoCalibration() {
    autoCalibrationEnabled = false;
  }
  bool isAutoCalibrationEnabled() {
    return autoCalibrationEnabled;
  }
  float getZeroOffset() {
    return zeroOffset;
  }
  void setZeroOffset(float offset) {
    zeroOffset = offset;
  }
  bool isCurrentlyCalibrating() {
    return isCalibrating;
  }
  unsigned long getLastCalibrationTime() {
    return lastCalibrationTime;
  }
  void triggerManualCalibration() {
    resetCalibration();
    startCalibration();
  }
};
CurrentMovingAverageFilter currentFilter;

float readFilteredCurrent() {
  float rawCurrent = 0.0;
  float filteredCurrent = currentFilter.addReading(rawCurrent);
  return filteredCurrent;
}

float getCurrentFilteredValue() {
  return currentFilter.getCurrentAverage();
}

void resetCurrentFilter() {
  currentFilter.reset();
}

void enableCurrentAutoCalibration() {
  currentFilter.enableAutoCalibration();
}

void disableCurrentAutoCalibration() {
  currentFilter.disableAutoCalibration();
}

bool isCurrentAutoCalibrationEnabled() {
  return currentFilter.isAutoCalibrationEnabled();
}

float getCurrentZeroOffset() {
  return currentFilter.getZeroOffset();
}

void setCurrentZeroOffset(float offset) {
  currentFilter.setZeroOffset(offset);
}

bool isCurrentSensorCalibrating() {
  return currentFilter.isCurrentlyCalibrating();
}
unsigned long getLastCurrentCalibrationTime() {
  return currentFilter.getLastCalibrationTime();
}

void triggerManualCurrentCalibration() {
  currentFilter.triggerManualCalibration();
}

void printCurrentCalibrationStatus() {
  Serial.println("=== Current Sensor Calibration Status ===");
  Serial.print("Auto Calibration: ");
  Serial.println(isCurrentAutoCalibrationEnabled() ? "ENABLED" : "DISABLED");
  Serial.print("Currently Calibrating: ");
  Serial.println(isCurrentSensorCalibrating() ? "YES" : "NO");
  Serial.print("Zero Offset: ");
  Serial.print(getCurrentZeroOffset(), 4);
  Serial.println(" A");
  unsigned long lastCal = getLastCurrentCalibrationTime();
  if (lastCal > 0) {
    Serial.print("Last Calibration: ");
    Serial.print((millis() - lastCal) / 1000);
    Serial.println(" seconds ago");
  } else {
    Serial.println("Last Calibration: Never");
  }
  Serial.println("==========================================");
}

void setup() {
  initializeSerial();
  initializePins();
  initializeLED();
  initializeI2C();
  initializeSensors();
  initializeTiming();
  if (debug_mode) {
    printWelcomeMessage();
  }
  performLEDTest();
}

void loop() {
  static unsigned long last_cycle_time = 0;
  unsigned long start_time = millis();
  handleLEDCommunication();
  handleSerialCommands();
  readAllSensors();
  if (serial_monitor_active) {
    handleSerialOutput(start_time);
  } else if (json_output_mode) {
    sendJsonData();
  } else {
    printSensorData();
  }
  if (recording_active) {
    handleRecording(start_time);
  }
  unsigned long execution_time = millis() - start_time;
  unsigned long sleep_time = (execution_time < 1000) ? (1000 - execution_time) : 0;
  if (debug_mode && (millis() / 1000) % 10 == 0) {
    printPerformanceInfo(execution_time, sleep_time);
  }
  delay(sleep_time);
}

