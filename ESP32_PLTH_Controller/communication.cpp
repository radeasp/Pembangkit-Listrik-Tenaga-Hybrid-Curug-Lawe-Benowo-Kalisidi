#include "communication.h"

String last_json_data = "";

bool data_changed = false;

String generateJsonData() {
  StaticJsonDocument<400> doc;
  doc["timestamp"] = millis();
  doc["uptime_seconds"] = millis() / 1000;
  doc["solar_voltage"] = round(solar_voltage * 100) / 100.0;
  doc["solar_current"] = round(solar_current * 1000) / 1000.0;
  doc["battery_voltage"] = round(battery_voltage * 100) / 100.0;
  doc["temperature"] = round(temperature * 10) / 10.0;
  doc["humidity"] = round(humidity * 10) / 10.0;
  doc["tma_value"] = round(tma_value * 10) / 10.0;
  String json_string;
  serializeJson(doc, json_string);
  return json_string;
}

void sendJsonData() {
  String current_json = generateJsonData();
  data_changed = (current_json != last_json_data);
  if (!serial_monitor_active && !debug_mode) {
    detectDataTransfer();
  }
  Serial.println(current_json);
  last_json_data = current_json;
}

void detectDataTransfer() {
  master_connected = true;
  data_transfer_active = true;
  last_data_request_time = millis();
  if (debug_mode) {
    Serial.println("Active data communication detected - LED will blink at 1s interval");
  }
}

