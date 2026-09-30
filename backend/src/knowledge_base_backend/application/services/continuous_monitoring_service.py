import asyncio
import os
import aiofiles
import logging
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from sqlalchemy import select
from typing import List, Optional

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
                    # Skip files that are explicitly paused or stopped
                    if getattr(monitored, "status", "MONITORING") in ("PAUSED", "STOPPED"):
                        continue

                    file_path = await self.storage.get_file_path(monitored.instrument_id, monitored.filename)
                    if not os.path.exists(file_path):
                        continue

                    # Fast check: count lines to see if new lines were added
                    async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                        full_content = await f.read()
                    
                    total_lines = len(full_content.split('\n'))

                    if total_lines > monitored.total_lines_analyzed:
                        logger.info(f"New lines detected in {monitored.filename} ({monitored.total_lines_analyzed} -> {total_lines}). Analyzing...")
                        
                        from src.knowledge_base_backend.infrastructure.database.models.instrument_memory_model import InstrumentMemoryModel
                        mem_query = select(InstrumentMemoryModel).where(InstrumentMemoryModel.instrument_id == monitored.instrument_id).order_by(InstrumentMemoryModel.analysis_timestamp.desc())
                        mem_result = await session.execute(mem_query)
                        mem_models = mem_result.scalars().all()
                        
                        from src.knowledge_base_backend.infrastructure.database.repositories.sqlalchemy_instrument_memory_repository import SqlAlchemyInstrumentMemoryRepository
                        mem_repo = SqlAlchemyInstrumentMemoryRepository(session)
                        memory_entries = [mem_repo._to_entity(m) for m in mem_models]

                        from src.knowledge_base_backend.infrastructure.database.models.instrument_model import InstrumentModel
                        inst_result = await session.execute(select(InstrumentModel).where(InstrumentModel.id == monitored.instrument_id))
                        try:
                            instrument = inst_result.scalar_one()
                        except Exception:
                            continue

                        from src.knowledge_base_backend.infrastructure.database.session_context import session_context
                        token = session_context.set(session)
                        
                        try:
                            analyze_use_case = self.analyze_use_case_factory()
                            dashboard_result = await analyze_use_case._process_single_file(
                                path=file_path,
                                filename=monitored.filename,
                                instrument_id=monitored.instrument_id,
                                instrument_name=instrument.name,
                                memory_entries=memory_entries,
                                analysis_mode="fast",
                            )
                            dashboard_result.monitoring_status = "MONITORING"
                            inst_files = [m for m in monitored_files if m.instrument_id == monitored.instrument_id]
                            if inst_files:
                                dashboard_result.monitored_files = [
                                    {
                                        "filename": m.filename,
                                        "status": getattr(m, "status", "MONITORING") or "MONITORING",
                                        "total_lines_analyzed": total_lines if m.filename == monitored.filename else m.total_lines_analyzed,
                                        "updated_at": m.updated_at.isoformat() if hasattr(m.updated_at, "isoformat") else str(m.updated_at),
                                    }
                                    for m in inst_files
                                ]
                                dashboard_result.files_analyzed = len(inst_files)
                            
                            # Broadcast the result to SSE clients
                            await self.event_bus.publish(str(monitored.instrument_id), dashboard_result)
                            
                            # Commit the changes made by the use case
                            await session.commit()
                        finally:
                            session_context.reset(token)

                except Exception as e:
                    await session.rollback()
                    logger.error(f"Error checking file {monitored.filename}: {e}")

    async def check_file_now(self, instrument_id: int, filename: Optional[str] = None) -> Optional[LogDashboardResult]:
        """Manually trigger immediate check for new lines on an instrument's monitored log file(s)."""
        async with self.session_factory() as session:
            query = select(MonitoredLogFileModel).where(MonitoredLogFileModel.instrument_id == instrument_id)
            if filename:
                query = query.where(MonitoredLogFileModel.filename == filename)
            result = await session.execute(query)
            monitored_files = result.scalars().all()

            for monitored in monitored_files:
                if getattr(monitored, "status", "MONITORING") in ("PAUSED", "STOPPED"):
                    continue

                file_path = await self.storage.get_file_path(monitored.instrument_id, monitored.filename)
                if not os.path.exists(file_path):
                    continue

                async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    full_content = await f.read()
                
                total_lines = len(full_content.split('\n'))
                if total_lines > monitored.total_lines_analyzed:
                    from src.knowledge_base_backend.infrastructure.database.models.instrument_memory_model import InstrumentMemoryModel
                    mem_query = select(InstrumentMemoryModel).where(InstrumentMemoryModel.instrument_id == monitored.instrument_id).order_by(InstrumentMemoryModel.analysis_timestamp.desc())
                    mem_result = await session.execute(mem_query)
                    mem_models = mem_result.scalars().all()
                    
                    from src.knowledge_base_backend.infrastructure.database.repositories.sqlalchemy_instrument_memory_repository import SqlAlchemyInstrumentMemoryRepository
                    mem_repo = SqlAlchemyInstrumentMemoryRepository(session)
                    memory_entries = [mem_repo._to_entity(m) for m in mem_models]

                    from src.knowledge_base_backend.infrastructure.database.models.instrument_model import InstrumentModel
                    inst_result = await session.execute(select(InstrumentModel).where(InstrumentModel.id == monitored.instrument_id))
                    try:
                        instrument = inst_result.scalar_one()
                    except Exception:
                        continue

                    from src.knowledge_base_backend.infrastructure.database.session_context import session_context
                    token = session_context.set(session)
                    try:
                        analyze_use_case = self.analyze_use_case_factory()
                        dashboard_result = await analyze_use_case._process_single_file(
                            path=file_path,
                            filename=monitored.filename,
                            instrument_id=monitored.instrument_id,
                            instrument_name=instrument.name,
                            memory_entries=memory_entries,
                            analysis_mode="fast",
                        )
                        dashboard_result.monitoring_status = "MONITORING"
                        if monitored_files:
                            dashboard_result.monitored_files = [
                                {
                                    "filename": m.filename,
                                    "status": getattr(m, "status", "MONITORING") or "MONITORING",
                                    "total_lines_analyzed": total_lines if m.filename == monitored.filename else m.total_lines_analyzed,
                                    "updated_at": m.updated_at.isoformat() if hasattr(m.updated_at, "isoformat") else str(m.updated_at),
                                }
                                for m in monitored_files
                            ]
                            dashboard_result.files_analyzed = len(monitored_files)
                        await self.event_bus.publish(str(monitored.instrument_id), dashboard_result)
                        await session.commit()
                        return dashboard_result
                    finally:
                        session_context.reset(token)
        return None
