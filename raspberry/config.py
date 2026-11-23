"""
Configurações do sistema da Cisterna Inteligente.

Os valores podem ser trocados por variáveis de ambiente, sem mexer no código:
    CISTERNA_PORTA=/dev/ttyUSB0 python3 app.py
    CISTERNA_SIMULAR=1 python3 app.py     (roda sem Arduino, com dados falsos)
"""
import os

# --- Comunicação com o Arduino ---
PORTA_SERIAL = os.getenv("CISTERNA_PORTA", "/dev/ttyACM0")  # Arduino Uno costuma aparecer assim
BAUD_RATE = 9600
SIMULAR = os.getenv("CISTERNA_SIMULAR", "0") == "1"

# Se ficar esse tempo sem receber leitura do Arduino, considera comunicação perdida
TIMEOUT_ARDUINO_S = 5

# --- Cisterna ---
CAPACIDADE_LITROS = 1000          # cisterna de referência

# --- Regras de controle (em % do nível) ---
NIVEL_CHEIA = 95                  # a partir daqui fecha a válvula
NIVEL_REABRIR = 90                # só volta a captar abaixo disso (evita abre/fecha sem parar)
NIVEL_RESERVA_BAIXA = 20          # abaixo disso: LED vermelho + alerta
NIVEL_MEDIO = 60                  # abaixo disso: LED amarelo; acima: verde

# --- Detecção de falha no sensor de nível ---
# Um nível de água real não pula dezenas de % em 1 segundo.
# Vários saltos grandes seguidos = sensor solto/com mau contato.
SALTO_SUSPEITO = 30               # variação em % entre duas leituras seguidas
SALTOS_PARA_FALHA = 3             # quantos saltos dentro da janela indicam falha
JANELA_LEITURAS = 10              # analisa as últimas N leituras

# --- Banco de dados e servidor web ---
CAMINHO_BANCO = os.getenv("CISTERNA_BANCO", os.path.join(os.path.dirname(__file__), "cisterna.db"))
HOST_WEB = "0.0.0.0"              # acessível por outros dispositivos da rede
PORTA_WEB = int(os.getenv("CISTERNA_PORTA_WEB", "5000"))
