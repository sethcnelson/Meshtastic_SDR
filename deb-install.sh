#!/bin/bash
#
# Meshtastic SDR Complete Installation Script
# For Debian 13 (Trixie) - Fresh Install
# Installs GNU Radio, gr-lora_sdr, and Meshtastic_SDR for RTL-SDR reception
#
# Usage: bash install_meshtastic_sdr.sh (run as regular user, NOT root)
#

set -e  # Exit on any error

# Prevent interactive dialogs during apt operations
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a
export NEEDRESTART_SUSPEND=1

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="$HOME/meshtastic_sdr_install"
GR_LORA_SDR_REPO="https://github.com/tapparelj/gr-lora_sdr.git"
MESHTASTIC_SDR_REPO="https://gitlab.com/crankylinuxuser/meshtastic_sdr.git"
ENHANCED_DECODER_REPO="https://github.com/tom-acco/Meshtastic_SDR.git"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}ERROR: This script should NOT be run as root!${NC}"
   echo -e "${YELLOW}Run it as a regular user: bash install_meshtastic_sdr.sh${NC}"
   exit 1
fi

# Function to print section headers
print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

# Function to print success messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print warning messages
print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Function to print error messages
print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Start installation
clear
print_header "Meshtastic SDR Installation Script"
echo "This script will install:"
echo "  - GNU Radio and dependencies"
echo "  - gr-lora_sdr (LoRa transceiver for GNU Radio)"
echo "  - Meshtastic_SDR (Meshtastic decoder flowgraphs)"
echo "  - RTL-SDR drivers and tools"
echo ""
echo "Installation directory: $INSTALL_DIR"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Installation cancelled."
    exit 0
fi

# Create installation directory
print_header "Creating Installation Directory"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"
print_success "Created $INSTALL_DIR"

# Update package lists
print_header "Updating Package Lists"
sudo DEBIAN_FRONTEND=noninteractive apt update
print_success "Package lists updated"

# Check if gnuradio is already installed
print_header "Checking Existing Installations"
GNURADIO_INSTALLED=false
GR_LORA_INSTALLED=false
MESHTASTIC_INSTALLED=false

if command_exists gnuradio-companion; then
    print_warning "GNU Radio is already installed"
    GNURADIO_INSTALLED=true
    read -p "Reinstall GNU Radio and dependencies? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Skipping GNU Radio installation"
    else
        GNURADIO_INSTALLED=false
    fi
fi

if ldconfig -p | grep -q lora_sdr; then
    print_warning "gr-lora_sdr is already installed"
    GR_LORA_INSTALLED=true
    read -p "Rebuild and reinstall gr-lora_sdr? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Skipping gr-lora_sdr build"
    else
        GR_LORA_INSTALLED=false
    fi
fi

if [ -d "$INSTALL_DIR/meshtastic_sdr" ]; then
    print_warning "Meshtastic_SDR directory already exists"
    MESHTASTIC_INSTALLED=true
    read -p "Re-clone Meshtastic_SDR repositories? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Skipping Meshtastic_SDR clone"
    else
        MESHTASTIC_INSTALLED=false
    fi
fi

