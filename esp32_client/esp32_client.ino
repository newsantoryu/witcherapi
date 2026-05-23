/*
 * Cyber-Visceral Link ESP32 Client
 * Minimal WebSocket client for ESP32 hardware
 * 
 * Hardware requirements:
 * - ESP32 board
 * - LED (GPIO 2) or PWM output for motors/vibration
 * - Button (GPIO 0) for panic button input
 */

#include <WiFi.h>
#include <WebSocketsClient.h>

// Configuration
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* WS_HOST = "192.168.1.100";  // Change to your API server IP
const int WS_PORT = 8000;
const char* WS_PATH = "/ws";

// Hardware pins
const int LED_PIN = 2;        // Built-in LED
const int BUTTON_PIN = 0;     // Boot button
const int MOTOR_PIN = 4;      // PWM output for vibration motor

// Timing
const unsigned long HEARTBEAT_INTERVAL = 30000;  // 30 seconds
const unsigned long RECONNECT_DELAY = 5000;      // 5 seconds

// WebSocket client
WebSocketsClient webSocket;

// State
unsigned long lastHeartbeat = 0;
unsigned long lastReconnectAttempt = 0;
bool isConnected = false;

// Event handlers
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
  switch(type) {
    case WStype_DISCONNECTED:
      Serial.println("[WS] Disconnected");
      isConnected = false;
      digitalWrite(LED_PIN, LOW);
      break;
      
    case WStype_CONNECTED:
      Serial.println("[WS] Connected");
      isConnected = true;
      digitalWrite(LED_PIN, HIGH);
      lastHeartbeat = millis();
      break;
      
    case WStype_TEXT:
      Serial.printf("[WS] Received: %s\n", payload);
      handleOutputMessage((char*)payload);
      break;
      
    case WStype_ERROR:
      Serial.println("[WS] Error");
      break;
  }
}

void handleOutputMessage(char* message) {
  // Parse protocol message: OUTPUT:EVENT
  // Example: OUTPUT:GORE_FLASH
  
  if (strncmp(message, "OUTPUT:", 7) == 0) {
    char* event = message + 7;
    
    Serial.printf("[OUTPUT] Event: %s\n", event);
    
    // Handle different events
    if (strcmp(event, "GORE_FLASH") == 0) {
      triggerGoreFlash();
    } else if (strcmp(event, "DAMAGE_PULSE") == 0) {
      triggerDamagePulse();
    } else if (strcmp(event, "KILL_STREAK") == 0) {
      triggerKillStreak();
    } else if (strcmp(event, "COMBO_HIT") == 0) {
      triggerComboHit();
    } else if (strcmp(event, "CRITICAL_HIT") == 0) {
      triggerCriticalHit();
    } else if (strcmp(event, "ADRENALINE") == 0) {
      triggerAdrenaline();
    } else if (strcmp(event, "LOW_HEALTH") == 0) {
      triggerLowHealth();
    } else if (strcmp(event, "DEATH") == 0) {
      triggerDeath();
    } else if (strcmp(event, "HEARTBEAT:PING") == 0) {
      // Respond to heartbeat
      webSocket.sendTXT("HEARTBEAT:PONG");
      lastHeartbeat = millis();
    }
  }
}

// Hardware effect functions
void triggerGoreFlash() {
  // Flash LED rapidly
  for (int i = 0; i < 5; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(50);
    digitalWrite(LED_PIN, LOW);
    delay(50);
  }
  // Vibration motor pulse
  analogWrite(MOTOR_PIN, 255);
  delay(200);
  analogWrite(MOTOR_PIN, 0);
}

void triggerDamagePulse() {
  // Single pulse
  digitalWrite(LED_PIN, HIGH);
  analogWrite(MOTOR_PIN, 200);
  delay(100);
  digitalWrite(LED_PIN, LOW);
  analogWrite(MOTOR_PIN, 0);
}

