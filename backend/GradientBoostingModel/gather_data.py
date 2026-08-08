from ..adapters import SP500_COMPANIES
from ..logger import get_configured_logger
from ..db_functions.supabase import AsyncClient

from typing import List, Dict, Union
from postgrest import AsyncSelectRequestBuilder

type TickerDateMap[T] = Dict[str, Dict[str, T]]

logger = get_configured_logger(__name__)


async def get_all_rows(half_query: AsyncSelectRequestBuilder):
    rows = []
    offset = 0
    batch_size = 1000

    while True:
        resp = await half_query.range(offset, offset + batch_size - 1).execute()
        cur_rows = resp.data
        if len(cur_rows) < batch_size:
            break
        rows.extend(cur_rows)
        offset += batch_size

    return rows


async def gather_ratios_data(
    sbac: AsyncClient,
    symbol_date_agg: TickerDateMap[Dict[str, float]],
    ratio_rows: List[Dict[str, Union[str, int, float]]],
):
    for row in ratio_rows:
        if row["date"] == "2025-06-30":
            logger.warning("skipping the earliest data")
            continue

        cur_company_sector = SP500_COMPANIES[SP500_COMPANIES["Symbol"] == row["symbol"]]
        if cur_company_sector.empty:
            continue
        symbol, date = str(row["symbol"]), str(row["date"])
        prop_info = await (
            sbac.table("proportionality_model")
            .select("gross_margin_mean, gross_margin_sd")
            .eq("sector", cur_company_sector["GICS Sector"].values[0])
            .eq("filings_date", row["date"])
            .maybe_single()
            .execute()
        )
        if prop_info is None or not isinstance(prop_data := prop_info.data, dict):
            logger.warning(f"proportionality data not found for {symbol=}, {date=}")
            continue
        symbol_date_agg[symbol][date] = {
            k: float(v) for k, v in row.items() if k not in ["symbol", "id", "date"]
        }
        cur_date_info = symbol_date_agg[symbol][date]
        symbol_date_agg[symbol][date]["gross_profit_z_score"] = (
            cur_date_info["gross_profit_pct"] - float(prop_data["gross_margin_mean"])  # type: ignore
        ) / float(
            prop_data["gross_margin_sd"]  # type: ignore
        )

    return symbol_date_agg


async def get_final_dataset(
    sbac: AsyncClient,
    symbol_date_agg: TickerDateMap[Dict[str, float]],
    ticker_filing_date_to_reaction_map: TickerDateMap[List[Dict[str, float]]],
):
    final_dataset = []

    def insert_into_dataset(rows: List, eps_prop_data: Dict):
        for index, row in enumerate(rows):
            data_point = {
                k: v
                for k, v in row.items()
                if k
                not in [
                    "symbol",
                    "id",
                    "filings_date",
                    "reaction_date",
                    "announcement_date",
                ]
            }
            final_dataset.append(
                {
                    **symbol_date_agg[ticker][filing_date],
                    **data_point,
                    "day": index + 1,
                    "pct_surprise_z_score": (
                        data_point["surprise"]
                        - float(eps_prop_data["pct_surprise_mean"])
                    )
                    / float(eps_prop_data["pct_surprise_sd"]),
                }
            )

    for ticker, date_info in ticker_filing_date_to_reaction_map.items():
        cur_company_sector = SP500_COMPANIES[SP500_COMPANIES["Symbol"] == ticker]
        if cur_company_sector.empty:
            continue

        for filing_date, rows in date_info.items():
            if not filing_date in symbol_date_agg[ticker]:
                continue
            eps_prop = await (
                sbac.table("proportionality_model")
                .select("pct_surprise_mean, pct_surprise_sd")
                .eq("sector", cur_company_sector["GICS Sector"].values[0])
                .eq("filings_date", filing_date)
                .maybe_single()
                .execute()
            )
            if eps_prop is None or not isinstance(eps_prop_data := eps_prop.data, dict):
                continue
            insert_into_dataset(rows, eps_prop_data)

    return final_dataset


async def get_dataset(sbac: AsyncClient):
    ratios_rows = await get_all_rows(
        sbac.table("earnings_calendar")
        .select()
        .not_.is_("drift", None)
        .not_.is_("volatility", None)
        .not_.is_("current_ratio", None)
        .not_.is_("gross_profit_pct", None)
        .not_.is_("asset_turnover", None)
        .order("id")
    )
    unique_tickers = list(set([row["symbol"] for row in ratios_rows]))
    symbol_date_agg = {ticker: {} for ticker in unique_tickers}

    symbol_date_agg = await gather_ratios_data(sbac, symbol_date_agg, ratios_rows)

    surprise_reaction_rows = await get_all_rows(
        sbac.table("ticker_data")
        .select()
        .in_("symbol", unique_tickers)
        .order("reaction_date")
    )
    ticker_filing_date_to_reaction_map = {ticker: {} for ticker in unique_tickers}
    for row in surprise_reaction_rows:
        if not isinstance(row, dict):
            continue

        if row["filings_date"] is None or row["announcement_date"] is None:
            continue

        if not row["filings_date"] in ticker_filing_date_to_reaction_map[row["symbol"]]:
            ticker_filing_date_to_reaction_map[row["symbol"]][row["filings_date"]] = []

        ticker_filing_date_to_reaction_map[row["symbol"]][row["filings_date"]].append(
            row
        )

    return await get_final_dataset(
        sbac, symbol_date_agg, ticker_filing_date_to_reaction_map
    )

