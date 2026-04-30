# Stock Surprise and Reaction

## My understanding of the task
- For all of the companies from S&P500 whos data I am able to retrieve, which surprised market the most
    - I will define raw-surprise as: $\frac{\text{Actual EPS} - \text{Estimated EPS}}{\text{Estimated EPS}}$
    - The absolute value of it can be used to determine if it actually is a surprise ($\pm 10\%$)


How will the surprise be calculated:
- lets say todays date is x
- Then I find the closest earnings, and then find the actual EPS and predicted EPS for this time
- if $\text{surprise}\geq\text{Threshold}$ then look for the market reaction over some time period 
    - this is just to filter out tickers with insignificant price movement

- for all of those companies, compare it to the market avg movement 
    - lets say the returns over the next few days after the earnings call is $R_m$
    - the reaction of the market can be defined as $R_\text{ticker} - R_m$



## plan

data storage
    - possible storage
        - local files
        - supabase
        - sqllite3 -> the simpliest and most appropiate for this small project

    - might not be needed, since all the other functions dont really have a rate limit

## API notes (current)
- Populate the DB (yfinance earnings history for S&P500): `POST /populate/sp500/earnings_calendar`
    - Uses a concurrency limit via `batch_size` query param (default 10).
    - Upserts all available earnings history rows into `earnings_calendar` keyed by `(symbol, date)`.
- Surprise endpoint: `GET /{ticker}/surprise?date=YYYY-MM-DD` (date optional)
    - If `date` is omitted, uses the most recent earnings date available in `earnings_calendar`.
- Reaction endpoint: `GET /{ticker}/reaction?date=YYYY-MM-DD&num_day_return=...&market_index=...&threshold=...`
    - Reaction is calculated starting from the same `date` used for the surprise.
