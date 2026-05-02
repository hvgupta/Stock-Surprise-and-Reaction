# Oxbow — Stock Surprise & Reaction

This directory contains the API and analysis code for measuring earnings surprises and market reactions for S&P 500 companies.

## Quick: how to read the code

- **Activate the project environment** (from the repository root):

```bash
source .venv/bin/activate
```

- **Install dependencies**

```bash
# If you use Poetry:
poetry install

# Or, if there's a requirements file:
pip install -r requirements.txt

# As an alternative editable install:
pip install -e .
```

- **Key files to inspect (in priority order)**

- `backend/app.py` — API route declarations and request/response wiring.
- `backend/main.py` — API entrypoint and server startup (how the service is launched).
- `backend/helper_functions.py` — utility helpers used by the API.
- `backend/model.py` — statistical logic (surprise, reaction, proportionality models).
- `backend/sql_functions.py` — persistence layer for `markets.db`.
- `backend/logger.py` — logging configuration.
- `adapters/` — data source wrappers:
	- `yf.py` — Yahoo Finance helper functions (price, EPS, returns).
	- `SP500_companies.py` — scraper for the S&P 500 constituents.
	- `financials.py` — any additional financial adapters.

- **Notebooks & examples**

- `test.ipynb` (repo root) and `oxbow/test.ipynb` contain exploratory analysis and example usage of the functions.

## Running the API locally

From the `oxbow/` directory, start a development server (example using `uvicorn`):

```bash
uvicorn backend.app:app --reload --port 8000
```

Then you can call endpoints (examples):

```bash
# Surprise for a ticker (most recent if date omitted)
curl "http://localhost:8000/AAPL/surprise?date=2024-10-25"

# Reaction / CAR example
curl "http://localhost:8000/AAPL/reaction?filings_date=2024-10-25&reaction_days_threshold=3"
```

## How to navigate the logic

- Start at `backend/app.py` to see how endpoints map to functions.
- Follow the handler to `backend/model.py` for calculation details (surprise calculation, z-score, regression).
- Check `adapters/yf.py` to see how data is sourced and any caveats about data availability or rate limits.
- Use `backend/sql_functions.py` to understand caching and where intermediate results are stored.
