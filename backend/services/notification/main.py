from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import redis.asyncio as redis
import json

app = FastAPI(title="Notification & Dashboard Service")
redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

active_websockets = []

def generate_ascii_dashboard(summary: dict) -> str:
    """Formats the data to match the specific UI requirements provided by the user."""
    critical = summary.get("critical_incidents", 0)
    warnings = summary.get("warnings", 0)
    errors = summary.get("errors", 0)
    healthy = summary.get("healthy_apps", 0)
    bullets = summary.get("daily_summary_bullets", [])
    
    dashboard = f"""
--------------------------------------------------------------
| AI Log Operations Dashboard                                  |
--------------------------------------------------------------
| Critical Incidents | Warnings | Errors | Healthy Apps      |
|        {critical:<12} |    {warnings:<6} |  {errors:<6} |      {healthy:<8}      |
--------------------------------------------------------------
| AI Generated Daily Summary                                   |
--------------------------------------------------------------
"""
    for bullet in bullets:
        # Pad strings to maintain border alignment roughly
        line = f"| * {bullet}"
        dashboard += f"{line.ljust(61)}|\n"
        
    dashboard += "--------------------------------------------------------------"
    return dashboard

async def listen_for_results():
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("AnalysisCompletedEvent")
    async for message in pubsub.listen():
        if message["type"] == "message":
            data = json.loads(message["data"])
            instrument_id = data.get("instrument_id")
            summary = data.get("summary")
            
            if instrument_id and summary:
                ascii_board = generate_ascii_dashboard(summary)
                print(f"\\n--- New Dashboard for Instrument: {instrument_id} ---\\n")
                print(ascii_board)
                print("\\n-----------------------------------------------------\\n")
                
                # Broadcast to connected UI websockets
                for ws in active_websockets:
                    try:
                        await ws.send_json({
                            "instrument_id": instrument_id,
                            "dashboard_text": ascii_board,
                            "raw_summary": summary
                        })
                    except Exception:
                        pass

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(listen_for_results())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_websockets.remove(websocket)
