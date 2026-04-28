from app.logger import get_configured_logger
logger = get_configured_logger(__name__)

import sqlite3

def initialize_db(db_path: str) -> None:
    """Initializes the SQLite database with the required tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
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
            
        )
    ''')
    
    conn.commit()
    conn.close()