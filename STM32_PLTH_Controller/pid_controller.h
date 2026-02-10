#ifndef PID_CONTROLLER_H
#define PID_CONTROLLER_H
#include "config.h"
extern float setpoint;
extern float kp, ki, kd;
extern float previous_error;
extern float integral;
extern unsigned long last_time;
extern int pwm_output;

void pidControl(float measured_voltage, unsigned long current_time);
void resetPIDParameters();
void updatePIDParameters(float new_setpoint, float new_kp, float new_ki, float new_kd);
#endif