# Install system dependencies
if [ "$GNURADIO_INSTALLED" = false ]; then
    print_header "Installing System Dependencies"
    echo "This may take several minutes..."

    # Use -o Dpkg::Options to suppress interactive prompts
    # Install in stages to avoid udisks2 issues in containers
    sudo DEBIAN_FRONTEND=noninteractive apt install -y \
        -o Dpkg::Options::="--force-confdef" \
        -o Dpkg::Options::="--force-confold" \
        --no-install-recommends \
        build-essential \
        cmake \
        git \
        pkg-config \
        libboost-all-dev \
        liblog4cpp5-dev \
        swig \
        python3-numpy \
        python3-scipy \
        python3-dev \
        python3-pip \
        python3-zmq \
        libsndfile1-dev \
        libfftw3-dev \
        libvolk-dev

    print_success "Core dependencies installed"

    # Install GNU Radio packages separately (these might pull in udisks2)
    print_header "Installing GNU Radio"
    sudo DEBIAN_FRONTEND=noninteractive apt install -y \
        -o Dpkg::Options::="--force-confdef" \
        -o Dpkg::Options::="--force-confold" \
        --no-install-recommends \
        gnuradio \
        gnuradio-dev \
        gr-osmosdr

    print_success "GNU Radio installed"

    # Install SDR hardware support
    print_header "Installing SDR Support (RTL-SDR)"
    sudo DEBIAN_FRONTEND=noninteractive apt install -y \
        -o Dpkg::Options::="--force-confdef" \
        -o Dpkg::Options::="--force-confold" \
        --no-install-recommends \
        rtl-sdr \
        librtlsdr0 \
        librtlsdr-dev \
        libusb-1.0-0 \
        libusb-1.0-0-dev \
        usbutils

    print_success "RTL-SDR support installed"

    # Install UHD separately as it may be optional
    sudo DEBIAN_FRONTEND=noninteractive apt install -y \
        -o Dpkg::Options::="--force-confdef" \
        -o Dpkg::Options::="--force-confold" \
        --no-install-recommends \
        libuhd-dev || print_warning "UHD installation optional, continuing..."

    # Skip uhd-host if it causes issues
    sudo DEBIAN_FRONTEND=noninteractive apt install -y \
        -o Dpkg::Options::="--force-confdef" \
        -o Dpkg::Options::="--force-confold" \
        --no-install-recommends \
        uhd-host || print_warning "uhd-host skipped (not critical)"

    print_success "System dependencies installed"
else
    print_header "Verifying System Dependencies"
    # Still ensure build tools are present
    sudo DEBIAN_FRONTEND=noninteractive apt install -y \
        -o Dpkg::Options::="--force-confdef" \
        -o Dpkg::Options::="--force-confold" \
        --no-install-recommends \
        build-essential cmake git pkg-config
    print_success "Core build tools verified"
fi

# Configure RTL-SDR udev rules for non-root access
print_header "Configuring RTL-SDR Permissions"

# Check if running in container
if [ -f /.dockerenv ] || grep -q docker /proc/1/cgroup 2>/dev/null; then
    print_warning "Running in Docker container - udev rules already configured in image"
    print_warning "USB device access requires running container with --privileged and -v /dev/bus/usb:/dev/bus/usb"
else
    # On bare metal system, create udev rules
    if [ ! -f /etc/udev/rules.d/20-rtlsdr.rules ]; then
        sudo bash -c 'cat > /etc/udev/rules.d/20-rtlsdr.rules << EOF
# RTL-SDR v3/v4
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2838", MODE="0666", GROUP="plugdev"
# Older RTL-SDR dongles
SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2832", MODE="0666", GROUP="plugdev"
# Generic DVB-T dongles
SUBSYSTEM=="usb", ATTRS{idVendor}=="1209", ATTRS{idProduct}=="2832", MODE="0666", GROUP="plugdev"

# Disable USB autosuspend for RTL-SDR
ACTION=="add", SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2838", TEST=="power/control", ATTR{power/control}="on"
ACTION=="add", SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2832", TEST=="power/control", ATTR{power/control}="on"
EOF'
        sudo udevadm control --reload-rules 2>/dev/null || print_warning "udevadm not available (OK in container)"
        sudo udevadm trigger 2>/dev/null || print_warning "udevadm trigger not available (OK in container)"
        print_success "RTL-SDR udev rules configured"
    else
        print_warning "RTL-SDR udev rules already exist"
    fi

    # Blacklist DVB-T driver to prevent conflicts
    if [ ! -f /etc/modprobe.d/blacklist-rtl.conf ]; then
        sudo bash -c 'cat > /etc/modprobe.d/blacklist-rtl.conf << EOF
# Blacklist DVB-T drivers that conflict with RTL-SDR
blacklist dvb_usb_rtl28xxu
blacklist rtl2832
blacklist rtl2830
EOF'
        print_success "DVB-T drivers blacklisted"
        print_warning "Reboot or replug RTL-SDR for blacklist to take effect"
    else
        print_warning "DVB-T blacklist already exists"
    fi
