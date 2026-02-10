#ifndef SERIAL_COMMANDS_H
#define SERIAL_COMMANDS_H
#include "config.h"
#include "sensors.h"
void handleSerialCommands();
void processCommand(String cmd);
void printMenu();
#endif

