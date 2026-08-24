import os
import aiofiles
from typing import BinaryIO
from src.knowledge_base_backend.domain.services.temporary_file_storage import TemporaryFileStorage
from src.knowledge_base_backend.configuration.application_settings import settings
import uuid
import logging

logger = logging.getLogger(__name__)

class LocalTemporaryFileStorage(TemporaryFileStorage):
    def __init__(self) -> None:
        self.directory = settings.temporary_file_directory
        os.makedirs(self.directory, exist_ok=True)
        
    async def store_temporary_file(self, filename: str, file_stream: BinaryIO) -> str:
        safe_filename = f"{uuid.uuid4().hex}_{os.path.basename(filename)}"
        path = os.path.join(self.directory, safe_filename)
        
        async with aiofiles.open(path, 'wb') as f:
            while chunk := file_stream.read(8192):
                await f.write(chunk)
                
        return path
        
    async def delete_temporary_file(self, file_path: str) -> None:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.error(f"Failed to delete temporary file {file_path}: {e}")
