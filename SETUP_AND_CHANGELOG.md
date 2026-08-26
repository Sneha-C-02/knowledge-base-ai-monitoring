# Project Setup & AI Monitoring Changelog

This document summarizes the architectural upgrades made to the **Proactive AI Log Monitoring** system and provides step-by-step instructions on how to run and test the full application.

---

## 1. Summary of Architectural Changes

The log monitoring feature was completely overhauled from a basic "upload and parse" mechanism to an **Intelligent, Continuous Live AI Monitoring** system.

### A. Persistent State & AI Memory
- **`MonitoredLogFile` Entity**: Created a new database model to track how far a file has been read (total lines) and to store a compressed "AI Context Summary" of everything the AI has seen so far.
- **Incremental Analysis**: The Groq AI service now handles two types of analysis:
  1. *Full Analysis*: On first upload, the AI reads the entire file and generates the initial context mapping.
  2. *Incremental Analysis*: On subsequent checks, the AI is only sent *new* log lines along with the stored context summary, saving processing time and LLM token limits while retaining full situational awareness.

### B. Continuous Live Monitoring (Background Polling)
- **Persistent Storage**: Uploaded log files are no longer deleted. They are saved in `backend/temp_files/persistent_logs/{instrument_id}/`.
- **`ContinuousMonitoringService`**: A background async task that runs as long as the FastAPI server is alive. Every 15 seconds, it polls all active files on disk. If new lines are detected, it reads them, runs the incremental AI analysis, and saves the new context.
- **Server-Sent Events (SSE)**: Built a lightweight, in-memory `EventBus`. When the background service finishes analyzing new lines, it broadcasts the updated dashboard JSON to the new `GET /monitoring/dashboard/stream/{instrument_id}` endpoint.

### C. Frontend Dashboard Upgrade
- **Live React Dashboard**: Completely rewrote `MonitoringPage.tsx` to feature:
  - Instrument selection dropdown.
  - Four dynamic stat cards (Critical, Warnings, Errors, Healthy).
  - An "AI Generated Daily Summary" box with severity-colored bullets.
  - A historical analysis table (`InstrumentMemory`).
- **Live Connection**: The React frontend uses standard browser `EventSource` to connect to the backend's SSE stream. It updates the dashboard and triggers toast notifications in real-time without requiring a page refresh.

---

## 2. How to Run the Application

### Step 1: Database Migrations
Because we added new features to track the AI's memory and log positions, you need to create two new tables in your Supabase PostgreSQL database.

Execute the following SQL files directly in your Supabase SQL Editor:
1. `backend/scripts/create_instrument_memory_table.sql`
2. `backend/scripts/create_monitored_log_files_table.sql`

### Step 2: Environment Configuration
Ensure your `backend/.env` file has the appropriate Groq AI credentials and database URL:
```env
# Database
DATABASE_URL="postgresql+asyncpg://postgres:YOUR_PASSWORD@db.YOUR_SUPABASE_ID.supabase.co:5432/postgres"

# AI Configuration
GROQ_API_KEY="your_groq_api_key_here"
GROQ_MODEL="llama3-8b-8192" # Or whatever model you prefer
```

### Step 3: Start the Backend (FastAPI)
Open a terminal, activate your virtual environment (if you have one), and start the server:

```bash
cd backend
pip install -r requirements.txt  # If you haven't installed dependencies recently
python -m uvicorn src.knowledge_base_backend.presentation.api.main:app --reload --port 8000
```
*(The Continuous Monitoring background service starts automatically with the server).*

### Step 4: Start the Frontend (React/Vite)
Open a new terminal tab:

```bash
cd frontend
npm install
npm run dev
```
Open your browser to the URL provided by Vite (usually `http://localhost:5173`).

---

## 3. How to Test "Live" Continuous Monitoring

To see the background polling and SSE streaming in action without needing an actual machine generating logs, we created a simulation script.

1. Go to the **Proactive Log Monitoring** page in the frontend.
2. Select an Instrument from the dropdown.
3. Upload a sample `.log` or `.txt` file and click **Start Monitoring**.
   - *You will see the initial AI dashboard load and a pulsing <span style="color:red">🔴 LIVE</span> badge appear next to the instrument name.*
4. The backend has saved your file permanently for watching. Look in your backend directory under `backend/temp_files/persistent_logs/{instrument_id}/`. Note the filename.
5. In a new terminal, run the simulation script, pointing it at that exact file:
   ```bash
   cd backend
   python scripts/simulate_live_logs.py ./temp_files/persistent_logs/1/your_filename.txt
   ```
6. The script will append a new dummy log line to the file every 16 seconds. 
7. Keep your browser open! Watch the React dashboard. Within 15-20 seconds, the backend will detect the new lines, trigger Groq AI, and stream the update to your browser. You'll see the stats update and a "Live Update" toast notification appear automatically!
