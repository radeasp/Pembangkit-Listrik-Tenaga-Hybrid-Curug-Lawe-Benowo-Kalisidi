#include "utilities.h"

bool json_output_mode = true;    
bool debug_mode = false;         
bool serial_monitor_active = false;  
bool plotter_mode = false;           
bool quick_view_mode = false;        
bool recording_active = false;       
unsigned long recording_start_time = 0;
unsigned long recording_duration = 5000;  
unsigned long last_recording_sample = 0;
unsigned long last_serial_output = 0;
const unsigned long RECORDING_SAMPLE_INTERVAL = 100;  
float current_zero_voltage = SOLAR_CURRENT_ZERO;  
float current_sensitivity = SOLAR_CURRENT_SENSITIVITY;  
bool current_calibrated = false;
float current_zero_threshold = 0.1;     
float current_divider_ratio = CURRENT_VOLTAGE_DIVIDER_RATIO;  
bool led_state = false;          
unsigned long led_toggle_time = 0;   
bool data_transfer_active = false;  
bool master_connected = false;      
unsigned long last_data_request_time = 0;  
void initializeSerial() {
  Serial.begin(115200);
  while (!Serial) delay(10);
  if (Serial.available()) {
    String command = Serial.readString();
    command.trim();
    if (command == "DEBUG") {
      debug_mode = true;
      json_output_mode = false;
    } else if (command == "JSON") {
      json_output_mode = true;
      debug_mode = false;
    }
  }
}

void initializePins() {
  pinMode(HCSR04_TRIG, OUTPUT);
  pinMode(HCSR04_ECHO, INPUT);
}

void initializeLED() {
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);  
  led_state = false;
  if (debug_mode) {
    Serial.println("LED Communication Indicator initialized (GPIO2)");
  }
}

void initializeI2C() {
  Wire.begin(I2C_SDA, I2C_SCL);
}

void initializeTiming() {
}

void printWelcomeMessage() {
  Serial.println("========== ESP32 PLTH Controller ==========");
  Serial.println("Mode: JSON Communication (Serial Monitor OFF)");
  Serial.println("Multi-sensor monitoring system for hydro power");
  Serial.println("Ketik 'm' untuk toggle serial monitor");
  Serial.println("Ketik 'h' untuk menu bantuan");
  Serial.println("==========================================");
}

void handleLEDCommunication() {
  unsigned long current_time = millis();
  if (master_connected && (current_time - last_data_request_time > MASTER_TIMEOUT)) {
    master_connected = false;
    data_transfer_active = false;
    if (debug_mode) {
      Serial.println("Master connection timeout - LED switched to idle mode");
    }
  }
  unsigned long led_interval = 0;
  if (serial_monitor_active || debug_mode) {
    digitalWrite(LED_BUILTIN, LOW);
    led_state = false;
    return;
  }
  if (!Serial) {
    led_interval = 0;
  } else if (data_transfer_active && master_connected) {
    led_interval = 1000;
  } else {
    led_interval = 3000;
  }
  if (led_interval == 0) {
    digitalWrite(LED_BUILTIN, HIGH);
    led_state = true;
  } else {
    if (current_time - led_toggle_time >= led_interval) {
      led_state = !led_state;
      digitalWrite(LED_BUILTIN, led_state ? HIGH : LOW);
      led_toggle_time = current_time;
    }
  }
}

