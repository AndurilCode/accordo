# Installation Script Interactive Input Fix

## Issue
When running the installation script via `curl | bash`, the script terminates when it tries to read user input because stdin is consumed by the curl process.

## Solutions

### Solution 1: Download and Run Separately (Recommended)
```bash
# Download the script first
curl -fsSL https://raw.githubusercontent.com/AndurilCode/workflow-commander/refs/heads/main/install.sh -o install.sh

# Make it executable and run
chmod +x install.sh
./install.sh
```

### Solution 2: Use Environment Variable for Non-Interactive Installation
```bash
# For global installation (default, recommended)
INSTALL_METHOD=global curl -fsSL https://raw.githubusercontent.com/AndurilCode/workflow-commander/refs/heads/main/install.sh | bash

# For virtual environment installation with uv
INSTALL_METHOD=venv_uv curl -fsSL https://raw.githubusercontent.com/AndurilCode/workflow-commander/refs/heads/main/install.sh | bash

# For virtual environment installation with pip
INSTALL_METHOD=venv_pip curl -fsSL https://raw.githubusercontent.com/AndurilCode/workflow-commander/refs/heads/main/install.sh | bash
```

### Solution 3: Force TTY Input (Alternative)
The modified script now includes `</dev/tty` to force reading from terminal even when piped:
```bash
curl -fsSL https://raw.githubusercontent.com/AndurilCode/workflow-commander/refs/heads/main/install.sh | bash
```

## Installation Methods Available

1. **global** - Global installation using pipx (recommended)
   - Accessible from anywhere
   - Automatically installs pipx if needed

2. **venv_uv** - Virtual environment installation using uv
   - Only available if you're in a virtual environment and uv is installed

3. **venv_pip** - Virtual environment installation using pip
   - Only available if you're in a virtual environment

## Fix Applied
The installation script has been modified to:
1. Support environment variable `INSTALL_METHOD` for non-interactive installation
2. Use `</dev/tty` to properly read input even when script is piped through curl
3. Provide clear error messages and fallback options

## Verification
After installation, verify with:
```bash
workflow-commander --version
```