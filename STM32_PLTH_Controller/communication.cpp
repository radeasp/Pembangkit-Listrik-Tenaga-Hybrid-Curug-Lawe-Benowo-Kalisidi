#include "communication.h"
void handleUSBCommunication(SensorData sensors, unsigned long current_time) {
  if (usb_connected && !serial_monitor_active && (current_time - last_data_send >= 500)) {
    sendSensorData(sensors);
    last_data_send = current_time;
    led_blink_interval = 1000;
  }
  if (usb_connected && !serial_monitor_active && Serial.available()) {
    receiveControlData();
  }
}

void sendSensorData(SensorData sensors) {
  DynamicJsonDocument doc(1024);
  doc["picohydro_voltage"] = sensors.picohydro_voltage;
  doc["picohydro_current"] = sensors.picohydro_current;
  doc["battery_in_current"] = sensors.battery_in_current;
  doc["battery_out_current"] = sensors.battery_out_current;
  doc["timestamp"] = millis();
  serializeJson(doc, Serial);
  Serial.println();
}

void receiveControlData() {
}

