#include "serial_commands.h"
#include "utilities.h"
#include "sensors.h"
String command_buffer = "";
bool command_mode = false;
void checkSerialCommands() {
  if (Serial.available()) {
    String command = Serial.readString();
    command.trim();
    command.toUpperCase();
    processSerialCommand(command);
  }
}

void handleSerialCommands() {
  
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (command_buffer.length() > 0) {
        processCommand(command_buffer);
        command_buffer = "";
      }
    } else {
      command_buffer += c;
    }
  }
}

void processSerialCommand(String command) {
  
  if (command == "DEBUG") {
    debug_mode = true;
    json_output_mode = false;
    serial_monitor_active = true;  
    Serial.println("Switched to DEBUG mode - Human readable output");
  } else if (command == "JSON") {
    json_output_mode = true;
    serial_monitor_active = false;  
    debug_mode = false;
    Serial.println("Switched to JSON mode - JSON output only");
  } else if (command == "SCAN") {
    scanI2CDevices();
  } else if (command == "LEDTEST") {
    Serial.println("LED Test - Simulating data transfer for 5 seconds");
    detectDataTransfer();
    for (int i = 0; i < 50; i++) {  
      handleLEDCommunication();
      delay(100);
    }
    data_transfer_active = false;
    master_connected = false;
    digitalWrite(LED_BUILTIN, LOW);
    Serial.println("LED Test completed");
  } else if (command == "CONNECT") {
    master_connected = true;
    detectDataTransfer();
    Serial.println("Master connection simulated - LED should start blinking");
  } else if (command == "DISCONNECT") {
    master_connected = false;
    data_transfer_active = false;
    digitalWrite(LED_BUILTIN, LOW);
    Serial.println("Master disconnection simulated - LED should stop blinking");
  } else if (command == "HELP") {
    printMenu();
  }
}

void processCommand(String cmd) {
  
  cmd.trim();
  if (cmd == "h") {
    printMenu();
  }
  else if (cmd == "m") {
    serial_monitor_active = !serial_monitor_active;
    json_output_mode = !serial_monitor_active;
    Serial.print("Serial Monitor: "); 
    Serial.println(serial_monitor_active ? "ON (JSON OFF)" : "OFF (JSON ON)");
    if (serial_monitor_active) {
      Serial.println("JSON communication dengan Master DIHENTIKAN");
      Serial.println("Mode debugging aktif");
    } else {
      Serial.println("JSON communication dengan Master AKTIF");
      Serial.println("Mode debugging dinonaktifkan");
    }
  }
  else if (cmd == "d") {
    debug_mode = !debug_mode;
    Serial.print("Debug Mode: "); Serial.println(debug_mode ? "ON" : "OFF");
  }
  else if (cmd == "g") {
    plotter_mode = !plotter_mode;
    if (plotter_mode) quick_view_mode = false;  
    Serial.print("Plotter Mode: "); Serial.println(plotter_mode ? "ON" : "OFF");
    if (plotter_mode) {
      Serial.println("Aktifkan Serial Plotter di Arduino IDE untuk melihat grafik");
    }
  }
  else if (cmd == "q") {
    quick_view_mode = !quick_view_mode;
    if (quick_view_mode) plotter_mode = false;  
    Serial.print("Quick View Mode: "); Serial.println(quick_view_mode ? "ON" : "OFF");
    if (quick_view_mode) {
      Serial.println("Mode tampilan ringkas - data dalam satu baris");
    }
  }
  else if (cmd == "s") {
    printSystemStatus();
  }
  else if (cmd.startsWith("r ")) {
    String duration_str = cmd.substring(2);
    duration_str.trim();
    if (duration_str.length() > 0) {
      float duration_seconds = duration_str.toFloat();
      if (duration_seconds > 0 && duration_seconds <= 300) {  
        recording_duration = duration_seconds * 1000;  
        startRecording();
      } else {
        Serial.println("Error: Durasi harus antara 0.1 - 300 detik");
      }
    } else {
      Serial.println("Error: Gunakan format 'r <durasi>' (contoh: r 10)");
    }
  }
  else if (cmd == "x") {
    if (recording_active) {
      stopRecording();
    } else {
      Serial.println("Recording tidak aktif");
    }
  }
  else if (cmd == "c") {
    printSensorCalibration();
  }
  else if (cmd == "l") {
    showCurrentCalibrationInfo();
  }
  else if (cmd == "cal" || cmd == "calibrate") {
    calibrateCurrentSensor();
  }
  else if (cmd.startsWith("sens ")) {
    String sensitivity_str = cmd.substring(5);
    sensitivity_str.trim();
    float sensitivity = sensitivity_str.toFloat();
    if (sensitivity > 0) {
      setCurrentSensitivity(sensitivity);
    } else {
      Serial.println("❌ Sensitivitas harus > 0");
    }
  }
  else if (cmd.startsWith("ratio ")) {
    String ratio_str = cmd.substring(6);
    ratio_str.trim();
    float ratio = ratio_str.toFloat();
    if (ratio > 0 && ratio <= 1.0) {
      setCurrentDividerRatio(ratio);
    } else {
      Serial.println("❌ Ratio harus antara 0 dan 1.0");
    }
  }
  else if (cmd == "reset") {
    current_zero_voltage = 2.5 * current_divider_ratio;
    current_calibrated = false;
    Serial.println("🔄 Kalibrasi direset ke default");
    Serial.print("📐 Tegangan teoritis 0A: "); Serial.print(current_zero_voltage, 3); Serial.println("V");
  }
  else if (cmd == "scan") {
    scanI2CDevices();
  }
  else if (cmd == "ledtest") {
    Serial.println("LED Test - Simulating data transfer for 5 seconds");
    detectDataTransfer();
    for (int i = 0; i < 50; i++) {  
      handleLEDCommunication();
      delay(100);
    }
    data_transfer_active = false;
    master_connected = false;
    digitalWrite(LED_BUILTIN, LOW);
    Serial.println("LED Test completed");
  }
  else if (cmd == "connect") {
    master_connected = true;
    detectDataTransfer();
    Serial.println("Master connection simulated - LED should start blinking");
  }
  else if (cmd == "disconnect") {
    master_connected = false;
    data_transfer_active = false;
    digitalWrite(LED_BUILTIN, LOW);
    Serial.println("Master disconnection simulated - LED should stop blinking");
  }
  else {
    Serial.println("Command tidak dikenali. Ketik 'h' untuk bantuan.");
  }
}

