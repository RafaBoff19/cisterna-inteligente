"""
Comunicação com o Arduino.

Duas implementações com a mesma interface (ler_linha / enviar):
  - ConexaoSerial:   fala com o Arduino de verdade pela USB (pyserial)
  - ConexaoSimulada: gera leituras falsas, para testar o painel sem hardware
"""
import random
import time


def interpretar_leitura(linha):
    """
    Converte 'NIVEL:62;CHUVA:1' em {'nivel': 62, 'chuva': True}.
    Devolve None se a mensagem estiver mal formada ou com valores impossíveis.
    """
    try:
        campos = dict(parte.split(":", 1) for parte in linha.strip().split(";"))
        nivel = int(campos["NIVEL"])
        chuva = int(campos["CHUVA"])
    except (ValueError, KeyError):
        return None

    if not 0 <= nivel <= 100 or chuva not in (0, 1):
        return None
    return {"nivel": nivel, "chuva": chuva == 1}


class ConexaoSerial:
    """Conexão real com o Arduino via Serial/USB."""

    def __init__(self, porta, baud):
        import serial  # importado aqui para o modo simulado funcionar sem pyserial
        self._serial_mod = serial
        self.porta = porta
        self.baud = baud
        self.conexao = None

    def conectar(self):
        """Tenta abrir a porta. Devolve True se conseguiu."""
        try:
            self.conexao = self._serial_mod.Serial(self.porta, self.baud, timeout=1)
            time.sleep(2)  # o Arduino reinicia ao abrir a serial; espera ele subir
            self.conexao.reset_input_buffer()
            return True
        except self._serial_mod.SerialException:
            self.conexao = None
            return False

    @property
    def conectado(self):
        return self.conexao is not None and self.conexao.is_open

    def ler_linha(self):
        """Lê uma linha (espera até 1 s). Devolve '' se nada chegou."""
        try:
            return self.conexao.readline().decode("utf-8", errors="ignore").strip()
        except (self._serial_mod.SerialException, OSError):
            self.fechar()  # cabo desconectado: força reconexão
            return ""

    def enviar(self, comando):
        try:
            self.conexao.write((comando + "\n").encode("utf-8"))
        except (self._serial_mod.SerialException, OSError):
            self.fechar()

    def fechar(self):
        if self.conexao is not None:
            try:
                self.conexao.close()
            except Exception:
                pass
        self.conexao = None


class ConexaoSimulada:
    """
    Simula o Arduino: a chuva liga e desliga sozinha e o nível
    sobe quando a válvula está aberta e desce com o consumo.
    """

    def __init__(self):
        self.nivel = 40.0
        self.chuva = False
        self.valvula_aberta = False
        self.conectado = False

    def conectar(self):
        self.conectado = True
        return True

    def ler_linha(self):
        time.sleep(1)  # o Arduino real envia a cada 1 s
        if random.random() < 0.05:          # de vez em quando a chuva muda
            self.chuva = not self.chuva
        if self.valvula_aberta:
            self.nivel += random.uniform(1.0, 3.0)   # entrando água
        self.nivel -= random.uniform(0.0, 0.6)       # consumo da casa
        self.nivel = max(0.0, min(100.0, self.nivel))
        return f"NIVEL:{round(self.nivel)};CHUVA:{1 if self.chuva else 0}"

    def enviar(self, comando):
        if comando == "VALVULA:1":
            self.valvula_aberta = True
        elif comando == "VALVULA:0":
            self.valvula_aberta = False

    def fechar(self):
        self.conectado = False
