# Meshtastic SDR Project

Passive SDR-based receiver and decoder for Meshtastic LoRa mesh networks. Captures RF packets using GNU Radio + gr-lora_sdr, decodes Meshtastic protocol, and provides a web dashboard for monitoring.

## Architecture

```
[RTL-SDR] → [GNU Radio + gr-lora_sdr] → ZMQ → [Python Decoder] → SQLite → [Flask WebUI]
```

### Components

| Component | Path | Description |
|-----------|------|-------------|
| GNU Radio flowgraphs | `gnuradio/*.grc` | LoRa demodulation, outputs via ZMQ |
| Decoder | `script/main.py` | Receives packets, decrypts, parses protobuf, logs to DB |
| Database | `script/db.py` | SQLite schema and write functions |
| WebUI | `webui/app.py` | Flask API server |
| Dashboard | `webui/static/dashboard.js` | Single-page app with map, tables, charts |

## Database Schema

### Tables

- **nodes** — discovered node metadata (ID, names, hardware, first/last seen, public_key)
- **traffic** — decoded packets (source, dest, type, payload, timestamps, via_mqtt, hop_start, hop_limit)
- **packets_raw** — all RF packets including undecrypted (for RF metrics, hop analysis)

### Key Fields (traffic table)

- `via_mqtt` — 1 if packet arrived via MQTT gateway, 0 if RF
- `hop_start` — original hop limit when transmitted (firmware 2.1+, from flags bits 5-7)
- `hop_limit` — remaining hops; `hop_start - hop_limit = hops_taken`

## Transport Classification

Every packet and node is classified by transport path:

| Transport | Condition | Icon | Color |
|-----------|-----------|------|-------|
| Direct RF | `via_mqtt=0`, `hop_start == hop_limit` | antenna-bars-5 | Green |
| RF-relayed | `via_mqtt=0`, `hop_start > hop_limit` or unknown | antenna-bars-3 | Yellow |
| MQTT-routed | `via_mqtt=1` | cloud-share | Blue |

Nodes are classified by their "best" transport ever observed (Direct RF > RF-relayed > MQTT-only).

## Node Status States

| Status | Criteria | Color |
|--------|----------|-------|
| Active | Traffic within 2h | Green (glowing) |
| Quiet | NodeInfo within 3h, no traffic in 2h | Blue |
| Hiding | Traffic within 2h, stale NodeInfo | Orange (glowing) |
| Dormant | Traffic 2-4h ago | Purple (dim) |
| Offline | No traffic in 4h+ | Grey (dim) |
| MQTT | Only seen via MQTT (mqtt_only transport) | Red |

## API Endpoints

All endpoints accept `?transport=rf|mqtt` filter parameter.

| Endpoint | Description |
|----------|-------------|
| `GET /api/nodes` | All nodes with transport aggregates |
| `GET /api/traffic` | Recent packets with via_mqtt, hop_start, hop_limit |
| `GET /api/positions` | Latest position per node |
| `GET /api/stats` | Packet counts, breakdown by type |
| `GET /api/metrics` | RF stats, channel utilization, hop distribution |
| `GET /api/metrics/activity` | Top active nodes, position frequency |
| `GET /api/watchlist?nodes=id1,id2` | Watched node details |
| `GET /api/node_telemetry?node=id` | Telemetry by sub-type |

## Key Files

### script/main.py
- ZMQ subscriber connecting to GNU Radio output
- Packet parsing via `PacketData` class
- AES-CTR decryption with multiple key support
- Protobuf parsing for all Meshtastic port types
- Robust error handling (never crashes)

### script/db.py
- SQLite with WAL mode
- Auto-migration for schema changes
- `upsert_node()`, `log_traffic()`, `log_raw_packet()`

### webui/app.py
- Flask with global exception handler (crash-proof)
- Read-only SQLite connection
- Transport filtering on all endpoints

### webui/static/dashboard.js
- Auto-refresh every 10s
- Transport filter (localStorage persisted)
- Online node count in header
- Leaflet map with transport-based marker colors
- Sortable/filterable tables
- Watch list with localStorage
- Expandable telemetry rows

## Running

```bash
# Terminal 1: GNU Radio (generates ZMQ output on ports 20000-20004)
python3 gnuradio/Meshtastic_US_250KHz_RTLSDR_headless.py

# Terminal 2: Decoder
python3 script/main.py --ip localhost --port 20000 --preset LongFast

# Terminal 3: WebUI
python3 webui/app.py --port 5000
```

## Deployment

See `docs/deployment_guide.md` for:
- Docker resource profiling (`script/profile_resources.py`)
- Raspberry Pi deployment recommendations
- ESP32 + SX1262 alternative architecture

## Icons

Transport icons are in `webui/icons/` (Tabler icon set):
- `antenna-bars-5.svg` — Direct RF
- `antenna-bars-3.svg` — RF-relayed
- `cloud-share.svg` — MQTT

## Dependencies

- GNU Radio 3.10+
- gr-lora_sdr (https://github.com/tapparelj/gr-lora_sdr)
- Python: meshtastic, pyzmq, cryptography, flask
- RTL-SDR or HackRF hardware