void printSensorData() {
  Serial.println();
  Serial.println("=== ALL SENSORS - 1 SECOND INTERVAL - " + String(millis()/1000) + "s ===");
  Serial.println("Solar Voltage (solar_voltage): " + String(solar_voltage, 2) + " V [ADS1115@0x48: " +
                 String(ads1115_detected ? "OK" : "FAIL") + "]");
  Serial.println("Solar Current (solar_current): " + String(solar_current, 3) + " A [WCS-1700 via ADS1115@0x48: " +
                 String(ads1115_detected ? "OK" : "FAIL") + "]");
  Serial.println("Battery Voltage (battery_voltage): " + String(battery_voltage, 2) + " V [ADS1115@0x48: " +
                 String(ads1115_detected ? "OK" : "FAIL") + "]");
  Serial.println("Temperature (temperature): " + String(temperature, 1) + "°C");
  Serial.println("Humidity (humidity): " + String(humidity, 1) + "%");
  Serial.println("Water Level (tma_value): " + String(tma_value, 1) + " cm");
  Serial.println("LED Status: " + String(data_transfer_active ? "COMMUNICATION" : "IDLE") + " [GPIO2]");
  Serial.println("Master Connected: " + String(master_connected ? "YES" : "NO"));
  Serial.println("Data Changed: " + String(data_changed ? "YES" : "NO"));
  Serial.println("=====================================");
}

void printPerformanceInfo(unsigned long execution_time, unsigned long sleep_time) {
  Serial.println("Performance: Execution " + String(execution_time) + "ms, Sleep " + String(sleep_time) + "ms");
  Serial.println("LED: " + String(led_state ? "ON" : "OFF") + ", Transfer: " + String(data_transfer_active ? "ACTIVE" : "IDLE"));
}

void performLEDTest() {
  for (int i = 0; i < 2; i++) {
    digitalWrite(LED_BUILTIN, HIGH);
    delay(150);
    digitalWrite(LED_BUILTIN, LOW);
    delay(150);
  }
}

void handleSerialOutput(unsigned long current_time) {
  if (plotter_mode) {
    handleSerialPlotter(current_time);
  } else if (quick_view_mode) {
    handleQuickView(current_time);
  } else {
    handleSerialDebug(current_time);
  }
}

void handleSerialDebug(unsigned long current_time) {
  if (debug_mode && (current_time - last_serial_output >= 500)) {
    clearScreen();
    Serial.println("========================================");
    Serial.println("       ESP32 PLTH CONTROLLER DATA");
    Serial.println("========================================");
    Serial.print("Timestamp: "); Serial.print(millis()/1000.0, 1); Serial.println(" s");
    Serial.print("System Mode: "); Serial.println(json_output_mode ? "JSON" : "DEBUG");
    Serial.print("Master Connected: "); Serial.println(master_connected ? "YES" : "NO");
    Serial.println();
    Serial.println("┌─ ENVIRONMENTAL SENSORS ─────────────────┐");
    Serial.print("│ Temperature  : "); Serial.print(temperature, 1); Serial.println(" °C        │");
    Serial.print("│ Humidity     : "); Serial.print(humidity, 1); Serial.println(" %         │");
    Serial.print("│ Water Level  : "); Serial.print(tma_value, 1); Serial.println(" cm        │");
    Serial.println("└─────────────────────────────────────────┘");
    Serial.println();
    Serial.println("┌─ POWER GENERATION ──────────────────────┐");
    Serial.print("│ Solar Voltage: "); Serial.print(solar_voltage, 2); Serial.println(" V         │");
    Serial.print("│ Solar Current: "); Serial.print(solar_current, 3); Serial.println(" A         │");
    Serial.print("│ Solar Power  : "); Serial.print(solar_voltage * solar_current, 1); Serial.println(" W         │");
    Serial.print("│ Battery Volt : "); Serial.print(battery_voltage, 2); Serial.println(" V         │");
    Serial.println("└─────────────────────────────────────────┘");
    Serial.println();
    Serial.println("┌─ SENSOR STATUS ─────────────────────────┐");
    Serial.print("│ ADS1115 (ADC): "); Serial.print(ads1115_detected ? "OK" : "FAIL"); Serial.println("               │");
    Serial.print("│ DHT22 (Temp/Hum): "); Serial.print("OK"); Serial.println("           │");
    Serial.print("│ Ultrasonic: "); Serial.print("OK"); Serial.println("                │");
    Serial.print("│ ACS-712 Current: "); Serial.print(ads1115_detected ? "OK" : "FAIL"); Serial.println("          │");
    Serial.println("└─────────────────────────────────────────┘");
    last_serial_output = current_time;
  }
}

