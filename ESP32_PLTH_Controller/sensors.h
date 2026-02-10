#ifndef SENSORS_H
#define SENSORS_H
#include "config.h"
extern DHT dht;
extern ADS1115 ads;

void initializeSensors();
void scanI2CDevices();
void readAllSensors();
void readDHT22();
void readHCSR04();
void readSolarPanel();
void readBatteryVoltage();  
void detectDataTransfer();  
#endif

