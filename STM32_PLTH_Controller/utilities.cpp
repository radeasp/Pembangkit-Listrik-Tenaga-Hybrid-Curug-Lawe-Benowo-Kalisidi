#include "utilities.h"
#include "pid_controller.h"
bool usb_connected = false;
unsigned long last_data_send = 0;
unsigned long last_serial_output = 0;
unsigned long last_led_toggle = 0;

bool led_state = false;
unsigned long led_blink_interval = 3000;  
unsigned long last_watchdog_reset = 0;
unsigned long watchdog_timeout = 15000;  
void printWelcomeMessage() {
  Serial.println("========== STM32 PLTH Controller ==========");
  Serial.println("Mode: JSON Communication (Serial Monitor OFF)");
  if (ads_available) {
    Serial.println("ADC: ADS1115 (16-bit External) - ACTIVE");
  } else {
    Serial.println("ADC: ADS1115 NOT FOUND! Check connections!");
  }
  Serial.println("Ketik 'm' untuk toggle serial monitor");
  Serial.println("Ketik 'h' untuk menu bantuan");
  Serial.println("==========================================");
}

bool debug_mode = false;  
bool serial_monitor_active = false;  
bool recording_active = false;
unsigned long recording_start_time = 0;
unsigned long recording_duration = 5000;  
unsigned long last_recording_sample = 0;
unsigned long recording_sample_interval = 100;  
String recording_type = "";  
bool show_menu = false;
bool plotter_mode = false;  
bool quick_view_mode = false;  
bool command_mode = false;
String command_buffer = "";
void initializePins() {
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(PWM_PIN, OUTPUT);
  analogWriteFrequency(1000);  
  analogWrite(PWM_PIN, 0);     
  digitalWrite(LED_BUILTIN, HIGH);
  Serial.println("Starting I2C initialization...");
  Wire.begin();
  delay(100);  
  initializeADS1115();
  Serial.println("Pin initialization complete");
}

void initializeSerial() {
  Serial.begin(115200);
}

void initializeTiming() {
  last_time = millis();
  last_data_send = millis();
  last_serial_output = millis();
  last_led_toggle = millis();
  last_recording_sample = millis();
  last_watchdog_reset = millis();  
}

void resetWatchdog() {
  last_watchdog_reset = millis();
}

void checkSystemStability() {
  unsigned long current_time = millis();
  if (current_time - last_watchdog_reset > watchdog_timeout) {
    Serial.println("CRITICAL: System crash/hang detected!");
    Serial.print("System unresponsive for: ");
    Serial.print((current_time - last_watchdog_reset)/1000.0);
    Serial.println(" seconds");
    Serial.println("Symptoms: Loop not executing, timestamp stuck, no serial output");
    analogWrite(PWM_PIN, 0);
    digitalWrite(LED_BUILTIN, LOW); 
    Serial.println("EMERGENCY: PWM output disabled for safety!");
    Serial.println("Attempting aggressive system recovery...");
    Wire.end();
    delay(1000); 
    Wire.begin();
    Wire.setClock(50000); 
    delay(500);
    ads_available = false;
    initializeADS1115();
    resetWatchdog();
    Serial.println("Recovery attempt completed - PWM remains disabled until next successful reading");
    Serial.println("Manual reset may be required if problems persist");
  }
}

void checkUSBConnection() {
  #ifdef USBCON
  usb_connected = (bool)Serial;
  #else
    usb_connected = true;
  #endif
  if (!usb_connected) {
    led_blink_interval = 0;  
  } else {
    led_blink_interval = 3000;  
  }
}

void handleLEDIndicator(unsigned long current_time) {
  if (led_blink_interval == 0) {
    digitalWrite(LED_BUILTIN, HIGH);
  } else {
    if (current_time - last_led_toggle >= led_blink_interval) {
      led_state = !led_state;
      digitalWrite(LED_BUILTIN, led_state);
      last_led_toggle = current_time;
    }
  }
}

void handleSerialOutput(SensorData sensors, unsigned long current_time) {
  if (plotter_mode) {
    handleSerialPlotter(sensors, current_time);
  } else if (quick_view_mode) {
    handleQuickView(sensors, current_time);
  } else {
    handleSerialDebug(sensors, current_time);
  }
}

