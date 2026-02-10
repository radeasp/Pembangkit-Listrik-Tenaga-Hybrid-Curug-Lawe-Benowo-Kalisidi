#include "pid_controller.h"
float setpoint = 15;                 
float kp = 4.5, ki = 0.015, kd = 0.017;  
float previous_error = 0;
float integral = 0;
unsigned long last_time = 0;

int pwm_output = 0;
void pidControl(float measured_voltage, unsigned long current_time) {
  float dt = (current_time - last_time) / 1000.0;  
  if (dt >= 0.01) {  
    float error = setpoint - measured_voltage;
    float proportional = kp * error;
    integral += error * dt;
    integral = constrain(integral, -100, 100);
    float integral_term = ki * integral;
    float derivative = (error - previous_error) / dt;
    float derivative_term = kd * derivative;
    float pid_output = proportional + integral_term + derivative_term;
    pid_output = -pid_output;
    pwm_output = constrain(pid_output, 0, 255);
    analogWrite(PWM_PIN, pwm_output);
    previous_error = error;
    last_time = current_time;
  }
}

void resetPIDParameters() {
  setpoint = 14.4;
  kp = 1.0;
  ki = 0.1;
  kd = 0.05;
  previous_error = 0;
  integral = 0;
  pwm_output = 0;
  analogWrite(PWM_PIN, 0);
}

void updatePIDParameters(float new_setpoint, float new_kp, float new_ki, float new_kd) {
  setpoint = new_setpoint;
  kp = new_kp;
  ki = new_ki;
  kd = new_kd;
  integral = 0;
}

