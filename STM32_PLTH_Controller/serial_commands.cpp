#include "serial_commands.h"
#include "utilities.h"
#include "pid_controller.h"
#include "sensors.h"  
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

void processCommand(String cmd) {
  cmd.trim();
  if (cmd == "h") {
    printMenu();
  }
  else if (cmd == "m") {
    serial_monitor_active = !serial_monitor_active;
    Serial.print("Serial Monitor: "); 
    Serial.println(serial_monitor_active ? "ON (JSON OFF)" : "OFF (JSON ON)");
    if (serial_monitor_active) {
      Serial.println("JSON communication dengan Raspberry Pi DIHENTIKAN");
      Serial.println("Mode debugging aktif");
    } else {
      Serial.println("JSON communication dengan Raspberry Pi AKTIF");
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
    String params = cmd.substring(2);
    params.trim();
    int space_pos = params.indexOf(' ');
    if (space_pos > 0) {
      String type = params.substring(0, space_pos);
      String duration_str = params.substring(space_pos + 1);
      duration_str.trim();
      if ((type == "ph" || type == "bt" || type == "pid") && duration_str.length() > 0) {
        float duration_seconds = duration_str.toFloat();
        if (duration_seconds > 0 && duration_seconds <= 300) {  
          recording_duration = duration_seconds * 1000;  
          startRecording(type);
        } else {
          Serial.println("Error: Durasi harus antara 0.1 - 300 detik");
        }
      } else {
        Serial.println("Error: Format tidak valid. Gunakan 'r ph <durasi>', 'r bt <durasi>', atau 'r pid <durasi>'");
        Serial.println("Contoh: r ph 10 (recording picohydro 10 detik)");
        Serial.println("Contoh: r bt 5 (recording battery 5 detik)");
        Serial.println("Contoh: r pid 15 (recording PID control 15 detik)");
      }
    } else {
      Serial.println("Error: Format tidak lengkap. Gunakan 'r ph <durasi>', 'r bt <durasi>', atau 'r pid <durasi>'");
    }
  }
  else if (cmd == "x") {
    if (recording_active) {
      stopRecording();
    } else {
      Serial.println("Recording tidak aktif");
    }
  }
  else if (cmd.startsWith("pid ")) {
    String params = cmd.substring(4);
    params.trim();
    int space1 = params.indexOf(' ');
    int space2 = params.indexOf(' ', space1 + 1);
    int space3 = params.indexOf(' ', space2 + 1);
    if (space1 > 0 && space2 > space1 && space3 > space2) {
      float new_setpoint = params.substring(0, space1).toFloat();
      float new_kp = params.substring(space1 + 1, space2).toFloat();
      float new_ki = params.substring(space2 + 1, space3).toFloat();
      float new_kd = params.substring(space3 + 1).toFloat();
      updatePIDParameters(new_setpoint, new_kp, new_ki, new_kd);
      Serial.println("Parameter PID berhasil diupdate:");
      printPIDParameters();
    } else {
      Serial.println("Error: Gunakan format 'pid <setpoint> <kp> <ki> <kd>'");
      Serial.println("Contoh: pid 14.4 1.0 0.1 0.05");
    }
  }
  else if (cmd == "c") {
    printPIDParameters();
  }
  else if (cmd == "z") {
    resetPIDParameters();
    Serial.println("Parameter PID direset ke default:");
    printPIDParameters();
  }
  else if (cmd == "raw") {
    printRawADCValues();
  }
  else if (cmd == "ads") {
    if (ads_available) {
      Serial.println("ADS1115 Status: ACTIVE");
    } else {
      Serial.println("ADS1115 Status: OFFLINE - Attempting recovery...");
      recoverADS1115();
      if (ads_available) {
        Serial.println("ADS1115 Recovery: SUCCESS");
      } else {
        Serial.println("ADS1115 Recovery: FAILED");
      }
    }
  }
  else if (cmd == "reset") {
    Serial.println("MANUAL SYSTEM RESET INITIATED...");
    forceSystemReset();
    Serial.println("Manual reset completed");
  }
  else if (cmd == "safe") {
    Serial.println("SAFE MODE: Disabling PWM output");
    analogWrite(PWM_PIN, 0);
    Serial.println("PWM output disabled for safety");
  }
  else if (cmd == "cal") {
    Serial.println("\n=== VOLTAGE CALIBRATION TEST WITH LINEAR REGRESSION ===");
    if (ads_available) {
      int16_t raw_adc = getRawADCValue(ADS_PICOHYDRO_VOLTAGE_CHANNEL);
      float adc_voltage = ((float)raw_adc * ADS_VREF) / 32768.0;
      float uncorrected_voltage = adc_voltage * VD_35V_RATIO;
      float corrected_voltage = readADSVoltageWithCorrection(ADS_PICOHYDRO_VOLTAGE_CHANNEL, VD_35V_RATIO);
      Serial.print("Raw ADC Value: "); Serial.println(raw_adc);
      Serial.print("ADC Pin Voltage: "); Serial.print(adc_voltage, 4); Serial.println(" V");
      Serial.print("Uncorrected Voltage: "); Serial.print(uncorrected_voltage, 2); Serial.println(" V");
      Serial.print("Corrected Voltage: "); Serial.print(corrected_voltage, 2); Serial.println(" V");
      Serial.print("Correction Applied: "); Serial.print(corrected_voltage - uncorrected_voltage, 3); Serial.println(" V");
      Serial.println("\nCompare 'Corrected Voltage' with your multimeter reading");
      Serial.println("Expected accuracy: ±0.05V (R² = 99.99%)");
    } else {
      Serial.println("ADS1115 not available");
    }
    Serial.println("=============================================\n");
  }
  else if (cmd == "filter") {
    printCurrentFilterStatus();
  }
  else if (cmd == "resetfilter") {
    resetCurrentFilters();
  }
  else if (cmd.startsWith("filteroff")) {
    if (cmd == "filteroff p") {
      picohydroCurrentFilter.disableAutoCalibration();
      Serial.println("Picohydro current filter auto-calibration DISABLED");
    } else if (cmd == "filteroff i") {
      batteryInCurrentFilter.disableAutoCalibration();
      Serial.println("Battery in current filter auto-calibration DISABLED");
    } else if (cmd == "filteroff o") {
      batteryOutCurrentFilter.disableAutoCalibration();
      Serial.println("Battery out current filter auto-calibration DISABLED");
    } else if (cmd == "filteroff all") {
      picohydroCurrentFilter.disableAutoCalibration();
      batteryInCurrentFilter.disableAutoCalibration();
      batteryOutCurrentFilter.disableAutoCalibration();
      Serial.println("ALL current filters auto-calibration DISABLED");
    } else {
      Serial.println("Usage: filteroff <p|i|o|all>");
      Serial.println("p=picohydro, i=battery_in, o=battery_out, all=semua");
    }
  }
  else if (cmd.startsWith("filteron")) {
    if (cmd == "filteron p") {
      picohydroCurrentFilter.enableAutoCalibration();
      Serial.println("Picohydro current filter auto-calibration ENABLED");
    } else if (cmd == "filteron i") {
      batteryInCurrentFilter.enableAutoCalibration();
      Serial.println("Battery in current filter auto-calibration ENABLED");
    } else if (cmd == "filteron o") {
      batteryOutCurrentFilter.enableAutoCalibration();
      Serial.println("Battery out current filter auto-calibration ENABLED");
    } else if (cmd == "filteron all") {
      picohydroCurrentFilter.enableAutoCalibration();
      batteryInCurrentFilter.enableAutoCalibration();
      batteryOutCurrentFilter.enableAutoCalibration();
      Serial.println("ALL current filters auto-calibration ENABLED");
    } else {
      Serial.println("Usage: filteron <p|i|o|all>");
      Serial.println("p=picohydro, i=battery_in, o=battery_out, all=semua");
    }
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
  Serial.println("CATATAN:");
  Serial.println("- Default: JSON mode (untuk Raspberry Pi)");
  Serial.println("- Serial Monitor ON: JSON dihentikan");
  Serial.println("- Serial Monitor OFF: JSON aktif");
  Serial.println();
  Serial.println("FITUR RECORDING:");
  Serial.println("r ph <durasi> - Mulai recording picohydro (voltage, current)");
  Serial.println("  Sampling: 100ms - Contoh: r ph 10 (recording picohydro 10 detik)");
  Serial.println("r bt <durasi> - Mulai recording battery (current in/out)");
  Serial.println("  Sampling: 100ms - Contoh: r bt 5 (recording battery 5 detik)");
  Serial.println("r pid <durasi> - Mulai recording PID control (voltage, current, PWM)");
  Serial.println("  Sampling: 10ms - Contoh: r pid 15 (recording PID control 15 detik)");
  Serial.println("x - Stop recording");
  Serial.println();
  Serial.println("KONTROL PID:");
  Serial.println("pid <setpoint> <kp> <ki> <kd> - Set semua parameter PID");
  Serial.println("  Contoh: pid 14.4 1.0 0.1 0.05");
  Serial.println("c - Tampilkan parameter PID saat ini");
  Serial.println();
  Serial.println("LAINNYA:");
  Serial.println("z - Reset parameter PID ke default");
  Serial.println("raw - Tampilkan raw ADC values untuk debugging");
  Serial.println("ads - Cek status ADS1115 dan coba recovery");
  Serial.println("reset - Force manual system reset (emergency)");
  Serial.println("safe - Emergency PWM disable untuk safety");
  Serial.println("cal - Test kalibrasi voltage dengan linear regression");
  Serial.println();
  Serial.println("CURRENT FILTER KONTROL:");
  Serial.println("filter - Tampilkan status filter moving average");
  Serial.println("resetfilter - Reset semua filter ke kondisi awal");
  Serial.println("filteron <p|i|o|all> - Enable auto-calibration filter");
  Serial.println("  p=picohydro, i=battery_in, o=battery_out, all=semua");
  Serial.println("filteroff <p|i|o|all> - Disable auto-calibration filter");
  Serial.println("  p=picohydro, i=battery_in, o=battery_out, all=semua");
  Serial.println("=========================================");
}

