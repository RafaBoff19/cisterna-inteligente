"""
Testes automáticos das regras e do protocolo (não precisa de Arduino).
Rodar:  python3 testes.py
"""
import unittest

import regras
from comunicacao import interpretar_leitura


class TestProtocolo(unittest.TestCase):
    def test_mensagem_valida(self):
        self.assertEqual(interpretar_leitura("NIVEL:62;CHUVA:1"), {"nivel": 62, "chuva": True})

    def test_mensagem_quebrada(self):
        self.assertIsNone(interpretar_leitura("NIVEL:6"))
        self.assertIsNone(interpretar_leitura("lixo na serial"))
        self.assertIsNone(interpretar_leitura("NIVEL:abc;CHUVA:1"))

    def test_valor_impossivel(self):
        self.assertIsNone(interpretar_leitura("NIVEL:150;CHUVA:0"))
        self.assertIsNone(interpretar_leitura("NIVEL:50;CHUVA:7"))


class TestValvula(unittest.TestCase):
    def test_abre_quando_chove(self):
        self.assertTrue(regras.decidir_valvula(50, True, False))

    def test_fecha_sem_chuva(self):
        self.assertFalse(regras.decidir_valvula(50, False, True))

    def test_fecha_quando_cheia(self):
        self.assertFalse(regras.decidir_valvula(95, True, True))

    def test_histerese(self):
        # Fechou cheia; em 92% ainda não reabre, em 89% reabre
        self.assertFalse(regras.decidir_valvula(92, True, False))
        self.assertTrue(regras.decidir_valvula(89, True, False))
        # Se já estava aberta, continua captando até 95%
        self.assertTrue(regras.decidir_valvula(92, True, True))


class TestLed(unittest.TestCase):
    def test_cores(self):
        self.assertEqual(regras.decidir_led(10), "R")
        self.assertEqual(regras.decidir_led(40), "A")
        self.assertEqual(regras.decidir_led(80), "V")


class TestFalhaSensor(unittest.TestCase):
    def test_leitura_estavel_nao_e_falha(self):
        d = regras.DetectorFalhaSensor()
        self.assertFalse(any(d.registrar(n) for n in [40, 41, 43, 44, 46, 47]))

    def test_leitura_pulando_e_falha(self):
        d = regras.DetectorFalhaSensor()
        resultados = [d.registrar(n) for n in [40, 90, 10, 85, 5]]
        self.assertTrue(resultados[-1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
