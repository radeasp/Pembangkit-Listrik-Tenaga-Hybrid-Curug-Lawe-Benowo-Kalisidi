#ifndef COMMUNICATION_H
#define COMMUNICATION_H
#include "config.h"
#include "sensors.h"
void handleUSBCommunication(SensorData sensors, unsigned long current_time);
void sendSensorData(SensorData sensors);
void receiveControlData();
#endif

