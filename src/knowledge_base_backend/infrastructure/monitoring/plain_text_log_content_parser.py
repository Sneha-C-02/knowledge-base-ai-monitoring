from typing import List, Dict, Any
import aiofiles
from src.knowledge_base_backend.domain.services.log_content_parser import LogContentParser

class PlainTextLogContentParser(LogContentParser):
    async def parse(self, file_path: str) -> List[Dict[str, Any]]:
        events = []
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                async for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    level = "INFO"
                    if "error" in line.lower() or "exception" in line.lower():
                        level = "ERROR"
                    elif "warn" in line.lower():
                        level = "WARN"
                        
                    events.append({"message": line, "level": level})
        except Exception:
            pass
        return events
