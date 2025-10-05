#!/bin/bash

# Setup script for rpi-rgb-led-matrix library
# Run this on your Raspberry Pi

set -e

echo "=== Installing rpi-rgb-led-matrix library ==="

# Update system
echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install dependencies
echo "Installing dependencies..."
sudo apt install -y git python3-dev python3-pillow libatlas-base-dev

# Clone and build the library
echo "Cloning rpi-rgb-led-matrix repository..."
cd /home/hung
if [ -d "rpi-rgb-led-matrix" ]; then
    echo "Directory already exists, pulling latest changes..."
    cd rpi-rgb-led-matrix
    git pull
else
    git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
    cd rpi-rgb-led-matrix
fi

# Build the library
echo "Building the library..."
make build-python PYTHON=$(which python3)

# Install Python bindings
echo "Installing Python bindings..."
sudo make install-python PYTHON=$(which python3)

# Test basic functionality
echo "=== Testing LED Matrix ==="
echo "Running basic text example..."
echo "You should see 'Hello world!' scrolling on your LED matrix"
echo "Press Ctrl+C to stop the test"

# Run with Adafruit bonnet settings for 64x64 panel
cd rpi-rgb-led-matrix
sudo ./examples-api-use/text-example \
    --led-rows=64 \
    --led-cols=64 \
    --led-gpio-mapping=adafruit-hat \
    --led-brightness=50 \
    --led-slowdown-gpio=4 \
    -t "Hello world!"

echo ""
echo "=== Setup Complete! ==="
echo "If you saw text scrolling on your LED matrix, the hardware is working correctly."
echo "If not, check your connections and try running with different --led-slowdown-gpio values (1-4)"
