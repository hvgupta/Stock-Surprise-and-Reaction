from app.logger import get_configured_logger

logger = get_configured_logger(__name__)

import sqlite3
from typing import Iterable, Optional, Dict, overload, Union

type DateValues[T] = Union[T, Dict[str, T]]


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
        except Exception as e:
            logger.error(f"Error during database commit/rollback: {e}, {traceback}")
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS earnings_calendar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                eps_actual REAL,
                eps_estimated REAL
            )
        """)

        # Ensure we can upsert by (symbol, date)
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_earnings_calendar_symbol_date
            ON earnings_calendar(symbol, date)
            """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ticker_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT,
                surprise REAL,
                eod_return REAL,
                reaction REAL
            )
        """)

        # Backfill schema for older DBs that lack ticker_data.date
        existing_columns = {
            row[1]
            for row in cursor.execute("PRAGMA table_info(ticker_data)").fetchall()
        }
        if "date" not in existing_columns:
            cursor.execute("ALTER TABLE ticker_data ADD COLUMN date TEXT")

        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_ticker_data_symbol_date
            ON ticker_data(symbol, date)
            """)

    def execute(
        self,
        query: str,
        params: tuple | list = (),
    ):
        cursor = self.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()

    def executemany(
        self,
        query: str,
        seq_of_params: Iterable[tuple | list],
    ) -> None:
        cursor = self.cursor()
        cursor.executemany(query, seq_of_params)


def get_all_supported_tickers(db: SQLiteDatabase) -> list[str]:
    """Fetches all supported tickers from the database."""
    rows = db.execute("SELECT DISTINCT symbol FROM earnings_calendar")
    return [row[0] for row in rows]

def is_date_supported_for_ticker(db: SQLiteDatabase, ticker: str, date: str) -> bool:
    """Checks if a specific date is supported for a given ticker."""
    rows = db.execute(
        """
        SELECT 1
        FROM earnings_calendar
        WHERE symbol = ? AND date = ?
        LIMIT 1
        """,
        (ticker, date),
    )
    return len(rows) > 0

@overload
def get_ticker_surprise(
    db: SQLiteDatabase, ticker: str, date: str
) -> Optional[float]: ...

@overload
def get_ticker_surprise(
    db: SQLiteDatabase, ticker: str, date: None = None
) -> Optional[Dict[str, float]]: ...


def get_ticker_surprise(
    db: SQLiteDatabase, ticker: str, date: Optional[str] = None
) -> Optional[DateValues[float]]:
    if date is not None:
        rows = db.execute(
            """
            SELECT surprise
            FROM ticker_data
            WHERE symbol = ? AND date = ?
            LIMIT 1
            """,
            (ticker, date),
        )
        return rows[0][0] if rows else None

    rows = db.execute(
        """
        SELECT surprise, date
        FROM ticker_data
        WHERE symbol = ? AND date IS NOT NULL AND surprise IS NOT NULL
        ORDER BY date DESC
        """,
        (ticker,),
    )
    return {row[1]: row[0] for row in rows} if rows else None

@overload
def get_ticker_reaction(
    db: SQLiteDatabase, ticker: str, date: str
) -> Optional[float]: ...

@overload
def get_ticker_reaction(
    db: SQLiteDatabase, ticker: str, date: None = None
) -> Optional[Dict[str, float]]: ...


def get_ticker_reaction(
    db: SQLiteDatabase, ticker: str, date: Optional[str] = None
) -> Optional[DateValues[float]]:
    if date is not None:
        rows = db.execute(
            """
            SELECT reaction
            FROM ticker_data
            WHERE symbol = ? AND date = ?
            LIMIT 1
            """,
            (ticker, date),
        )
        return rows[0][0] if rows else None

    rows = db.execute(
        """
        SELECT reaction, date
        FROM ticker_data
        WHERE symbol = ? AND date IS NOT NULL AND reaction IS NOT NULL
        ORDER BY date DESC
        LIMIT 1
        """,
        (ticker,),
    )
    return {row[1]: row[0] for row in rows} if rows else None


def get_dates_of_ticker(db: SQLiteDatabase, ticker: str) -> list[str]:
    rows = db.execute(
        """
        SELECT date
        FROM earnings_calendar
        WHERE symbol = ?
        ORDER BY date DESC
        """,
        (ticker,),
    )
    return [row[0] for row in rows if row[0] is not None]

def ticker_in_db(db: SQLiteDatabase, ticker: str):
    rows = db.execute(
        """
        SELECT 1
        FROM earnings_calendar
        WHERE symbol = ?
        LIMIT 1
        """,
        (ticker,),
    )
    return len(rows) > 0


def upsert_earnings_calendar_rows(
    db: SQLiteDatabase,
    rows: list[tuple[str, str, Optional[float], Optional[float]]],
) -> None:
    if not rows:
        return

    db.executemany(
        """
        INSERT INTO earnings_calendar (symbol, date, eps_actual, eps_estimated)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(symbol, date) DO UPDATE SET
            eps_actual = COALESCE(excluded.eps_actual, earnings_calendar.eps_actual),
            eps_estimated = COALESCE(excluded.eps_estimated, earnings_calendar.eps_estimated)
        """,
        rows,
    )

def upsert_eps_data_of_ticker(
    db: SQLiteDatabase, ticker: str, date: str, eps_actual: Optional[float], eps_estimated: Optional[float]
) -> None:
    db.execute(
        """
        INSERT INTO earnings_calendar (symbol, date, eps_actual, eps_estimated)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(symbol, date) DO UPDATE SET
            eps_actual = COALESCE(excluded.eps_actual, earnings_calendar.eps_actual),
            eps_estimated = COALESCE(excluded.eps_estimated, earnings_calendar.eps_estimated)
        """,
        (ticker, date, eps_actual, eps_estimated),
)


def upsert_surprise_data(
    db: SQLiteDatabase, ticker: str, date: str, surprise: float
) -> None:
    db.execute(
        """
        INSERT INTO ticker_data (symbol, date, surprise)
        VALUES (?, ?, ?)
        ON CONFLICT(symbol, date) DO UPDATE SET
            surprise = excluded.surprise
        """,
        (ticker, date, surprise),
    )


def upsert_reaction_data(
    db: SQLiteDatabase, ticker: str, date: str, reaction: float
) -> None:
    db.execute(
        """
        INSERT INTO ticker_data (symbol, date, reaction)
        VALUES (?, ?, ?)
        ON CONFLICT(symbol, date) DO UPDATE SET
            reaction = excluded.reaction
        """,
        (ticker, date, reaction),
    )
