"""Main application entry point for the trading bot."""
import asyncio
import signal
import sys
from typing import List

from data.finnhub_ws import FinnhubWebSocket
from data.candle_builder import CandleBuilder
from data.tick_store import TickStore
from scanner.market_scanner import MarketScanner
from telegram_bot.bot import TradingBot
from storage.database import Database
from storage.signal_repo import SignalRepository
from storage.performance_repo import PerformanceRepository
from config.settings import settings
from utils.logger import logger
from health_check import health_monitor, init_health_monitor


class TradingBotApp:
    """Main application that coordinates all components."""
    
    def __init__(self):
        """Initialize the trading bot application."""
        # Initialize storage
        self.database = Database()
        self.signal_repo = SignalRepository(self.database)
        self.performance_repo = PerformanceRepository(self.database)
        
        # Initialize data components
        self.tick_store = TickStore()
        self.candle_builder = CandleBuilder(
            on_candle_close=self.on_candle_close
        )
        self.finnhub_ws = FinnhubWebSocket(
            on_tick=self.on_tick
        )
        
        # Initialize scanner
        self.scanner = MarketScanner(
            candle_builder=self.candle_builder,
            tick_store=self.tick_store,
            on_signal=self.on_signal
        )
        
        # Initialize Telegram bot
        self.telegram_bot = TradingBot(
            scanner=self.scanner,
            signal_repo=self.signal_repo,
            performance_repo=self.performance_repo
        )
        
        # Initialize health monitor
        init_health_monitor()
        
        # Shutdown flag
        self._shutdown_requested = False
        
    async def on_tick(self, tick_data: dict) -> None:
        """Handle incoming tick data."""
        # Add tick to storage
        await self.tick_store.add_tick(tick_data)
        
        # Process tick in candle builder
        await self.candle_builder.process_tick(tick_data)
    
    async def on_candle_close(self, update) -> None:
        """Handle closed candle from candle builder."""
        # Forward to scanner
        await self.scanner.on_candle_close(update)
    
    async def on_signal(self, signal) -> None:
        """Handle generated signal."""
        logger.info(f"Processing signal: {signal.direction} {signal.symbol}")
        
        # Save signal to database
        signal_id = await self.signal_repo.insert(signal)
        logger.info(f"Signal saved with ID: {signal_id}")
        
        # Broadcast signal to Telegram users
        await self.telegram_bot.broadcast_signal(signal)
    
    async def setup_shutdown_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler():
            logger.info("Shutdown signal received, initiating graceful shutdown...")
            self._shutdown_requested = True
        
        # Handle SIGTERM and SIGINT (skip on Windows which doesn't support it)
        if sys.platform != 'win32':
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, signal_handler)
        else:
            logger.info("Running on Windows - signal handlers not available")
    
    async def initialize(self):
        """Initialize all components."""
        logger.info("Initializing trading bot application...")
        
        try:
            # Validate settings
            settings.validate()
            logger.info("Settings validated successfully")
            health_monitor.update_component_status('settings', True, 'Settings validated successfully')
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            health_monitor.update_component_status('settings', False, f'Settings validation failed: {e}')
            raise
        
        # Initialize database
        await self.database.initialize()
        logger.info("Database initialized")
        health_monitor.update_component_status('database', True, 'Database initialized successfully')
        
        # Build Telegram bot application
        self.telegram_bot.build()
        logger.info("Telegram bot built")
        
        # Setup shutdown handlers
        await self.setup_shutdown_handlers()
        
        logger.info("Initialization complete")
    
    async def run(self):
        """Run the trading bot application."""
        logger.info("Starting trading bot application...")
        
        try:
            # Start Telegram bot
            telegram_task = asyncio.create_task(self.telegram_bot.start())
            health_monitor.update_component_status('telegram_bot', True, 'Telegram bot service started')
            
            # Start WebSocket connection
            ws_task = asyncio.create_task(self.finnhub_ws.connect())
            health_monitor.update_component_status('websocket_connection', True, 'WebSocket connection started')
            
            # Start scanner
            scanner_task = asyncio.create_task(self.scanner.run())
            health_monitor.update_component_status('scanner', True, 'Market scanner started')
            
            # Monitor tasks and handle shutdown
            tasks = [telegram_task, ws_task, scanner_task]
            
            logger.info("All services started successfully")
            
            while not self._shutdown_requested:
                # Check if any task has failed
                for i, task in enumerate(tasks):
                    if task.done():
                        exception = task.exception()
                        if exception:
                            logger.error(f"Critical service {i} failed: {exception}")
                            
                            # Update health status based on which service failed
                            if i == 0:  # telegram bot
                                health_monitor.update_component_status('telegram_bot', False, f'Telegram bot error: {exception}')
                            elif i == 1:  # websocket
                                health_monitor.update_component_status('websocket_connection', False, f'WebSocket error: {exception}')
                            elif i == 2:  # scanner
                                health_monitor.update_component_status('scanner', False, f'Scanner error: {exception}')
                                
                            raise exception
                
                # Small sleep to prevent busy waiting
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        except Exception as e:
            logger.error(f"Critical error in main application: {e}")
            raise
        finally:
            logger.info("Initiating shutdown sequence...")
            await self.shutdown()
    
    async def shutdown(self):
        """Gracefully shut down all components."""
        logger.info("Shutting down trading bot application...")
        
        # Stop scanner
        await self.scanner.stop()
        health_monitor.update_component_status('scanner', False, 'Scanner service stopped')
        
        # Stop WebSocket
        await self.finnhub_ws.disconnect()
        health_monitor.update_component_status('websocket_connection', False, 'WebSocket disconnected')
        
        # Stop Telegram bot
        await self.telegram_bot.stop()
        health_monitor.update_component_status('telegram_bot', False, 'Telegram bot stopped')
        
        # Disconnect from database
        await self.database.disconnect()
        health_monitor.update_component_status('database', False, 'Database disconnected')
        
        logger.info("All components shut down")


async def main():
    """Main entry point."""
    app = TradingBotApp()
    
    try:
        await app.initialize()
        await app.run()
    except ValueError as e:
        logger.error(f"Configuration error - please check your environment variables: {e}")
        print("\nCRITICAL: Missing or invalid configuration detected!")
        print("Please ensure you have set up your .env file with:")
        print("- TELEGRAM_BOT_TOKEN: Your Telegram bot token from @BotFather")
        print("- FINNHUB_API_KEY: Your Finnhub API key from https://finnhub.io/")
        print("\nRefer to .env.example for the format.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to run application: {e}")
        print(f"\nERROR: Application failed to start: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())