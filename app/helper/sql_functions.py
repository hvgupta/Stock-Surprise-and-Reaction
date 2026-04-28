from app.logger import get_configured_logger

logger = get_configured_logger(__name__)

import sqlite3
from typing import Optional, Tuple

class SQLiteDatabase:
    """Small wrapper around a SQLite connection with context-managed cleanup."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection: sqlite3.Connection | None = None

    def __enter__(self):
        self.connection = sqlite3.connect(self.db_path)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.connection is None:
            return False

        try:
            if exc_type is None:
                self.connection.commit()
            else:
                self.connection.rollback()
        finally:
            self.connection.close()
            self.connection = None

        return False

    def cursor(self):
        if self.connection is None:
            raise RuntimeError("Database connection is not open")
        return self.connection.cursor()

    def initialize(self) -> None:
        cursor = self.cursor()

        # Create earnings_calendar table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS earnings_calendar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                eps_actual REAL,
                eps_estimated REAL
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ticker_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                surprise REAL,
                eod_return REAL,
                reaction REAL
            )
        """
        )

    def execute(
        self,
        query: str,
        params: tuple | list = (),
    ):
        cursor = self.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()


def get_all_supported_tickers(db: SQLiteDatabase) -> list[str]:
    """Fetches all supported tickers from the database."""
    rows = db.execute("SELECT DISTINCT symbol FROM earnings_calendar")
    return [row[0] for row in rows]


def get_ticker_surprise(db: SQLiteDatabase, ticker: str) -> Optional[float]: 
    surprise_value = db.execute(
        """
        SELECT surprise 
        FROM ticker_data
        WHERE symbol = ?
        LIMIT 1
        """,
        (ticker,),
    )
    if surprise_value:
        return surprise_value[0][0]
    else:
        return None
    

def get_eps_data_of_ticker(db: SQLiteDatabase, ticker: str) -> Optional[Tuple[float, float]]:
    eps_data = db.execute(
        """
        SELECT eps_actual, eps_estimated
        FROM earnings_calendar
        WHERE symbol = ?
        LIMIT 1
        """,
        (ticker,),
    )
    if eps_data:
        return eps_data[0][0], eps_data[0][1]
    else:
        return None
    
def insert_surprise_data(db: SQLiteDatabase, ticker: str, surprise: float) -> None:
    db.execute(
        """
        INSERT INTO ticker_data (symbol, surprise)
        VALUES (?, ?)
        """,
        (ticker, surprise),
    )