Running frontend + backend locally (no Docker)

Linux / macOS

1. Ensure Python (3.10+), pip and Node/npm are installed.
2. From the `oxbow` project folder run:

```bash
./run-dev.sh
```

This starts the backend (uvicorn serving `backend.app:app` on port 8000) and the Next frontend (`npm run dev`) concurrently. Press Ctrl+C to stop both.

Windows (PowerShell)

1. Ensure Python (3.10+), pip and Node/npm are installed.
2. Open PowerShell in the `oxbow` folder and run:

```powershell
.\run-dev.ps1
```

Notes
- The scripts assume dependencies are already installed. Install Python deps with `pip install -r backend/requirements.txt` if you maintain a `requirements.txt`, or `pip install -r <your deps>`.
- If `uvicorn` is not installed, install it with: `pip install 'uvicorn[standard]'`.
- The scripts do not create virtualenvs—if you prefer isolation, create and activate a venv before running.
- Logs for both processes are printed to the console. You can redirect them to files manually if you want.
