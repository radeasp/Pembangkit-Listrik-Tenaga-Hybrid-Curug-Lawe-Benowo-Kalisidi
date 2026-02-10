#ifndef UTILITIES_H
#define UTILITIES_H
#include "config.h"
#include "sensors.h"
void initializePins();
void initializeSerial();
void initializeTiming();
void printWelcomeMessage();
void checkUSBConnection();
void handleLEDIndicator(unsigned long current_time);
void handleSerialOutput(SensorData sensors, unsigned long current_time);
void handleSerialDebug(SensorData sensors, unsigned long current_time);
void handleSerialPlotter(SensorData sensors, unsigned long current_time);
void handleQuickView(SensorData sensors, unsigned long current_time);
void handleRecording(SensorData sensors, unsigned long current_time);
void printSystemStatus();
void printPIDParameters();
void resetWatchdog();
void checkSystemStability();
void startRecording(String type);
void stopRecording();
#endif

