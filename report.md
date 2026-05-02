# Stock Surprise and Reaction

## My understanding of the task
> For the most recent earnings season, which S&P 500 companies surprised the market — and was the stock reaction proportionate to the surprise?

My understanding of this question is that there are three sub-questions, which are.
### Surprise
Calculate the `raw_surprise` of S&P 500 companies, and then use a threshold to determine actual _Surprise_
- this is going to help to reduce the downstream computation and also helps us to know what is actually a _Surprise_ 
### Reaction
Get the _Reaction_ (over next few days) of market to the _Surprise_. Here _Reaction_ will be defined as the change in the stock price which is not attributable to the market movement.
- The reaction can be over multiple days, I looked at a shorter term window, since there are going to fewer **other** factors affecting the stock price. 
### Proportionality
Get the _Proportionality_ of the _Reaction_. This part of the question askes, if the _Surprise_ follows the expected _Reaction_.

## Definition of Each Section
### Surprise
`raw_surprise` in this project is defined as $$\frac{\text{Actual EPS} - \text{Estimated EPS}}{|\text{Estimated EPS}|}$$ (Just Standardised Unexpected Earnings)

This will give us the percentage difference, and could be any real number. Therefore to reduce the noise in data, a customizable variable `SURPRISE_THRESHOLD` will be set (currently set to 0.03).

If |`raw_surprise`|$\ge$ `SURPRISE_THRESHOLD`, then it is returned for the ticker 

### Reaction
If |`raw_surprise`|$\ge$ `SURPRISE_THRESHOLD`, then reaction is calulated

Reaction is defined as 
$\text{Reaction}(\text{days from earnings report}) \\ =R_\text{ticker}(\text{days from earnings report}) - R_\text{market}(\text{days from earnings report})$

Where 
- $R_\text{ticker}(\text{days from earnings report})$ is defined as the returns from the company's stock from the closing price of the day the earnings report was published.
- $R_\text{market}(\text{days from earnings report})$ follows the same logic.

Essentially, the assumption here is that the impact of _Surpise_ over-powers any other factors over the `days_from_earnings_report` period

### Proportionality
In order to determine this, 
A linear regression is set up, where the formula idea is basically $$E[\text{Reaction}] = \text{intercept} + \beta\times\text{surprise-z-score}$$

here `surprise-z-score` is just $$\frac{\text{surprise of ticker} - \mu_\text{surprise of companies in the same sector}}{\sigma_\text{surprise of the companies in the same sector}}$$

Finally if to know the _Reaction_ is proportional, we can just compute $$\frac{\text{Actual Reaction} - E[Reaction]}{|E[Reaction]|}$$
This will give us the percentage difference between the expected reaction and the actual reaction, then finally we can define another configurable parameter `PROP_REACTION_THESHOLD`, then we can say that the reaction is Proportionate if |percentage diff| $\le$ `PROP_REACTION_THESHOLD`

The reason why I have choose to use a linear regression is because it is reletively simple to implement and test in the time period provided to me.

## Code functionality
### Core Algorithms & Formulas

| # | Name | Formula | Output |
|---|------|---------|--------|
| 1 | EPS Surprise | `(epsEstimate − epsActual) / \|epsActual\|` | Dimensionless ratio; negative = beat |
| 2 | Daily Return | `(Close[n] − Close[n−1]) / Close[n−1]` | Fraction of price change in one day |
| 3 | Cumulative Return | `Σ daily_return[i]` over window | Total return across N days |
| 4 | CAR (reaction) | `cumulative_ticker_return − cumulative_market_return` | Abnormal return vs. benchmark |
| 5 | Z-Score of Surprise | `(surprise − μ_sector) / σ_sector` | Sector-normalised surprise |
| 6 | Expected CAR | `α + β × z_score` | Sector model prediction |
| 7 | Proportionality | `(actual_CAR − expected_CAR) / \|expected_CAR\|` | Over/under-reaction vs. sector norm |

The regression coefficients `α` and `β` are fitted with `numpy.polyfit(z_scores, cars, deg=1)` using population standard deviation (`ddof=0`). The model requires a minimum of **12** (surprise, CAR) pairs and collects up to **60** pairs per sector before fitting.

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Web framework | FastAPI + uvicorn | Async HTTP API |
| Data validation | Pydantic v2 | Request/response schema enforcement |
| Stock data | yfinance | EPS history, price history, P/E ratios |
| Numerics | numpy, pandas | Statistical calculations, regression |
| Persistence | SQLite (`markets.db`) | Local cache for computed values |
| HTML parsing | lxml | Scrape S&P 500 list from Wikipedia |

### Data fetching functions

**`yf.py`** — Yahoo Finance wrapper:

| Function | Returns |
|----------|---------|
| `get_earnings_history_of_ticker(ticker)` | DataFrame with `epsActual`, `epsEstimate` indexed by date |
| `get_1d_return_of_ticker(ticker, date)` | Single-day return as a float; uses `_ceil_working_day` to skip weekends/holidays |
| `fetch_ticker_historical_prices(ticker, start, end)` | OHLCV DataFrame |
| `get_current_pe_of_ticker(ticker)` | Trailing P/E from `yf.Ticker.info` |
| `get_current_forward_pe_of_ticker(ticker)` | Forward P/E |
| `get_last_earnings_call_of_ticker(ticker)` | Most recent earnings date |

**`SP500_companies.py`** — scrapes Wikipedia's S&P 500 table, returning a DataFrame with `Symbol` and `GICS Sector` columns used to organise tickers by sector for the proportionality model.

### API Reference

| Endpoint | Method | Key Parameters | Description |
|----------|--------|---------------|-------------|
| `/health` | GET | — | Liveness check |
| `/{ticker}/surprise` | GET | `date` (YYYY-MM-DD, optional) | Surprise % for a filing date; omit date for most recent |
| `/{ticker}/reaction` | GET | `filings_date`, `reaction_date`, `reaction_days_threshold` (1–3), `market_index`, `surprise_threshold` | CAR over the reaction window |
| `/{ticker}/proportionate` | GET | `filings_date` + `reaction_date` OR `surprise` + `cumalative_reaction` | Expected vs. actual CAR and proportionality ratio |

All endpoints return JSON. Errors use standard HTTP status codes with a `detail` field.

## Possible improvments to the project
- The calculation of reaction currently does not consider public holidays (but weekends are considered). Although this would be reletively simple fix as the `_round_to_working_day` function can be updated to include that information, but the process is time consuming and would lead to bruteforce
- Another improvment that can be made is the access to more hisotrical data, as the model being used does not have many data points to get a full understanding of the model.
- Improvement to the model: the model is a simple linear regression model and may not be able to solve for cases where relationship is not linear