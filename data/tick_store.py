"""In-memory tick storage with buffer management."""
import asyncio
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional

from config.settings import settings


@dataclass
class Tick:
    """Represents a single price tick."""
    symbol: str
    price: float
    volume: float
    timestamp: int  # Unix timestamp in milliseconds


class TickStore:
    """Thread-safe in-memory tick buffer per symbol."""
    
    def __init__(self, max_size: int = None):
        """
        Initialize tick store.
        
        Args:
            max_size: Maximum ticks to keep per symbol. Defaults to settings.tick_buffer_size.
        """
        self._max_size = max_size or settings.tick_buffer_size
        self._buffers: Dict[str, deque] = {}
        self._lock = asyncio.Lock()
        self._last_prices: Dict[str, float] = {}
    
    async def add_tick(self, tick_data: dict) -> None:
        """
        Add a tick to the store.
        
        Args:
            tick_data: Dict with keys: symbol, price, volume, timestamp
        """
        tick = Tick(
            symbol=tick_data["symbol"],
            price=float(tick_data["price"]),
            volume=float(tick_data.get("volume", 0)),
            timestamp=int(tick_data["timestamp"]),
        )
        
        async with self._lock:
            if tick.symbol not in self._buffers:
                self._buffers[tick.symbol] = deque(maxlen=self._max_size)
            
            self._buffers[tick.symbol].append(tick)
            self._last_prices[tick.symbol] = tick.price
    
    async def get_ticks(
        self, 
        symbol: str, 
        since_ts: Optional[int] = None,
        limit: Optional[int] = None
    ) -> List[Tick]:
        """
        Get ticks for a symbol.
        
        Args:
            symbol: The symbol to get ticks for
            since_ts: Only return ticks after this timestamp (ms)
            limit: Maximum number of ticks to return
        
        Returns:
            List of Tick objects
        """
        async with self._lock:
            if symbol not in self._buffers:
                return []
            
            ticks = list(self._buffers[symbol])
        
        if since_ts is not None:
            ticks = [t for t in ticks if t.timestamp > since_ts]
        
        if limit is not None:
            ticks = ticks[-limit:]
        
        return ticks
    
    async def get_latest_tick(self, symbol: str) -> Optional[Tick]:
        """Get the most recent tick for a symbol."""
        async with self._lock:
            if symbol not in self._buffers or not self._buffers[symbol]:
                return None
            return self._buffers[symbol][-1]
    
    async def get_last_price(self, symbol: str) -> Optional[float]:
        """Get the last known price for a symbol."""
        async with self._lock:
            return self._last_prices.get(symbol)
    
    async def get_tick_count(self, symbol: str) -> int:
        """Get the number of ticks stored for a symbol."""
        async with self._lock:
            if symbol not in self._buffers:
                return 0
            return len(self._buffers[symbol])
    
    async def get_all_symbols(self) -> List[str]:
        """Get all symbols with stored ticks."""
        async with self._lock:
            return list(self._buffers.keys())
    
    async def clear(self, symbol: Optional[str] = None) -> None:
        """
        Clear ticks from the store.
        
        Args:
            symbol: Specific symbol to clear. If None, clears all.
        """
        async with self._lock:
            if symbol:
                if symbol in self._buffers:
                    self._buffers[symbol].clear()
                    self._last_prices.pop(symbol, None)
            else:
                self._buffers.clear()
                self._last_prices.clear()
