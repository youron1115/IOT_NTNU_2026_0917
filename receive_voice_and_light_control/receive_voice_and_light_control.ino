// ============================
// AMB82-mini LED 控制程式
// ============================

#define BAUD_RATE 115200

// 板載 LED 腳位（LED_G 為綠燈、LED_B 為藍燈）
#define BLUE_LED  LED_B
#define GREEN_LED LED_G

#define LED_LEFT  BLUE_LED
#define LED_RIGHT GREEN_LED

enum LedMode {
  MODE_OFF,
  MODE_LEFT,
  MODE_RIGHT,
  MODE_BLINK
};

LedMode currentMode = MODE_OFF;
unsigned long lastBlinkTime = 0;
bool blinkState = false;

void updateLeds(LedMode mode) {
  currentMode = mode;

  if (mode == MODE_LEFT) {
    digitalWrite(LED_LEFT, HIGH);
    digitalWrite(LED_RIGHT, LOW);
  } else if (mode == MODE_RIGHT) {
    digitalWrite(LED_LEFT, LOW);
    digitalWrite(LED_RIGHT, HIGH);
  } else if (mode == MODE_OFF) {
    digitalWrite(LED_LEFT, LOW);
    digitalWrite(LED_RIGHT, LOW);
  }
}

void blinkLeds() {
  digitalWrite(BLUE_LED, LOW);
  digitalWrite(GREEN_LED, LOW);
  delay(1000);

  digitalWrite(BLUE_LED, HIGH);
  delay(2000);
  digitalWrite(BLUE_LED, LOW);

  digitalWrite(GREEN_LED, HIGH);
  delay(2000);
  digitalWrite(GREEN_LED, LOW);

  digitalWrite(BLUE_LED, HIGH);
  delay(2000);
  digitalWrite(BLUE_LED, LOW);

  digitalWrite(GREEN_LED, HIGH);
  delay(2000);
  digitalWrite(GREEN_LED, LOW);

  Serial.println("LED Blink");

  currentMode = MODE_OFF;
}

void setup() {
  Serial.begin(BAUD_RATE);

  pinMode(LED_LEFT, OUTPUT);
  pinMode(LED_RIGHT, OUTPUT);
  updateLeds(MODE_OFF);

  // 發送開機就緒訊號
  Serial.println("AMB82_READY");
}

void loop() {
  // 1. 處理閃爍模式
  if (currentMode == MODE_BLINK) {
    blinkLeds();
  }

  // 2. 接收來自 Python 的指令
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd == "LEFT") {
      updateLeds(MODE_LEFT);
    } else if (cmd == "RIGHT") {
      updateLeds(MODE_RIGHT);
    } else if (cmd == "OFF") {
      updateLeds(MODE_OFF);
    } else if (cmd == "Blink") {
      currentMode = MODE_BLINK;
    }
  }
}