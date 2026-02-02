# Complete Meshtastic SDR Setup Guide
## GNU Radio + RTL-SDR for Meshtastic Reception on Debian

### Overview
This guide covers the complete installation and configuration of GNU Radio with the gr-lora_sdr module to receive and decode Meshtastic LoRa messages using an RTL-SDR on Debian Linux.

---

## Prerequisites
- Latest Debian Linux installation
- GNU Radio already installed (`sudo apt install gnuradio`)
- RTL-SDR dongle
- Internet connection for downloads

---

## Installation Process

### Step 1: Install Build Dependencies
```bash
sudo apt update
sudo apt install -y cmake git build-essential pkg-config \
    libboost-all-dev liblog4cpp5-dev swig python3-numpy \
    python3-scipy python3-dev gnuradio-dev libvolk-dev \
    libsndfile1-dev rtl-sdr librtlsdr-dev gr-osmosdr
```

### Step 2: Install Meshtastic Python Library
```bash
pip3 install meshtastic --break-system-packages
```
**Note**: `--break-system-packages` is required on Debian to install outside virtual environments.

### Step 3: Install gr-lora_sdr (Critical Component)
```bash
cd ~/Downloads
git clone https://github.com/tapparelj/gr-lora_sdr.git
cd gr-lora_sdr
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=/usr/local
make -j$(nproc)
sudo make install
sudo ldconfig  # CRITICAL: Do not skip this step!
```

**Verification**:
```bash
# Check if library is installed
ls -la /usr/local/lib/libgnuradio-lora_sdr.so*

# Verify ldconfig can find it
ldconfig -p | grep lora_sdr
```

### Step 4: Clone Meshtastic_SDR Project
```bash
cd ~/Downloads
git clone https://gitlab.com/crankylinuxuser/meshtastic_sdr.git
```

### Step 5: Verify GNU Radio Installation
```bash
gnuradio-companion
```
- Look for "LoRa_TX" or "LoRa_RX" blocks in the block list
- If not visible, close and reopen GNU Radio Companion

---

## Running the Receiver

### Open the Appropriate Flowgraph
For RTL-SDR (limited to ~2.4 MHz bandwidth):
```bash
cd ~/Downloads/meshtastic_sdr/gnuradio\ scripts/RX/

# For US users:
gnuradio-companion Meshtastic_US_62KHz_RTLSDR.grc

# For EU users:
gnuradio-companion Meshtastic_EU_62KHz_RTLSDR.grc
```

### Configure RTL-SDR Parameters
In the GNU Radio flowgraph, verify:
- **Sample Rate**: 2.048e6 (2.048 MHz)
- **Center Frequency**: 
  - US LongFast: 906.875 MHz or 902.125 MHz
  - EU: 869.525 MHz
- **RF Gain**: 40 dB (adjust as needed)
- **IF Gain**: 20 dB
- **BB Gain**: 20 dB

### Start the Flowgraph
Click the "Execute" (play) button in GNU Radio Companion.

### Run the Python Decoder Script
In a separate terminal:
```bash
cd ~/Downloads/meshtastic_sdr/python\ scripts
python3 meshtastic_gnuradio_RX.py -n 127.0.0.1 -p 20004
```

