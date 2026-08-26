from fastapi import FastAPI
import asyncio
import redis.asyncio as redis
import json
import httpx
import os
import random

app = FastAPI(title="Log Analysis Service")
redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

MEMORY_SERVICE_URL = "http://instrument-memory:3002/memory"

async def analyze_log(instrument_id: str, file_path: str):
    # 1. Fetch complete log file
    try:
        with open(file_path, "r") as f:
            log_content = f.read()
    except Exception as e:
        log_content = f"Error reading log: {e}"

    # 2. Fetch instrument memory context
    memory_context = ""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{MEMORY_SERVICE_URL}/{instrument_id}")
            if response.status_code == 200:
                memory_context = response.json().get("memory_context", "")
    except Exception as e:
        memory_context = f"Could not fetch memory: {e}"

    # 3. Simulate AI processing (Complete Log + Context)
    # In a real scenario, this would send `log_content` and `memory_context` to an LLM like Groq/OpenAI.
    # We generate a structured output directly mapping to the UI format.
    
    # Mocked LLM JSON Output based on the requested format
    result_summary = {
        "critical_incidents": random.randint(0, 15),
        "warnings": random.randint(10, 50),
        "errors": random.randint(20, 150),
        "healthy_apps": random.randint(10, 30),
        "daily_summary_bullets": [
            f"Analyzed {len(log_content)} bytes of log data.",
            f"Found previous context length: {len(memory_context)} characters.",
            "Database connection failures detected.",
            "Payment service latency increased."
        ]
    }

    # 4. Publish Analysis Completed
    event_payload = {
        "instrument_id": instrument_id,
        "summary": result_summary
    }
    await redis_client.publish("AnalysisCompletedEvent", json.dumps(event_payload))
    print(f"Analysis completed for {instrument_id}")

async def listen_for_logs():
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("LogReceivedEvent")
    async for message in pubsub.listen():
        if message["type"] == "message":
            data = json.loads(message["data"])
            instrument_id = data.get("instrument_id")
            file_path = data.get("file_path")
            
            if instrument_id and file_path:
                # Run analysis asynchronously so we don't block the listener
                asyncio.create_task(analyze_log(instrument_id, file_path))

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(listen_for_logs())

@app.get("/health")
def health_check():
    return {"status": "healthy"}
