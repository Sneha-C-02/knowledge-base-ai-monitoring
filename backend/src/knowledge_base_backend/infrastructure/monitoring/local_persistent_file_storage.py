import os
import aiofiles
from typing import BinaryIO
from src.knowledge_base_backend.domain.services.persistent_file_storage import PersistentFileStorage
from src.knowledge_base_backend.configuration.application_settings import settings
import logging

logger = logging.getLogger(__name__)

class LocalPersistentFileStorage(PersistentFileStorage):
    def __init__(self) -> None:
        self.directory = os.path.join(settings.temporary_file_directory, "persistent_logs")
        os.makedirs(self.directory, exist_ok=True)
        
    async def store_persistent_file(self, instrument_id: int, filename: str, file_stream: BinaryIO) -> str:
        # Create an instrument-specific directory
        inst_dir = os.path.join(self.directory, str(instrument_id))
        os.makedirs(inst_dir, exist_ok=True)
        
        # Use the original filename to make it easy to append to later
        safe_filename = os.path.basename(filename)
        path = os.path.join(inst_dir, safe_filename)
        
        # Overwrite if exists, since this is a new "upload" starting the monitoring
        async with aiofiles.open(path, 'wb') as f:
            while chunk := file_stream.read(8192):
                await f.write(chunk)
                
        return path
        
    async def get_file_path(self, instrument_id: int, filename: str) -> str:
        safe_filename = os.path.basename(filename)
        return os.path.join(self.directory, str(instrument_id), safe_filename)
