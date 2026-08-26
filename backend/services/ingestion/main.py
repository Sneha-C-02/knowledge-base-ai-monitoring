from fastapi import FastAPI, UploadFile, File, Form, HTTPException
import redis
import json
import os
import uuid
import shutil

app = FastAPI(title="Log Ingestion Service")

# Setup Redis connection
redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

# Ensure temporary storage directory exists
UPLOAD_DIR = "/app/tmp/logs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/ingest")
async def ingest_logs(instrument_id: str = Form(...), files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    saved_files = []
    
    for file in files:
        file_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
        
        # Save file to disk
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        saved_files.append(file_path)
        
        # Publish event to Redis
        event_payload = {
            "instrument_id": instrument_id,
            "file_path": file_path,
            "filename": file.filename,
            "file_id": file_id
        }
        redis_client.publish("LogReceivedEvent", json.dumps(event_payload))

    return {"message": "Logs successfully ingested and queued for processing", "saved_files": saved_files}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