**Port mapping** (check your flowgraph's ZMQ PUB Sink):
- ShortFast: TCP/20000
- ShortSlow: TCP/20001
- MediumFast: TCP/20002
- MediumSlow: TCP/20003
- **LongFast: TCP/20004** (most common)
- LongModerate: TCP/20005
- LongSlow: TCP/20006
- VeryLongSlow: TCP/20007

---

## Optional: Enhanced Decoder Script

For improved functionality with multi-key support:
```bash
cd ~/Downloads
git clone https://github.com/tom-acco/Meshtastic_SDR.git tom-acco-meshtastic
cd tom-acco-meshtastic/script
python3 meshtastic_gnuradio_decoder.py -n 127.0.0.1 -p 20004
```

---

## Adding GUI Visualization

The default Meshtastic_SDR flowgraphs don't include visual displays. To add them:

1. Open your `.grc` file in GNU Radio Companion
2. Add visualization blocks from the right panel:
   - **QT GUI Waterfall Sink** (for spectrum waterfall)
   - **QT GUI Frequency Sink** (for frequency spectrum)
   - **QT GUI Time Sink** (for time domain view)
3. Connect them to the **RTL-SDR Source** output
4. Configure block parameters:
   - Type: Complex
   - Sample Rate: `samp_rate` (or 2048000)
   - Center Frequency: Your operating frequency
   - FFT Size: 1024 or 2048
   - Update Rate: 10 Hz
5. Save and re-run the flowgraph

---

## Understanding the System Architecture

```
RTL-SDR Hardware
    ↓
GNU Radio Flowgraph (receives RF)
    ↓
gr-lora_sdr Decoder Blocks (demodulates LoRa)
    ↓
ZMQ PUB Sink (sends to TCP port 20000-20007)
    ↓
Python Script (decrypts and decodes Meshtastic protobuf)
    ↓
Decoded Messages (displayed in terminal)
```

---

## Lessons Learned

### Critical Issues Encountered and Solutions

#### 1. **Missing `sudo ldconfig` Command**
**Problem**: Most critical issue - without running `sudo ldconfig` after `make install`, the gr-lora_sdr library won't be found by GNU Radio.

**Error Message**:
```
ImportError: libgnuradio-lora_sdr.so.1.0.0git: cannot open shared object file
```

**Solution**: Always run `sudo ldconfig` after installing any GNU Radio OOT module.

**Verification**:
```bash
ldconfig -p | grep lora_sdr
```

#### 2. **No GUI Display in GNU Radio**
**Problem**: The Meshtastic_SDR flowgraphs are headless by design - they only output data via ZMQ TCP sockets, not visual displays.

**Understanding**: Console output shows low-level LoRa decoder messages, not actual decoded Meshtastic data. The Python script is required to see meaningful messages.

**Solution**: Add QT GUI blocks manually if visualization is needed.

#### 3. **"INVALID PROTOBUF" Messages are Normal**
**Problem**: Frequent "INVALID PROTOBUF" errors appear when running the decoder.

**Understanding**: These are NOT errors in your setup. They occur because:
- You're receiving all LoRa traffic, not just valid Meshtastic
- Packets may be encrypted with different keys
- Some packets may have RF corruption
- Partial packet captures can occur

**Expected Behavior**: Mix of valid decoded messages AND invalid protobuf errors is completely normal.

#### 4. **CMAKE_INSTALL_PREFIX Matters**
**Problem**: If gr-lora_sdr is installed to the wrong location, GNU Radio can't find it.

**Solution**: Always specify `-DCMAKE_INSTALL_PREFIX=/usr/local` to match where GNU Radio looks for modules.

**Troubleshooting**: If blocks don't appear, verify installation location matches GNU Radio's search paths.

#### 5. **RTL-SDR Bandwidth Limitations**
**Problem**: RTL-SDR has only ~2.4 MHz usable bandwidth, limiting which presets can be monitored simultaneously.

**Solution**: Use the `_62KHz_RTLSDR.grc` flowgraphs designed for narrowband reception. For all-preset monitoring, a HackRF or better SDR with 20+ MHz bandwidth is required.

### Installation Best Practices

1. **Always verify each step** before proceeding to the next
2. **Run `sudo ldconfig`** after every OOT module installation
3. **Check library paths** with `ldconfig -p` to confirm installation
4. **Test GNU Radio Companion** to verify blocks appear before trying to run flowgraphs
5. **Start with visualization** - add QT GUI blocks to understand signal reception before attempting decoding

### Common Troubleshooting Commands

```bash
# Verify gr-lora_sdr installation
find /usr -name "*lora_sdr*" 2>/dev/null

# Check Python module paths
python3 -c "import sys; print('\n'.join(sys.path))"

# Test RTL-SDR hardware
rtl_test

# Re-install gr-lora_sdr if needed
cd ~/Downloads/gr-lora_sdr/build
sudo make uninstall
sudo make clean
cd ..
rm -rf build
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=/usr/local
sudo make install -j$(nproc)
sudo ldconfig
```

### Performance Considerations

- **CPU Usage**: Decoding multiple LoRa presets simultaneously is CPU-intensive
- **Single Channel**: Use single-preset flowgraphs to reduce CPU load
- **Sample Rate**: Higher sample rates increase processing requirements
- **RF Gain**: Start with 40 dB and adjust based on local signal strength

---

## Key Resources

- **gr-lora_sdr GitHub**: https://github.com/tapparelj/gr-lora_sdr
- **Meshtastic_SDR GitLab**: https://gitlab.com/crankylinuxuser/meshtastic_sdr
- **Enhanced Decoder (tom-acco)**: https://github.com/tom-acco/Meshtastic_SDR
- **Jeff Geerling's Guide**: https://www.jeffgeerling.com/blog/2025/decoding-meshtastic-gnuradio-on-raspberry-pi
- **RTL-SDR Blog Article**: https://www.rtl-sdr.com/decoding-meshtastic-in-realtime-with-an-rtl-sdr-and-gnu-radio/

---

## Quick Start Checklist

- [ ] Install build dependencies
- [ ] Install Meshtastic Python library
- [ ] Clone and build gr-lora_sdr
- [ ] **Run `sudo ldconfig`** (critical!)
- [ ] Verify library installation with `ldconfig -p`
- [ ] Clone Meshtastic_SDR project
- [ ] Open GNU Radio Companion and verify LoRa blocks appear
- [ ] Load appropriate `.grc` file for your region and SDR
- [ ] Configure RTL-SDR parameters
- [ ] Start GNU Radio flowgraph
- [ ] Run Python decoder script in separate terminal
- [ ] Verify reception (expect mix of valid messages and "INVALID PROTOBUF")

---

## Expected Output

**GNU Radio Console** (low-level messages):
```
LoRa RX: CRC valid
[LoRa decoder debug output]
```

**Python Decoder Terminal** (parsed messages):
```
From: !abc123 To: !xyz789
Message: "Test message from node"
INVALID PROTOBUF  <-- This is normal!
From: !def456 To: !all
Position: 37.7749° N, 122.4194° W
INVALID PROTOBUF  <-- This is normal!
```

The mix of valid decoded messages and invalid protobuf errors indicates a correctly functioning system receiving real LoRa/Meshtastic traffic.
