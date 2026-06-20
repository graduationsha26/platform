#include <Arduino.h>
#include <SPI.h>

// --- Pins ---
const int BRUSHLESS_PIN = 14;
const int SERVO_PIN = 12;
const int CS_PIN = 5;

// --- MPU6500 Registers ---
#define PWR_MGMT_1        0x6B
#define GYRO_YOUT_H       0x45
#define SIGNAL_PATH_RESET 0x68

// ================= LEDC (raw ESP32 core 2.x PWM) =================
#define LEDC_FREQ_HZ        50
#define LEDC_RES_BITS       16
#define PWM_PERIOD_US       20000.0f   // 1e6 / 50 Hz
#define LEDC_MAX_COUNT      65536.0f   // 2^16 counts per full period (matches servo convention)

#define LEDC_ESC_CHANNEL    0          // timer 0, pin 14
#define LEDC_GIMBAL_CHANNEL 2          // timer 1, pin 12

// --- Gimbal geometry / trim ---
#define GIMBAL_CENTER_US    1500
#define CMG_GIMBAL_TRIM_US  0          // shift mechanical neutral; keep small (±100 µs)
#define GIMBAL_SPAN_US      600        // ± travel for full ±1.0 torque
#define GIMBAL_MIN_US       900
#define GIMBAL_MAX_US       2100

// --- ESC throttle (µs) ---
#define ESC_ARM_US          1000       // idle / arming pulse
#define ESC_RUN_US          1080       // constant flywheel speed

// --- Torque normalization (preserves legacy 2.5 µs/unit × 400 µs span; PID math unchanged) ---
#define TORQUE_FULL_SCALE   160.0f

// --- Slew rate limiter ---
#define TORQUE_SLEW_PER_S   40.0f       // 4.0 for full -1→+1 swing in ~0.5 s
#define MAX_DT_S            0.05f      // clamp loop dt (protects slew + PID derivative)

// --- Time ---
unsigned long lastTime;

// --- Velocity PID Tuning ---
// Start with a small Kp. Ki and Kd are 0 for initial tuning.
// We are dealing with fast-changing velocity now, not slow angles.
float Kp = 2.0;
float Ki = 0.0;
float Kd = 0.05;

// The target is absolute stillness (0 degrees per second)
float targetVelocity = 0.0;
float error = 0, lastError = 0, integral = 0;

// ================= SPI Helpers =================
uint8_t readRegister(uint8_t reg) {
  uint8_t value;
  digitalWrite(CS_PIN, LOW);
  SPI.transfer(reg | 0x80);
  value = SPI.transfer(0x00);
  digitalWrite(CS_PIN, HIGH);
  return value;
}

void writeRegister(uint8_t reg, uint8_t val) {
  digitalWrite(CS_PIN, LOW);
  SPI.transfer(reg & 0x7F);
  SPI.transfer(val);
  digitalWrite(CS_PIN, HIGH);
}

// ================= Actuation Helpers =================
// Float-precise microseconds → 16-bit LEDC duty (no integer truncation until the final round)
uint32_t microsToDuty(float us) {
  return (uint32_t)lroundf(us / PWM_PERIOD_US * LEDC_MAX_COUNT);
}

// Normalized torque [-1,1] → microseconds, with center trim and physical-limit clamp
float torqueToMicros(float torque) {
  torque = constrain(torque, -1.0f, 1.0f);
  float us = (float)(GIMBAL_CENTER_US + CMG_GIMBAL_TRIM_US) + torque * (float)GIMBAL_SPAN_US;
  return constrain(us, (float)GIMBAL_MIN_US, (float)GIMBAL_MAX_US);
}