void handleSerialPlotter(unsigned long current_time) {
  if (serial_monitor_active && current_time - last_serial_output >= 100) { 
    Serial.print("Temp:");
    Serial.print(temperature);
    Serial.print(",Humidity:");
    Serial.print(humidity);
    Serial.print(",WaterLevel:");
    Serial.print(tma_value);
    Serial.print(",SolarV:");
    Serial.print(solar_voltage);
    Serial.print(",SolarI:");
    Serial.print(solar_current);
    Serial.print(",SolarP:");
    Serial.print(solar_voltage * solar_current);
    Serial.print(",BatteryV:");
    Serial.print(battery_voltage);
    Serial.println();
    last_serial_output = current_time;
  }
}

void handleQuickView(unsigned long current_time) {
  if (current_time - last_serial_output >= 1000) {
    Serial.print("["); Serial.print(millis()/1000); Serial.print("s] ");
    Serial.print("T:"); Serial.print(temperature, 1);
    Serial.print("°C H:"); Serial.print(humidity, 1);
    Serial.print("% W:"); Serial.print(tma_value, 1);
    Serial.print("cm SV:"); Serial.print(solar_voltage, 1);
    Serial.print("V SI:"); Serial.print(solar_current, 2);
    Serial.print("A SP:"); Serial.print(solar_voltage * solar_current, 1);
    Serial.print("W BV:"); Serial.print(battery_voltage, 1);
    Serial.print("V");
    Serial.println();
    last_serial_output = current_time;
  }
}

void handleRecording(unsigned long current_time) {
  if (!recording_active) return;
  if (current_time - recording_start_time >= recording_duration) {
    stopRecording();
    return;
  }
  if (current_time - last_recording_sample >= RECORDING_SAMPLE_INTERVAL) {
    Serial.print(current_time - recording_start_time);
    Serial.print(", ");
    Serial.print(solar_voltage, 3);
    Serial.print(", ");
    Serial.print(solar_current, 3);
    Serial.print(", ");
    Serial.print(battery_voltage, 3);
    Serial.println();
    last_recording_sample = current_time;
  }
}

void printSystemStatus() {
  Serial.println("\n========== STATUS SISTEM ==========");
  Serial.print("Serial Monitor: "); 
  Serial.print(serial_monitor_active ? "ON" : "OFF");
  Serial.print(" (JSON: ");
  Serial.print(serial_monitor_active ? "OFF" : "ON");
  Serial.println(")");
  Serial.print("Debug Mode: "); Serial.println(debug_mode ? "ON" : "OFF");
  Serial.print("Plotter Mode: "); Serial.println(plotter_mode ? "ON" : "OFF");
  Serial.print("Quick View Mode: "); Serial.println(quick_view_mode ? "ON" : "OFF");
  Serial.print("Master Connected: "); Serial.println(master_connected ? "YES" : "NO");
  Serial.print("Recording: "); Serial.println(recording_active ? "ACTIVE" : "INACTIVE");
  if (recording_active) {
    Serial.print("Recording Time Left: "); 
    Serial.print((recording_duration - (millis() - recording_start_time))/1000.0, 1);
    Serial.println(" seconds");
  }
  Serial.println("==================================");
}

void printCalibrationInfo() {
  Serial.println("========== SENSOR CALIBRATION INFO ==========");
  Serial.println("ESP32 Multi-Sensor Controller");
  Serial.println("Sensor specifications and calibration values:");
  Serial.println();
  Serial.println("ENVIRONMENTAL SENSORS:");
  Serial.println("- DHT22: Temperature (-40 to 80°C), Humidity (0-100%)");
  Serial.println("- HC-SR04: Ultrasonic distance (2-400 cm)");
  Serial.println();
  Serial.println("POWER GENERATION SENSORS:");
  Serial.println("- ADS1115: 16-bit ADC for solar panel measurements");
  Serial.println("  - Channel A0: Solar voltage (0-25V range)");
  Serial.println("  - Channel A1: Solar current (ACS712 sensor)");
  Serial.println();
  Serial.println("I2C ADDRESSES:");
  Serial.println("- ADS1115: 0x48 (solar panel ADC)");
  Serial.println("=============================================");
}

