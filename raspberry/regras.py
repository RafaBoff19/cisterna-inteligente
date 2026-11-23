"""
Regras de controle da cisterna.

Funções puras (sem serial, sem banco): recebem a leitura e o estado anterior
e devolvem a decisão. Isso facilita testar as regras sozinhas (ver testes.py).
"""
from collections import deque

import config


def decidir_valvula(nivel, chuva, valvula_aberta):
    """
    Decide se a válvula de entrada deve ficar aberta.
      - Cisterna cheia (>= 95%)           -> fecha
      - Chovendo e abaixo do limite       -> abre
      - Sem chuva                         -> fecha
    Depois de fechar por estar cheia, só reabre abaixo de 90% (histerese),
    para o servo não ficar abrindo e fechando no limite.
    """
    if nivel >= config.NIVEL_CHEIA or not chuva:
        return False
    if valvula_aberta:
        return True
    return nivel < config.NIVEL_REABRIR


def decidir_led(nivel):
    """V = cheia/boa, A = média, R = reserva baixa."""
    if nivel < config.NIVEL_RESERVA_BAIXA:
        return "R"
    if nivel < config.NIVEL_MEDIO:
        return "A"
    return "V"


def situacao(nivel):
    """Texto curto para o painel."""
    if nivel >= config.NIVEL_CHEIA:
        return "Cisterna cheia"
    if nivel < config.NIVEL_RESERVA_BAIXA:
        return "Reserva baixa — economize água"
    if nivel < config.NIVEL_MEDIO:
        return "Nível médio"
    return "Nível bom"


def litros(nivel):
    return round(nivel / 100 * config.CAPACIDADE_LITROS)


class DetectorFalhaSensor:
    """
    Detecta sensor de nível com defeito (fio solto, mau contato).
    A água numa cisterna sobe e desce devagar; se o valor ficar pulando
    muito de uma leitura para a outra, o sensor provavelmente está com problema.
    """

    def __init__(self):
        self.saltos = deque(maxlen=config.JANELA_LEITURAS)
        self.ultimo_nivel = None

    def registrar(self, nivel):
        """Registra a leitura e devolve True se o sensor parece com falha."""
        if self.ultimo_nivel is not None:
            self.saltos.append(abs(nivel - self.ultimo_nivel) >= config.SALTO_SUSPEITO)
        self.ultimo_nivel = nivel
        return sum(self.saltos) >= config.SALTOS_PARA_FALHA
