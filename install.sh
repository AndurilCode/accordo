#!/bin/bash

# Accordo Global Installation Script
# This script installs accordo with support for pipx (global) and uv (venv)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Installation method variable
INSTALL_METHOD=""

# Print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python 3.12+ is available
check_python() {
    print_status "Checking Python version..."
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed or not in PATH"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    REQUIRED_VERSION="3.12"
    
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 12) else 1)"; then
        print_success "Python ${PYTHON_VERSION} detected (>= ${REQUIRED_VERSION})"
    else
        print_error "Python ${REQUIRED_VERSION}+ is required. Found: ${PYTHON_VERSION}"
        print_status "Please upgrade Python and try again."
        exit 1
    fi
}

# Detect environment and available tools
detect_environment() {
    print_status "Detecting environment and available tools..."
    
    # Check if we're in a virtual environment
    if [[ -n "$VIRTUAL_ENV" ]]; then
        print_status "Virtual environment detected: $VIRTUAL_ENV"
        IN_VENV=true
    else
        print_status "No virtual environment detected"
        IN_VENV=false
    fi
    
    # Check available tools
    HAS_PIPX=false
    HAS_UV=false
    
    if command -v pipx &> /dev/null; then
        print_status "pipx is available"
        HAS_PIPX=true
    fi
    
    if command -v uv &> /dev/null; then
        print_status "uv is available"
        HAS_UV=true
    fi
}

# Let user choose installation method
choose_installation_method() {
    # Check if INSTALL_METHOD is already set via environment variable
    if [[ -n "$INSTALL_METHOD" ]]; then
        print_success "Using preset installation method: $INSTALL_METHOD"
        return 0
    fi
    
    echo
    print_status "Choose installation method:"
    echo
    
    local options=()
    local choice_num=1
    
    # Option 1: Always offer global installation first (pipx)
    echo "${choice_num}. 🌍 Global installation (pipx) - Recommended"
    echo "   Installs accordo globally, accessible from anywhere"
    if [[ "$HAS_PIPX" == true ]]; then
        echo "   ✅ pipx is available"
    else
        echo "   ⚠️  pipx will be installed automatically"
    fi
    options[$choice_num]="global"
    ((choice_num++))
    
    # Option 2: Virtual environment installation (if in venv and uv available)
    if [[ "$IN_VENV" == true && "$HAS_UV" == true ]]; then
        echo "${choice_num}. 📦 Virtual environment installation (uv)"
        echo "   Installs in current virtual environment: $(basename $VIRTUAL_ENV)"
        echo "   ✅ uv is available"
        options[$choice_num]="venv_uv"
        ((choice_num++))
    fi
    
    # Option 3: Virtual environment with pip (if in venv)
    if [[ "$IN_VENV" == true ]]; then
        echo "${choice_num}. 📦 Virtual environment installation (pip)"
        echo "   Installs in current virtual environment using pip"
        options[$choice_num]="venv_pip"
        ((choice_num++))
    fi
    
    echo
    
    # Get user choice
    local max_choice=$((choice_num - 1))
    while true; do
        read -p "Enter your choice (1-${max_choice}) [default: 1]: " choice </dev/tty
        
        # Default to 1 if empty
        if [[ -z "$choice" ]]; then
            choice=1
        fi
        
        if [[ "$choice" =~ ^[0-9]+$ ]] && [[ "$choice" -ge 1 ]] && [[ "$choice" -le "$max_choice" ]]; then
            INSTALL_METHOD="${options[$choice]}"
            break
        else
            print_error "Invalid choice. Please enter a number between 1 and ${max_choice}."
        fi
    done
    
    print_success "Selected installation method: $INSTALL_METHOD"
}