fi

# Add user to plugdev group
print_header "Adding User to plugdev Group"

# Get actual username (handle various environments)
ACTUAL_USER="${USER:-$(whoami)}"

if [ -z "$ACTUAL_USER" ] || [ "$ACTUAL_USER" = "root" ]; then
    print_warning "Cannot determine non-root username or running as root"
    print_warning "Skipping user group modification"
else
    # Check if plugdev group exists
    if getent group plugdev >/dev/null 2>&1; then
        # Check if user is already in group
        if groups "$ACTUAL_USER" | grep -q plugdev; then
            print_warning "User $ACTUAL_USER already in plugdev group"
        else
            sudo usermod -a -G plugdev "$ACTUAL_USER"
            print_success "User $ACTUAL_USER added to plugdev group"
            print_warning "You may need to log out and back in for group changes to take effect"
        fi
    else
        # Create plugdev group if it doesn't exist
        print_warning "plugdev group does not exist, creating it..."
        sudo groupadd plugdev
        sudo usermod -a -G plugdev "$ACTUAL_USER"
        print_success "Created plugdev group and added user $ACTUAL_USER"
    fi
fi

# Install Python dependencies
print_header "Installing Python Dependencies"
if python3 -c "import meshtastic" 2>/dev/null; then
    print_warning "Meshtastic Python library already installed"
    python3 -c "import meshtastic; print('  Version: ' + meshtastic.__version__)" 2>/dev/null || true
    read -p "Reinstall/update Python packages? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pip3 install --user --break-system-packages --upgrade meshtastic protobuf cryptography
        print_success "Python dependencies updated"
    else
        print_warning "Skipping Python package installation"
    fi
else
    pip3 install --user --break-system-packages meshtastic protobuf cryptography
    print_success "Python dependencies installed"
fi

# Add ~/.local/bin to PATH if not already there
print_header "Configuring PATH"
LOCAL_BIN="$HOME/.local/bin"
if [ -d "$LOCAL_BIN" ]; then
    if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
        print_warning "Adding $LOCAL_BIN to PATH"
        
        # Add to current session
        export PATH="$LOCAL_BIN:$PATH"
        
        # Add to .bashrc for future sessions
        if [ -f "$HOME/.bashrc" ]; then
            if ! grep -q "/.local/bin" "$HOME/.bashrc"; then
                echo "" >> "$HOME/.bashrc"
                echo "# Added by Meshtastic SDR installation script" >> "$HOME/.bashrc"
                echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
                print_success "Added $LOCAL_BIN to PATH in .bashrc"
            else
                print_warning ".bashrc already contains .local/bin PATH entry"
            fi
        fi
        
        # Add to .profile as fallback
        if [ -f "$HOME/.profile" ]; then
            if ! grep -q "/.local/bin" "$HOME/.profile"; then
                echo "" >> "$HOME/.profile"
                echo "# Added by Meshtastic SDR installation script" >> "$HOME/.profile"
                echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.profile"
                print_success "Added $LOCAL_BIN to PATH in .profile"
            fi
        fi
        
        print_success "PATH configured for current and future sessions"
    else
        print_success "$LOCAL_BIN already in PATH"
    fi
else
    print_warning "$LOCAL_BIN does not exist yet (will be created by pip)"
fi

# Clone and build gr-lora_sdr
if [ "$GR_LORA_INSTALLED" = false ]; then
    print_header "Installing gr-lora_sdr"
    cd "$INSTALL_DIR"

    if [ -d "gr-lora_sdr" ]; then
        print_warning "gr-lora_sdr directory exists, removing..."
        rm -rf gr-lora_sdr
    fi

    echo "Cloning gr-lora_sdr repository..."
    git clone "$GR_LORA_SDR_REPO"
    cd gr-lora_sdr

    echo "Building gr-lora_sdr..."
    mkdir build
    cd build
    cmake .. -DCMAKE_INSTALL_PREFIX=/usr/local
    make -j$(nproc)
    sudo make install

    # CRITICAL STEP
    print_warning "Running sudo ldconfig (CRITICAL STEP)..."
    sudo ldconfig
    print_success "gr-lora_sdr installed"
