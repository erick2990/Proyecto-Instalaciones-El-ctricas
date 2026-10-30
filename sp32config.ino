#include <WiFi.h>
#include <WebServer.h>

const char* ssid_ap = "ESP32_Luminarias";
const char* pass_ap = "control1234";

WebServer server(80);

const int FOCO_1 = 20;
const int FOCO_2 = 21;
const int FOCO_3 = 47;
const int FOCO_4 = 48;
const int FOCO_5 = 45;

#define ENCENDER LOW
#define APAGAR   HIGH

void apagarTodo() {
  digitalWrite(FOCO_1, APAGAR);
  digitalWrite(FOCO_2, APAGAR);
  digitalWrite(FOCO_3, APAGAR);
  digitalWrite(FOCO_4, APAGAR);
  digitalWrite(FOCO_5, APAGAR);
}

void aplicarGesto(int dedos) {
  switch (dedos) {
    case 0: 
      apagarTodo();
      break;

    case 1:
      digitalWrite(FOCO_1, ENCENDER);
      digitalWrite(FOCO_2, APAGAR);
      digitalWrite(FOCO_3, APAGAR);
      digitalWrite(FOCO_4, APAGAR);
      digitalWrite(FOCO_5, APAGAR);
      break;

    case 2: 
      digitalWrite(FOCO_1, ENCENDER);
      digitalWrite(FOCO_2, ENCENDER);
      digitalWrite(FOCO_3, APAGAR);
      digitalWrite(FOCO_4, APAGAR);
      digitalWrite(FOCO_5, APAGAR);
      break;

    case 3: 
      digitalWrite(FOCO_1, ENCENDER);
      digitalWrite(FOCO_2, ENCENDER);
      digitalWrite(FOCO_3, ENCENDER);
      digitalWrite(FOCO_4, APAGAR);
      digitalWrite(FOCO_5, APAGAR);
      break;

    case 4: 
      digitalWrite(FOCO_1, ENCENDER);
      digitalWrite(FOCO_2, ENCENDER);
      digitalWrite(FOCO_3, ENCENDER);
      digitalWrite(FOCO_4, ENCENDER);
      digitalWrite(FOCO_5, APAGAR);
      break;

    case 5: 
      digitalWrite(FOCO_1, ENCENDER);
      digitalWrite(FOCO_2, ENCENDER);
      digitalWrite(FOCO_3, ENCENDER);
      digitalWrite(FOCO_4, ENCENDER);
      digitalWrite(FOCO_5, ENCENDER);
      break;
  }
  Serial.printf("[ACCION] Gesto de %d dedo(s) aplicado\n", dedos);
}

void handleControl() {
  if (server.hasArg("count")) {
    int dedos = server.arg("count").toInt();
    if (dedos >= 0 && dedos <= 5) {
      aplicarGesto(dedos);
      server.send(200, "text/plain", "OK");
      return;
    }
  }

  if (server.hasArg("relay") && server.hasArg("state")) {
    String relayArg = server.arg("relay");
    int state = server.arg("state").toInt();

    if (relayArg == "all" || state == 0) {
      aplicarGesto(0);
      server.send(200, "text/plain", "OK");
      return;
    }

    int idx = relayArg.toInt();
    if (idx >= 0 && idx < 5) {
      aplicarGesto(idx + 1);
      server.send(200, "text/plain", "OK");
      return;
    }
  }

  server.send(400, "text/plain", "Bad Request");
}

void setup() {
  Serial.begin(115200);

  apagarTodo();

  pinMode(FOCO_1, OUTPUT);
  pinMode(FOCO_2, OUTPUT);
  pinMode(FOCO_3, OUTPUT);
  pinMode(FOCO_4, OUTPUT);
  pinMode(FOCO_5, OUTPUT);

  apagarTodo();

  WiFi.softAP(ssid_ap, pass_ap);

  Serial.println("\n--- ESP32-S3 INICIADO ---");
  Serial.print("Red Wi-Fi creada: ");
  Serial.println(ssid_ap);
  Serial.print("Direccion IP fija: ");
  Serial.println(WiFi.softAPIP());

  server.on("/control", HTTP_GET, handleControl);
  server.begin();
}

void loop() {
  server.handleClient();

  if (Serial.available() > 0) {
    char comando = Serial.read();
    if (comando >= '0' && comando <= '5') {
      aplicarGesto(comando - '0');
    }
  }
}