# Check if pipx is available and install if needed
ensure_pipx() {
    if command -v pipx &> /dev/null; then
        print_success "pipx is available"
        return 0
    fi
    
    print_warning "pipx not found. Installing pipx..."
    
    # Try to install pipx using different methods
    if command -v apt &> /dev/null; then
        # Ubuntu/Debian
        print_status "Installing pipx using apt..."
        if command -v sudo &> /dev/null; then
            sudo apt update && sudo apt install -y pipx
        else
            print_error "sudo not available. Please install pipx manually:"
            echo "  sudo apt install pipx"
            exit 1
        fi
    elif command -v brew &> /dev/null; then
        # macOS with Homebrew
        print_status "Installing pipx using Homebrew..."
        brew install pipx
    elif command -v pip3 &> /dev/null; then
        # Fallback to pip3 --user
        print_status "Installing pipx using pip3..."
        pip3 install --user pipx
        
        # Add to PATH if needed
        local user_bin="$HOME/.local/bin"
        if [[ -d "$user_bin" ]] && [[ ":$PATH:" != *":$user_bin:"* ]]; then
            export PATH="$user_bin:$PATH"
        fi
    else
        print_error "Could not install pipx automatically."
        print_status "Please install pipx manually and run this script again:"
        echo "  # Ubuntu/Debian:"
        echo "  sudo apt install pipx"
        echo "  # macOS:"
        echo "  brew install pipx"
        echo "  # Other systems:"
        echo "  pip3 install --user pipx"
        exit 1
    fi
    
    # Verify pipx installation
    if command -v pipx &> /dev/null; then
        print_success "pipx installed successfully"
        
        # Ensure pipx path is set up
        print_status "Ensuring pipx path is configured..."
        pipx ensurepath --force
    else
        print_error "pipx installation failed"
        exit 1
    fi
}

# Install accordo
install_workflow_commander() {
    # Smart installation source detection:
    # - For development: If running from accordo project directory, install from local source
    # - For end users: Install from PyPI package (default behavior)
    # This allows the same script to work for both development and public installation
    local install_source="accordo-workflow-mcp"
    if [[ -f "pyproject.toml" ]] && grep -q '"accordo-workflow-mcp"' pyproject.toml; then
        # We're in the accordo project directory, install from local source for development
        install_source="."
        print_status "Detected accordo project directory - installing from local source"
    else
        # Standard end-user installation from PyPI - works from any directory
        print_status "Installing accordo from PyPI"
    fi
    
    case "$INSTALL_METHOD" in
        "global")
            print_status "Installing accordo globally using pipx..."
            ensure_pipx
            if pipx install --force "$install_source"; then
                print_success "accordo installed globally with pipx"
            else
                print_error "Failed to install accordo with pipx"
                if [[ "$install_source" == "accordo-workflow-mcp" ]]; then
                    print_status "This may be because the package is not yet available on PyPI."
                    print_status "Please check if the package name is correct or try installing from source."
                fi
                exit 1
            fi
            ;;
        "venv_uv")
            print_status "Installing accordo in virtual environment using uv..."
            if ! command -v uv &> /dev/null; then
                print_error "uv not available"
                exit 1
            fi
            if uv pip install --force-reinstall "$install_source"; then
                print_success "accordo installed in virtual environment with uv"
            else
                print_error "Failed to install accordo with uv"
                if [[ "$install_source" == "accordo-workflow-mcp" ]]; then
                    print_status "This may be because the package is not yet available on PyPI."
                    print_status "Please check if the package name is correct or try installing from source."
                fi
                exit 1
            fi
            ;;
        "venv_pip")
            print_status "Installing accordo in virtual environment using pip..."
            if pip install --force-reinstall "$install_source"; then
                print_success "accordo installed in virtual environment with pip"
            else
                print_error "Failed to install accordo with pip"
                if [[ "$install_source" == "accordo-workflow-mcp" ]]; then
                    print_status "This may be because the package is not yet available on PyPI."
                    print_status "Please check if the package name is correct or try installing from source."
                fi
                exit 1
            fi
            ;;
        *)
            print_error "Unknown installation method: $INSTALL_METHOD"
            exit 1
            ;;
    esac
}

