"""Signal repository for storing and retrieving signals."""
from typing import List, Optional
from dataclasses import asdict

from storage.database import Database
from engine.signal_generator import Signal
from utils.logger import logger


class SignalRepository:
    """Repository for signal CRUD operations."""
    
    def __init__(self, database: Database):
        """
        Initialize signal repository.
        
        Args:
            database: Database instance
        """
        self.db = database
    
    async def insert(self, signal: Signal) -> int:
        """
        Insert a new signal.
        
        Args:
            signal: Signal object to insert
        
        Returns:
            The ID of the inserted signal
        """
        query = """
            INSERT INTO signals (
                symbol, direction, score, confidence, expiry_seconds,
                timeframe, entry_price, timestamp, trend_score,
                momentum_score, volatility_score, structure_score,
                rsi, adx, atr_ratio
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            signal.symbol,
            signal.direction,
            signal.score,
            signal.confidence,
            signal.expiry_seconds,
            signal.timeframe,
            signal.entry_price,
            signal.timestamp,
            signal.trend_score,
            signal.momentum_score,
            signal.volatility_score,
            signal.structure_score,
            signal.rsi,
            signal.adx,
            signal.atr_ratio,
        )
        
        cursor = await self.db.execute(query, params)
        await self.db.commit()
        
        signal_id = cursor.lastrowid
        logger.debug(f"Inserted signal {signal_id}: {signal.direction} {signal.symbol}")
        
        return signal_id
    
    async def get_by_id(self, signal_id: int) -> Optional[dict]:
        """
        Get a signal by ID.
        
        Args:
            signal_id: The signal ID
        
        Returns:
            Signal data as dict or None
        """
        query = "SELECT * FROM signals WHERE id = ?"
        row = await self.db.fetchone(query, (signal_id,))
        
        if row:
            return dict(row)
        return None
    
    async def get_recent(self, limit: int = 20) -> List[dict]:
        """
        Get recent signals.
        
        Args:
            limit: Maximum number of signals to return
        
        Returns:
            List of signal dicts (newest first)
        """
        query = """
            SELECT * FROM signals 
            ORDER BY timestamp DESC 
            LIMIT ?
        """
        
        rows = await self.db.fetchall(query, (limit,))
        return [dict(row) for row in rows]
    
    async def get_by_symbol(self, symbol: str, limit: int = 20) -> List[dict]:
        """
        Get signals for a specific symbol.
        
        Args:
            symbol: The trading symbol
            limit: Maximum number of signals
        
        Returns:
            List of signal dicts
        """
        query = """
            SELECT * FROM signals 
            WHERE symbol = ?
            ORDER BY timestamp DESC 
            LIMIT ?
        """
        
        rows = await self.db.fetchall(query, (symbol, limit))
        return [dict(row) for row in rows]
    
    async def get_today(self) -> List[dict]:
        """
        Get all signals from today.
        
        Returns:
            List of signal dicts
        """
        import time
        
        # Start of today (midnight) in milliseconds
        today_start = int(time.time() // 86400 * 86400 * 1000)
        
        query = """
            SELECT * FROM signals 
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
        """
        
        rows = await self.db.fetchall(query, (today_start,))
        return [dict(row) for row in rows]
    
    async def update_result(self, signal_id: int, result: str) -> None:
        """
        Update the result of a signal.
        
        Args:
            signal_id: The signal ID
            result: "WIN", "LOSS", or "EXPIRED"
        """
        query = "UPDATE signals SET result = ? WHERE id = ?"
        await self.db.execute(query, (result, signal_id))
        await self.db.commit()
        
        logger.debug(f"Updated signal {signal_id} result: {result}")
    
    async def get_count(self) -> int:
        """Get total number of signals."""
        query = "SELECT COUNT(*) as count FROM signals"
        row = await self.db.fetchone(query)
        return row['count'] if row else 0
    
    async def get_count_today(self) -> int:
        """Get number of signals today."""
        import time
        today_start = int(time.time() // 86400 * 86400 * 1000)
        
        query = "SELECT COUNT(*) as count FROM signals WHERE timestamp >= ?"
        row = await self.db.fetchone(query, (today_start,))
        return row['count'] if row else 0
