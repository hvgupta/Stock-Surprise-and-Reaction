import re
import aiohttp
import requests
import pandas as pd
from typing import Dict
from pandas import Timestamp

HEADERS = {"User-Agent": "Mozilla/5.0 (Company info@company.com)"}


def fetch_ticker_to_cik_map() -> Dict[str, str]:
    print("Fetching ticker to CIK mapping from SEC (async)")
    url = "https://www.sec.gov/files/company_tickers.json"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    ticker_to_cik_map = {
        info["ticker"]: str(info["cik_str"]).zfill(10)
        for info in response.json().values()
    }

    print("Successfully fetched ticker to CIK mapping")
    return ticker_to_cik_map


async def fetch_sec_concepts(cik: str) -> dict:
    print(f"Fetching SEC concepts for CIK={cik} (async)")
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                raise Exception(
                    f"Failed to fetch data, code: {resp.status}, reason: {resp.reason or (await resp.text())}"
                )


def _get_start_and_end_of_quarter(year: int, quarter: int):
    if quarter == 1:
        start, end = Timestamp(year=year, month=1, day=1), Timestamp(
            year=year, month=3, day=31
        )
    elif quarter == 2:
        start, end = Timestamp(year=year, month=4, day=1), Timestamp(
            year=year, month=6, day=30
        )
    elif quarter == 3:
        start, end = Timestamp(year=year, month=7, day=1), Timestamp(
            year=year, month=9, day=30
        )
    elif quarter == 4:
        start, end = Timestamp(year=year, month=10, day=1), Timestamp(
            year=year, month=12, day=31
        )
    else:
        start, end = Timestamp(year=year, month=1, day=1), Timestamp(
            year=year, month=12, day=31
        )
    return start, end


def _compute_missing_quarter_from_fy(
    y_q_to_quantity_map: dict, year: int, quantity_name: str, fy_val: float
) -> dict:

    # collect present quarters
    present = {}
    for q in ("Q1", "Q2", "Q3", "Q4"):
        v = y_q_to_quantity_map.get((year, q), {})
        val = v.get(quantity_name) if isinstance(v, dict) else None
        try:
            val_num = float(val) if val is not None else None
        except Exception:
            val_num = None
        if val_num is not None:
            present[q] = val_num

    if len(present) == 4:
        print(f"All quarters present for {year}, no imputation needed")
        return y_q_to_quantity_map

    missing_qs = [q for q in ("Q1", "Q2", "Q3", "Q4") if q not in present]
    if len(missing_qs) != 1:
        print(
            f"{year} has {len(missing_qs)} missing quarters; need exactly 1 to impute"
        )
        return y_q_to_quantity_map

    missing_q = missing_qs[0]
    sum_three = sum(present.values())

    imputed_val = fy_val - sum_three
    start, end = _get_start_and_end_of_quarter(year, int(missing_q[1]))
    y_q_to_quantity_map[(year, missing_q)] = {
        "start": start,
        "end": end,
        quantity_name: imputed_val,
        "fp": missing_q,
    }
    print(
        f"Computed {missing_q} for {year}: {quantity_name}={imputed_val} "
        f"(FY {fy_val} - sum_other_three {sum_three})"
    )
    return y_q_to_quantity_map


def _get_frame_data(table: pd.DataFrame, year: int, quarter: str):
    subset = table[(table["frame"] == f"CY{year}{quarter}")].sort_values(
        "filed", ascending=False
    )

    if subset.empty:
        print(f"No data for year {year} quarter {quarter}")
        return None

    return subset.iloc[0]


def clean_period_table(
    table_val: pd.DataFrame, start_year: int, end_year: int, quantity_name: str
):
    print(f"Starting to clean EPS table with {len(table_val)} rows")
    filtered_period_table = pd.DataFrame(columns=["start", "end", quantity_name, "fp"])
    y_q_to_quantity_map = {}
    for year in range(start_year, end_year + 1):
        for quarter in ["Q1", "Q2", "Q3", "Q4"]:

            y_q_eps_table = _get_frame_data(table_val, year, quarter)
            if y_q_eps_table is None:
                continue

            start, end = _get_start_and_end_of_quarter(year, int(quarter[1]))

            y_q_to_quantity_map[(year, quarter)] = {
                "start": start,
                "end": end,
                quantity_name: y_q_eps_table["val"],
                "fp": quarter,
            }

        y_q_eps_table = _get_frame_data(table_val, year, "")
        if y_q_eps_table is None:
            print(f"No FY data for year {year}, cannot impute missing quarters")
            continue

        fy_val = y_q_eps_table["val"]
        y_q_to_quantity_map = _compute_missing_quarter_from_fy(
            y_q_to_quantity_map, year, quantity_name, fy_val
        )

    filtered_period_table = pd.concat(
        [filtered_period_table, pd.DataFrame(list(y_q_to_quantity_map.values()))],
        ignore_index=True,
    )
    print(f"Cleaned period table: {len(filtered_period_table)} rows after processing")

    filtered_period_table.sort_values(
        ["end", "start"], ascending=[True, False], inplace=True
    )
    filtered_period_table.reset_index(drop=True, inplace=True)

    filtered_period_table["start"] = pd.to_datetime(filtered_period_table["start"])
    filtered_period_table["end"] = pd.to_datetime(filtered_period_table["end"])

    return filtered_period_table

def conv_dict_to_df(facts: dict, metric_name: str, unit: str) -> pd.DataFrame:
    """
    Extract quarterly fact entries from the SEC companyfacts JSON.
    Performs DataFrame construction and datetime conversion in a thread to avoid blocking.
    """
    print(f"Extracting quarterly data for {metric_name} in {unit} (async)")

    def _extract() -> pd.DataFrame:
        if "us-gaap" not in facts:
            print("us-gaap data not found in facts")
            return pd.DataFrame()

        if metric_name not in facts["us-gaap"]:
            print(f"{metric_name} not found in us-gaap facts")
            return pd.DataFrame()

        units = facts["us-gaap"][metric_name].get("units", {})
        if unit not in units:
            print(f"{unit} not found for {metric_name}")
            return pd.DataFrame()

        data = facts["us-gaap"][metric_name]["units"][unit]
        df = pd.DataFrame(data)
        if "end" in df.columns:
            df["end"] = pd.to_datetime(df["end"], errors="coerce")
            df = df.sort_values(by="end").reset_index(drop=True)
        else:
            # no end column -> empty
            return pd.DataFrame()
        return df

    df = _extract()
    if df.empty:
        print(f"No quarterly data extracted for {metric_name}")
    else:
        print(f"Successfully extracted quarterly data for {metric_name}")
    return df