void printSensorCalibration() {
  Serial.println("\n========== SENSOR READINGS & STATUS ==========");
  Serial.print("Temperature: "); Serial.print(temperature, 1); Serial.println(" °C");
  Serial.print("Humidity: "); Serial.print(humidity, 1); Serial.println(" %");
  Serial.print("Water Level: "); Serial.print(tma_value, 1); Serial.println(" cm");
  Serial.print("Solar Voltage: "); Serial.print(solar_voltage, 2); Serial.println(" V");
  Serial.print("Solar Current: "); Serial.print(solar_current, 3); Serial.println(" A");
  Serial.print("Solar Power: "); Serial.print(solar_voltage * solar_current, 1); Serial.println(" W");
  Serial.print("Battery Voltage: "); Serial.print(battery_voltage, 2); Serial.println(" V");
  Serial.println();
  Serial.println("I2C SENSOR STATUS:");
  Serial.print("ADS1115 (Solar): "); Serial.println(ads1115_detected ? "OK" : "FAIL");
  Serial.println("===============================================");
}

void startRecording() {
  recording_active = true;
  recording_start_time = millis();
  last_recording_sample = millis();
  Serial.println("\n========== MULAI RECORDING ==========");
  Serial.print("Durasi: "); Serial.print(recording_duration/1000.0, 1); Serial.println(" detik");
  Serial.print("Sampling: 100ms (akan menghasilkan "); 
  Serial.print((recording_duration/100), 0);
  Serial.println(" data)");
  Serial.println("Format: Time(ms), SolarV(V), SolarI(A), BatteryV(V)");
  Serial.println("=====================================");
}

void stopRecording() {
  recording_active = false;
  Serial.println("\n========== RECORDING DIHENTIKAN ==========");
  Serial.print("Total waktu: "); 
  Serial.print((millis() - recording_start_time)/1000.0, 1); 
  Serial.println(" detik");
  Serial.println("=========================================");
}

void clearScreen() {
  Serial.print("\033[2J");
  Serial.print("\033[H");
}

