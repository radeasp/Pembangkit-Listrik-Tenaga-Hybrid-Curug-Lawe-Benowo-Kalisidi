#ifndef SENSORS_H
#define SENSORS_H
#include "config.h"
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
  CurrentMovingAverageFilter();
  float addReading(float newReading);
  float getCurrentAverage();
  void reset();
  void enableAutoCalibration();
  void disableAutoCalibration();
  bool isAutoCalibrationEnabled();
  float getZeroOffset();
  void setZeroOffset(float offset);
  bool isCurrentlyCalibrating();
  unsigned long getLastCalibrationTime();
  void triggerManualCalibration();
private:
  void performAutoCalibration(float rawReading);
  void startCalibration();
  void completeCalibration();
  void resetCalibration();
};
struct SensorData {
  float picohydro_voltage;
  float picohydro_current;
  float battery_in_current;
  float battery_out_current;
};

SensorData readSensors();
void initializeADS1115();
bool checkADS1115Connection();
void recoverADS1115();
float readADSVoltage(int channel, float divider_ratio);
float readADSVoltageWithCorrection(int channel, float divider_ratio);
float readADSCalibratedCurrent(int channel, float zero_voltage, float sensitivity);
float readADSCalibratedCurrentWithFilter(int channel, float zero_voltage, float sensitivity, CurrentMovingAverageFilter& filter);
float readADSCorrectedCurrentWithFilter(int channel, float zero_voltage, float sensitivity, CurrentMovingAverageFilter& filter);
void initializeCurrentFilters();
void resetCurrentFilters();
float getFilteredPicohydroCurrent();
float getFilteredBatteryInCurrent();
float getFilteredBatteryOutCurrent();
extern CurrentMovingAverageFilter picohydroCurrentFilter;
extern CurrentMovingAverageFilter batteryInCurrentFilter;
extern CurrentMovingAverageFilter batteryOutCurrentFilter;

bool detectStuckValues(SensorData& data);
void forceSystemReset();
void printRawADCValues();
void printCurrentFilterStatus();
int16_t getRawADCValue(int channel);
extern bool ads_available;
extern unsigned long last_ads_check;
extern unsigned long ads_check_interval;
#endif

