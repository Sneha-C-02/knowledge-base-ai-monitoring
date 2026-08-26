from fastapi import FastAPI, HTTPException
import asyncio
import redis.asyncio as redis
import json
import sqlite3
import os

app = FastAPI(title="Instrument Memory Service")

# Use a local SQLite DB for simple memory storage, or could use postgres
DB_PATH = "/app/tmp/memory.db"
os.makedirs("/app/tmp", exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS instrument_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  instrument_id TEXT, 
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, 
                  summary TEXT)''')
    conn.commit()
    conn.close()

init_db()

redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

async def listen_for_analysis():
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("AnalysisCompletedEvent")
    async for message in pubsub.listen():
        if message["type"] == "message":
            data = json.loads(message["data"])
            instrument_id = data.get("instrument_id")
            summary = data.get("summary")
            if instrument_id and summary:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                # Insert the daily summary bullets into memory
                bullets = "\\n".join(summary.get("daily_summary_bullets", []))
                c.execute("INSERT INTO instrument_history (instrument_id, summary) VALUES (?, ?)", 
                          (instrument_id, bullets))
                conn.commit()
                conn.close()

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(listen_for_analysis())

@app.get("/memory/{instrument_id}")
async def get_memory(instrument_id: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT timestamp, summary FROM instrument_history WHERE instrument_id = ? ORDER BY timestamp DESC", (instrument_id,))
    rows = c.fetchall()
    conn.close()
    
    memory_context = ""
    for row in rows:
        memory_context += f"At {row[0]}: {row[1]}\\n"
        
    return {"instrument_id": instrument_id, "memory_context": memory_context}
