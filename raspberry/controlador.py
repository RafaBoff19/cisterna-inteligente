"""
Controlador: o "cérebro" do sistema, rodando numa thread separada do servidor web.

A cada ciclo (~1 s):
  1. lê a linha enviada pelo Arduino e interpreta
  2. aplica as regras (regras.py) e decide válvula e LED
  3. envia os comandos para o Arduino (isso também serve de "sinal de vida"
     para o Arduino não entrar em modo seguro)
  4. grava a leitura e os eventos no SQLite
  5. atualiza o estado que o painel web mostra
"""
import threading
import time

import banco
import config
import regras
from comunicacao import ConexaoSerial, ConexaoSimulada, interpretar_leitura


class Controlador:
    def __init__(self):
        if config.SIMULAR:
            self.conexao = ConexaoSimulada()
        else:
            self.conexao = ConexaoSerial(config.PORTA_SERIAL, config.BAUD_RATE)

        self.detector = regras.DetectorFalhaSensor()
        self.trava = threading.Lock()
        self.mensagens_invalidas = 0
        self.ultima_leitura_em = 0.0

        # Estado atual, lido pelo painel web
        self.estado = {
            "modo": "simulação" if config.SIMULAR else "serial",
            "conectado": False,
            "nivel": None,
            "litros": None,
            "capacidade": config.CAPACIDADE_LITROS,
            "chuva": False,
            "valvula": False,
            "led": "V",
            "situacao": "Aguardando o Arduino...",
            "falha_sensor": False,
            "atualizado_em": None,
        }

    # ---------------- API usada pelo app.py ----------------
    def iniciar(self):
        threading.Thread(target=self._laco, daemon=True).start()

    def obter_estado(self):
        with self.trava:
            return dict(self.estado)

    # ---------------- Laço principal ----------------
    def _laco(self):
        while True:
            if not self.conexao.conectado:
                self._tentar_conectar()
                continue

            linha = self.conexao.ler_linha()
            if linha:
                self._tratar_linha(linha)

            self._verificar_comunicacao()
            self._enviar_comandos()

    def _tentar_conectar(self):
        if self.conexao.conectar():
            banco.salvar_evento("info", "Conectado ao Arduino")
            self.ultima_leitura_em = time.time()
        else:
            self._atualizar(conectado=False, situacao=f"Arduino não encontrado em {config.PORTA_SERIAL}")
            time.sleep(2)

    def _tratar_linha(self, linha):
        leitura = interpretar_leitura(linha)

        if leitura is None:
            # Mensagem corrompida ou valor impossível: 3 seguidas = falha no sensor
            self.mensagens_invalidas += 1
            if self.mensagens_invalidas >= 3:
                self._marcar_falha(True, f"Leituras inválidas do Arduino: '{linha}'")
            return

        self.mensagens_invalidas = 0
        self.ultima_leitura_em = time.time()
        self._processar(leitura["nivel"], leitura["chuva"])

    def _processar(self, nivel, chuva):
        anterior = self.obter_estado()

        falha = self.detector.registrar(nivel)
        self._marcar_falha(falha, "Sensor de nível instável (leituras pulando)")

        # Com sensor em falha, por segurança a válvula fica fechada
        valvula = False if falha else regras.decidir_valvula(nivel, chuva, anterior["valvula"])
        led = regras.decidir_led(nivel)

        if not anterior["conectado"] and anterior["nivel"] is not None:
            banco.salvar_evento("info", "Comunicação com o Arduino restabelecida")

        # Com o sensor em falha os valores não são confiáveis: não gera alertas de nível
        if not falha:
            self._registrar_eventos(anterior, nivel, chuva, valvula)
        elif anterior["valvula"]:
            banco.salvar_evento("valvula", "Válvula fechada por segurança")

        banco.salvar_leitura(nivel, chuva, valvula, led)
        self._atualizar(
            conectado=True,
            nivel=nivel,
            litros=regras.litros(nivel),
            chuva=chuva,
            valvula=valvula,
            led=led,
            situacao="Falha no sensor de nível" if falha else regras.situacao(nivel),
            atualizado_em=time.strftime("%H:%M:%S"),
        )

    def _registrar_eventos(self, anterior, nivel, chuva, valvula):
        """Grava só as MUDANÇAS (não repete o mesmo alerta a cada segundo)."""
        nivel_anterior = anterior["nivel"]

        if chuva != anterior["chuva"]:
            banco.salvar_evento("chuva", "Começou a chover" if chuva else "Parou de chover")

        if valvula != anterior["valvula"]:
            banco.salvar_evento("valvula", "Válvula aberta — captando água" if valvula else "Válvula fechada")

        if nivel >= config.NIVEL_CHEIA and (nivel_anterior is None or nivel_anterior < config.NIVEL_CHEIA):
            banco.salvar_evento("alerta", f"Cisterna cheia ({nivel}%)")
            self.conexao.enviar("BUZZER:1")

        if nivel < config.NIVEL_RESERVA_BAIXA and (nivel_anterior is None or nivel_anterior >= config.NIVEL_RESERVA_BAIXA):
            banco.salvar_evento("alerta", f"Reserva baixa ({nivel}%)")
            self.conexao.enviar("BUZZER:1")

    def _marcar_falha(self, falha, mensagem):
        if falha != self.estado["falha_sensor"]:
            banco.salvar_evento("falha" if falha else "info", mensagem if falha else "Sensor de nível normalizado")
            self._atualizar(falha_sensor=falha)
            if falha:  # por segurança, fecha a válvula na hora
                self._atualizar(valvula=False, situacao="Falha no sensor de nível")

    def _verificar_comunicacao(self):
        """Sem leitura há mais de 5 s = perda de comunicação."""
        sem_dados = time.time() - self.ultima_leitura_em > config.TIMEOUT_ARDUINO_S
        if sem_dados and self.estado["conectado"]:
            banco.salvar_evento("falha", "Comunicação com o Arduino perdida")
            self._atualizar(conectado=False, valvula=False, situacao="Sem comunicação com o Arduino — válvula fechada")
        if not self.conexao.conectado and self.estado["conectado"]:
            banco.salvar_evento("falha", "Cabo USB desconectado")
            self._atualizar(conectado=False, valvula=False, situacao="Arduino desconectado")

    def _enviar_comandos(self):
        """Envia o estado desejado a cada ciclo (também funciona como sinal de vida)."""
        if not self.conexao.conectado:
            return
        estado = self.obter_estado()
        self.conexao.enviar("VALVULA:1" if estado["valvula"] else "VALVULA:0")
        self.conexao.enviar("LED:" + estado["led"])

    def _atualizar(self, **campos):
        with self.trava:
            self.estado.update(campos)
