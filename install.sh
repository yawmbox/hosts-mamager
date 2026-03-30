#!/bin/bash

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_TEMPLATE="$APP_DIR/hosts-manager.desktop"
DESKTOP_FILE="$HOME/.local/share/applications/hosts-manager.desktop"

print_green() {
    echo -e "\e[32m$1\e[0m"
}

print_red() {
    echo -e "\e[31m$1\e[0m"
}

install() {
    echo "Installing application dependencies (customtkinter)..."
    pip3 install customtkinter --user --break-system-packages 2>/dev/null || pip3 install customtkinter --user

    echo "Building launcher shortcuts..."
    if [ ! -f "$DESKTOP_TEMPLATE" ]; then
        print_red "Error: $DESKTOP_TEMPLATE not found."
        exit 1
    fi

    mkdir -p "$HOME/.local/share/applications"
    
    # Create the desktop file by replacing the placeholder
    awk -v appdir="$APP_DIR" '{ gsub(/\{\{APP_DIR\}\}/, appdir); print }' "$DESKTOP_TEMPLATE" > "$DESKTOP_FILE"
    
    chmod +x "$DESKTOP_FILE"
    chmod +x "$APP_DIR/hosts_manager.py"
    
    print_green "Installation complete! 'Hosts Manager' should now appear in your application menu."
}

uninstall() {
    echo "Removing desktop shortcuts..."
    if [ -f "$DESKTOP_FILE" ]; then
        rm "$DESKTOP_FILE"
        print_green "Removed $DESKTOP_FILE"
    else
        echo "Launcher not found in $DESKTOP_FILE"
    fi
    
    print_green "Uninstallation complete!"
    echo "Note: Dependencies like customtkinter were not uninstalled. You can remove them manually with: pip3 uninstall customtkinter"
}

if [ "$1" == "--remove" ]; then
    uninstall
elif [ "$1" == "--install" ] || [ -z "$1" ]; then
    install
else
    echo "Usage: ./install.sh [--install | --remove]"
fi
