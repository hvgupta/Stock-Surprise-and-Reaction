# Stock-Surprise-and-Reaction
Created by [Harsh Vardhan Gupta](https://github.com/hvgupta)

## Quick Start

### 1. Install UV itself

If `uv` is not already installed on your machine, install it with Python first:

#### macOS / Linux

```bash
python3 -m pip install uv
```

#### Windows PowerShell

```powershell
py -m pip install uv
```

### 2. Clone the repository

```bash
git clone https://github.com/hvgupta/Stock-Surprise-and-Reaction.git
cd Stock-Surprise-and-Reaction
```

### 3. Install the project with UV

#### macOS / Linux

```bash
uv sync
```

#### Windows PowerShell

```powershell
uv sync
```

If you want to create the environment explicitly first, UV can do that too:

```bash
uv venv
```

### 4. Run the application

```bash
uv run fastapi run backend/app.py
```

## How to use the API

### Browser UI

Open the Swagger docs in your browser:

```text
http://0.0.0.0:8000/docs
```

### cURL examples

```bash
# Surprise for a ticker (most recent if date is omitted)
curl "http://localhost:8000/AAPL/surprise?date=2024-10-25"

# Reaction / CAR example
curl "http://localhost:8000/AAPL/reaction?filings_date=2024-10-25&reaction_days_threshold=3"
```

To install a development dependency, use the same command with the package name you need for local work.

## How to read the code

Start with the files below in this order:

1. `app/app.py` - API routes and request handling.
2. `app/model.py` - surprise, reaction, and proportionality logic.
3. `app/helper_functions.py` - shared helper utilities.
4. `app/sql_functions.py` - database and caching code.
5. `app/adapters/` - external data sources such as Yahoo Finance and S&P 500 company data.

## Notes
- The `/docs` page is the easiest way to explore available endpoints.
- If a command fails on Windows, run it from the same PowerShell session where you used `uv sync` or `uv venv`.
