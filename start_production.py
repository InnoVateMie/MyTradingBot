#!/usr/bin/env python3
"""Production startup script for the trading bot with comprehensive checks."""
import os
import sys
import asyncio
from pathlib import Path

from config.settings import settings
from utils.logger import logger
from health_check import get_system_health


def check_environment_variables():
    """Check that all required environment variables are set."""
    print("🔍 Checking environment variables...")
    
    required_vars = ['TELEGRAM_BOT_TOKEN', 'FINNHUB_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value or value.strip().lower().startswith('your_'):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing or invalid environment variables: {missing_vars}")
        print("\nPlease set these variables in your .env file:")
        for var in missing_vars:
            if var == 'TELEGRAM_BOT_TOKEN':
                print(f"  {var}=your_actual_telegram_bot_token_from_botfather")
            elif var == 'FINNHUB_API_KEY':
                print(f"  {var}=your_actual_finnhub_api_key_from_finnhub_io")
        print("\nSee .env.example for format.")
        return False
    
    print("✅ All required environment variables are set")
    return True


def check_api_access():
    """Basic check to see if API keys are valid (without actually calling APIs)."""
    print("🔍 Checking API key formats...")
    
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    finnhub_key = os.getenv('FINNHUB_API_KEY', '')
    
    # Basic validation of token/key formats
    if not telegram_token or len(telegram_token) < 20 or ':' not in telegram_token:
        print("❌ Telegram bot token format appears invalid")
        return False
    
    if not finnhub_key or len(finnhub_key) < 10:
        print("❌ Finnhub API key format appears invalid")
        return False
    
    print("✅ API key formats appear valid")
    return True


def check_directories_and_permissions():
    """Check that required directories exist and are writable."""
    print("🔍 Checking directory permissions...")
    
    # Check if we can write to the current directory
    try:
        test_file = Path("test_write_access.tmp")
        test_file.touch()
        test_file.unlink()  # Remove the test file
        print("✅ Write access confirmed")
        return True
    except Exception as e:
        print(f"❌ Cannot write to current directory: {e}")
        return False


def check_database_path():
    """Check if database path is accessible."""
    print("🔍 Checking database path...")
    
    db_path = Path(settings.database_path)
    db_dir = db_path.parent
    
    if not db_dir.exists():
        print(f"❌ Database directory does not exist: {db_dir}")
        return False
    
    # Check if we can write to the database directory
    try:
        test_db = db_dir / "test_db_access.tmp"
        test_db.touch()
        test_db.unlink()
        print("✅ Database directory is writable")
        return True
    except Exception as e:
        print(f"❌ Cannot write to database directory: {e}")
        return False


def print_production_warning():
    """Print a warning about production readiness."""
    print("\n" + "="*60)
    print("⚠️  PRODUCTION READINESS CHECKLIST")
    print("="*60)
    print("Before deploying to production, please ensure:")
    print("• You have tested with real market data in a safe environment")
    print("• You have proper risk management measures in place")
    print("• You understand that trading involves substantial risk")
    print("• You have backups of your database and configurations")
    print("• You have monitoring and alerting set up")
    print("• You have reviewed all security settings")
    print("="*60)


def main():
    """Main production startup check."""
    print("🚀 Starting production readiness check for Trading Bot...")
    print()
    
    # Perform all checks
    checks = [
        ("Environment Variables", check_environment_variables),
        ("API Key Formats", check_api_access),
        ("Directory Permissions", check_directories_and_permissions),
        ("Database Path", check_database_path),
    ]
    
    all_passed = True
    for check_name, check_func in checks:
        print(f"\n📋 {check_name}")
        print("-" * len(f"📋 {check_name}"))
        if not check_func():
            all_passed = False
            print()
            break
        print()
    
    if not all_passed:
        print("❌ Production readiness check FAILED")
        print("Please fix the issues above before starting the bot.")
        sys.exit(1)
    
    # If all checks pass
    print("✅ All production readiness checks PASSED!")
    print_production_warning()
    
    # Show current settings
    print(f"\n📊 Current Configuration:")
    print(f"   Telegram Bot Token: {'SET' if settings.telegram_bot_token else 'NOT SET'}")
    print(f"   Finnhub API Key: {'SET' if settings.finnhub_api_key else 'NOT SET'}")
    print(f"   Database Path: {settings.database_path}")
    print(f"   Symbols: {settings.symbols}")
    print(f"   Timeframes: {settings.timeframes}")
    print(f"   Log Level: {settings.log_level}")
    
    # Show health status
    health = get_system_health()
    print(f"\n🏥 System Health: {'HEALTHY' if health['overall_status'] else 'UNHEALTHY'}")
    
    print(f"\n🎯 Ready to start trading bot in production!")
    print("Run 'python main.py' to start the bot.")


if __name__ == "__main__":
    main()