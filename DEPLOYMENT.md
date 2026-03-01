# MyTradingBot Deployment Guide for PythonAnywhere

## Overview
This guide explains how to deploy your trading bot to PythonAnywhere using GitHub.

## Prerequisites
1. PythonAnywhere account (free tier works)
2. GitHub account
3. Telegram Bot Token from @BotFather
4. Finnhub API Key from https://finnhub.io/

## Deployment Steps

### 1. Prepare Your Local Repository

First, ensure all your files are committed:

```bash
git add .
git commit -m "Initial commit: Trading bot ready for deployment"
```

### 2. Push to GitHub

```bash
git remote add origin https://github.com/InnoVateMie/MyTradingBot.git
git branch -M main
git push -u origin main
```

### 3. Set Up on PythonAnywhere

1. **Log in to PythonAnywhere**
   - Go to https://www.pythonanywhere.com
   - Sign in or create a free account

2. **Create a New Console**
   - Click "Consoles" in the top menu
   - Choose "Bash" console
   - Run these commands:

```bash
# Clone your repository
git clone https://github.com/InnoVateMie/MyTradingBot.git
cd MyTradingBot

# Create virtual environment
mkvirtualenv tradingbot --python=/usr/bin/python3.11
pip install -r requirements.txt
```

3. **Configure Environment Variables**
   - In the same console, create your `.env` file:
```bash
cp .env.example .env
nano .env
```
   - Add your credentials:
```
TELEGRAM_BOT_TOKEN=your_actual_telegram_bot_token_here
FINNHUB_API_KEY=your_actual_finnhub_api_key_here
```
   - Press Ctrl+X, then Y, then Enter to save

4. **Test the Application**
```bash
python main.py
```
   - You should see the bot starting up
   - Press Ctrl+C to stop it

### 4. Set Up Always-On Task (Recommended)

For a trading bot, you want it running 24/7:

1. **Go to Tasks tab** on PythonAnywhere dashboard
2. **Add a new scheduled task**:
   - Set time to `*` (runs every minute)
   - Command: `cd ~/MyTradingBot && python main.py`

**OR** for better control, use a process manager script:

Create `~/MyTradingBot/start_bot.sh`:
```bash
#!/bin/bash
cd ~/MyTradingBot
source ~/.virtualenvs/tradingbot/bin/activate
python main.py
```

Make it executable:
```bash
chmod +x ~/MyTradingBot/start_bot.sh
```

Then schedule this task instead:
```bash
* * * * * cd ~/MyTradingBot && ./start_bot.sh
```

### 5. Set Up Web Interface (Optional)

If you want a web status page:

1. **Go to Web tab** on PythonAnywhere dashboard
2. **Add a new web app**
3. **Choose Manual configuration**
4. **Select Python 3.11**
5. **Configure the web app**:
   - Source code: `/home/yourusername/MyTradingBot`
   - Working directory: `/home/yourusername/MyTradingBot`
   - Virtual environment: `/home/yourusername/.virtualenvs/tradingbot`
   - WSGI file: `/var/www/yourusername_pythonanywhere_com_wsgi.py`

6. **Edit the WSGI file** to point to your app:
```python
import sys
import os

path = '/home/yourusername/MyTradingBot'
if path not in sys.path:
    sys.path.append(path)

os.chdir(path)
from wsgi import application
```

### 6. Monitoring and Maintenance

**Check logs:**
```bash
# View recent logs
tail -f ~/MyTradingBot/logs/*.log

# Or check PythonAnywhere task logs
# Go to Tasks tab and click on your task
```

**Restart the bot:**
```bash
# Kill existing processes
pkill -f "python main.py"

# Start fresh
cd ~/MyTradingBot
python main.py
```

## Important Notes

### Free Tier Limitations
- **CPU time**: 100 seconds per day (consider upgrading for 24/7 trading)
- **No persistent connections**: WebSocket connections may drop
- **Limited concurrent processes**: Only one always-on task recommended

### Production Considerations
For serious trading, consider:
1. **Paid PythonAnywhere plan** ($5+/month for more CPU time)
2. **Alternative hosting**: AWS EC2, DigitalOcean, or dedicated server
3. **Process monitoring**: Use systemd or supervisor
4. **Backup strategy**: Regular database backups
5. **Error handling**: Set up alerts for bot downtime

### Security Best Practices
- Never commit `.env` files to version control
- Use strong, unique passwords
- Regularly rotate API keys
- Monitor logs for suspicious activity
- Keep dependencies updated

## Troubleshooting

**Common issues:**

1. **Import errors**: Ensure virtual environment is activated
2. **Permission denied**: Check file permissions with `ls -la`
3. **API key errors**: Verify environment variables are set correctly
4. **Database errors**: Check if `trading_bot.db` file is writable
5. **Connection issues**: Free tier may have network limitations

**Debug commands:**
```bash
# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Test imports
python -c "from main import TradingBotApp; print('Import successful')"

# Check environment variables
python -c "import os; print(os.environ.get('TELEGRAM_BOT_TOKEN', 'Not set'))"
```

## Support
- PythonAnywhere help: https://help.pythonanywhere.com/
- GitHub repository: https://github.com/InnoVateMie/MyTradingBot
- Telegram bot documentation: https://core.telegram.org/bots

Last updated: March 2026