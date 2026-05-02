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

If $|$`raw_surprise`$|\ge$ `SURPRISE_THRESHOLD`, then it is returned for the ticker 

### Reaction
If $|$`raw_surprise`$|\ge$ `SURPRISE_THRESHOLD`, then reaction is calulated

Reaction is defined as 
$$
\begin{aligned}
    \text{Reaction}&(\text{days\_from\_earnings\_report}) \\ 
    &=R_\text{ticker}(\text{days\_from\_earnings\_report}) - R_\text{market}(\text{days\_from\_earnings\_report})
\end{aligned}
$$

Where 
- $R_\text{ticker}(\text{days\_from\_earnings\_report})$ is defined as the returns from the company's stock from the closing price of the day the earnings report was published.
- $R_\text{market}(\text{days\_from\_earnings\_report})$ follows the same logic.

Essentially, the assumption here is that the impact of _Surpise_ over-powers any other factors over the `days_from_earnings_report` period

### Proportionality
In order to determine this, 
A linear regression is set up, where the formula idea is basically $$\text{Reaction} = \text{intercept} + \beta\times\text{surprise-z-score}$$

here `surprise-z-score` is just $$\frac{\text{surprise of ticker} - \mu_\text{surprise of companies in the same sector}}{\sigma_\text{surprise of the companies in the same sector}}$$

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
