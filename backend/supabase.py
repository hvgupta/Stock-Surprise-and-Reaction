from backend.logger import get_configured_logger

from supabase import AsyncClient
from typing import Optional, Dict, Any, cast, Tuple

type DateValues[T] = Dict[str, T]

logger = get_configured_logger(__name__)

SUPABASE_URL = "https://xtetgruwektiyndlfvju.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "sb_publishable_ME2wkmZCDfW1TceAK4WaiQ_WqqANIsr"


def create_async_client(API_KEY: str = SUPABASE_PUBLISHABLE_KEY):
    return AsyncClient(SUPABASE_URL, API_KEY)


async def get_ticker_surprise(
    sbac: AsyncClient, ticker: str, filing_date: Optional[str] = None
) -> Optional[DateValues[float]]:
    query = sbac.table("surprises").select("filing_date, surprise").eq("ticker", ticker)
    if filing_date:
        query = query.eq("filing_date", filing_date)

    try:
        result = await query.execute()
    except Exception as e:
        logger.error(f"Error fetching surprise for {ticker} on {filing_date}: {e}")
        return None

    if result is None:
        logger.warning(f"No surprise found for {ticker} on {filing_date}")
        return None

    data = cast(list[dict[str, Any]], result.data or [])
    return {
        row["filing_date"]: row["surprise"]
        for row in data
        if isinstance(row.get("filing_date"), str)
        and isinstance(row.get("surprise"), (int, float))
    }


async def get_ticker_reaction(
    sbac: AsyncClient,
    ticker: str,
    filing_date: Optional[str] = None,
    reaction_date: Optional[str] = None,
) -> Optional[DateValues[DateValues[float]]]:
    query = (
        sbac.table("reactions")
        .select("filing_date, reaction_date, reaction")
        .eq("ticker", ticker)
    )
    if filing_date:
        query = query.eq("filing_date", filing_date)
    if reaction_date:
        query = query.eq("reaction_date", reaction_date)

    try:
        result = await query.execute()
    except Exception as e:
        logger.error(
            f"Error fetching reaction for {ticker} on {filing_date} and {reaction_date}: {e}"
        )
        return None

    if result is None:
        logger.warning(
            f"No reaction found for {ticker} on {filing_date} and {reaction_date}"
        )
        return None

    data = cast(list[dict[str, Any]], result.data or [])
    reactions_by_filing_date: Dict[str, DateValues[float]] = {}
    for row in data:
        filing_date = row.get("filing_date")
        reaction_date = row.get("reaction_date")
        reaction = row.get("reaction")
        if (
            isinstance(filing_date, str)
            and isinstance(reaction_date, str)
            and isinstance(reaction, (int, float))
        ):
            if filing_date not in reactions_by_filing_date:
                reactions_by_filing_date[filing_date] = {}
            reactions_by_filing_date[filing_date][reaction_date] = reaction
    return reactions_by_filing_date


async def get_ticker_propotionality_data(
    sbac: AsyncClient, sector: str, filing_date: Optional[str] = None
) -> Optional[DateValues[Tuple[float, float, float, float]]]:
    query = (
        sbac.table("proportionality")
        .select("filing_date, pct_surprise_mean, pct_surprise_sd, alpha, beta")
        .eq("sector", sector)
    )
    if filing_date:
        query = query.eq("filing_date", filing_date)
    try:
        result = await query.execute()
    except Exception as e:
        logger.error(
            f"Error fetching proportionality data for sector {sector} on {filing_date}: {e}"
        )
        return None

    if result is None:
        logger.warning(
            f"No proportionality data found for sector {sector} on {filing_date}"
        )
        return None

    data = cast(list[dict[str, Any]], result.data or [])
    return {
        row["filing_date"]: (
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
            .eq("filing_date", filings_date)
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