void calibrateCurrentSensor() {
  if (!ads1115_detected) {
    Serial.println("❌ ADS1115 tidak terdeteksi! Kalibrasi gagal.");
    return;
  }
  Serial.println("🔧 Memulai kalibrasi sensor arus...");
  Serial.println("📋 Pastikan TIDAK ADA ARUS yang mengalir (0A)!");
  Serial.println("⚡ Sensor ACS712-20A mengeluarkan 2.5V saat 0A (sama dengan STM32)");
  Serial.print("🔧 Dengan voltage divider ratio: "); Serial.print(current_divider_ratio, 4); Serial.println(" (sama dengan STM32)");
  float theoretical_zero = 2.5 * current_divider_ratio;
  Serial.print("📐 Tegangan teoritis saat 0A: "); Serial.print(theoretical_zero, 3); Serial.println("V");
  Serial.println("⏳ Mengambil 50 sampel dalam 5 detik...");
  float total_voltage = 0.0;
  int sample_count = 50;
  for (int i = 0; i < sample_count; i++) {
    int16_t current_raw = ads.readADC(1);
    float current_voltage = (current_raw * 4.096) / 32768.0;
    total_voltage += current_voltage;
    Serial.print("Sampel "); Serial.print(i + 1);
    Serial.print("/"); Serial.print(sample_count);
    Serial.print(": "); Serial.print(current_voltage, 4);
    Serial.println("V");
    delay(100);  
  }
  current_zero_voltage = total_voltage / sample_count;
  current_calibrated = true;
  Serial.println("✅ Kalibrasi selesai!");
  Serial.print("📊 Tegangan saat 0A: "); Serial.print(current_zero_voltage, 4); Serial.println("V");
  Serial.print("📐 Teoritis: "); Serial.print(theoretical_zero, 3); Serial.println("V");
  Serial.print("📏 Selisih: "); Serial.print(abs(current_zero_voltage - theoretical_zero), 3); Serial.println("V");
  Serial.print("🎯 Sensitivitas: "); Serial.print(current_sensitivity, 3); Serial.println("V/A");
  Serial.print("🔍 Threshold: "); Serial.print(current_zero_threshold, 2); Serial.println("A");
  float expected_min = theoretical_zero - 0.3;
  float expected_max = theoretical_zero + 0.3;
  if (current_zero_voltage < expected_min || current_zero_voltage > expected_max) {
    Serial.println("⚠️  WARNING: Tegangan nol tidak sesuai dengan voltage divider!");
    Serial.print("   Diharapkan: "); Serial.print(theoretical_zero, 3); Serial.println("V ± 0.3V");
    Serial.println("   Periksa:");
    Serial.println("   - Koneksi voltage divider");
    Serial.println("   - Nilai resistor R1 dan R2");
    Serial.println("   - Power supply ACS712 (5V)");
    Serial.println("   - Atau ubah ratio dengan command 'ratio <nilai>'");
  } else {
    Serial.println("✅ Kalibrasi berhasil - tegangan sesuai dengan voltage divider!");
  }
}

void setCurrentSensitivity(float sensitivity) {
  current_sensitivity = sensitivity;
  Serial.print("🔧 Sensitivitas sensor diatur ke: ");
  Serial.print(sensitivity, 3);
  Serial.println("V/A");
  Serial.println("📋 Referensi sensitivitas:");
  Serial.println("   ACS712-5A:  0.185 V/A");
  Serial.println("   ACS712-20A: 0.100 V/A (STM32 default)");
  Serial.println("   ACS712-30A: 0.066 V/A");
  Serial.println("   ACS758-50A: 0.040 V/A");
}

void setCurrentDividerRatio(float ratio) {
  current_divider_ratio = ratio;
  Serial.print("🔧 Voltage divider ratio diatur ke: ");
  Serial.print(ratio, 3);
  Serial.println();
  Serial.println("📋 Referensi voltage divider:");
  Serial.println("   STM32 setup: 0.6458 (sama dengan rangkaian STM32)");
  Serial.println("   No divider: 1.0 (langsung)");
  Serial.println("   R1=1kΩ, R2=4kΩ: 0.8");
  Serial.println("   R1=1kΩ, R2=1kΩ: 0.5");
}

void showCurrentCalibrationInfo() {
  Serial.println("📊 INFO KALIBRASI SENSOR ARUS:");
  Serial.println("================================");
  Serial.print("🔋 Tegangan saat 0A: "); Serial.print(current_zero_voltage, 4); Serial.println("V");
  Serial.print("📏 Sensitivitas: "); Serial.print(current_sensitivity, 3); Serial.println("V/A");
  Serial.print("🔧 Voltage Divider: "); Serial.print(current_divider_ratio, 3); Serial.println();
  Serial.print("🎯 Threshold: "); Serial.print(current_zero_threshold, 2); Serial.println("A");
  Serial.print("✅ Status kalibrasi: "); Serial.println(current_calibrated ? "SELESAI" : "BELUM");
  Serial.println("================================");
  float theoretical_zero = 2.5 * current_divider_ratio;
  Serial.print("📐 Teoritis 0A: "); Serial.print(theoretical_zero, 3); Serial.println("V");
  if (!current_calibrated) {
    Serial.println("💡 Ketik 'cal' untuk melakukan kalibrasi");
  }
}