else
    print_header "Verifying gr-lora_sdr Installation"
    print_success "gr-lora_sdr already installed, skipping build"
fi

# Verify installation
print_header "Verifying gr-lora_sdr Installation"
if ldconfig -p | grep -q lora_sdr; then
    print_success "gr-lora_sdr library found in ldconfig"
    
    # Show where it's installed
    LORA_LIB=$(ldconfig -p | grep lora_sdr | head -n 1 | awk '{print $NF}')
    if [ -n "$LORA_LIB" ] && [ -f "$LORA_LIB" ]; then
        print_success "gr-lora_sdr shared library found at: $LORA_LIB"
    else
        # Check common locations
        if ls /usr/local/lib/libgnuradio-lora_sdr.so* >/dev/null 2>&1; then
            print_success "gr-lora_sdr shared library found in /usr/local/lib/"
        elif ls /usr/lib/*/libgnuradio-lora_sdr.so* >/dev/null 2>&1; then
            print_success "gr-lora_sdr shared library found in /usr/lib/"
        else
            print_warning "gr-lora_sdr library registered but file location unclear (this is OK)"
        fi
    fi
else
    print_error "gr-lora_sdr library NOT found in ldconfig"
    print_error "Installation may have failed!"
    exit 1
fi

# Clone Meshtastic_SDR project (original)
if [ "$MESHTASTIC_INSTALLED" = false ]; then
    print_header "Installing Meshtastic_SDR (Original)"
    cd "$INSTALL_DIR"

    if [ -d "meshtastic_sdr" ]; then
        print_warning "meshtastic_sdr directory exists, removing..."
        rm -rf meshtastic_sdr
    fi

    echo "Cloning Meshtastic_SDR repository..."
    git clone "$MESHTASTIC_SDR_REPO"
    print_success "Meshtastic_SDR cloned"
else
    print_header "Meshtastic_SDR Already Installed"
    print_success "Using existing Meshtastic_SDR installation"
    cd "$INSTALL_DIR"
fi

# Clone enhanced decoder (optional)
if [ "$MESHTASTIC_INSTALLED" = false ]; then
    print_header "Installing Enhanced Decoder (tom-acco fork)"
    cd "$INSTALL_DIR"

    if [ -d "meshtastic_sdr_enhanced" ]; then
        print_warning "meshtastic_sdr_enhanced directory exists, removing..."
        rm -rf meshtastic_sdr_enhanced
    fi

    echo "Cloning enhanced decoder repository..."
    git clone "$ENHANCED_DECODER_REPO" meshtastic_sdr_enhanced
    print_success "Enhanced decoder cloned"
else
    print_success "Using existing enhanced decoder installation"
fi

# Create convenience scripts
print_header "Creating Convenience Scripts"

# US receiver script
if [ ! -f "$INSTALL_DIR/run_us_receiver.sh" ]; then
    cat > "$INSTALL_DIR/run_us_receiver.sh" << 'EOF'
#!/bin/bash
# Launch US Meshtastic receiver for RTL-SDR
cd "$(dirname "$0")/meshtastic_sdr/gnuradio scripts/RX"
gnuradio-companion "Meshtastic_US_62KHz_RTLSDR.grc"
EOF
    chmod +x "$INSTALL_DIR/run_us_receiver.sh"
    print_success "Created run_us_receiver.sh"
else
    print_warning "run_us_receiver.sh already exists, skipping"
fi

# EU receiver script
if [ ! -f "$INSTALL_DIR/run_eu_receiver.sh" ]; then
    cat > "$INSTALL_DIR/run_eu_receiver.sh" << 'EOF'
#!/bin/bash
# Launch EU Meshtastic receiver for RTL-SDR
cd "$(dirname "$0")/meshtastic_sdr/gnuradio scripts/RX"
gnuradio-companion "Meshtastic_EU_62KHz_RTLSDR.grc"
EOF
    chmod +x "$INSTALL_DIR/run_eu_receiver.sh"
    print_success "Created run_eu_receiver.sh"
else
    print_warning "run_eu_receiver.sh already exists, skipping"
fi

# Decoder script (original)
if [ ! -f "$INSTALL_DIR/run_decoder.sh" ]; then
    cat > "$INSTALL_DIR/run_decoder.sh" << 'EOF'
#!/bin/bash
# Run Meshtastic decoder
# Usage: ./run_decoder.sh [port]
# Default port is 20004 (LongFast)
PORT=${1:-20004}
cd "$(dirname "$0")/meshtastic_sdr/python scripts"
python3 meshtastic_gnuradio_RX.py -n 127.0.0.1 -p "$PORT"
EOF
    chmod +x "$INSTALL_DIR/run_decoder.sh"
    print_success "Created run_decoder.sh"
else
    print_warning "run_decoder.sh already exists, skipping"
fi

# Enhanced decoder script
if [ ! -f "$INSTALL_DIR/run_enhanced_decoder.sh" ]; then
    cat > "$INSTALL_DIR/run_enhanced_decoder.sh" << 'EOF'
#!/bin/bash
# Run Enhanced Meshtastic decoder (tom-acco fork)
# Usage: ./run_enhanced_decoder.sh [port]
# Default port is 20004 (LongFast)
PORT=${1:-20004}
cd "$(dirname "$0")/meshtastic_sdr_enhanced/script"
python3 meshtastic_gnuradio_decoder.py -n 127.0.0.1 -p "$PORT"
EOF
    chmod +x "$INSTALL_DIR/run_enhanced_decoder.sh"
    print_success "Created run_enhanced_decoder.sh"
else
    print_warning "run_enhanced_decoder.sh already exists, skipping"
fi

# Test RTL-SDR script
if [ ! -f "$INSTALL_DIR/test_rtlsdr.sh" ]; then
    cat > "$INSTALL_DIR/test_rtlsdr.sh" << 'EOF'
#!/bin/bash
# Test RTL-SDR connectivity
echo "Testing RTL-SDR device..."
echo "Press Ctrl+C to stop the test"
echo ""
rtl_test -t
EOF
    chmod +x "$INSTALL_DIR/test_rtlsdr.sh"
    print_success "Created test_rtlsdr.sh"
else
    print_warning "test_rtlsdr.sh already exists, skipping"
fi

# Create README
print_header "Creating README"
cat > "$INSTALL_DIR/README.md" << 'EOF'
# Meshtastic SDR Installation

## Installation Complete!

Your Meshtastic SDR receiver is now installed and ready to use.

## Quick Start Guide

### 1. Test Your RTL-SDR
```bash
./test_rtlsdr.sh
```
This will verify your RTL-SDR is detected and working.

### 2. Launch the GNU Radio Receiver

For US users:
```bash
./run_us_receiver.sh
```

For EU users:
```bash
./run_eu_receiver.sh
```

This will open GNU Radio Companion with the appropriate flowgraph.
Click the "Execute" (play) button to start receiving.

### 3. Run the Decoder (in a separate terminal)

Original decoder:
```bash
./run_decoder.sh
```

Enhanced decoder (with multi-key support):
```bash
./run_enhanced_decoder.sh
```

For different Meshtastic presets, specify the port:
```bash
./run_decoder.sh 20000    # ShortFast
./run_decoder.sh 20004    # LongFast (default, most common)
./run_decoder.sh 20005    # LongModerate
```

## Directory Structure

```
meshtastic_sdr_install/
├── gr-lora_sdr/              # LoRa transceiver for GNU Radio
├── meshtastic_sdr/           # Original Meshtastic_SDR project
├── meshtastic_sdr_enhanced/  # Enhanced decoder with multi-key support
├── run_us_receiver.sh        # Launch US receiver
├── run_eu_receiver.sh        # Launch EU receiver
├── run_decoder.sh            # Run original decoder
├── run_enhanced_decoder.sh   # Run enhanced decoder
├── test_rtlsdr.sh           # Test RTL-SDR hardware
└── README.md                # This file
```

## Understanding the Output

### Expected Behavior
You will see a mix of:
- **Valid decoded messages**: Actual Meshtastic traffic with readable content
- **"INVALID PROTOBUF" errors**: Normal! These occur when receiving:
  - Encrypted messages with different keys
  - Corrupted packets
  - Non-Meshtastic LoRa traffic
  - Partial packet captures

This is completely normal and indicates your system is working correctly!

## Troubleshooting

### RTL-SDR Not Detected
```bash
# Check if device is connected
lsusb | grep Realtek

# Test with rtl_test
./test_rtlsdr.sh
```

### No LoRa Blocks in GNU Radio Companion
```bash
# Verify gr-lora_sdr installation
ldconfig -p | grep lora_sdr

# If not found, reinstall
cd gr-lora_sdr/build
sudo make install
sudo ldconfig
```

### No Messages Received
- Verify you're tuned to the correct frequency for your region
- Check antenna connection
- Ensure local Meshtastic nodes exist in your area
- Try increasing RF gain in the flowgraph (start at 40 dB)

## Port Mapping

The GNU Radio flowgraph sends data to these TCP ports:
- 20000: ShortFast
- 20001: ShortSlow
- 20002: MediumFast
- 20003: MediumSlow
- 20004: **LongFast** (most common, default)
- 20005: LongModerate
- 20006: LongSlow
- 20007: VeryLongSlow

## Adding Visualization

To add visual displays (waterfall, spectrum):
1. Open the .grc file in GNU Radio Companion
2. Add "QT GUI Waterfall Sink" or "QT GUI Frequency Sink" blocks
3. Connect them to the RTL-SDR Source output
4. Configure with sample_rate and center_freq variables
5. Save and re-run

## Resources

- gr-lora_sdr: https://github.com/tapparelj/gr-lora_sdr
- Meshtastic_SDR: https://gitlab.com/crankylinuxuser/meshtastic_sdr
- Enhanced Decoder: https://github.com/tom-acco/Meshtastic_SDR
- Meshtastic Documentation: https://meshtastic.org

## Important Notes

1. **Group Changes**: You were added to the `plugdev` group. Log out and back in for this to take effect.
2. **"INVALID PROTOBUF" is Normal**: Don't worry about these errors - they're expected!
3. **Default Channel**: The decoder uses the default Meshtastic key (AQ==) for the public channel.

Enjoy monitoring Meshtastic traffic!
EOF
print_success "Created README.md"

# Create desktop shortcuts (optional)
print_header "Creating Desktop Shortcuts"
DESKTOP_DIR="$HOME/Desktop"
if [ -d "$DESKTOP_DIR" ]; then
    cat > "$DESKTOP_DIR/Meshtastic_US_Receiver.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Meshtastic US Receiver
Comment=Launch Meshtastic SDR receiver for US frequencies
Exec=$INSTALL_DIR/run_us_receiver.sh
Icon=gnuradio-grc
Terminal=false
Categories=HamRadio;Network;
EOF
    chmod +x "$DESKTOP_DIR/Meshtastic_US_Receiver.desktop"
    
    cat > "$DESKTOP_DIR/Meshtastic_EU_Receiver.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Meshtastic EU Receiver
Comment=Launch Meshtastic SDR receiver for EU frequencies
Exec=$INSTALL_DIR/run_eu_receiver.sh
Icon=gnuradio-grc
Terminal=false
Categories=HamRadio;Network;
EOF
    chmod +x "$DESKTOP_DIR/Meshtastic_EU_Receiver.desktop"
    
    print_success "Desktop shortcuts created"
else
    print_warning "Desktop directory not found, skipping desktop shortcuts"
fi

# Final verification
print_header "Final Verification"

echo "Checking installations..."
ERRORS=0

if command_exists gnuradio-companion; then
    print_success "GNU Radio Companion: Installed"
else
    print_error "GNU Radio Companion: NOT FOUND"
    ((ERRORS++))
fi

if command_exists rtl_test; then
    print_success "RTL-SDR tools: Installed"
    
    # Show RTL-SDR library info
    if ldconfig -p | grep -q librtlsdr; then
        print_success "RTL-SDR library: Registered with ldconfig"
    else
        print_warning "RTL-SDR library: Found but not in ldconfig cache"
    fi
else
    print_error "RTL-SDR tools: NOT FOUND"
    ((ERRORS++))
fi

if ldconfig -p | grep -q lora_sdr; then
    print_success "gr-lora_sdr library: Installed and registered"
else
    print_error "gr-lora_sdr library: NOT FOUND in ldconfig"
    ((ERRORS++))
fi

if python3 -c "import meshtastic" 2>/dev/null; then
    print_success "Meshtastic Python library: Installed"
else
    print_error "Meshtastic Python library: NOT FOUND"
    ((ERRORS++))
fi

if [ -f "$INSTALL_DIR/run_us_receiver.sh" ]; then
    print_success "Convenience scripts: Created"
else
    print_error "Convenience scripts: NOT FOUND"
    ((ERRORS++))
fi

# RTL-SDR hardware check (only if not in Docker or if USB is available)
echo ""
print_header "RTL-SDR Hardware Check"
if lsusb | grep -qi realtek 2>/dev/null; then
    print_success "RTL-SDR hardware detected!"
    lsusb | grep -i realtek | head -n 1
elif [ -f /.dockerenv ] || grep -q docker /proc/1/cgroup 2>/dev/null; then
    print_warning "Running in Docker - RTL-SDR check skipped"
    print_warning "Make sure to run container with: --privileged -v /dev/bus/usb:/dev/bus/usb"
else
    print_warning "No RTL-SDR hardware detected (this is OK if not connected)"
fi

# Installation summary
print_header "Installation Summary"

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                ║${NC}"
    echo -e "${GREEN}║     Installation Completed Successfully!      ║${NC}"
    echo -e "${GREEN}║                                                ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Installation directory: $INSTALL_DIR"
    echo ""
    echo "Next steps:"
    echo ""
    echo "=== HEADLESS MODE (No GUI - Recommended for SSH/Docker) ==="
    echo "  1. cd $INSTALL_DIR"
    echo "  2. Test RTL-SDR: ./test_rtlsdr.sh"
    echo "  3. Start receiver (headless):"
    echo "     cd meshtastic_sdr/gnuradio\ scripts/RX/"
    echo "     python3 Meshtastic_US_62KHz_RTLSDR.py --no-gui"
    echo "     (or Meshtastic_EU_62KHz_RTLSDR.py for EU)"
    echo "  4. In another terminal/tmux: ./run_decoder.sh"
    echo ""
    echo "=== GUI MODE (Requires X11/Display) ==="
    echo "  1. cd $INSTALL_DIR"
    echo "  2. Run: ./run_us_receiver.sh (or run_eu_receiver.sh)"
    echo "  3. Click the play button in GNU Radio Companion"
    echo "  4. In another terminal: ./run_decoder.sh"
    echo ""
    
    # Docker-specific instructions
    if [ -f /.dockerenv ] || grep -q docker /proc/1/cgroup 2>/dev/null; then
        echo "🐋 DOCKER DETECTED - Headless Mode Instructions:"
        echo "  • Container must run with: --privileged -v /dev/bus/usb:/dev/bus/usb"
        echo "  • Use headless mode (--no-gui) since there's no display"
        echo "  • Use tmux or multiple SSH sessions for receiver + decoder"
        echo ""
        echo "  Quick start:"
        echo "    Terminal 1: cd $INSTALL_DIR/meshtastic_sdr/gnuradio\\ scripts/RX/"
        echo "                python3 Meshtastic_US_62KHz_RTLSDR.py --no-gui"
        echo "    Terminal 2: cd $INSTALL_DIR && ./run_decoder.sh"
        echo ""
    fi
    
    echo "Read $INSTALL_DIR/README.md for detailed usage instructions."
    echo ""
else
    echo -e "${RED}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║                                                ║${NC}"
    echo -e "${RED}║  Installation Completed With $ERRORS Error(s)       ║${NC}"
    echo -e "${RED}║                                                ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Please review the errors above and try reinstalling."
    exit 1
fi
