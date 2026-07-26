class Supabase:
    from .supabase import (
        get_ticker_surprise,
        get_ticker_reaction,
        create_async_client,
        get_model_data_points,
        insert_model_data_points,
        get_sp500_latest_surprises,
        insert_proportionality_model,
        get_ticker_propotionality_data,
    )

class SQLite:
    from .sql_functions import (
        ticker_in_db,
        SQLiteDatabase,
        get_ticker_surprise,
        get_ticker_reaction,
        get_dates_of_ticker,
        upsert_surprise_data,
        upsert_reaction_data,
        upsert_eps_data_of_ticker,
        get_all_supported_tickers,
        upsert_proportionality_model,
        is_date_supported_for_ticker,
        get_ticker_proportionality_data
    )

__all__ = [
    "Supabase",
    "SQLite"
]