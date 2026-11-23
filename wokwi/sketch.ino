/*
 * ============================================================
 *  Cisterna Inteligente de Água da Chuva — Firmware do Arduino
 *  Hardware Architecture — ATITUS — Projeto Final G2
 *  Equipe: Rafael Boff e Wagner Segala
 * ============================================================
 *
 *  Papel do Arduino no sistema:
 *    - LER os sensores (potenciômetro = nível, botão = chuva)
 *    - ENVIAR as leituras para a Raspberry Pi pela Serial/USB
 *    - RECEBER comandos da Raspberry Pi e ACIONAR os atuadores
 *      (servo = válvula, LEDs = nível, buzzer = aviso)
 *    - MODO SEGURO: se ficar 5 s sem receber nada da Raspberry,
 *      fecha a válvula sozinho e pisca o LED amarelo.
 *
 *  Toda a decisão (quando abrir/fechar, qual LED acender) fica
 *  na Raspberry Pi. O Arduino só obedece.
 *
 *  Protocolo (texto, uma mensagem por linha, 9600 baud):
 *    Arduino  -> Raspberry : NIVEL:62;CHUVA:1        (a cada 1 s)
 *    Raspberry -> Arduino  : VALVULA:1 | VALVULA:0
 *                            LED:V | LED:A | LED:R
 *                            BUZZER:1
 *
 *  Ligações:
 *    Potenciômetro (pino do meio) -> A0   (pontas no 5V e GND)
 *    Botão                        -> D2 e GND (usa pull-up interno)
 *    Servo (sinal)                -> D9   (V+ no 5V, GND no GND)
 *    LED verde / amarelo / verm.  -> D5 / D6 / D7 (resistor 220 ohms)
 *    Buzzer                       -> D8 e GND
 */

#include <Servo.h>

// ---------------- Pinos ----------------
const int PINO_NIVEL    = A0;  // potenciômetro (simula a boia)
const int PINO_CHUVA    = 2;   // botão (simula o sensor de chuva)
const int PINO_SERVO    = 9;   // servo = válvula de entrada
const int PINO_LED_VERDE    = 5;
const int PINO_LED_AMARELO  = 6;
const int PINO_LED_VERMELHO = 7;
const int PINO_BUZZER   = 8;

// ---------------- Configurações ----------------
const unsigned long INTERVALO_ENVIO_MS   = 1000;  // envia leitura a cada 1 s
const unsigned long TIMEOUT_RASPBERRY_MS = 5000;  // sem comando por 5 s = modo seguro
const unsigned long DEBOUNCE_MS          = 50;    // filtro do botão
const int ANGULO_FECHADA = 0;    // posição do servo com a válvula fechada
const int ANGULO_ABERTA  = 90;   // posição do servo com a válvula aberta

// ---------------- Estado ----------------
Servo valvula;
bool chovendo = false;          // o botão alterna entre chovendo / não chovendo
bool valvulaAberta = false;
bool modoSeguro = false;
char ledAtual = 'V';            // último LED pedido pela Raspberry

unsigned long ultimoEnvio = 0;
unsigned long ultimoComando = 0;  // última vez que chegou algo da Raspberry

// Debounce do botão
int leituraAnteriorBotao = HIGH;
int estadoEstavelBotao = HIGH;
unsigned long ultimaMudancaBotao = 0;

String bufferSerial = "";       // acumula os caracteres até chegar '\n'

// Protótipos das funções (definidas mais abaixo)
int  lerNivel();
void lerBotaoChuva();
void enviarLeitura();
void receberComandos();
void processarComando(String cmd);
void verificarModoSeguro();
void abrirValvula();
void fecharValvula();
void acenderLed(char cor);

// ============================================================
void setup() {
  Serial.begin(9600);

  pinMode(PINO_CHUVA, INPUT_PULLUP);   // solto = HIGH, apertado = LOW
  pinMode(PINO_LED_VERDE, OUTPUT);
  pinMode(PINO_LED_AMARELO, OUTPUT);
  pinMode(PINO_LED_VERMELHO, OUTPUT);
  pinMode(PINO_BUZZER, OUTPUT);

  valvula.attach(PINO_SERVO);
  fecharValvula();
  acenderLed('V');

  ultimoComando = millis();
  bufferSerial.reserve(32);
}

