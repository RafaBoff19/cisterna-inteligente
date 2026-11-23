"""
Registro dos dados em SQLite.

Tabelas:
  leituras: uma linha por leitura recebida do Arduino (1 por segundo)
  eventos:  alertas e mudanças importantes (cisterna cheia, falha, etc.)
"""
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta

import config

_trava = threading.Lock()  # o Flask e o controlador usam o banco em threads diferentes


@contextmanager
def _conectar():
    """Abre o banco, confirma as alterações (commit) e sempre fecha a conexão."""
    conexao = sqlite3.connect(config.CAMINHO_BANCO)
    conexao.row_factory = sqlite3.Row
    try:
        yield conexao
        conexao.commit()
    finally:
        conexao.close()


def criar_tabelas():
    with _trava, _conectar() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS leituras (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                data_hora TEXT NOT NULL,
                nivel    INTEGER NOT NULL,
                chuva    INTEGER NOT NULL,
                valvula  INTEGER NOT NULL,
                led      TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS eventos (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                data_hora TEXT NOT NULL,
                tipo      TEXT NOT NULL,
                mensagem  TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_leituras_data ON leituras(data_hora);
        """)


def _agora():
    return datetime.now().isoformat(timespec="seconds")


def salvar_leitura(nivel, chuva, valvula, led):
    with _trava, _conectar() as db:
        db.execute(
            "INSERT INTO leituras (data_hora, nivel, chuva, valvula, led) VALUES (?, ?, ?, ?, ?)",
            (_agora(), nivel, int(chuva), int(valvula), led),
        )


def salvar_evento(tipo, mensagem):
    with _trava, _conectar() as db:
        db.execute(
            "INSERT INTO eventos (data_hora, tipo, mensagem) VALUES (?, ?, ?)",
            (_agora(), tipo, mensagem),
        )


def historico(minutos=10):
    """Leituras dos últimos N minutos, da mais antiga para a mais nova."""
    desde = (datetime.now() - timedelta(minutes=minutos)).isoformat(timespec="seconds")
    with _trava, _conectar() as db:
        linhas = db.execute(
            "SELECT data_hora, nivel, chuva, valvula FROM leituras WHERE data_hora >= ? ORDER BY id",
            (desde,),
        ).fetchall()
    return [dict(l) for l in linhas]


def ultimos_eventos(quantidade=10):
    with _trava, _conectar() as db:
        linhas = db.execute(
            "SELECT data_hora, tipo, mensagem FROM eventos ORDER BY id DESC LIMIT ?",
            (quantidade,),
        ).fetchall()
    return [dict(l) for l in linhas]
