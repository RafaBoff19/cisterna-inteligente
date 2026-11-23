/*
 * ============================================================
 *  TESTE DE COMPONENTES — Cisterna Inteligente
 *  Use este programa durante a MONTAGEM (Aula 4).
 *  Depois que tudo funcionar, grave o firmware final (cisterna.ino).
 * ============================================================
 *
 *  O que ele faz:
 *   1. Ao ligar, testa cada atuador sozinho e escreve no Monitor Serial
 *      o que você deveria estar vendo/ouvindo.
 *   2. Depois mostra os sensores em tempo real, em português.
 *   3. Aceita comandos de UMA letra no Monitor Serial:
 *        v = liga/desliga LED verde      a = liga/desliga LED amarelo
 *        r = liga/desliga LED vermelho   s = abre/fecha o servo
 *        b = bipe no buzzer              t = repete o autoteste
 *        h = mostra a ajuda
 *
 *  Monitor Serial: 9600 baud (qualquer opção de fim de linha serve).
 *  Ligações: as mesmas do firmware final (veja o guia de montagem).
 */

#include <Servo.h>

const int PINO_NIVEL = A0;
const int PINO_CHUVA = 2;
const int PINO_SERVO = 9;
const int PINO_LED_VERDE = 5;
const int PINO_LED_AMARELO = 6;
const int PINO_LED_VERMELHO = 7;
const int PINO_BUZZER = 8;

Servo servo;
bool servoAberto = false;
int ultimoPercentual = -100;
int ultimoBotao = -1;
unsigned long ultimoRelatorio = 0;

void ajuda();
void autoteste();
void alternarLed(int pino, const char *nome);
void mostrarSensores(bool forcar);

void setup() {
  Serial.begin(9600);
  pinMode(PINO_CHUVA, INPUT_PULLUP);
  pinMode(PINO_LED_VERDE, OUTPUT);
  pinMode(PINO_LED_AMARELO, OUTPUT);
  pinMode(PINO_LED_VERMELHO, OUTPUT);
  pinMode(PINO_BUZZER, OUTPUT);
  servo.attach(PINO_SERVO);
  servo.write(0);

  delay(500);
  Serial.println();
  Serial.println(F("=========================================="));
  Serial.println(F("  TESTE DE COMPONENTES - Cisterna Inteligente"));
  Serial.println(F("=========================================="));
  autoteste();
  ajuda();
}

void loop() {
  // Comandos de uma letra
  while (Serial.available() > 0) {
    char c = Serial.read();
    switch (c) {
      case 'v': case 'V': alternarLed(PINO_LED_VERDE, "verde"); break;
      case 'a': case 'A': alternarLed(PINO_LED_AMARELO, "amarelo"); break;
      case 'r': case 'R': alternarLed(PINO_LED_VERMELHO, "vermelho"); break;
      case 's': case 'S':
        servoAberto = !servoAberto;
        servo.write(servoAberto ? 90 : 0);
        Serial.println(servoAberto ? F(">> Servo em 90 graus (valvula ABERTA)")
                                   : F(">> Servo em 0 graus (valvula FECHADA)"));
        break;
      case 'b': case 'B':
        tone(PINO_BUZZER, 2000, 300);
        Serial.println(F(">> Bipe! (se nao ouviu, confira o + do buzzer no pino 8)"));
        break;
      case 't': case 'T': autoteste(); break;
      case 'h': case 'H': ajuda(); break;
      default: break;  // ignora Enter, espacos, etc.
    }
  }

  // Sensores: mostra quando algo muda, e um resumo a cada 3 s
  mostrarSensores(millis() - ultimoRelatorio > 3000);
  delay(50);
}

void mostrarSensores(bool forcar) {
  int bruto = analogRead(PINO_NIVEL);
  int pct = map(bruto, 0, 1023, 0, 100);
  int botao = digitalRead(PINO_CHUVA);

  if (botao != ultimoBotao && ultimoBotao != -1) {
    Serial.println(botao == LOW ? F(">> BOTAO APERTADO (no programa final isso liga/desliga a chuva)")
                                : F(">> Botao solto"));
  }

  bool mudouNivel = abs(pct - ultimoPercentual) >= 3;
  if (mudouNivel || forcar) {
    Serial.print(F("Potenciometro: "));
    Serial.print(bruto);
    Serial.print(F(" de 1023  ->  nivel "));
    Serial.print(pct);
    Serial.print(F("%   |   Botao: "));
    Serial.println(botao == LOW ? F("apertado") : F("solto"));
    ultimoPercentual = pct;
    ultimoRelatorio = millis();
  }
  ultimoBotao = botao;
}

void alternarLed(int pino, const char *nome) {
  bool ligado = !digitalRead(pino);
  digitalWrite(pino, ligado);
  Serial.print(F(">> LED "));
  Serial.print(nome);
  Serial.println(ligado ? F(" LIGADO") : F(" desligado"));
}

void passo(const char *texto) {
  Serial.print(F("  - "));
  Serial.println(texto);
}

void autoteste() {
  Serial.println();
  Serial.println(F("AUTOTESTE - observe a protoboard:"));

  passo("LED VERDE aceso por 1 s (pino 5)");
  digitalWrite(PINO_LED_VERDE, HIGH); delay(1000); digitalWrite(PINO_LED_VERDE, LOW);

  passo("LED AMARELO aceso por 1 s (pino 6)");
  digitalWrite(PINO_LED_AMARELO, HIGH); delay(1000); digitalWrite(PINO_LED_AMARELO, LOW);

  passo("LED VERMELHO aceso por 1 s (pino 7)");
  digitalWrite(PINO_LED_VERMELHO, HIGH); delay(1000); digitalWrite(PINO_LED_VERMELHO, LOW);

  passo("BUZZER: um bipe (pino 8)");
  tone(PINO_BUZZER, 2000, 300); delay(700);

  passo("SERVO: vai para 90 graus e volta para 0 (pino 9)");
  servo.write(90); delay(1000); servo.write(0); delay(800);
  servoAberto = false;

  Serial.println(F("Autoteste concluido. Algo nao aconteceu? Confira a ligacao daquele pino."));
  Serial.println(F("Agora gire o potenciometro e aperte o botao:"));
  Serial.println();
}

void ajuda() {
  Serial.println(F("Comandos (digite a letra e Enter):"));
  Serial.println(F("  v / a / r = liga/desliga LED verde / amarelo / vermelho"));
  Serial.println(F("  s = abre/fecha servo   b = bipe   t = repetir autoteste   h = ajuda"));
  Serial.println();
}