void triggerKillStreak() {
  // Triple pulse
  for (int i = 0; i < 3; i++) {
    digitalWrite(LED_PIN, HIGH);
    analogWrite(MOTOR_PIN, 255);
    delay(100);
    digitalWrite(LED_PIN, LOW);
    analogWrite(MOTOR_PIN, 0);
    delay(100);
  }
}

void triggerComboHit() {
  // Quick flash
  digitalWrite(LED_PIN, HIGH);
  delay(50);
  digitalWrite(LED_PIN, LOW);
}

void triggerCriticalHit() {
  // Double flash
  digitalWrite(LED_PIN, HIGH);
  analogWrite(MOTOR_PIN, 255);
  delay(150);
  digitalWrite(LED_PIN, LOW);
  analogWrite(MOTOR_PIN, 0);
  delay(50);
  digitalWrite(LED_PIN, HIGH);
  delay(100);
  digitalWrite(LED_PIN, LOW);
}

void triggerAdrenaline() {
  // Continuous vibration for 2 seconds
  analogWrite(MOTOR_PIN, 180);
  digitalWrite(LED_PIN, HIGH);
  delay(2000);
  analogWrite(MOTOR_PIN, 0);
  digitalWrite(LED_PIN, LOW);
}

void triggerLowHealth() {
  // Slow pulsing
  for (int i = 0; i < 3; i++) {
    digitalWrite(LED_PIN, HIGH);
    analogWrite(MOTOR_PIN, 100);
    delay(500);
    digitalWrite(LED_PIN, LOW);
    analogWrite(MOTOR_PIN, 0);
    delay(500);
  }
}

void triggerDeath() {
  // Long fade out
  for (int i = 255; i >= 0; i -= 5) {
    analogWrite(MOTOR_PIN, i);
    analogWrite(LED_PIN, i);
    delay(50);
  }
  analogWrite(MOTOR_PIN, 0);
  digitalWrite(LED_PIN, LOW);
}

// Input handling
void checkButton() {
  static unsigned long lastDebounce = 0;
  static int lastButtonState = HIGH;
  static int buttonState;
  
  int reading = digitalRead(BUTTON_PIN);
  
  if (reading != lastButtonState) {
    lastDebounce = millis();
  }
  
  if ((millis() - lastDebounce) > 50) {
    if (reading != buttonState) {
      buttonState = reading;
      
      if (buttonState == LOW) {
        // Button pressed (active low)
        sendInput("PANIC_BUTTON");
      }
    }
  }
  
  lastButtonState = reading;
}

void sendInput(const char* event) {
  if (isConnected) {
    char message[64];
    snprintf(message, sizeof(message), "INPUT:%s", event);
    webSocket.sendTXT(message);
    Serial.printf("[INPUT] Sent: %s\n", message);
  } else {
    Serial.println("[INPUT] Not connected, cannot send");
  }
}

void setup() {
  Serial.begin(115200);
  Serial.println("\n[Cyber-Visceral Link] ESP32 Client Starting");
  
  // Initialize pins
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(MOTOR_PIN, OUTPUT);
  
  digitalWrite(LED_PIN, LOW);
  analogWrite(MOTOR_PIN, 0);
  
  // Connect to WiFi
  Serial.println("[WiFi] Connecting...");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\n[WiFi] Connected");
  Serial.print("[WiFi] IP: ");
  Serial.println(WiFi.localIP());
  
  // Setup WebSocket
  webSocket.begin(WS_HOST, WS_PORT, WS_PATH);
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(RECONNECT_DELAY);
  
  Serial.println("[WS] Setup complete");
}

void loop() {
  webSocket.loop();
  
  // Check button input
  checkButton();
  
  // Send periodic heartbeat if connected
  if (isConnected && (millis() - lastHeartbeat > HEARTBEAT_INTERVAL)) {
    webSocket.sendTXT("HEARTBEAT:PONG");
    lastHeartbeat = millis();
    Serial.println("[HEARTBEAT] Sent");
  }
  
  delay(10);
}