void handleSerialDebug(SensorData sensors, unsigned long current_time) {
  if (debug_mode && (current_time - last_serial_output >= 500)) {
  Serial.println("\n\n========================================");
  Serial.println("       STM32 PLTH CONTROLLER DATA");
  Serial.println("========================================");
    Serial.print("Timestamp: "); Serial.print(millis()/1000.0, 1); Serial.println(" s");
    Serial.print("ADC Status: "); 
    if (ads_available) {
      Serial.println("ADS1115 ACTIVE");
    } else {
      Serial.println("ADS1115 OFFLINE - ZERO VALUES");
    }
    Serial.print("Watchdog: "); Serial.print((millis() - last_watchdog_reset)/1000.0, 1); Serial.println(" s ago");
    Serial.print("PWM Output: "); Serial.print(pwm_output); Serial.print("/255 ("); Serial.print((pwm_output/255.0)*100, 1); Serial.println("%)");
    Serial.println("Note: Stuck detection = system crash (timestamp stuck), NOT sensor values");
    Serial.println();
    Serial.println("┌─ VOLTAGE MEASUREMENTS ─────────────────┐");
    Serial.print("│ Picohydro    : "); Serial.print(sensors.picohydro_voltage, 2); Serial.println(" V         │");
    Serial.println("└─────────────────────────────────────────┘");
    Serial.println();
    Serial.println("┌─ CURRENT MEASUREMENTS ──────────────────┐");
    Serial.print("│ Picohydro    : "); Serial.print(sensors.picohydro_current, 2); Serial.println(" A         │");
    Serial.print("│ Battery In   : "); Serial.print(sensors.battery_in_current, 2); Serial.println(" A         │");
    Serial.print("│ Battery Out  : "); Serial.print(sensors.battery_out_current, 2); Serial.println(" A         │");
    Serial.println("└─────────────────────────────────────────┘");
    Serial.println();
    Serial.println("┌─ PID CONTROLLER ────────────────────────┐");
    Serial.print("│ Setpoint     : "); Serial.print(setpoint, 2); Serial.println(" V         │");
    Serial.print("│ Error        : "); Serial.print(setpoint - sensors.picohydro_voltage, 2); Serial.println(" V         │");
    Serial.print("│ Kp = "); Serial.print(kp, 2); Serial.print("  Ki = "); Serial.print(ki, 3); Serial.print("  Kd = "); Serial.print(kd, 3); Serial.println(" │");
    Serial.println("└─────────────────────────────────────────┘");
    float pico_power = sensors.picohydro_voltage * sensors.picohydro_current;
    Serial.println();
    Serial.println("┌─ POWER CALCULATIONS ────────────────────┐");
    Serial.print("│ Picohydro    : "); Serial.print(pico_power, 1); Serial.println(" W         │");
    Serial.println("└─────────────────────────────────────────┘");
    last_serial_output = current_time;
  }
}

void handleSerialPlotter(SensorData sensors, unsigned long current_time) {
  if (serial_monitor_active && current_time - last_serial_output >= 100) { 
    Serial.print("PicoV:");
    Serial.print(sensors.picohydro_voltage);
    Serial.print(",PicoI:");
    Serial.print(sensors.picohydro_current);
    Serial.print(",BattInI:");
    Serial.print(sensors.battery_in_current);
    Serial.print(",BattOutI:");
    Serial.print(sensors.battery_out_current);
    Serial.print(",Setpoint:");
    Serial.print(setpoint);
    Serial.print(",PWM:");
    Serial.print(pwm_output);
    Serial.println();
    last_serial_output = current_time;
  }
}

void handleQuickView(SensorData sensors, unsigned long current_time) {
  if (current_time - last_serial_output >= 1000) {
    Serial.print("["); Serial.print(millis()/1000); Serial.print("s] ");
    Serial.print("PV:"); Serial.print(sensors.picohydro_voltage, 1); 
    Serial.print("V PI:"); Serial.print(sensors.picohydro_current, 1); 
    Serial.print("A PWM:"); Serial.print((pwm_output/255.0)*100, 0); 
    Serial.print("% SP:"); Serial.print(setpoint, 1); 
    Serial.print("V ERR:"); Serial.print(setpoint - sensors.picohydro_voltage, 1); 
    Serial.println("V");
    last_serial_output = current_time;
  }
}

