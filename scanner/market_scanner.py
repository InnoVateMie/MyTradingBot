"""Market scanner - scans all symbols for trading opportunities."""
import asyncio
import time
from typing import Callable, Dict, Optional, Set

from data.candle_builder import CandleBuilder, CandleUpdate
from data.tick_store import TickStore
from engine.signal_generator import SignalGenerator, Signal, AnalysisResult
from config.settings import settings
from utils.logger import logger


class MarketScanner:
    """
    Async market scanner that monitors all symbols for opportunities.
    
    Listens for candle updates and runs analysis when new candles close.
    Implements cooldown to prevent duplicate signals.
    """
    
    def __init__(
        self,
        candle_builder: CandleBuilder,
        tick_store: TickStore,
        on_signal: Optional[Callable] = None,
    ):
        """
        Initialize market scanner.
        
        Args:
            candle_builder: CandleBuilder instance for candle data
            tick_store: TickStore instance for latest prices
            on_signal: Async callback when a signal is generated
        """
        self.candle_builder = candle_builder
        self.tick_store = tick_store
        self.signal_generator = SignalGenerator()
        self._on_signal = on_signal
        
        # Cooldown tracking: {symbol: last_signal_timestamp}
        self._cooldowns: Dict[str, int] = {}
        
        # Scanning state
        self._running = False
        self._queue: asyncio.Queue = asyncio.Queue()
        
        # Current best opportunity (for GET SIGNAL button)
        self._best_opportunity: Optional[AnalysisResult] = None
        self._monitoring_symbol: Optional[str] = None
        self._monitoring_active = False
        
        # Signal numbering
        self._signal_counter = 0
        
        # Signal sending enabled/disabled
        self._signals_enabled = True
        
        # Continuous scanning enabled
        self._continuous_scanning = True  # Enable by default for automatic signal detection
    
    def _is_on_cooldown(self, symbol: str) -> bool:
        """Check if a symbol is on signal cooldown."""
        last_signal = self._cooldowns.get(symbol, 0)
        cooldown_ms = settings.signal_cooldown * 1000
        return (time.time() * 1000 - last_signal) < cooldown_ms
    
    def get_remaining_cooldown(self, symbol: str) -> int:
        """Get remaining cooldown time in seconds for a symbol."""
        last_signal = self._cooldowns.get(symbol, 0)
        cooldown_ms = settings.signal_cooldown * 1000
        elapsed_ms = time.time() * 1000 - last_signal
        remaining_ms = max(0, cooldown_ms - elapsed_ms)
        return int(remaining_ms / 1000)
    
    def get_global_cooldown_status(self) -> tuple[bool, int]:
        """Get global cooldown status - if any symbol is on cooldown, return time remaining."""
        max_remaining = 0
        is_any_on_cooldown = False
        
        for symbol in settings.symbols:
            remaining = self.get_remaining_cooldown(symbol)
            if remaining > 0:
                is_any_on_cooldown = True
                max_remaining = max(max_remaining, remaining)
        
        return is_any_on_cooldown, max_remaining
    
    def _set_cooldown(self, symbol: str) -> None:
        """Set cooldown for a symbol."""
        self._cooldowns[symbol] = int(time.time() * 1000)
    
    async def on_candle_close(self, update: CandleUpdate) -> None:
        """
        Handle candle close event from candle builder.
        
        This is called by the candle builder when a candle closes.
        """
        await self._queue.put(update)
    
    async def _process_candle_update(self, update: CandleUpdate) -> Optional[Signal]:
        """
        Process a candle update and check for signals.
        
        Returns Signal if one is generated, None otherwise.
        """
        symbol = update.symbol
        
        # Check if signals are enabled
        if not self._signals_enabled:
            return None
        
        # Check cooldown
        if self._is_on_cooldown(symbol):
            return None
        
        # Get all timeframe candles for this symbol
        candles_by_tf = await self.candle_builder.get_all_timeframe_candles(symbol)
        
        # Analyze
        result = self.signal_generator.analyze_all_timeframes(symbol, candles_by_tf)
        
        if result and result.meets_threshold:
            # Get current price
            price = await self.tick_store.get_last_price(symbol)
            if price is None:
                return None
            
            # Generate signal
            signal = self.signal_generator.generate_signal(result, price)
            
            # Increment signal counter and add to signal
            signal_number = self.increment_signal_counter()
            signal.signal_number = signal_number  # We'll need to add this field to Signal
            
            # Set cooldown
            self._set_cooldown(symbol)
            
            logger.info(
                f"Signal #{signal_number} generated: {signal.direction} {symbol} "
                f"Score: {signal.score:.1f} Expiry: {signal.expiry_label}"
            )
            
            return signal
        
        return None
    
    async def scan_once(self) -> Optional[AnalysisResult]:
        """
        Scan all symbols once and return best opportunity.
        
        Used by the GET SIGNAL button to find current best setup.
        """
        best_result: Optional[AnalysisResult] = None
        best_score = 0.0
        
        for symbol in settings.symbols:
            # Check if enough data
            has_data = await self.candle_builder.has_enough_data(symbol)
            if not has_data:
                logger.debug(f"Not enough data for {symbol}")
                continue
            
            # Get all timeframe candles
            candles_by_tf = await self.candle_builder.get_all_timeframe_candles(symbol)
            
            # Analyze all timeframes
            result = self.signal_generator.analyze_all_timeframes(symbol, candles_by_tf)
            
            if result:
                logger.debug(
                    f"{symbol}: Score {result.score.total_score:.1f} "
                    f"Threshold: {result.meets_threshold}"
                )
                
                if result.score.total_score > best_score:
                    best_score = result.score.total_score
                    best_result = result
        
        self._best_opportunity = best_result
        return best_result
    
    async def start_monitoring(self, symbol: str) -> None:
        """
        Start monitoring a specific symbol for entry signal.
        
        Called after user presses START SIGNAL button.
        """
        self._monitoring_symbol = symbol
        self._monitoring_active = True
        logger.info(f"Started monitoring {symbol} for entry signal")
    
    async def stop_monitoring(self) -> None:
        """Stop monitoring mode."""
        self._monitoring_symbol = None
        self._monitoring_active = False
        logger.info("Stopped signal monitoring")
    
    @property
    def is_monitoring(self) -> bool:
        """Check if actively monitoring a symbol."""
        return self._monitoring_active
    
    @property
    def monitoring_symbol(self) -> Optional[str]:
        """Get currently monitored symbol."""
        return self._monitoring_symbol
    
    @property
    def best_opportunity(self) -> Optional[AnalysisResult]:
        """Get the last best opportunity from scan."""
        return self._best_opportunity
    
    def enable_signals(self) -> None:
        """Enable signal generation."""
        self._signals_enabled = True
        logger.info("Signals enabled")
    
    def disable_signals(self) -> None:
        """Disable signal generation."""
        self._signals_enabled = False
        logger.info("Signals disabled")
    
    @property
    def signals_enabled(self) -> bool:
        """Check if signals are enabled."""
        return self._signals_enabled
    
    def increment_signal_counter(self) -> int:
        """Increment and return the next signal number."""
        self._signal_counter += 1
        return self._signal_counter
    
    @property
    def signal_count(self) -> int:
        """Get the current signal count."""
        return self._signal_counter
    
    def enable_continuous_scanning(self) -> None:
        """Enable continuous scanning mode."""
        self._continuous_scanning = True
        logger.info("Continuous scanning enabled")
    
    def disable_continuous_scanning(self) -> None:
        """Disable continuous scanning mode."""
        self._continuous_scanning = False
        logger.info("Continuous scanning disabled")
    
    @property
    def continuous_scanning_enabled(self) -> bool:
        """Check if continuous scanning is enabled."""
        return self._continuous_scanning
    
    async def run(self) -> None:
        """
        Main scanner loop.
        
        Processes candle updates from queue and generates signals.
        """
        self._running = True
        logger.info("Market scanner started")
        
        # Start continuous scanning task if enabled
        continuous_scan_task = None
        if self._continuous_scanning:
            continuous_scan_task = asyncio.create_task(self._continuous_scan_loop())
        
        while self._running:
            try:
                # Wait for candle update with timeout
                try:
                    update = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process the update
                signal = await self._process_candle_update(update)
                
                # If signal generated and callback exists
                if signal and self._on_signal:
                    try:
                        await self._on_signal(signal)
                    except Exception as e:
                        logger.error(f"Error in signal callback: {e}")
                
                # If monitoring active and this is our symbol
                if (
                    self._monitoring_active and 
                    signal and 
                    signal.symbol == self._monitoring_symbol
                ):
                    # This is the entry signal!
                    logger.info(f"Entry signal triggered for {signal.symbol}")
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scanner loop: {e}")
                await asyncio.sleep(1)
        
        # Cancel continuous scanning task if running
        if continuous_scan_task and not continuous_scan_task.done():
            continuous_scan_task.cancel()
            try:
                await continuous_scan_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Market scanner stopped")
    
    async def _continuous_scan_loop(self) -> None:
        """
        Background task that continuously scans for opportunities
        even without candle updates.
        """
        logger.info("Continuous scanning loop started")
        
        while self._running and self._continuous_scanning:
            try:
                # Only scan if signals are enabled
                if self._signals_enabled:
                    # Check if any symbol is ready to be scanned (not on cooldown)
                    ready_to_scan = False
                    for symbol in settings.symbols:
                        if not self._is_on_cooldown(symbol):
                            ready_to_scan = True
                            break
                    
                    if ready_to_scan:
                        # Perform a manual scan
                        result = await self.scan_once()
                        
                        if result and result.meets_threshold:
                            # Get current price for the symbol
                            price = await self.tick_store.get_last_price(result.symbol)
                            if price is not None:
                                # Generate signal
                                signal = self.signal_generator.generate_signal(result, price)
                                
                                # Increment signal counter and add to signal
                                signal_number = self.increment_signal_counter()
                                signal.signal_number = signal_number
                                
                                # Set cooldown
                                self._set_cooldown(result.symbol)
                                
                                logger.info(
                                    f"Continuous scan signal #{signal_number}: {signal.direction} {result.symbol} "
                                    f"Score: {signal.score:.1f} Expiry: {signal.expiry_label}"
                                )
                                
                                # Send the signal if callback exists
                                if self._on_signal:
                                    try:
                                        await self._on_signal(signal)
                                    except Exception as e:
                                        logger.error(f"Error in continuous scan signal callback: {e}")
                
                # Wait before next scan (every 30 seconds)
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                logger.info("Continuous scan loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in continuous scan loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def stop(self) -> None:
        """Stop the scanner."""
        self._running = False
        await self.stop_monitoring()