// ================= Setup =================
void setup() {
  Serial.begin(115200);

  pinMode(CS_PIN, OUTPUT);
  digitalWrite(CS_PIN, HIGH);

  // SPI init
  SPI.begin(18, 19, 23, 5);
  delay(100);

  // MPU6500 init
  writeRegister(SIGNAL_PATH_RESET, 0x07);
  delay(100);
  writeRegister(PWR_MGMT_1, 0x01);
  delay(100);

  // ===== Motors Setup (raw LEDC) =====
  // ESC first: claim channel 0 / timer 0, then idle immediately so the pin
  // doesn't sit at 0% duty.
  ledcSetup(LEDC_ESC_CHANNEL, LEDC_FREQ_HZ, LEDC_RES_BITS);
  ledcAttachPin(BRUSHLESS_PIN, LEDC_ESC_CHANNEL);
  ledcWrite(LEDC_ESC_CHANNEL, microsToDuty(ESC_ARM_US));

  // Gimbal: channel 2 / timer 1, centered immediately so it stays neutral
  // during ESC arming instead of slamming to a hard-over position.
  ledcSetup(LEDC_GIMBAL_CHANNEL, LEDC_FREQ_HZ, LEDC_RES_BITS);
  ledcAttachPin(SERVO_PIN, LEDC_GIMBAL_CHANNEL);
  ledcWrite(LEDC_GIMBAL_CHANNEL, microsToDuty(torqueToMicros(0.0f)));

  // ESC Arming Sequence
  Serial.println("Arming ESC... Keep hands clear!");

  // A full 5-second delay to guarantee the ESC unlocks
  delay(5000);

  // Start the flywheel at a low, constant speed
  // This provides the gyroscopic anchor without over-speeding
  Serial.println("Starting Flywheel...");
  ledcWrite(LEDC_ESC_CHANNEL, microsToDuty(ESC_RUN_US));

  lastTime = micros();
}

// ================= Loop =================
void loop() {
  // ===== 1. Read Sensor (Gyroscope Y-Axis ONLY) =====
  // We only need rotational velocity to detect a tremor
  int16_t rawGyroY  = (readRegister(0x45) << 8) | readRegister(0x46);

  // Calculate delta time
  unsigned long currentTime = micros();
  float dt = (currentTime - lastTime) / 1000000.0;
  lastTime = currentTime;

  // Clamp dt to guard the slew limiter and the PID derivative against a
  // first-iteration / stalled-read spike.
  if (dt > MAX_DT_S) dt = MAX_DT_S;

  // Convert raw gyro to Degrees Per Second (°/s)
  // 131.0 is the scale factor for the default ±250 dps range
  float gyroRateY = rawGyroY / 131.0;

  // ===== 2. PID Calculation =====
  error = targetVelocity - gyroRateY;

  // Anti-windup (Clamped integral to prevent runaway)
  integral += error * dt;
  integral = constrain(integral, -100, 100);

  float derivative = (error - lastError) / dt;
  float output = (Kp * error) + (Ki * integral) + (Kd * derivative);

  lastError = error;

  // ===== 3. Actuation (Gimbal Servo via raw LEDC) =====
  // Normalize PID output to torque [-1,1]; sign preserves the legacy
  // "1500 - output" counter-force direction.
  float torqueCmd = constrain(-output / TORQUE_FULL_SCALE, -1.0f, 1.0f);

  // Slew rate limiter (applied to torque, before PWM mapping) to cap current
  // ramp and prevent brownouts.
  static float currentTorque = 0.0f;
  float maxStep = TORQUE_SLEW_PER_S * dt;
  currentTorque += constrain(torqueCmd - currentTorque, -maxStep, maxStep);

  // Float mapping → microseconds (with trim) → 16-bit LEDC duty
  float gimbalUs = torqueToMicros(currentTorque);
  ledcWrite(LEDC_GIMBAL_CHANNEL, microsToDuty(gimbalUs));

  // Note: Brushless motor throttle is NOT updated here. It stays constant.

  // ===== Debug =====
  static unsigned long debugTimer = 0;
  if (millis() - debugTimer > 100) {
    debugTimer = millis();
    Serial.print("Velocity (°/s): ");
    Serial.print(gyroRateY);
    Serial.print(" | Error: ");
    Serial.print(error);
    Serial.print(" | Output: ");
    Serial.print(output);
    Serial.print(" | Gimbal (µs): ");
    Serial.println(gimbalUs);
  }
}
