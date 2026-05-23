# Cyber-Visceral Link API

WebSocket API para integração ESP32 com The Witcher 3 usando FastAPI + AsyncIO + leitura de logs em RAM disk.

## Arquitetura

```
The Witcher 3
    ↓
WitcherScript
    ↓
/dev/shm/witcher_events.log (RAM disk)
    ↓
FastAPI Async Reader
    ↓
WebSocket
    ↓
ESP32
    ↓
LED / motores / sensores
```

## Características

- **Conexão WebSocket persistente** com ESP32
- **Leitura assíncrona de logs** em RAM disk (/dev/shm)
- **Protocolo bidirecional** de mensagens
- **Heartbeat automático** para detecção de desconexões
- **Reconexão automática** em caso de falha
- **Segurança básica**: whitelist de IPs e limite de payload
- **Observabilidade**: logs detalhados de todas as operações

## Protocolo de Mensagens

### Mensagens de Saída (API → ESP32)

Formato: `OUTPUT:EVENTO`

- `OUTPUT:GORE_FLASH` - Flash de sangue
- `OUTPUT:DAMAGE_PULSE` - Pulso de dano
- `OUTPUT:KILL_STREAK` - Sequência de kills
- `OUTPUT:COMBO_HIT` - Combo acertado
- `OUTPUT:CRITICAL_HIT` - Crítico
- `OUTPUT:ADRENALINE` - Adrenalina
- `OUTPUT:LOW_HEALTH` - Vida baixa
- `OUTPUT:DEATH` - Morte

### Mensagens de Entrada (ESP32 → API)

Formato: `INPUT:EVENTO`

- `INPUT:PANIC_BUTTON` - Botão de pânico
- `INPUT:QUICK_SAVE` - Quick save
- `INPUT:QUICK_LOAD` - Quick load
- `INPUT:DODGE_LEFT` - Esquiva esquerda
- `INPUT:DODGE_RIGHT` - Esquiva direita
- `INPUT:ATTACK` - Ataque
- `INPUT:SIGN` - Sinal

## Instalação

### Pré-requisitos

- Python 3.8+
- pip
- Linux (Xubuntu recomendado)
- sudo access para /dev/shm

### Setup

```bash
# Clonar o repositório
cd /home/victor/witcherapi

# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Criar arquivo de log em RAM disk
sudo touch /dev/shm/witcher_events.log
sudo chmod 666 /dev/shm/witcher_events.log
```

## Execução

### Usando o script de startup

```bash
chmod +x run.sh
./run.sh
```

### Manualmente

```bash
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Endpoints

### REST API

- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /stats` - Estatísticas do sistema
- `GET /clients` - Lista de clientes conectados
- `POST /broadcast` - Broadcast mensagem para todos
- `POST /send/{client_id}` - Enviar para cliente específico

### WebSocket

- `WS /ws` - Endpoint WebSocket para ESP32

### Documentação

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Simulador de Eventos

Para testar sem o jogo, use o simulador:

```bash
# Modo aleatório (1 evento por segundo)
python simulator.py --mode random --interval 1.0

# Modo combate (sequência realista)
python simulator.py --mode combat

# Stress test (10 eventos por segundo)
python simulator.py --mode stress --rate 10

# Caminho customizado
python simulator.py --log-path /dev/shm/witcher_events.log
```

## Cliente ESP32

O código do cliente ESP32 está em `esp32_client/`.

### Configuração

Edite `esp32_client/esp32_client.ino`:

```cpp
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* WS_HOST = "192.168.1.100";  // IP do servidor API
```

### Upload com PlatformIO

```bash
cd esp32_client
pio run --target upload
```

### Upload com Arduino IDE

1. Abra `esp32_client/esp32_client.ino` no Arduino IDE
2. Instale a biblioteca `ArduinoWebsockets`
3. Selecione a placa ESP32
4. Upload

## Hardware ESP32

- **LED**: GPIO 2 (built-in)
- **Botão**: GPIO 0 (boot button)
- **Motor**: GPIO 4 (PWM para vibração)

## Estrutura do Projeto

```
cyber-visceral-link/
├── app/
│   ├── main.py              # FastAPI application
│   ├── websocket_manager.py # WebSocket connection manager
│   ├── protocol.py          # Message protocol definitions
│   ├── log_reader.py        # Async RAM disk log reader
│   ├── input_handler.py     # Event processing and dispatch
│   ├── state.py             # Application state management
│   └── config.py            # Configuration settings
├── esp32_client/
│   ├── esp32_client.ino     # ESP32 firmware
│   └── platformio.ini      # PlatformIO config
├── logs/                    # Application logs
├── tests/                   # Test suite
├── simulator.py             # Event simulator
├── requirements.txt         # Python dependencies
├── run.sh                   # Startup script
└── README.md               # This file
```

## Configuração

Crie um arquivo `.env` para customizar configurações:

```env
# WebSocket
WS_HOST=0.0.0.0
WS_PORT=8000

# RAM disk
RAM_DISK_LOG_PATH=/dev/shm/witcher_events.log

# Security
ALLOWED_IPS=["127.0.0.1", "::1"]
MAX_PAYLOAD_SIZE=64

# Heartbeat
HEARTBEAT_INTERVAL=30
HEARTBEAT_TIMEOUT=60

# Logging
LOG_LEVEL=INFO
```

## Testes

```bash
# Executar testes
pytest tests/

# Teste de WebSocket
python tests/test_websocket.py

# Teste de estresse
python tests/test_stress.py
```

## Troubleshooting

### Permissão negada em /dev/shm

```bash
sudo chmod 666 /dev/shm/witcher_events.log
```

### ESP32 não conecta

- Verifique IP do servidor em `esp32_client.ino`
- Confirme que ESP32 está na mesma rede
- Verifique firewall do servidor

### Latência alta

- Confirme que /dev/shm está montado (RAM disk)
- Verifique uso de CPU
- Reduza intervalo de polling no log_reader

## Roadmap

- [x] API FastAPI básica
- [x] WebSocket manager
- [x] Leitor assíncrono de logs
- [x] Simulador de eventos
- [x] Cliente ESP32 mínimo
- [ ] Integração com WitcherScript
- [ ] Input injection com xdotool/evdev
- [ ] Múltiplos ESP32
- [ ] Sensores corporais
- [ ] Vibração háptica avançada
- [ ] Telemetria biométrica

## Licença

MIT License
# witcherapi
