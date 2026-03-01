"""
WSGI application for PythonAnywhere deployment.
This file is required for PythonAnywhere web apps.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the project directory to Python path
project_home = Path(__file__).parent
if str(project_home) not in sys.path:
    sys.path.insert(0, str(project_home))

# Import the main application
from main import TradingBotApp

# For PythonAnywhere, we need to run the bot in a way that works with their infrastructure
# Since this is primarily a Telegram bot (not a web app), we'll create a simple WSGI app
# that indicates the service is running

def application(environ, start_response):
    """
    Simple WSGI application that returns status information.
    This is mainly for health checking on PythonAnywhere.
    """
    status = '200 OK'
    headers = [('Content-type', 'text/plain; charset=utf-8')]
    start_response(status, headers)
    
    response_lines = [
        "MyTradingBot is running!",
        "",
        "This is a Telegram trading bot service.",
        "For bot access, use your configured Telegram bot.",
        "",
        f"Python version: {sys.version}",
        f"Working directory: {os.getcwd()}",
        "",
        "Health status: OK"
    ]
    
    return [line.encode('utf-8') for line in response_lines]

# Note: The actual bot logic runs via the console/task system on PythonAnywhere
# This WSGI file is just for web interface compatibility