# Verify installation
verify_installation() {
    print_status "Verifying installation..."
    
    # For global installation, ensure PATH is set up
    if [[ "$INSTALL_METHOD" == "global" ]]; then
        # Refresh PATH for pipx binaries
        if [[ -d "$HOME/.local/bin" ]] && [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
            export PATH="$HOME/.local/bin:$PATH"
        fi
    fi
    
    if command -v accordo &> /dev/null; then
        VERSION=$(accordo --version 2>/dev/null || echo "Unknown")
        print_success "accordo is accessible: $VERSION"
        return 0
    else
        print_warning "accordo not found in PATH"
        
        if [[ "$INSTALL_METHOD" == "global" ]]; then
            print_status "Trying to refresh PATH..."
            
            # Try to source common shell configs
            for config in ~/.bashrc ~/.zshrc ~/.profile; do
                if [[ -f "$config" ]]; then
                    source "$config" 2>/dev/null || true
                fi
            done
            
            # Check again
            if command -v accordo &> /dev/null; then
                VERSION=$(accordo --version 2>/dev/null || echo "Unknown")
                print_success "accordo is now accessible: $VERSION"
            else
                print_warning "accordo still not in PATH"
                print_status "You may need to restart your terminal or run:"
                echo "  source ~/.bashrc  # or ~/.zshrc"
                print_status "Or manually add pipx bin directory to PATH:"
                echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
            fi
        else
            print_status "Make sure your virtual environment is activated:"
            echo "  source $VIRTUAL_ENV/bin/activate"
        fi
    fi
}

# Display usage examples
show_usage_examples() {
    print_success "Installation complete! Here are some usage examples:"
    echo
    echo "📋 List supported platforms:"
    echo "   accordo list-platforms"
    echo
    echo "🔧 Interactive configuration:"
    echo "   accordo configure"
    echo
    echo "⚡ Quick non-interactive setup:"
    echo "   accordo configure -p cursor -s accordo -y"
    echo "   accordo configure -p claude-code -s accordo -y"
    echo
    echo "🚀 Deploy workflow guidelines to AI assistants:"
    echo "   accordo bootstrap-rules              # Deploy to all assistants"
    echo "   accordo bootstrap-rules cursor       # Deploy to Cursor only"
    echo "   accordo bootstrap-rules --force all  # Overwrite existing content"
    echo
    echo "📊 List configured servers:"
    echo "   accordo list-servers -p cursor"
    echo
    echo "✅ Validate configuration:"
    echo "   accordo validate -p cursor"
    echo
    echo "🗑️ Remove a server:"
    echo "   accordo remove-server accordo -p cursor"
    echo
    echo "❓ Get help:"
    echo "   accordo --help"
    echo
    
    if [[ "$INSTALL_METHOD" == "global" ]]; then
        echo "🔧 Manage with pipx:"
        echo "   pipx list                    # List installed packages"
        echo "   pipx upgrade accordo    # Upgrade to latest version"
        echo "   pipx uninstall accordo  # Uninstall completely"
    else
        echo "🔧 Manage in virtual environment:"
        echo "   pip list | grep accordo    # Check installation"
        if [[ "$INSTALL_METHOD" == "venv_uv" ]]; then
            echo "   uv pip install --upgrade accordo    # Upgrade"
            echo "   uv pip uninstall accordo           # Uninstall"
        else
            echo "   pip install --upgrade accordo      # Upgrade"
            echo "   pip uninstall accordo              # Uninstall"
        fi
    fi
    echo
}

# Main installation flow
main() {
    echo "🚀 accordo Installation Script"
    echo "=========================================="
    echo
    
    check_python
    detect_environment
    choose_installation_method
    install_workflow_commander
    verify_installation
    show_usage_examples
    
    print_success "Ready to configure accordo MCP server for your AI coding platforms!"
    
    if [[ "$INSTALL_METHOD" == "global" ]]; then
        print_status "Note: If accordo is not immediately available, restart your terminal."
    else
        print_status "Note: accordo is installed in your virtual environment."
    fi
}

# Run main function
main "$@" 