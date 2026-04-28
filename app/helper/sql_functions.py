import sqlite3

from app.logger import get_configured_logger

logger = get_configured_logger(__name__)


def initialize_db(db_path: str) -> None:
    """Initializes the SQLite database with the required tables."""
    with SQLiteDatabase(db_path) as database:
        database.initialize()


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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS earnings_calendar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                eps_actual REAL,
                eps_estimated REAL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ticker_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                surprise REAL,
                eod_return REAL,
                reaction REAL
            )
        ''')

    def execute(
        self,
        query: str,
        params: tuple | list = (),
    ):
        cursor = self.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()
