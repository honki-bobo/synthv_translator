#!/usr/bin/env bash

echo "============================================"
echo "  SynthV Translator - macOS Installer"
echo "============================================"
echo

# -----------------------------------------------
# Step 1: Check / Install Homebrew
# -----------------------------------------------
echo "[Step 1/5] Checking for Homebrew..."

if command -v brew &>/dev/null; then
    echo "  Found: $(brew --version | head -n 1)"
else
    echo "  Homebrew not found. Installing..."
    echo
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Add brew to PATH for Apple Silicon Macs
    if [ -f /opt/homebrew/bin/brew ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi

    if command -v brew &>/dev/null; then
        echo "  Homebrew installed: $(brew --version | head -n 1)"
    else
        echo "  WARNING: Homebrew installation may have failed."
        echo "  Please install Homebrew manually from https://brew.sh"
    fi
fi

echo

# -----------------------------------------------
# Step 2: Check / Install Python
# -----------------------------------------------
echo "[Step 2/5] Checking for Python..."

if command -v python3 &>/dev/null; then
    echo "  Found: $(python3 --version)"
else
    echo "  Python not found. Installing via Homebrew..."
    brew install python

    if command -v python3 &>/dev/null; then
        echo "  Python installed: $(python3 --version)"
    else
        echo "  WARNING: Python installation failed."
        echo "  Please install Python manually: brew install python"
    fi
fi

echo

# -----------------------------------------------
# Step 3: Check / Install eSpeak NG
# -----------------------------------------------
echo "[Step 3/5] Checking for eSpeak NG..."

if command -v espeak-ng &>/dev/null; then
    echo "  Found: $(espeak-ng --version | head -n 1)"
else
    echo "  eSpeak NG not found. Installing via Homebrew..."
    brew install espeak-ng

    if command -v espeak-ng &>/dev/null; then
        echo "  eSpeak NG installed: $(espeak-ng --version | head -n 1)"
    else
        echo "  WARNING: eSpeak NG installation failed."
        echo "  Please install eSpeak NG manually: brew install espeak-ng"
    fi
fi

echo

# -----------------------------------------------
# Step 4: Install Python dependencies
# -----------------------------------------------
echo "[Step 4/5] Installing Python dependencies..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

pip3 install -r "$SCRIPT_DIR/requirements.txt"
if [ $? -ne 0 ]; then
    echo
    echo "  WARNING: pip install failed. You can retry manually with:"
    echo "  pip3 install -r requirements.txt"
fi

echo

# -----------------------------------------------
# Step 5: Copy inserter script to SynthV
# -----------------------------------------------
echo "[Step 5/5] Copying inserter script to Synthesizer V..."

INSERTER_SRC="$SCRIPT_DIR/synthv_translator_inserter.js"

if [ ! -f "$INSERTER_SRC" ]; then
    echo "  WARNING: synthv_translator_inserter.js not found in project directory."
    echo "  Skipping this step."
else
    SYNTHV_SCRIPTS=""

    # Check system-level path
    if [ -d "/Library/Application Support/Dreamtonics/Synthesizer V Studio 2/scripts" ]; then
        SYNTHV_SCRIPTS="/Library/Application Support/Dreamtonics/Synthesizer V Studio 2/scripts"
    fi

    # Check user-level path (takes precedence)
    if [ -d "$HOME/Library/Application Support/Dreamtonics/Synthesizer V Studio 2/scripts" ]; then
        SYNTHV_SCRIPTS="$HOME/Library/Application Support/Dreamtonics/Synthesizer V Studio 2/scripts"
    fi

    if [ -n "$SYNTHV_SCRIPTS" ]; then
        cp "$INSERTER_SRC" "$SYNTHV_SCRIPTS/"
        echo "  Copied to: $SYNTHV_SCRIPTS"
        echo "  Open Synthesizer V and go to Scripts > Rescan to load the script."
    else
        echo "  Synthesizer V scripts folder not found."
        echo
        echo "  If Synthesizer V is installed, you can find the scripts folder by"
        echo "  opening Synthesizer V and going to Scripts > Open Scripts Folder."
        echo "  Then copy synthv_translator_inserter.js there manually."
    fi
fi

echo

# -----------------------------------------------
# Done
# -----------------------------------------------
echo "============================================"
echo "  Installation complete!"
echo "============================================"
echo
echo "  To test the translator, run:"
echo "  python3 synthv_translator.py \"Hallo Welt\""
echo
