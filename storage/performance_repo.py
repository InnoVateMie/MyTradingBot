"""Performance repository for tracking signal accuracy."""
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from storage.database import Database
from utils.logger import logger


@dataclass
class PerformanceStats:
    """Overall performance statistics."""
    total_signals: int
    total_wins: int
    total_losses: int
    win_rate: float
    today_signals: int
    today_wins: int
    today_losses: int
    today_win_rate: float


@dataclass
class SymbolStats:
    """Performance statistics for a single symbol."""
    symbol: str
    total: int
    wins: int
    losses: int
    win_rate: float


class PerformanceRepository:
    """Repository for performance tracking and statistics."""
    
    def __init__(self, database: Database):
        """
        Initialize performance repository.
        
        Args:
            database: Database instance
        """
        self.db = database
    
    async def record_result(self, symbol: str, is_win: bool) -> None:
        """
        Record a signal result.
        
        Args:
            symbol: The trading symbol
            is_win: True if signal was winning
        """
        now = int(time.time() * 1000)
        
        # Check if symbol exists
        existing = await self.db.fetchone(
            "SELECT * FROM performance WHERE symbol = ?",
            (symbol,)
        )
        
        if existing:
            # Update existing record
            if is_win:
                query = """
                    UPDATE performance 
                    SET total = total + 1, wins = wins + 1, last_updated = ?
                    WHERE symbol = ?
                """
            else:
                query = """
                    UPDATE performance 
                    SET total = total + 1, losses = losses + 1, last_updated = ?
                    WHERE symbol = ?
                """
            await self.db.execute(query, (now, symbol))
        else:
            # Insert new record
            wins = 1 if is_win else 0
            losses = 0 if is_win else 1
            query = """
                INSERT INTO performance (symbol, total, wins, losses, last_updated)
                VALUES (?, 1, ?, ?, ?)
            """
            await self.db.execute(query, (symbol, wins, losses, now))
        
        await self.db.commit()
        logger.debug(f"Recorded {'WIN' if is_win else 'LOSS'} for {symbol}")
    
    async def get_symbol_stats(self, symbol: str) -> Optional[SymbolStats]:
        """
        Get performance stats for a symbol.
        
        Args:
            symbol: The trading symbol
        
        Returns:
            SymbolStats or None
        """
        row = await self.db.fetchone(
            "SELECT * FROM performance WHERE symbol = ?",
            (symbol,)
        )
        
        if not row:
            return None
        
        total = row['total']
        wins = row['wins']
        losses = row['losses']
        win_rate = (wins / total * 100) if total > 0 else 0.0
        
        return SymbolStats(
            symbol=symbol,
            total=total,
            wins=wins,
            losses=losses,
            win_rate=win_rate,
        )
    
    async def get_all_symbol_stats(self) -> List[SymbolStats]:
        """
        Get performance stats for all symbols.
        
        Returns:
            List of SymbolStats
        """
        rows = await self.db.fetchall(
            "SELECT * FROM performance ORDER BY total DESC"
        )
        
        results = []
        for row in rows:
            total = row['total']
            wins = row['wins']
            win_rate = (wins / total * 100) if total > 0 else 0.0
            
            results.append(SymbolStats(
                symbol=row['symbol'],
                total=total,
                wins=wins,
                losses=row['losses'],
                win_rate=win_rate,
            ))
        
        return results
    
    async def get_overall_stats(self) -> PerformanceStats:
        """
        Get overall performance statistics.
        
        Returns:
            PerformanceStats
        """
        # Get totals from performance table
        row = await self.db.fetchone("""
            SELECT 
                COALESCE(SUM(total), 0) as total,
                COALESCE(SUM(wins), 0) as wins,
                COALESCE(SUM(losses), 0) as losses
            FROM performance
        """)
        
        total_signals = row['total']
        total_wins = row['wins']
        total_losses = row['losses']
        win_rate = (total_wins / total_signals * 100) if total_signals > 0 else 0.0
        
        # Get today's stats from signals table
        today_start = int(time.time() // 86400 * 86400 * 1000)
        
        today_row = await self.db.fetchone("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN result = 'LOSS' THEN 1 ELSE 0 END) as losses
            FROM signals
            WHERE timestamp >= ?
        """, (today_start,))
        
        today_signals = today_row['total'] or 0
        today_wins = today_row['wins'] or 0
        today_losses = today_row['losses'] or 0
        today_win_rate = (today_wins / today_signals * 100) if today_signals > 0 else 0.0
        
        return PerformanceStats(
            total_signals=total_signals,
            total_wins=total_wins,
            total_losses=total_losses,
            win_rate=win_rate,
            today_signals=today_signals,
            today_wins=today_wins,
            today_losses=today_losses,
            today_win_rate=today_win_rate,
        )
    
    async def get_accuracy_by_symbol(self, symbol: str) -> float:
        """
        Get win rate for a specific symbol.
        
        Args:
            symbol: The trading symbol
        
        Returns:
            Win rate percentage (0-100)
        """
        stats = await self.get_symbol_stats(symbol)
        return stats.win_rate if stats else 0.0
