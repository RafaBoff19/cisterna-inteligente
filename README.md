# Cisterna Inteligente de Água da Chuva

Projeto Final G2 — **Hardware Architecture** — Ciência da Computação, ATITUS
Equipe: **Rafael Boff** e **Wagner Segala**

Protótipo que automatiza a captação de água da chuva: abre a entrada da cisterna quando chove, fecha antes de transbordar e mostra em tempo real o nível, os litros disponíveis e os alertas num painel web.

Tema: **Mudanças Climáticas e Cidades Resilientes**. A cisterna guarda água para as estiagens e, nas chuvas fortes, segura parte da água que iria direto para os bueiros.

---

## Arquitetura

```
[Potenciômetro]──┐                          ┌──> SQLite (histórico)
[Botão chuva]────┤                          │
                 ▼        Serial/USB        │
             [ARDUINO] <──────────────> [RASPBERRY PI] ──> Painel web (Flask)
                 │                      regras de alerta
      ┌──────────┼──────────┐
      ▼          ▼          ▼
   [Servo]    [LEDs]    [Buzzer]
```

- **Arduino:** lê os sensores, envia as leituras e obedece aos comandos. Tem um **modo seguro**: se ficar 5 s sem receber nada da Raspberry, fecha a válvula sozinho e pisca o LED amarelo.
- **Raspberry Pi:** aplica as regras, grava tudo em SQLite e serve o painel web.

### Protocolo (texto, uma mensagem por linha, 9600 baud)

| Direção | Mensagem | Significado |
|---|---|---|
| Arduino → Raspberry | `NIVEL:62;CHUVA:1` | Nível em % e chuva (1 = chovendo), a cada 1 s |
| Raspberry → Arduino | `VALVULA:1` / `VALVULA:0` | Abre ou fecha a válvula (servo) |
| Raspberry → Arduino | `LED:V` / `LED:A` / `LED:R` | LED verde, amarelo ou vermelho |
| Raspberry → Arduino | `BUZZER:1` | Bipe de aviso |

A Raspberry envia `VALVULA` e `LED` a cada ciclo. Isso também serve de "sinal de vida" para o Arduino.

### Regras

| Situação | Ação |
|---|---|
| Chovendo e nível < 95% | Abre a válvula |
| Nível ≥ 95% | Fecha a válvula + bipe (só reabre abaixo de 90%) |
| Sem chuva | Válvula fechada |
| Nível < 20% | LED vermelho + alerta de reserva baixa + bipe |
| 20% a 59% / 60% ou mais | LED amarelo / LED verde |
| Sensor de nível instável ou mensagens inválidas | Fecha a válvula + alerta de falha |
| 5 s sem leituras do Arduino | Alerta de comunicação perdida (o Arduino fecha a válvula sozinho) |

---

## Estrutura do repositório

```
cisterna-inteligente/
├── arduino/cisterna/cisterna.ino   # firmware do Arduino (C/C++)
├── raspberry/
│   ├── app.py            # servidor web (Flask) — ponto de entrada
│   ├── controlador.py    # laço principal: lê, decide, comanda, grava
│   ├── regras.py         # regras de controle e detecção de falha
│   ├── comunicacao.py    # serial real + modo simulação
│   ├── banco.py          # SQLite
│   ├── config.py         # limites, porta serial, etc.
│   ├── testes.py         # testes automáticos das regras
│   ├── requirements.txt
│   └── templates/index.html   # painel web
└── wokwi/                # circuito pronto para simular no Wokwi
```

---

## Montagem

| Componente | Pino do Arduino |
|---|---|
| Potenciômetro (pino do meio) | A0 (pontas no 5V e GND) |
| Botão (simula a chuva) | D2 e GND (usa o pull-up interno) |
| Servo — sinal | D9 (V+ no 5V, GND no GND) |
| LED verde / amarelo / vermelho | D5 / D6 / D7, cada um com resistor de 220 ohms até o GND |
| Buzzer | D8 (+) e GND (−) |
| Raspberry Pi | Cabo USB do Arduino |

> Cada aperto no botão **liga ou desliga** a chuva.
> A comunicação é por USB, então não tem problema de nível lógico entre os 3,3 V da Raspberry e os 5 V do Arduino.

---

## Como executar

### 1. Arduino
1. Abra `arduino/cisterna/cisterna.ino` na Arduino IDE.
2. Placa: **Arduino Uno**. A biblioteca `Servo` já vem com a IDE.
3. Faça o upload. No Monitor Serial (9600 baud) aparece `NIVEL:..;CHUVA:..` a cada segundo.
   *(Sem a Raspberry conectada, o LED amarelo pisca depois de 5 s: é o modo seguro, comportamento esperado.)*
4. **Feche o Monitor Serial** antes de ligar o Arduino na Raspberry (a porta só pode ter um dono).

### 2. Raspberry Pi
```bash
sudo usermod -a -G dialout $USER      # permissão para usar a serial (faça logout/login depois)
cd raspberry
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```
Abra no navegador: `http://<ip-da-raspberry>:5000` (ou `http://localhost:5000` na própria Raspberry).

Se o Arduino aparecer em outra porta (veja com `ls /dev/tty*`):
```bash
CISTERNA_PORTA=/dev/ttyUSB0 python3 app.py
```

### 3. Sem hardware (modo simulação)
Para desenvolver o painel em qualquer computador:
```bash
CISTERNA_SIMULAR=1 python3 app.py
```
No Windows (PowerShell): `$env:CISTERNA_SIMULAR="1"; python app.py`

### 4. Testes automáticos
```bash
python3 testes.py
```

### 5. Wokwi
Crie um projeto **Arduino Uno** em [wokwi.com](https://wokwi.com). Depois cole `wokwi/sketch.ino` no `sketch.ino` e `wokwi/diagram.json` no `diagram.json`, e adicione a biblioteca **Servo** (aba Library Manager ou `libraries.txt`). Para simular a Raspberry, digite comandos no Serial Monitor, por exemplo `VALVULA:1` e `LED:R`.

---

## Roteiro de testes (Aula 7)

| # | Cenário | Como provocar | Resultado esperado |
|---|---|---|---|
| 1 | Normal | Nível em ~50%, apertar o botão (chuva) | Válvula abre, LED amarelo, evento "Começou a chover" |
| 2 | Cisterna cheia | Girar o potenciômetro até o fim | Válvula fecha, bipe, alerta "Cisterna cheia" |
| 3 | Reserva baixa | Girar até perto de 0 | LED vermelho, bipe, alerta "Reserva baixa" |
| 4 | Falha de sensor | Soltar o fio do pino do meio do potenciômetro (A0 fica "flutuando") | Alerta "Sensor de nível instável", válvula fecha |
| 5 | Perda de comunicação | Parar o `app.py` (Ctrl+C) ou tirar o USB | Arduino: válvula fecha e LED amarelo pisca em 5 s. Painel: "Comunicação perdida" |

Os eventos ficam registrados no painel e na tabela `eventos` do banco `raspberry/cisterna.db`.
