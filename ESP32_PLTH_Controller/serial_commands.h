#ifndef SERIAL_COMMANDS_H
#define SERIAL_COMMANDS_H
#include "config.h"
extern String command_buffer;
extern bool command_mode;

void checkSerialCommands();
void handleSerialCommands();
void processSerialCommand(String command);
void processCommand(String cmd);
void printMenu();
#endif

