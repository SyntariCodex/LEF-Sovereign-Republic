#!/bin/bash
# Fix Node.js PATH issue
# Node.js is installed but Terminal can't find it

echo "Fixing Node.js PATH..."

# Check which shell you're using
SHELL_TYPE=$(basename $SHELL)

# Find where Node.js is installed
NODE_PATH=""
if [ -f "/opt/homebrew/bin/node" ]; then
    NODE_PATH="/opt/homebrew/bin"
elif [ -f "/usr/local/bin/node" ]; then
    NODE_PATH="/usr/local/bin"
else
    # Try to find it via Homebrew
    NODE_PATH=$(brew --prefix node@24 2>/dev/null)
    if [ -n "$NODE_PATH" ]; then
        NODE_PATH="$NODE_PATH/bin"
    fi
fi

if [ -z "$NODE_PATH" ] || [ ! -f "$NODE_PATH/node" ]; then
    echo "Could not find Node.js installation"
    echo "Trying alternative method..."
    
    # Check common Homebrew locations
    if [ -d "/opt/homebrew/opt/node@24/bin" ]; then
        NODE_PATH="/opt/homebrew/opt/node@24/bin"
    elif [ -d "/usr/local/opt/node@24/bin" ]; then
        NODE_PATH="/usr/local/opt/node@24/bin"
    elif [ -f "/opt/homebrew/Cellar/node@24/24.12.0/bin/node" ]; then
        NODE_PATH="/opt/homebrew/Cellar/node@24/24.12.0/bin"
    fi
fi

if [ -n "$NODE_PATH" ] && [ -f "$NODE_PATH/node" ]; then
    echo "Found Node.js at: $NODE_PATH"
    
    # Add to PATH for current session
    export PATH="$NODE_PATH:$PATH"
    
    # Verify it works
    if command -v node &> /dev/null; then
        echo "✅ Node.js is now accessible: $(node --version)"
        echo "✅ npm is now accessible: $(npm --version)"
        
        # Add to shell config file for permanent fix
        if [ "$SHELL_TYPE" = "zsh" ]; then
            CONFIG_FILE="$HOME/.zshrc"
        else
            CONFIG_FILE="$HOME/.bash_profile"
        fi
        
        # Check if already added
        if ! grep -q "$NODE_PATH" "$CONFIG_FILE" 2>/dev/null; then
            echo "" >> "$CONFIG_FILE"
            echo "# Node.js PATH (added by Admin LEF)" >> "$CONFIG_FILE"
            echo "export PATH=\"$NODE_PATH:\$PATH\"" >> "$CONFIG_FILE"
            echo "✅ Added to $CONFIG_FILE for permanent fix"
            echo "   Restart Terminal or run: source $CONFIG_FILE"
        else
            echo "✅ Already in $CONFIG_FILE"
        fi
    else
        echo "❌ Still not working. May need to restart Terminal."
    fi
else
    echo "❌ Could not locate Node.js installation"
    echo "   Node.js may need to be reinstalled"
fi
