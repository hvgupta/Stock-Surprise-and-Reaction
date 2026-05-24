from backend.logger import get_configured_logger

logger = get_configured_logger(__name__)

import sqlite3
from typing import Iterable, Optional, Dict, overload, Union, Tuple

type DateValues[T] = Dict[str, T]


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
                filing_date TEXT,
                reaction_date TEXT,
                surprise REAL,
                reaction REAL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS proportionality_model (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sector TEXT NOT NULL,
                filing_date TEXT,
                percent_surprise_mean REAL,
                percent_surprise_sd REAL,
                alpha REAL,
                beta REAL
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_proportionality_model_sector_filing_date
            ON proportionality_model(sector, filing_date)
            """)

        # Backfill schema for older DBs that lack ticker_data.date
        existing_columns = {
            row[1]
            for row in cursor.execute("PRAGMA table_info(ticker_data)").fetchall()
        }
        if "reaction_date" not in existing_columns:
            cursor.execute("ALTER TABLE ticker_data ADD COLUMN reaction_date TEXT")

        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_ticker_data_symbol_reaction_date
            ON ticker_data(symbol, reaction_date)
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

    def commit(self) -> None:
        if self.connection is None:
            raise RuntimeError("Database connection is not open")
        self.connection.commit()


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



def get_ticker_surprise(
    db: SQLiteDatabase, ticker: str, filing_date: Optional[str] = None
) -> Optional[DateValues[float]]:
    if filing_date is not None:
        rows = db.execute(
            """
            SELECT surprise
            FROM ticker_data
            WHERE symbol = ? AND filing_date = ?
            LIMIT 1
            """,
            (ticker, filing_date),
        )
        return {filing_date: rows[0][0]} if rows else None

    rows = db.execute(
        """
        SELECT surprise, filing_date
        FROM ticker_data
        WHERE symbol = ? AND filing_date IS NOT NULL AND surprise IS NOT NULL
        ORDER BY reaction_date DESC
        """,
        (ticker,),
    )
    return {row[1]: row[0] for row in rows} if rows else None


def get_ticker_reaction(
    db: SQLiteDatabase,
    ticker: str,
    filing_date: Optional[str] = None,
    reaction_date: Optional[str] = None,
) -> Optional[DateValues[DateValues[float]]]:
    """Fetch reaction values grouped by filing_date then date.

    Return shape is always:
        { filing_date: { date: reaction } }

    Parameter behavior:
    - filing_date is None and date is None: return all available reaction entries.
    - filing_date only: return all dates under that filing_date.
    - date only: return the entry/entries for that date keyed by filing_date.
    - both: return the specific value if it exists.
    """

    if filing_date is not None and reaction_date is not None:
        rows = db.execute(
            """
            SELECT reaction
            FROM ticker_data
            WHERE symbol = ? AND filing_date = ? AND reaction_date = ? AND reaction IS NOT NULL
            LIMIT 1
            """,
            (ticker, filing_date, reaction_date),
        )
        return {filing_date: {reaction_date: rows[0][0]}} if rows else None

    if filing_date is not None:
        rows = db.execute(
            """
            SELECT reaction_date, reaction
            FROM ticker_data
            WHERE symbol = ? AND filing_date = ? AND reaction_date IS NOT NULL AND reaction IS NOT NULL
            ORDER BY reaction_date DESC
            """,
            (ticker, filing_date),
        )
        if not rows:
            return None
        return {filing_date: {str(row[0]): float(row[1]) for row in rows}}

    if reaction_date is not None:
        rows = db.execute(
            """
            SELECT filing_date, reaction
            FROM ticker_data
            WHERE symbol = ? AND reaction_date = ? AND filing_date IS NOT NULL AND reaction IS NOT NULL
            ORDER BY filing_date DESC
            """,
            (ticker, reaction_date),
        )
        if not rows:
            return None
        out: DateValues[float] = {}
        return {str(row[0]): {reaction_date: float(row[1])} for row in rows}

    rows = db.execute(
        """
        SELECT filing_date, reaction_date, reaction
        FROM ticker_data
        WHERE symbol = ?
          AND filing_date IS NOT NULL
          AND reaction_date IS NOT NULL
          AND reaction IS NOT NULL
        ORDER BY filing_date DESC, reaction_date DESC
        """,
        (ticker,),
    )
    if not rows:
        return None
    return {str(row[0]): {str(row[1]): float(row[2])} for row in rows}


def get_ticker_proportionality_data(
    db: SQLiteDatabase, sector: str, filings_date: Optional[str] = None
) -> Optional[DateValues[Tuple[float, float, float, float]]]:
    if filings_date is not None:
        rows = db.execute(
            """
            SELECT percent_surprise_mean, percent_surprise_sd, alpha, beta
            FROM proportionality_model
            WHERE sector = ? AND filing_date = ?
            LIMIT 1
            """,
            (sector, filings_date),
        )
        return {filings_date: rows[0]} if rows else None
    rows = db.execute(
        """
        SELECT filing_date, percent_surprise_mean, percent_surprise_sd, alpha, beta
        FROM proportionality_model
        WHERE sector = ?
        ORDER BY filing_date
        """,
        (sector,),
    )
    return {row[0]: row[1:] for row in rows} if rows else None


def upsert_proportionality_model(
    db: SQLiteDatabase,
    sector: str,
    filing_date: str,
    percent_surprise_mean: float,
    percent_surprise_sd: float,
    alpha: float,
    beta: float,
) -> None:
    """Save a proportionality model for a sector.

    The table does not enforce uniqueness on sector, so we delete prior rows
    for the sector before inserting the latest values.
    """

    db.execute(
        """
        DELETE FROM proportionality_model
        WHERE sector = ? AND filing_date = ?
        """,
        (sector, filing_date),
    )
    db.execute(
        """
        INSERT INTO proportionality_model (
            sector,
            filing_date,
            percent_surprise_mean,
            percent_surprise_sd,
            alpha,
            beta
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (sector, filing_date, percent_surprise_mean, percent_surprise_sd, alpha, beta),
    )

    db.commit()


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
    db.commit()


def upsert_eps_data_of_ticker(
    db: SQLiteDatabase,
    ticker: str,
    date: str,
    eps_actual: Optional[float],
    eps_estimated: Optional[float],
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
    db.commit()


def upsert_surprise_data(
    db: SQLiteDatabase, ticker: str, date: str, surprise: float
) -> None:
    db.execute(
        """
        INSERT INTO ticker_data (symbol, filing_date, surprise)
        VALUES (?, ?, ?)
        """,
        (ticker, date, surprise),
    )
    db.commit()


def upsert_reaction_data(
    db: SQLiteDatabase, ticker: str, filing_date: str, reaction_date: str, reaction: float
) -> None:
    db.execute(
        """
        INSERT INTO ticker_data (symbol, filing_date, reaction_date, reaction)
        VALUES (?, ?, ?, ?)
        """,
        (ticker, filing_date, reaction_date, reaction),
    )
    db.commit()
