"""SQLite database setup and management."""
import aiosqlite
from typing import Optional

from config.settings import settings
from utils.logger import logger


class Database:
    """Async SQLite database manager."""
    
    def __init__(self, db_path: str = None):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path or settings.database_path
        self._connection: Optional[aiosqlite.Connection] = None
    
    async def connect(self) -> None:
        """Connect to the database."""
        self._connection = await aiosqlite.connect(self.db_path)
        self._connection.row_factory = aiosqlite.Row
        logger.info(f"Connected to database: {self.db_path}")
    
    async def disconnect(self) -> None:
        """Disconnect from the database."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Disconnected from database")
    
    @property
    def connection(self) -> aiosqlite.Connection:
        """Get the database connection."""
        if not self._connection:
            raise RuntimeError("Database not connected")
        return self._connection
    
    async def initialize(self) -> None:
        """Create database tables if they don't exist."""
        await self.connect()
        
        # Create signals table
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL,
                score REAL NOT NULL,
                confidence TEXT NOT NULL,
                expiry_seconds INTEGER NOT NULL,
                timeframe INTEGER NOT NULL,
                entry_price REAL,
                timestamp INTEGER NOT NULL,
                result TEXT DEFAULT NULL,
                trend_score REAL,
                momentum_score REAL,
                volatility_score REAL,
                structure_score REAL,
                rsi REAL,
                adx REAL,
                atr_ratio REAL
            )
        """)
        
        # Create performance table
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS performance (
                symbol TEXT PRIMARY KEY,
                total INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                last_updated INTEGER
            )
        """)
        
        # Create index on timestamp for faster queries
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_signals_timestamp 
            ON signals(timestamp)
        """)
        
        # Create index on symbol for faster filtering
        await self._connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_signals_symbol 
            ON signals(symbol)
        """)
        
        await self._connection.commit()
        logger.info("Database tables initialized")
    
    async def execute(self, query: str, params: tuple = ()) -> aiosqlite.Cursor:
        """Execute a query and return the cursor."""
        return await self.connection.execute(query, params)
    
    async def executemany(self, query: str, params_list: list) -> aiosqlite.Cursor:
        """Execute a query for multiple parameter sets."""
        return await self.connection.executemany(query, params_list)
    
    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.connection.commit()
    
    async def fetchone(self, query: str, params: tuple = ()) -> Optional[aiosqlite.Row]:
        """Execute query and fetch one result."""
        cursor = await self.execute(query, params)
        return await cursor.fetchone()
    
    async def fetchall(self, query: str, params: tuple = ()) -> list:
        """Execute query and fetch all results."""
        cursor = await self.execute(query, params)
        return await cursor.fetchall()
