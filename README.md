# Stock-Surprise-and-Reaction
Created by [Harsh Vardhan Gupta](https://github.com/hvgupta)

## Quick Start

### 1. Install UV itself

If you prefer the project's helper scripts, you do not need to install `uv` yourself. The repository includes convenience launch scripts for Linux and Windows which handle starting the backend and frontend together.

#### Linux / macOS

Run the provided shell script from the repository root:

```bash
./launch-application-linux.sh
```

#### Windows (PowerShell)

Run the provided PowerShell script from the repository root:

```powershell
./launch-application-windows.ps1
```

If you still want to install `uv` manually, you can use:

```bash
python3 -m pip install uv
```

### 2. Clone the repository

```bash
git clone https://github.com/hvgupta/Stock-Surprise-and-Reaction.git
cd Stock-Surprise-and-Reaction
```

### 3. Install dependencies

If you prefer to prepare the environment manually (instead of using the launch scripts), follow these steps.

Linux / macOS / Windows (WSL / PowerShell):

```bash
# create a virtual environment and install Python deps
python3 -m pip install -r requirements.txt  # or use the pyproject/uv.lock flow if desired

# install frontend deps
cd frontend && npm install
```

### 4. Run the application locally (manual)

If you want to start backend and frontend separately instead of using the provided launch scripts:

```bash
# start backend (from repo root)
uv run uvicorn backend.app:app --host 0.0.0.0 --port 8000

# in a separate terminal, start frontend
cd frontend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run dev
```

Then open:

```text
http://localhost:3000
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

# SP500 top surprises (sorted by absolute surprise)
curl "http://localhost:8000/sp500/surprises"

# SP500 ticker detail payload (reaction + proportionality + regression model)
curl "http://localhost:8000/sp500/AAPL/details"
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
