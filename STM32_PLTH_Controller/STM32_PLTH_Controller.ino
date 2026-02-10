#include "config.h"
#include "sensors.h"
#include "pid_controller.h"
#include "communication.h"
#include "utilities.h"
#include "serial_commands.h"
void setup() {
  initializeSerial();  
  delay(1000);         
  Serial.println("=== STM32 PLTH Controller Starting ===");
  initializePins();
  initializeTiming();
  printWelcomeMessage();
}

void loop() {
  unsigned long current_time = millis();
  
  checkSystemStability();
  checkUSBConnection();
  handleLEDIndicator(current_time);
  unsigned long sensor_start = millis();
  SensorData sensors = readSensors();
  unsigned long sensor_time = millis() - sensor_start;
  if (sensor_time > 500) { 
    Serial.print("CRITICAL: Sensor read took ");
    Serial.print(sensor_time);
    Serial.println("ms - potential hang detected!");
    last_watchdog_reset = 0;
  } else {
    resetWatchdog();
  }
  if (ads_available && sensors.picohydro_voltage > 0) {
    pidControl(sensors.picohydro_voltage, current_time);
  } else {
    analogWrite(PWM_PIN, 0);
  }
  handleRecording(sensors, current_time);
  handleSerialCommands();
  handleUSBCommunication(sensors, current_time);
  if (serial_monitor_active) {
    handleSerialOutput(sensors, current_time);
  }
  if (recording_active) {
    delay(1);  
  } else {
    delay(10); 
  }
} 

