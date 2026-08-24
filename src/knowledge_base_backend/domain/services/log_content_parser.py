from typing import Protocol, List, Dict, Any

class LogContentParser(Protocol):
    async def parse(self, file_path: str) -> List[Dict[str, Any]]: ...
