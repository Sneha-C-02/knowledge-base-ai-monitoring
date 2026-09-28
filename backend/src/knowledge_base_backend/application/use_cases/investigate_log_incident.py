from typing import List, Tuple, Union, Optional
from src.knowledge_base_backend.domain.services.log_incident_investigation_service import LogIncidentInvestigationService
from src.knowledge_base_backend.domain.repositories.support_feedback_repository import SupportFeedbackRepository
from src.knowledge_base_backend.domain.value_objects.reactive_support_models import IncidentInvestigationResult
from src.knowledge_base_backend.domain.exceptions.validation_exceptions import ValidationError


class InvestigateLogIncidentUseCase:
    """
    Application use case for reactive support log incident investigation.
    Coordinates loading past feedback weights to improve search accuracy,
    decoding multi-file/folder logs, and pinpointing issue patterns.
    """

    def __init__(
        self,
        investigation_service: LogIncidentInvestigationService,
        feedback_repository: Optional[SupportFeedbackRepository] = None,
    ) -> None:
        self.investigation_service = investigation_service
        self.feedback_repository = feedback_repository

    async def execute(
        self,
        files: List[Tuple[str, Union[bytes, str]]],
        problem_description: str,
    ) -> IncidentInvestigationResult:
        if not problem_description or not problem_description.strip():
            raise ValidationError("Problem description cannot be empty")

        if not files or len(files) == 0:
            raise ValidationError("No log files or folder uploaded. At least one log file or folder is required for incident investigation.")

        # Retrieve feedback weights to improve newer searches
        weights = {}
        if self.feedback_repository:
            try:
                weights = await self.feedback_repository.get_pattern_weights()
            except Exception:
                weights = {}

        # Decode file contents safely, filtering out binary, system, hidden, and empty files
        decoded_files: List[Tuple[str, str]] = []
        ignored_extensions = (
            ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
            ".pdf", ".zip", ".tar", ".gz", ".7z",
            ".exe", ".bin", ".dll", ".so", ".pyc", ".iso",
        )
        had_empty_file = False
        for fname, content in files:
            if not fname or not str(fname).strip():
                continue
            clean_fname = str(fname).replace("\\", "/")
            base_name = clean_fname.rsplit("/", 1)[-1]
            if not base_name.strip() or base_name.startswith(".") or base_name in ("Thumbs.db", "desktop.ini"):
                continue
            if any(clean_fname.lower().endswith(ext) for ext in ignored_extensions):
                continue

            if isinstance(content, bytes):
                # Binary file check: null byte or high control character ratio in initial chunk
                if b"\x00" in content[:4096]:
                    continue
                sample = content[:4096]
                if len(sample) > 0:
                    control_chars = sum(1 for b in sample if b < 32 and b not in (9, 10, 13))
                    if (control_chars / len(sample)) > 0.05:
                        continue
                try:
                    text = content.decode("utf-8")
                except UnicodeDecodeError:
                    text = content.decode("latin-1", errors="replace")
            else:
                text = str(content)

            if len(text.strip()) == 0:
                had_empty_file = True
                continue

            decoded_files.append((fname, text))

        if not decoded_files:
            if had_empty_file:
                raise ValidationError("Uploaded log file(s) are empty. Please upload a log file or folder with content.")
            raise ValidationError("No valid log files found in the upload. Please upload at least one valid log file or folder.")

        if hasattr(self.investigation_service, "investigate_async"):
            return await self.investigation_service.investigate_async(
                files=decoded_files,
                problem_description=problem_description.strip(),
                pattern_weights=weights,
            )

        return self.investigation_service.investigate(
            files=decoded_files,
            problem_description=problem_description.strip(),
            pattern_weights=weights,
        )
