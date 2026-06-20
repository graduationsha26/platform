#include <ESP32Servo.h>
#include <SPI.h>

// --- Pins ---
const int BRUSHLESS_PIN = 14;
const int SERVO_PIN = 12;
const int CS_PIN = 5;

// --- MPU6500 Registers ---
#define PWR_MGMT_1        0x6B
#define GYRO_YOUT_H       0x45
#define SIGNAL_PATH_RESET 0x68

// --- Objects ---
Servo brushlessMotor;
Servo stabilizerServo;

// --- Time ---
unsigned long lastTime;

// --- Velocity PID Tuning ---
// Start with a small Kp. Ki and Kd are 0 for initial tuning.
// We are dealing with fast-changing velocity now, not slow angles.
float Kp = 1.2; 
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

  // Motors Setup
  brushlessMotor.attach(BRUSHLESS_PIN, 1000, 2000);
  stabilizerServo.attach(SERVO_PIN, 500, 2500);

  // Center the servo initially
  stabilizerServo.writeMicroseconds(1500);

  // ESC Arming Sequence
  Serial.println("Arming ESC... Keep hands clear!");
  brushlessMotor.writeMicroseconds(1000);
  
  // A full 5-second delay to guarantee the ESC unlocks
  delay(5000); 

  // Start the flywheel at a low, constant speed
  // This provides the gyroscopic anchor without over-speeding
  Serial.println("Starting Flywheel...");
  brushlessMotor.writeMicroseconds(1080); 

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

  // ===== 3. Actuation (Servo Only) =====
  // Base center is 1500µs. Subtract the output to apply counter-force.
  // The multiplier (e.g., 2.0) maps the PID output intensity to servo microseconds.
  // If the servo moves the wrong way and makes the tremor worse, change the minus sign to a plus.
  int servoPos = 1500 - (int)(output * 2.5); 

  // Safety constraint: keep the servo from breaking its physical limits
  servoPos = constrain(servoPos, 1100, 1900);
  stabilizerServo.writeMicroseconds(servoPos);

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
    Serial.print(" | Servo Pos: ");
    Serial.println(servoPos);
  }
}