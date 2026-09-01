import asyncio
import os
import aiofiles
import logging
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import select
from typing import List

from src.knowledge_base_backend.infrastructure.events.event_bus import EventBus
from src.knowledge_base_backend.domain.services.persistent_file_storage import PersistentFileStorage
from src.knowledge_base_backend.infrastructure.database.models.monitored_log_file_model import MonitoredLogFileModel
from src.knowledge_base_backend.application.use_cases.analyze_logs_with_memory import AnalyzeLogsWithMemoryUseCase
from src.knowledge_base_backend.domain.value_objects.log_dashboard_result import LogDashboardResult

logger = logging.getLogger(__name__)

class ContinuousMonitoringService:
    """
    Background service that continuously polls monitored log files for new lines.
    If new lines are found, it triggers an incremental AI analysis and broadcasts
    the result to connected SSE clients via the EventBus.
    """
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        storage: PersistentFileStorage,
        analyze_use_case_factory,
        event_bus: EventBus,
        polling_interval_seconds: int = 15
    ):
        self.session_factory = session_factory
        self.storage = storage
        self.analyze_use_case_factory = analyze_use_case_factory
        self.event_bus = event_bus
        self.polling_interval_seconds = polling_interval_seconds
        self._running = False
        self._task = None

    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._run_loop())
            logger.info("ContinuousMonitoringService started.")

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            logger.info("ContinuousMonitoringService stopped.")

    async def _run_loop(self):
        while self._running:
            try:
                await self._check_files()
            except Exception as e:
                logger.error(f"Error in continuous monitoring loop: {e}")
            
            await asyncio.sleep(self.polling_interval_seconds)

    async def _check_files(self):
        """Check all monitored files for size changes and analyze new lines."""
        async with self.session_factory() as session:
            # Query all monitored log files
            query = select(MonitoredLogFileModel)
            result = await session.execute(query)
            monitored_files = result.scalars().all()

            for monitored in monitored_files:
                try:
                    file_path = await self.storage.get_file_path(monitored.instrument_id, monitored.filename)
                    if not os.path.exists(file_path):
                        continue

                    # Fast check: just count lines or use file size to see if it changed
                    async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                        full_content = await f.read()
                    
                    total_lines = len(full_content.split('\n'))

                    if total_lines > monitored.total_lines_analyzed:
                        logger.info(f"New lines detected in {monitored.filename}. Analyzing...")
                        
                        # We use the existing use case. However, since the use case expects a BinaryIO stream
                        # for validation and storage (which we already did), we can bypass the public execute()
                        # and directly call the internal single file processor to avoid re-validating and storing.
                        
                        # To do this cleanly, we fetch the memory entries for the instrument first.
                        from src.knowledge_base_backend.infrastructure.database.models.instrument_memory_model import InstrumentMemoryModel
                        mem_query = select(InstrumentMemoryModel).where(InstrumentMemoryModel.instrument_id == monitored.instrument_id).order_by(InstrumentMemoryModel.analysis_timestamp.desc())
                        mem_result = await session.execute(mem_query)
                        mem_models = mem_result.scalars().all()
                        
                        # Convert to entities
                        from src.knowledge_base_backend.infrastructure.database.repositories.sqlalchemy_instrument_memory_repository import SqlAlchemyInstrumentMemoryRepository
                        mem_repo = SqlAlchemyInstrumentMemoryRepository(session)
                        memory_entries = [mem_repo._to_entity(m) for m in mem_models]

                        # Fetch instrument name
                        from src.knowledge_base_backend.infrastructure.database.models.instrument_model import InstrumentModel
                        inst_result = await session.execute(select(InstrumentModel).where(InstrumentModel.id == monitored.instrument_id))
                        instrument = inst_result.scalar_one()

                        # The analyze_use_case is wired to the current request session in HTTP,
                        # but here we are in a background task. Since the DI container passes the 
                        # ContextVar session, we need to ensure the use case uses our background session.
                        # Actually, our background task has its own session. 
                        # Let's call the internal method. It reads the file again, which is fine.
                        
                        # Set context var manually for this execution if needed, but since we rely on 
                        # dependency injection, it might be safer to construct an isolated use case
                        # or just pass the dependencies. For now, we'll rely on the existing use case
                        # which uses repositories that read from the current session context.
                        # Let's set the session context.
                        from src.knowledge_base_backend.infrastructure.database.session_context import session_context
                        token = session_context.set(session)
                        
                        try:
                            analyze_use_case = self.analyze_use_case_factory()
                            dashboard_result = await analyze_use_case._process_single_file(
                                path=file_path,
                                filename=monitored.filename,
                                instrument_id=monitored.instrument_id,
                                instrument_name=instrument.name,
                                memory_entries=memory_entries
                            )
                            
                            # Broadcast the result to SSE clients
                            await self.event_bus.publish(str(monitored.instrument_id), dashboard_result)
                            
                            # Commit the changes made by the use case
                            await session.commit()
                        finally:
                            session_context.reset(token)

                except Exception as e:
                    logger.error(f"Error checking file {monitored.filename}: {e}")
