#!/bin/bash
# ─────────────────────────────────────────────────────────────────
#  ChatWith — Setup Script
#  Works on: Termux (Android), Ubuntu, Debian, Kali, Arch Linux
# ─────────────────────────────────────────────────────────────────

CYAN='\033[96m'
GREEN='\033[92m'
YELLOW='\033[93m'
RED='\033[91m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

echo ""
echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════════════${RESET}"
echo -e "${CYAN}${BOLD}       ChatWith — Installer  |  ZeroByte Technologies      ${RESET}"
echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════════════${RESET}"
echo ""

# Detect environment
if [ -d "/data/data/com.termux" ]; then
    ENV="termux"
    echo -e "${GREEN}  ✔  Detected: Termux (Android)${RESET}"
else
    ENV="linux"
    echo -e "${GREEN}  ✔  Detected: Linux System${RESET}"
fi

# Check Python
if ! command -v python3 &>/dev/null; then
    echo -e "${YELLOW}  ℹ  Python3 not found. Installing...${RESET}"
    if [ "$ENV" = "termux" ]; then
        pkg install python -y
    else
        sudo apt-get install python3 -y 2>/dev/null || \
        sudo yum install python3 -y 2>/dev/null || \
        sudo pacman -S python -y 2>/dev/null
    fi
else
    VER=$(python3 --version 2>&1)
    echo -e "${GREEN}  ✔  ${VER} found${RESET}"
fi

# Create app directory
APP_DIR="$HOME/.chatwith"
mkdir -p "$APP_DIR/exports"
echo -e "${GREEN}  ✔  App directory: ${APP_DIR}${RESET}"

# Copy main script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/chat.py" "$APP_DIR/chat.py"
chmod +x "$APP_DIR/chat.py"
echo -e "${GREEN}  ✔  Installed to: ${APP_DIR}/chat.py${RESET}"

# Create launcher
if [ "$ENV" = "termux" ]; then
    BIN_DIR="$PREFIX/bin"
else
    BIN_DIR="/usr/local/bin"
fi

LAUNCHER="$BIN_DIR/chatwith"
cat > "$LAUNCHER" << EOF
#!/bin/bash
python3 $APP_DIR/chat.py "\$@"
EOF
chmod +x "$LAUNCHER"
echo -e "${GREEN}  ✔  Launcher created: chatwith${RESET}"

echo ""
echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════════════${RESET}"
echo -e "${GREEN}${BOLD}  ✅  ChatWith installed successfully!${RESET}"
echo ""
echo -e "${YELLOW}  Run it with:  ${BOLD}chatwith${RESET}"
echo -e "${DIM}  Or directly:  python3 ~/.chatwith/chat.py${RESET}"
echo -e "${DIM}  Exports:       ~/.chatwith/exports/${RESET}"
echo -e "${DIM}  Database:      ~/.chatwith/chatwith.db${RESET}"
echo ""
echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════════════${RESET}"
echo ""
