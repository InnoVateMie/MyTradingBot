"""Multi-timeframe OHLCV candle builder."""
import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from collections import deque

from config.settings import settings
from utils.logger import logger


@dataclass
class Candle:
    """Represents an OHLCV candle."""
    symbol: str
    timeframe: int  # In seconds
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: int  # Candle open timestamp in ms
    close_timestamp: int  # Candle close timestamp in ms
    is_closed: bool = False


@dataclass
class CandleUpdate:
    """Event emitted when a candle closes."""
    symbol: str
    timeframe: int
    candle: Candle


class CandleBuilder:
    """Builds multi-timeframe OHLCV candles from tick data."""
    
    def __init__(
        self,
        timeframes: Optional[List[int]] = None,
        buffer_size: Optional[int] = None,
        on_candle_close: Optional[Callable] = None,
    ):
        """
        Initialize candle builder.
        
        Args:
            timeframes: List of timeframes in seconds. Defaults to settings.timeframes.
            buffer_size: Number of candles to keep per symbol/timeframe.
            on_candle_close: Async callback when a candle closes.
        """
        self._timeframes = timeframes or settings.timeframes
        self._buffer_size = buffer_size or settings.candle_buffer_size
        self._on_candle_close = on_candle_close
        
        # Storage: {symbol: {timeframe: deque[Candle]}}
        self._candles: Dict[str, Dict[int, deque]] = {}
        
        # Current building candles: {symbol: {timeframe: Candle}}
        self._current: Dict[str, Dict[int, Candle]] = {}
        
        self._lock = asyncio.Lock()
    
    def _get_candle_start_time(self, timestamp_ms: int, timeframe_seconds: int) -> int:
        """Get the aligned candle start timestamp."""
        timestamp_s = timestamp_ms // 1000
        aligned_s = (timestamp_s // timeframe_seconds) * timeframe_seconds
        return aligned_s * 1000
    
    def _initialize_symbol(self, symbol: str) -> None:
        """Initialize storage for a new symbol."""
        if symbol not in self._candles:
            self._candles[symbol] = {}
            self._current[symbol] = {}
            
            for tf in self._timeframes:
                self._candles[symbol][tf] = deque(maxlen=self._buffer_size)
    
    async def process_tick(self, tick_data: dict) -> None:
        """
        Process a new tick and update candles.
        
        Args:
            tick_data: Dict with keys: symbol, price, volume, timestamp
        """
        symbol = tick_data["symbol"]
        price = float(tick_data["price"])
        volume = float(tick_data.get("volume", 0))
        timestamp = int(tick_data["timestamp"])
        
        async with self._lock:
            self._initialize_symbol(symbol)
            
            for timeframe in self._timeframes:
                await self._update_candle(symbol, timeframe, price, volume, timestamp)
    
    async def _update_candle(
        self,
        symbol: str,
        timeframe: int,
        price: float,
        volume: float,
        timestamp: int,
    ) -> None:
        """Update or create candle for a specific timeframe."""
        candle_start = self._get_candle_start_time(timestamp, timeframe)
        candle_end = candle_start + (timeframe * 1000)
        
        current = self._current[symbol].get(timeframe)
        
        # Check if we need to close the current candle and start a new one
        if current is not None and candle_start > current.timestamp:
            # Close the current candle
            current.is_closed = True
            current.close_timestamp = current.timestamp + (timeframe * 1000)
            self._candles[symbol][timeframe].append(current)
            
            # Emit candle close event
            if self._on_candle_close:
                update = CandleUpdate(
                    symbol=symbol,
                    timeframe=timeframe,
                    candle=current,
                )
                try:
                    await self._on_candle_close(update)
                except Exception as e:
                    logger.error(f"Error in candle close callback: {e}")
            
            current = None
        
        if current is None:
            # Start a new candle
            self._current[symbol][timeframe] = Candle(
                symbol=symbol,
                timeframe=timeframe,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=volume,
                timestamp=candle_start,
                close_timestamp=candle_end,
                is_closed=False,
            )
        else:
            # Update the current candle
            current.high = max(current.high, price)
            current.low = min(current.low, price)
            current.close = price
            current.volume += volume
    
    async def get_candles(
        self,
        symbol: str,
        timeframe: int,
        limit: Optional[int] = None,
        include_current: bool = False,
    ) -> List[Candle]:
        """
        Get closed candles for a symbol and timeframe.
        
        Args:
            symbol: The symbol to get candles for
            timeframe: The timeframe in seconds
            limit: Maximum number of candles to return
            include_current: Include the currently building candle
        
        Returns:
            List of Candle objects (oldest first)
        """
        async with self._lock:
            if symbol not in self._candles:
                return []
            
            if timeframe not in self._candles[symbol]:
                return []
            
            candles = list(self._candles[symbol][timeframe])
            
            if include_current:
                current = self._current[symbol].get(timeframe)
                if current:
                    candles.append(current)
            
            if limit is not None:
                candles = candles[-limit:]
            
            return candles
    
    async def get_current_candle(self, symbol: str, timeframe: int) -> Optional[Candle]:
        """Get the currently building candle."""
        async with self._lock:
            if symbol not in self._current:
                return None
            return self._current[symbol].get(timeframe)
    
    async def get_candle_count(self, symbol: str, timeframe: int) -> int:
        """Get the number of closed candles for a symbol/timeframe."""
        async with self._lock:
            if symbol not in self._candles:
                return 0
            if timeframe not in self._candles[symbol]:
                return 0
            return len(self._candles[symbol][timeframe])
    
    async def has_enough_data(self, symbol: str, min_candles: int = 200) -> bool:
        """Check if we have enough candle data for analysis."""
        for tf in self._timeframes:
            count = await self.get_candle_count(symbol, tf)
            if count >= min_candles:
                return True
        return False
    
    async def get_all_timeframe_candles(
        self,
        symbol: str,
        limit: Optional[int] = None,
    ) -> Dict[int, List[Candle]]:
        """Get candles for all timeframes for a symbol."""
        result = {}
        for tf in self._timeframes:
            result[tf] = await self.get_candles(symbol, tf, limit)
        return result
