# Deployment Guide: Resource Profiling & Platform Options

## Part 1: Docker Resource Profiling

### Quick Commands (Run on Host)

```bash
# One-shot stats
docker stats --no-stream <container_name>

# Continuous monitoring
docker stats <container_name>

# Detailed view with process breakdown
docker exec -it <container_name> top -b -n 1
```

### Detailed Profiling Script

Run the profiler inside your container to collect data over time:

```bash
# Copy into container
docker cp script/profile_resources.py <container>:/app/

# Run for 60 minutes
docker exec -it <container> python3 /app/profile_resources.py 60
```

The profiler outputs:
- Real-time stats every 5 seconds
- CSV file in `logs/profile_YYYYMMDD_HHMMSS.csv`
- Summary with Pi deployment recommendations

### Key Metrics to Watch

| Metric | Pi 4 (2GB) Limit | Pi 4 (4GB) Limit | Pi 5 Limit |
|--------|------------------|------------------|------------|
| Total RSS Memory | < 1.5 GB | < 3 GB | < 6 GB |
| CPU (sustained) | < 70% | < 80% | < 85% |
| Load Average (1m) | < 3.5 | < 3.5 | < 3.5 |

### Expected Baseline

Based on architecture analysis:

| Component | Memory (RSS) | CPU (idle) | CPU (active) |
|-----------|--------------|------------|--------------|
| GNU Radio + gr-lora_sdr | 250-400 MB | 30-50% | 50-75% |
| Python Decoder | 80-120 MB | <1% | 1-2% |
| Flask WebUI | 70-100 MB | <1% | <1% |
| **Total** | **400-620 MB** | **~35%** | **~55%** |

---

## Part 2: Raspberry Pi Deployment

### Recommended Hardware

| Use Case | Model | RAM | Notes |
|----------|-------|-----|-------|
| Full stack (5 presets) | Pi 5 | 4GB | Best performance |
| Full stack (headless) | Pi 4B | 4GB | Good, may need CPU governor tuning |
| Reduced (2 presets) | Pi 4B | 2GB | LongFast + MediumFast only |
| Not recommended | Pi Zero 2 W | 512MB | CPU too weak |

### Optimization Checklist

1. **Reduce decoder chains** (if CPU-bound):
   Edit GNU Radio flowgraph to use only 2 presets:
   - SF11 (LongFast) - most common for long-range
   - SF9 (MediumFast) - common for balanced use

2. **CPU performance mode**:
   ```bash
   echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
   ```

3. **Disable WebUI** (headless):
   Don't start Flask; query SQLite directly via SSH or sync database file.

4. **Use USB SSD** instead of SD card:
   SQLite WAL mode benefits from faster I/O.

5. **Compile optimizations** (if building from source):
   ```bash
   export CFLAGS="-O3 -march=native -mfpu=neon-vfpv4"
   export CXXFLAGS="$CFLAGS"
   ```

### Database Indexes (add for large deployments)

```sql
CREATE INDEX IF NOT EXISTS idx_traffic_timestamp ON traffic(timestamp);
CREATE INDEX IF NOT EXISTS idx_traffic_source ON traffic(source_id);
CREATE INDEX IF NOT EXISTS idx_packets_timestamp ON packets_raw(timestamp);
CREATE INDEX IF NOT EXISTS idx_nodes_last_heard ON nodes(last_heard);
```

---

## Part 3: ESP32-S3 + SX1262 Sniffer

### Why Not SDR on ESP32?

The current SDR approach (GNU Radio + gr-lora_sdr) requires:
- 250+ MB RAM (ESP32 has 512 KB)
- Linux OS (ESP32 runs FreeRTOS)
- ~2000 MIPS CPU (ESP32 provides ~300)

**The ESP32 cannot run GNU Radio.** However, it can run as a Meshtastic node with hardware LoRa.

### Architecture Options

#### Option A: ESP32 as MQTT Gateway (Recommended)

```
[SX1262 LoRa] ←SPI→ [ESP32-S3] ←WiFi→ [MQTT Broker] → [Pi/Server with DB]
```

**How it works:**
1. Flash ESP32 with official Meshtastic firmware
2. Configure same channel/key as your monitored mesh
3. Enable MQTT uplink - device forwards ALL received packets
4. Server subscribes to MQTT and logs to database

**Pros:**
- Uses official firmware (maintained, reliable)
- Full packet decryption (if you have the key)
- Low power (~50mA active)
- ~$15-25 hardware cost

**Cons:**
- Single preset at a time (one SF/BW combination)
- Requires WiFi connectivity
- Part of the mesh (not truly passive)

#### Option B: RadioLib Raw Receiver

```
[SX1262 LoRa] ←SPI→ [ESP32-S3 + RadioLib] ←WiFi→ [Server]
```

