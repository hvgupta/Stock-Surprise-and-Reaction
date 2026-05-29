from backend.logger import get_configured_logger

from supabase import AsyncClient
from typing import Optional, Dict, Any, cast, Tuple, TypeVar

# Python 3.11-compatible generic type alias
T = TypeVar("T")
DateValues = Dict[str, T]

logger = get_configured_logger(__name__)

SUPABASE_URL = "https://xtetgruwektiyndlfvju.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "sb_publishable_ME2wkmZCDfW1TceAK4WaiQ_WqqANIsr"


def create_async_client(API_KEY: Optional[str]):
    logger.info("Creating Supabase AsyncClient")
    return AsyncClient(SUPABASE_URL, API_KEY or SUPABASE_PUBLISHABLE_KEY)


async def get_ticker_surprise(
    sbac: AsyncClient, symbol: str, filings_date: Optional[str] = None
) -> Optional[DateValues[float]]:
    query = sbac.table("ticker_data").select("filings_date, surprise").eq("symbol", symbol)
    if filings_date:
        query = query.eq("filings_date", filings_date)

    try:
        result = await query.execute()
    except Exception as e:
        logger.error(f"Error fetching surprise for {symbol} on {filings_date}: {e}")
        return None
    logger.info(f"Result for {symbol} on {filings_date}: {result}")
    if result is None:
        logger.warning(f"No surprise found for {symbol} on {filings_date}")
        return None

    data = cast(list[dict[str, Any]], result.data or [])
    return {
        row["filings_date"]: row["surprise"]
        for row in data
        if isinstance(row.get("filings_date"), str)
        and isinstance(row.get("surprise"), (int, float))
    }


async def get_ticker_reaction(
    sbac: AsyncClient,
    symbol: str,
    filings_date: Optional[str] = None,
    reaction_date: Optional[str] = None,
) -> Optional[DateValues[DateValues[float]]]:
    query = (
        sbac.table("ticker_data")
        .select("filings_date, reaction_date, reaction")
        .eq("symbol", symbol)
    )
    if filings_date:
        query = query.eq("filings_date", filings_date)
    if reaction_date:
        query = query.eq("reaction_date", reaction_date)

    query = query.order("reaction_date")
    try:
        result = await query.execute()
    except Exception as e:
        logger.error(
            f"Error fetching reaction for {symbol} on {filings_date} and {reaction_date}: {e}"
        )
        return None

    if result is None:
        logger.warning(
            f"No reaction found for {symbol} on {filings_date} and {reaction_date}"
        )
        return None

    data = cast(list[dict[str, Any]], result.data or [])
    reactions_by_filing_date: Dict[str, DateValues[float]] = {}
    for row in data:
        filings_date = row.get("filings_date")
        reaction_date = row.get("reaction_date")
        reaction = row.get("reaction")
        if (
            isinstance(filings_date, str)
            and isinstance(reaction_date, str)
            and isinstance(reaction, (int, float))
        ):
            if filings_date not in reactions_by_filing_date:
                reactions_by_filing_date[filings_date] = {}
            reactions_by_filing_date[filings_date][reaction_date] = reaction
    return reactions_by_filing_date


async def get_ticker_propotionality_data(
    sbac: AsyncClient, sector: str, filings_date: Optional[str] = None
) -> Optional[DateValues[Tuple[float, float, float, float]]]:
    query = (
        sbac.table("proportionality_model")
        .select("filings_date, pct_surprise_mean, pct_surprise_sd, alpha, beta")
        .eq("sector", sector)
    )
    if filings_date:
        query = query.eq("filings_date", filings_date)
    try:
        result = await query.execute()
    except Exception as e:
        logger.error(
            f"Error fetching proportionality data for sector {sector} on {filings_date}: {e}"
        )
        return None

    if result is None:
        logger.warning(
            f"No proportionality data found for sector {sector} on {filings_date}"
        )
        return None

    data = cast(list[dict[str, Any]], result.data or [])
    return {
        row["filings_date"]: (
            row["pct_surprise_mean"],
            row["pct_surprise_sd"],
            row["alpha"],
            row["beta"],
        )
        for row in data
    }


async def get_sp500_latest_surprises(sbac: AsyncClient):
    try:
        resp = (await sbac.rpc("sp500_latest_surprises").execute()).data
        if not isinstance(resp, list):
            raise ValueError("Unexpected response format from RPC: expected a list")
        return resp
    except Exception as e:
        logger.error(f"Error fetching SP500 latest surprises: {e}")
        return None


async def get_model_data_points(sbac: AsyncClient, sector: str, filings_date: str):
    try:
        resp = (
            await sbac.table("data_points")
            .select("data")
            .eq("sector", sector)
            .eq("filings_date", filings_date)
            .maybe_single()
            .execute()
        )
        if resp is None:
            logger.warning(
                f"No data points found for sector {sector} on {filings_date}"
            )
            return None
        output = resp.data.get("data") if isinstance(resp.data, dict) else None
        if not isinstance(output, dict):
            logger.warning(
                f"Unexpected data format for data points of sector {sector} on {filings_date}: expected a dict"
            )
            return None
        return output
    except Exception as e:
        logger.error(
            f"Error fetching model data points for sector {sector} on {filings_date}: {e}"
        )
        return None
    
async def insert_model_data_points(admin_sbac: AsyncClient, sector: str, filings_date: str, data_points: dict):
    try:
        await admin_sbac.table("data_points").insert({
            "sector": sector,
            "filings_date": filings_date,
            "data": data_points
        }).execute()
        logger.info(f"Successfully inserted model data points for sector {sector} on {filings_date}")
    except Exception as e:
        logger.error(f"Error inserting model data points for sector {sector} on {filings_date}: {e}")


async def insert_proportionality_model(admin_sbac: AsyncClient, sector: str, filings_date: str, pct_surprise_mean: float, pct_surprise_sd: float, alpha: float, beta: float):
    try:
        await admin_sbac.table("proportionality_model").insert({
            "sector": sector,
            "filings_date": filings_date,
            "pct_surprise_mean": pct_surprise_mean,
            "pct_surprise_sd": pct_surprise_sd,
            "alpha": alpha,
            "beta": beta
        }).execute()
        logger.info(f"Successfully inserted proportionality model for sector {sector} on {filings_date}")
    except Exception as e:
        logger.error(f"Error inserting proportionality model for sector {sector} on {filings_date}: {e}")