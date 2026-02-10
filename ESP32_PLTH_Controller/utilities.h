#ifndef UTILITIES_H
#define UTILITIES_H
#include "config.h"
#include "sensors.h"
void initializeSerial();
void initializePins();
void initializeLED();
void initializeI2C();
void initializeTiming();
void printWelcomeMessage();
void handleLEDCommunication();
void printSensorData();
void printPerformanceInfo(unsigned long execution_time, unsigned long sleep_time);
void performLEDTest();
void handleSerialOutput(unsigned long current_time);
void handleSerialDebug(unsigned long current_time);
void handleSerialPlotter(unsigned long current_time);
void handleQuickView(unsigned long current_time);
void handleRecording(unsigned long current_time);
void printSystemStatus();
void printCalibrationInfo();
void printSensorCalibration();
void startRecording();
void stopRecording();
void clearScreen();
void calibrateCurrentSensor();
void setCurrentSensitivity(float sensitivity);
void setCurrentDividerRatio(float ratio);
void showCurrentCalibrationInfo();
#endif