void handleRecording(SensorData sensors, unsigned long current_time) {
  if (!recording_active) return;
  if (current_time - recording_start_time >= recording_duration) {
    stopRecording();
    return;
  }
  if (current_time - last_recording_sample >= recording_sample_interval) {
    if (recording_type == "ph") {
      Serial.print(current_time - recording_start_time);
      Serial.print(", ");
      Serial.print(sensors.picohydro_voltage, 3);
      Serial.print(", ");
      Serial.println(sensors.picohydro_current, 3);
    } else if (recording_type == "bt") {
      Serial.print(current_time - recording_start_time);
      Serial.print(", ");
      Serial.print(sensors.battery_in_current, 3);
      Serial.print(", ");
      Serial.println(sensors.battery_out_current, 3);
    } else if (recording_type == "pid") {
      Serial.print(current_time - recording_start_time);
      Serial.print(", ");
      Serial.print(sensors.picohydro_voltage, 3);
      Serial.print(", ");
      Serial.print(sensors.picohydro_current, 3);
      Serial.print(", ");
      Serial.println(pwm_output);
    }
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
  Serial.print("USB Connected: "); Serial.println(usb_connected ? "YES" : "NO");
  Serial.print("Recording: "); Serial.println(recording_active ? "ACTIVE" : "INACTIVE");
  if (recording_active) {
    Serial.print("Recording Type: "); 
    if (recording_type == "ph") {
      Serial.println("PICOHYDRO");
    } else if (recording_type == "bt") {
      Serial.println("BATTERY");
    }
    Serial.print("Recording Time Left: "); 
    Serial.print((recording_duration - (millis() - recording_start_time))/1000.0, 1);
    Serial.println(" seconds");
  }
  Serial.println("==================================");
}

void printPIDParameters() {
  Serial.println("\n========== PARAMETER PID ==========");
  Serial.print("Setpoint: "); Serial.print(setpoint, 3); Serial.println(" V");
  Serial.print("Kp: "); Serial.println(kp, 3);
  Serial.print("Ki: "); Serial.println(ki, 3);
  Serial.print("Kd: "); Serial.println(kd, 3);
  Serial.print("PWM Output: "); Serial.print(pwm_output); Serial.print("/255 ("); Serial.print((pwm_output/255.0)*100, 1); Serial.println("%)");
  Serial.println("==================================");
}

void startRecording(String type) {
  recording_active = true;
  recording_type = type;
  recording_start_time = millis();
  last_recording_sample = millis();
  if (type == "ph") {
    recording_sample_interval = 100;  
  } else if (type == "bt") {
    recording_sample_interval = 100;  
  } else if (type == "pid") {
    recording_sample_interval = 10;   
  }
  Serial.println("\n========== MULAI RECORDING ==========");
  Serial.print("Jenis: "); 
  if (type == "ph") {
    Serial.println("PICOHYDRO");
    Serial.println("Format: Time(ms), Voltage(V), Current(A)");
    Serial.print("Sampling: 100ms (akan menghasilkan "); 
    Serial.print((recording_duration/100), 0); 
    Serial.println(" data)");
  } else if (type == "bt") {
    Serial.println("BATTERY");
    Serial.println("Format: Time(ms), Battery_In_Current(A), Battery_Out_Current(A)");
    Serial.print("Sampling: 100ms (akan menghasilkan "); 
    Serial.print((recording_duration/100), 0); 
    Serial.println(" data)");
  } else if (type == "pid") {
    Serial.println("PID CONTROL");
    Serial.println("Format: Time(ms), Voltage(V), Current(A), PWM");
    Serial.print("Sampling: 10ms (akan menghasilkan "); 
    Serial.print((recording_duration/10), 0); 
    Serial.println(" data)");
  }
  Serial.print("Durasi: "); Serial.print(recording_duration/1000.0, 1); Serial.println(" detik");
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

