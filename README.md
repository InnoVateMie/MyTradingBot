# MyTradingBot

A sophisticated trading signal bot that analyzes market data and sends trading signals via Telegram.

## Features

- Real-time market data streaming from Finnhub
- Multi-timeframe technical analysis
- Advanced signal generation with scoring system
- Telegram bot integration for signal delivery
- Performance tracking and analytics
- Automatic candlestick formation from tick data

## Architecture

The system consists of several interconnected modules:

- **Data Layer**: Handles market data collection and processing
  - `finnhub_ws.py`: WebSocket client for real-time market data
  - `tick_store.py`: In-memory storage for tick data
  - `candle_builder.py`: Converts ticks to OHLCV candles

- **Engine Layer**: Core signal generation logic
  - `signal_generator.py`: Orchestrates signal creation
  - `scoring.py`: Calculates signal scores
  - `expiry.py`: Determines signal validity periods

- **Indicators**: Technical analysis calculations
  - `trend.py`: Trend indicators (EMAs, MACD, etc.)
  - `momentum.py`: Momentum indicators (RSI, Stochastic, etc.)
  - `volatility.py`: Volatility indicators (ATR, Bollinger Bands, etc.)
  - `structure.py`: Market structure indicators (Support/Resistance, etc.)

- **Storage**: Data persistence
  - `database.py`: SQLite database management
  - `signal_repo.py`: Signal storage and retrieval
  - `performance_repo.py`: Performance tracking

- **Telegram Bot**: User interface
  - `bot.py`: Main bot logic
  - `handlers.py`: Command processing
  - `dashboard.py`: Message formatting
  - `notifier.py`: Signal broadcasting

## Production Deployment Requirements

### Prerequisites

1. **Telegram Bot Token**:
   - Create a bot with [@BotFather](https://t.me/BotFather) on Telegram
   - Get your unique bot token
   
2. **Finnhub API Key**:
   - Sign up at [Finnhub.io](https://finnhub.io/)
   - Get your free API key (no credit card required)

3. **Environment Variables**:
   - Set up the `.env` file with required credentials

### Setup for Production

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd MyTradingBot
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
   
   Edit the `.env` file and add your credentials:
   ```
   TELEGRAM_BOT_TOKEN=your_actual_telegram_bot_token_here
   FINNHUB_API_KEY=your_actual_finnhub_api_key_here
   ```
   
   Optional configurations:
   ```
   BOT_PASSWORD=your_custom_password  # Default: TradePro2024
   DATABASE_PATH=/path/to/trading_bot.db  # Default: trading_bot.db
   LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR
   ```

4. Run the application:
   ```bash
   python main.py
   ```

### Security Considerations

- Store API keys securely and never commit them to version control
- Use strong passwords for bot access
- Regularly rotate API keys
- Monitor logs for suspicious activity
- Ensure SSL/TLS for any web interfaces

### Monitoring & Health Checks

The application includes:
- Comprehensive logging for all components
- Graceful shutdown handling
- Error detection and reporting
- Service status monitoring

### Running in Production

For production deployments, consider:

1. **Process Management**:
   - Use a process manager like systemd (Linux) or NSSM (Windows)
   - Set up automatic restart on failure

2. **Logging**:
   - Set up log rotation
   - Forward logs to centralized logging system

3. **Backup Strategy**:
   - Regular backups of the SQLite database
   - Secure storage of backup files

4. **Health Monitoring**:
   - Monitor WebSocket connections
   - Track signal generation rates
   - Watch for performance degradation

## Configuration

The bot can be configured via the `config/settings.py` file or environment variables:

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `FINNHUB_API_KEY`: Your Finnhub API key
- `BOT_PASSWORD`: Access password for the bot (default: TradePro2024)
- `LOG_LEVEL`: Logging level (default: INFO)

## Usage

1. Start the bot: `python main.py`
2. Open Telegram and find your bot
3. Use `/start` to begin
4. Enter the password (default: TradePro2024) with `/password TradePro2024`
5. Use `/dashboard` to access the main interface
6. Press "GET SIGNAL" to scan for trading opportunities

## Signals

The bot generates signals when:

- Score reaches 72/100 threshold
- All indicator conditions align
- Market structure confirms direction

Each signal includes:
- Direction (BUY/SELL)
- Trading pair
- Score (0-100)
- Confidence level
- Expiration time
- Entry price

## License

MIT