**How it works:**
1. Use RadioLib library in promiscuous mode
2. Receive raw LoRa frames without Meshtastic stack
3. Forward raw bytes to server for decoding
4. Server handles Meshtastic protocol parsing

**Pros:**
- Truly passive (not part of mesh)
- Can capture packets you can't decrypt
- More flexibility in RF parameters

**Cons:**
- Must implement LoRa receive logic
- Single preset at a time
- More development work

### Recommended Hardware

| Board | Price | Notes |
|-------|-------|-------|
| [Heltec WiFi LoRa 32 V3](https://heltec.org/project/wifi-lora-32-v3/) | ~$20 | ESP32-S3 + SX1262, OLED display |
| [XIAO ESP32S3 + Wio-SX1262](https://www.seeedstudio.com/Wio-SX1262-with-XIAO-ESP32S3-p-5982.html) | ~$25 | Compact, modular |
| [RAK WisMesh Starter Kit](https://store.rakwireless.com/products/meshtastic-starter-kit-esp32-s3-lora-sx1262) | ~$35 | Plug-and-play Meshtastic |
| [LilyGo T3-S3](https://www.lilygo.cc/) | ~$25 | Popular choice, good docs |

### ESP32 Sniffer Implementation Plan

#### Phase 1: MQTT Gateway Approach

1. **Flash Meshtastic firmware** on ESP32 + SX1262 board
2. **Configure for your mesh:**
   - Set region (US, EU, etc.)
   - Set channel name + PSK (same as monitored mesh)
   - Enable MQTT module with uplink
3. **Set up MQTT broker** (Mosquitto on Pi or server)
4. **Create MQTT-to-SQLite bridge** in Python

#### Phase 2: Custom Logger Firmware (Optional)

For deeper control, a custom ESP32 firmware that:
- Receives on multiple presets (time-division)
- Logs to SD card when WiFi unavailable
- Syncs to server when connected
- Reports RSSI/SNR per packet

### MQTT Bridge Script Skeleton

```python
#!/usr/bin/env python3
"""
MQTT bridge for ESP32 Meshtastic gateway.
Receives packets from MQTT and logs to SQLite.
"""
import json
import sqlite3
import paho.mqtt.client as mqtt
from meshtastic import mesh_pb2, mqtt_pb2, portnums_pb2

MQTT_BROKER = "localhost"
MQTT_TOPIC = "msh/US/2/e/#"  # Adjust region/channel
DB_PATH = "mesh.db"

def on_message(client, userdata, msg):
    try:
        # Decode ServiceEnvelope
        envelope = mqtt_pb2.ServiceEnvelope()
        envelope.ParseFromString(msg.payload)

        packet = envelope.packet

        # Log to database
        # ... (similar to current log_traffic logic)

        print(f"[{packet.from_:08x}→{packet.to:08x}] "
              f"port={packet.decoded.portnum} "
              f"rssi={packet.rx_rssi} snr={packet.rx_snr}")

    except Exception as e:
        print(f"Error: {e}")

def main():
    client = mqtt.Client()
    client.on_message = on_message
    client.connect(MQTT_BROKER, 1883)
    client.subscribe(MQTT_TOPIC)
    print(f"Subscribed to {MQTT_TOPIC}")
    client.loop_forever()

if __name__ == "__main__":
    main()
```

---

## Part 4: Comparison Matrix

| Feature | SDR (Current) | Pi + SDR | ESP32 + MQTT |
|---------|---------------|----------|--------------|
| Multi-preset | ✅ 5 parallel | ✅ 2-5 | ❌ 1 at a time |
| Power consumption | ~15W | ~5W | ~0.3W |
| Hardware cost | $30-50 | $80-120 | $15-25 |
| Truly passive | ✅ | ✅ | ❌ (joins mesh) |
| Encrypted capture | ✅ | ✅ | ❌ (needs key) |
| Deployment size | Desktop | Small SBC | Pocket |
| WiFi required | ❌ | ❌ | ✅ |
| Battery operation | ❌ | Possible | ✅ Easy |

---

## Related Projects

- [Meshstellar](https://github.com/jurriaan/meshstellar) - Rust-based Meshtastic monitor (MQTT-based)
- [LoRaMon](https://github.com/markqvist/LoRaMon) - LoRa packet sniffer for RNode hardware
- [RadioLib](https://github.com/jgromes/RadioLib) - Arduino LoRa library with promiscuous mode

---

## Next Steps

1. **Run profiler** on current Docker setup for 1+ hours during active mesh time
2. **Analyze CSV** to determine actual resource usage
3. **Decide deployment target:**
   - Pi 4/5 for full SDR capability
   - ESP32 for low-power, single-preset monitoring
4. **For ESP32 path:** Order hardware, flash Meshtastic, configure MQTT