void printMenu() {
  Serial.println("\n========== MENU KONTROL SERIAL ==========");
  Serial.println("FITUR UTAMA:");
  Serial.println("h - Tampilkan menu ini");
  Serial.println("m - Toggle serial monitor (ON=Debug, OFF=JSON)");
  Serial.println("d - Toggle debug mode (ON/OFF)");
  Serial.println("g - Toggle plotter mode (untuk Serial Plotter)");
  Serial.println("q - Quick view mode (tampilan ringkas)");
  Serial.println("s - Tampilkan status sistem");
  Serial.println();
  Serial.println("KALIBRASI SENSOR ARUS:");
  Serial.println("cal - Kalibrasi sensor arus (pastikan 0A)");
  Serial.println("sens <nilai> - Set sensitivitas sensor");
  Serial.println("  Contoh: sens 0.100 (ACS712-20A, default STM32)");
  Serial.println("  Contoh: sens 0.185 (ACS712-5A)");
  Serial.println("  Contoh: sens 0.066 (ACS712-30A)");
  Serial.println("ratio <nilai> - Set voltage divider ratio");
  Serial.println("  Default: ratio 0.6458 (sama dengan STM32)");
  Serial.println("  Contoh: ratio 0.8 (R1=1kΩ, R2=4kΩ)");
  Serial.println("  Contoh: ratio 1.0 (tanpa voltage divider)");
  Serial.println("reset - Reset kalibrasi ke default");
  Serial.println("l - Tampilkan info kalibrasi sensor arus");
  Serial.println();
  Serial.println("CATATAN:");
  Serial.println("- Default: JSON mode (untuk Master/Raspberry Pi)");
  Serial.println("- Serial Monitor ON: JSON dihentikan");
  Serial.println("- Serial Monitor OFF: JSON aktif");
  Serial.println("- Kalibrasi diperlukan untuk akurasi sensor arus");
  Serial.println();
  Serial.println("FITUR RECORDING:");
  Serial.println("r <durasi> - Mulai recording sensor power (Solar V/I, Battery V)");
  Serial.println("  Contoh: r 10 (recording 10 detik = 100 data)");
  Serial.println("x - Stop recording");
  Serial.println();
  Serial.println("SENSOR & KALIBRASI:");
  Serial.println("c - Tampilkan pembacaan sensor saat ini");
  Serial.println("scan - Scan perangkat I2C");
  Serial.println();
  Serial.println("TESTING:");
  Serial.println("ledtest - Test LED communication indicator");
  Serial.println("connect - Simulasi koneksi master");
  Serial.println("disconnect - Simulasi pemutusan koneksi master");
  Serial.println("=========================================");
}