// ============================================================
void loop() {
  lerBotaoChuva();
  receberComandos();
  verificarModoSeguro();

  // Envia a leitura dos sensores a cada 1 segundo
  if (millis() - ultimoEnvio >= INTERVALO_ENVIO_MS) {
    ultimoEnvio = millis();
    enviarLeitura();
  }

  // No modo seguro o LED amarelo pisca para indicar o problema
  if (modoSeguro) {
    digitalWrite(PINO_LED_AMARELO, (millis() / 500) % 2);
  }
}

// ------------------------------------------------------------
// Sensores
// ------------------------------------------------------------

// Lê o potenciômetro (0–1023) e converte para 0–100 %
int lerNivel() {
  int bruto = analogRead(PINO_NIVEL);
  return map(bruto, 0, 1023, 0, 100);
}

// Cada aperto no botão liga/desliga a "chuva" (com debounce)
void lerBotaoChuva() {
  int leitura = digitalRead(PINO_CHUVA);

  if (leitura != leituraAnteriorBotao) {
    ultimaMudancaBotao = millis();
  }

  if (millis() - ultimaMudancaBotao > DEBOUNCE_MS && leitura != estadoEstavelBotao) {
    estadoEstavelBotao = leitura;
    if (estadoEstavelBotao == LOW) {   // botão acabou de ser apertado
      chovendo = !chovendo;
    }
  }

  leituraAnteriorBotao = leitura;
}

// Monta e envia a mensagem: NIVEL:62;CHUVA:1
void enviarLeitura() {
  Serial.print("NIVEL:");
  Serial.print(lerNivel());
  Serial.print(";CHUVA:");
  Serial.println(chovendo ? 1 : 0);
}

// ------------------------------------------------------------
// Comandos vindos da Raspberry Pi
// ------------------------------------------------------------

// Junta os caracteres recebidos até formar uma linha completa
void receberComandos() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n') {
      bufferSerial.trim();
      if (bufferSerial.length() > 0) {
        processarComando(bufferSerial);
      }
      bufferSerial = "";
    } else if (bufferSerial.length() < 30) {
      bufferSerial += c;   // limite evita estouro de memória com lixo na serial
    }
  }
}

// Interpreta um comando, ex.: "VALVULA:1", "LED:R", "BUZZER:1"
void processarComando(String cmd) {
  ultimoComando = millis();   // a Raspberry está viva

  if (modoSeguro) {           // comunicação voltou: sai do modo seguro
    modoSeguro = false;
    acenderLed(ledAtual);
  }

  if (cmd == "VALVULA:1") {
    abrirValvula();
  } else if (cmd == "VALVULA:0") {
    fecharValvula();
  } else if (cmd.startsWith("LED:") && cmd.length() == 5) {
    ledAtual = cmd.charAt(4);
    acenderLed(ledAtual);
  } else if (cmd == "BUZZER:1") {
    tone(PINO_BUZZER, 2000, 300);   // bipe de 300 ms
  }
  // Comandos desconhecidos são ignorados
}

// ------------------------------------------------------------
// Modo seguro
// ------------------------------------------------------------
void verificarModoSeguro() {
  if (!modoSeguro && millis() - ultimoComando > TIMEOUT_RASPBERRY_MS) {
    modoSeguro = true;
    fecharValvula();               // nunca deixa a válvula aberta sem supervisão
    digitalWrite(PINO_LED_VERDE, LOW);
    digitalWrite(PINO_LED_VERMELHO, LOW);
  }
}

// ------------------------------------------------------------
// Atuadores
// ------------------------------------------------------------
void abrirValvula() {
  if (modoSeguro) return;
  valvula.write(ANGULO_ABERTA);
  valvulaAberta = true;
}

void fecharValvula() {
  valvula.write(ANGULO_FECHADA);
  valvulaAberta = false;
}

// Acende só o LED pedido: 'V' verde, 'A' amarelo, 'R' vermelho
void acenderLed(char cor) {
  digitalWrite(PINO_LED_VERDE,    cor == 'V' ? HIGH : LOW);
  digitalWrite(PINO_LED_AMARELO,  cor == 'A' ? HIGH : LOW);
  digitalWrite(PINO_LED_VERMELHO, cor == 'R' ? HIGH : LOW);
}
