#!/bin/bash
# PythonAnywhere deployment script for MyTradingBot

echo "=== MyTradingBot Deployment Script ==="
echo "Starting deployment to PythonAnywhere..."

# Check if we're on PythonAnywhere
if [[ ! -d "/home" ]] || [[ ! -f "/etc/pythonanywhere_version" ]]; then
    echo "Warning: This script is designed for PythonAnywhere"
    echo "You appear to be running on a different system"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Set up variables
REPO_URL="https://github.com/InnoVateMie/MyTradingBot.git"
PROJECT_DIR="$HOME/MyTradingBot"
VENV_NAME="tradingbot"
PYTHON_VERSION="python3.11"

echo "1. Cloning repository..."
if [ -d "$PROJECT_DIR" ]; then
    echo "Project directory already exists. Updating..."
    cd "$PROJECT_DIR"
    git pull
else
    git clone "$REPO_URL" "$PROJECT_DIR"
    cd "$PROJECT_DIR"
fi

echo "2. Setting up virtual environment..."
if [ ! -d "$HOME/.virtualenvs/$VENV_NAME" ]; then
    mkvirtualenv "$VENV_NAME" --python="/usr/bin/$PYTHON_VERSION"
else
    workon "$VENV_NAME"
fi

echo "3. Installing dependencies..."
pip install -r requirements.txt

echo "4. Setting up environment variables..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env file from template"
    echo "IMPORTANT: You need to edit .env and add your API keys!"
    echo "Run: nano .env"
else
    echo ".env file already exists"
fi

echo "5. Testing import..."
python -c "from main import TradingBotApp; print('✓ Import successful')"

echo ""
echo "=== Deployment Complete! ==="
echo ""
echo "Next steps:"
echo "1. Edit your .env file to add your credentials:"
echo "   nano $PROJECT_DIR/.env"
echo ""
echo "2. Add your TELEGRAM_BOT_TOKEN and FINNHUB_API_KEY"
echo ""
echo "3. Test the bot:"
echo "   cd $PROJECT_DIR && python main.py"
echo ""
echo "4. For 24/7 operation, set up a scheduled task:"
echo "   - Go to Tasks tab in PythonAnywhere"
echo "   - Add task: */5 * * * * (every 5 minutes)"
echo "   - Command: cd $PROJECT_DIR && python main.py"
echo ""
echo "For detailed instructions, see DEPLOYMENT.md in your project directory"