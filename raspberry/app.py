"""
Cisterna Inteligente de Água da Chuva — aplicação da Raspberry Pi.
Hardware Architecture — ATITUS — Projeto Final G2
Equipe: Rafael Boff e Wagner Segala

Como rodar:
    python3 app.py                       # com o Arduino ligado na USB
    CISTERNA_SIMULAR=1 python3 app.py    # sem Arduino (dados simulados)

Depois abra no navegador: http://<ip-da-raspberry>:5000
"""
from flask import Flask, jsonify, render_template, request

import banco
import config
from controlador import Controlador

app = Flask(__name__)
controlador = Controlador()


@app.route("/")
def painel():
    """Página do painel de monitoramento."""
    return render_template("index.html", capacidade=config.CAPACIDADE_LITROS)


@app.route("/api/estado")
def api_estado():
    """Estado atual: nível, litros, chuva, válvula, LED, situação."""
    return jsonify(controlador.obter_estado())


@app.route("/api/historico")
def api_historico():
    """Leituras dos últimos N minutos (padrão 10) para o gráfico."""
    minutos = request.args.get("minutos", default=10, type=int)
    minutos = max(1, min(minutos, 24 * 60))
    return jsonify(banco.historico(minutos))


@app.route("/api/eventos")
def api_eventos():
    """Últimos alertas e eventos registrados."""
    return jsonify(banco.ultimos_eventos(15))


if __name__ == "__main__":
    banco.criar_tabelas()
    controlador.iniciar()
    print(f"Modo: {'SIMULAÇÃO' if config.SIMULAR else 'serial em ' + config.PORTA_SERIAL}")
    print(f"Painel em http://localhost:{config.PORTA_WEB}")
    # use_reloader=False: evita o Flask iniciar o controlador duas vezes
    app.run(host=config.HOST_WEB, port=config.PORTA_WEB, debug=False, use_reloader=False)
