import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from src.knowledge_base_backend.presentation.api.schemas.dashboard_schemas import (
    DiscoverKeywordsResponse,
    DiscoveredKeywordSchema,
)


# Curated catalog of domain failure signatures and their diagnostic indications
KNOWN_FAILURE_PATTERNS = [
    (
        re.compile(r"\b(?:socket\s+timeout|connection\s+lost|comm(?:unication)?\s+lost|comm(?:unication)?\s+error|packet\s+dropped|handshake\s+fail(?:ed)?)\b", re.IGNORECASE),
        "communication timeout",
        "critical",
        "Indicates communication loss or network socket timeout with the instrument controller or module.",
    ),
    (
        re.compile(r"\b(?:pressure\s+limit\s+exceeded|overpressure|high\s+pressure\s+limit|max(?:imum)?\s+pressure)\b", re.IGNORECASE),
        "pressure limit exceeded",
        "critical",
        "Indicates fluidic pump pressure exceeded the maximum safety limit, risking column damage or tubing rupture.",
    ),
    (
        re.compile(r"\b(?:pressure\s+drop|sudden\s+pressure\s+loss|fluidic\s+leak|leak\s+detected|seal\s+leak)\b", re.IGNORECASE),
        "fluidic leak",
        "critical",
        "Indicates unexpected fluid pressure loss or active liquid leak detected by optical/conductive leak sensors.",
    ),
    (
        re.compile(r"\b(?:vacuum\s+leak|vacuum\s+failure|turbo\s+pump\s+fault|vacuum\s+read\s+failure)\b", re.IGNORECASE),
        "vacuum leak",
        "critical",
        "Indicates loss of high vacuum or turbo-molecular pump failure in the mass spectrometer chamber.",
    ),
    (
        re.compile(r"\b(?:failed\s+to\s+write|write\s+error|cannot\s+set|unable\s+to\s+set)\b", re.IGNORECASE),
        "write error",
        "error",
        "Indicates hardware register or calibration parameter write failure to the instrument controller board.",
    ),
    (
        re.compile(r"\b(?:needle\s+drive\s+stall|pierce\s+error|sample\s+vial\s+missing|tray\s+positioning\s+error|vial\s+pierce\s+failure)\b", re.IGNORECASE),
        "needle drive stall",
        "critical",
        "Indicates autosampler needle obstruction, mechanical motor stall, or sample vial alignment fault.",
    ),
    (
        re.compile(r"\b(?:lamp\s+ignition\s+fail(?:ure)?|lamp\s+intensity\s+low|lamp\s+degraded|deuterium\s+failure)\b", re.IGNORECASE),
        "lamp ignition failure",
        "error",
        "Indicates optical detector lamp failed to ignite or energy intensity degraded below operating threshold.",
    ),
    (
        re.compile(r"\b(?:temp(?:erature)?\s+regulation\s+(?:timeout|failure)|heater\s+timeout|thermal\s+runaway|cooler\s+error)\b", re.IGNORECASE),
        "temperature regulation timeout",
        "warning",
        "Indicates column compartment or autosampler cooler failed to achieve or maintain target temperature.",
    ),
    (
        re.compile(r"\b(?:riostatus\b\s*(?:=>|=)\s*(-?[1-9]\d*))\b", re.IGNORECASE),
        "riostatus error",
        "critical",
        "Indicates low-level National Instruments RIO FPGA bus communication or hardware status error.",
    ),
    (
        re.compile(r"\b(?:out\s+of\s+memory|buffer\s+overflow|oom[\s_-]*killer|queue\s+full|deadlock)\b", re.IGNORECASE),
        "buffer overflow",
        "critical",
        "Indicates software memory exhaustion, acquisition data buffer overflow, or thread deadlock.",
    ),
    (
        re.compile(r"\b(?:emergency\s+stop|safety\s+interlock\s+tripped|interlock\s+open)\b", re.IGNORECASE),
        "safety interlock tripped",
        "critical",
        "Indicates hardware safety interlock tripped or emergency stop was actuated, halting instrument operation.",
    ),
    (
        re.compile(r"\b(?:unhandled\s+exception|fatal\s+error|system\s+crash|kernel\s+panic|catastrophic\s+abort)\b", re.IGNORECASE),
        "catastrophic abort",
        "critical",
        "Indicates unhandled software exception or fatal system crash that forcibly terminated instrument run.",
    ),
    (
        re.compile(r"\b(?:baseline\s+drift|detector\s+noise|absorbance\s+out\s+of\s+range)\b", re.IGNORECASE),
        "baseline drift",
        "warning",
        "Indicates optical baseline instability, detector noise, or abnormal chromatography absorbance.",
    ),
    (
        re.compile(r"\b(?:power\s+loss|unexpected\s+restart|hard\s+reboot|brownout)\b", re.IGNORECASE),
        "power failure",
        "critical",
        "Indicates electrical power interruption or sudden unexpected hardware reboot during operation.",
    ),
    (
        re.compile(r"\b(?:flow\s+rate\s+zero|flow\s+sensor\s+error|pump\s+head\s+fault)\b", re.IGNORECASE),
        "pump flow error",
        "critical",
        "Indicates solvent delivery failure or fluidic pump head motor stall.",
    ),
    (
        re.compile(r"\b(?:calibration\s+error|alignment\s+fault|prescan\s+failed)\b", re.IGNORECASE),
        "calibration error",
        "warning",
        "Indicates mass spectrometer calibration or optical alignment verification failed.",
    ),
]

STOP_TERMS = {
    "error", "warning", "info", "debug", "line", "file", "time", "date",
    "true", "false", "null", "none", "system", "test", "waters", "status",
    "value", "code", "mode", "level", "message", "event", "type",
}


@dataclass
class _CandidateOccurrence:
    keyword: str
    severity: str
    failure_indicator: str
    sample_line: str
    sample_line_number: int
    sample_file: str
    count: int = 1


class DiscoverFailureKeywordsUseCase:
    """
    Scans uploaded log file(s) or instrument folder content and discovers
    keywords and phrases indicating instrument failures, faults, and anomalies.
    Designed for human-in-the-loop review and acceptance.
    """

    def __init__(self, learned_keyword_repository=None) -> None:
        self.learned_keyword_repository = learned_keyword_repository

    async def execute(self, files: List[Tuple[str, str]]) -> DiscoverKeywordsResponse:
        """
        Analyze files and return ranked candidate failure keywords.
        files: List of (filename, text_content)
        """
        if not files:
            return DiscoverKeywordsResponse(keywords=[], total_discovered=0, files_scanned=0)

        candidates: Dict[str, _CandidateOccurrence] = {}

        for filename, content in files:
            lines = content.splitlines()
            for line_idx, raw_line in enumerate(lines, start=1):
                clean_line = raw_line.strip()
                if not clean_line:
                    continue

                line_lower = clean_line.lower()

                # 1. Match against curated domain failure patterns
                for regex, canon_keyword, default_severity, indicator in KNOWN_FAILURE_PATTERNS:
                    match = regex.search(clean_line)
                    if match:
                        matched_term = canon_keyword
                        if matched_term not in candidates:
                            candidates[matched_term] = _CandidateOccurrence(
                                keyword=matched_term,
                                severity=default_severity,
                                failure_indicator=indicator,
                                sample_line=clean_line[:300],
                                sample_line_number=line_idx,
                                sample_file=filename,
                                count=1,
                            )
                        else:
                            candidates[matched_term].count += 1
                            if candidates[matched_term].severity != "critical" and default_severity == "critical":
                                candidates[matched_term].severity = "critical"

                # 2. Extract specific hardware error terms from failure lines
                # Look for lines containing "fail", "error", "abort", "fault", "crash"
                if any(err_word in line_lower for err_word in ("error", "fail", "fault", "abort", "crash", "timeout")):
                    # Extract phrases like "sensor <name> error", "voltage <name> failure", "valve <x> fault"
                    specific_matches = re.finditer(
                        r"\b([a-zA-Z]{3,15}\s+(?:failure|fault|error|timeout|stall|drift|leak|warning))\b",
                        line_lower,
                    )
                    for m in specific_matches:
                        term = m.group(1).strip()
                        if term in STOP_TERMS or term.split()[0] in STOP_TERMS:
                            continue
                        if len(term) < 5 or len(term) > 35:
                            continue

                        if term not in candidates:
                            # Determine severity
                            sev = "critical" if any(w in term for w in ("fault", "stall", "leak", "abort", "crash")) else "warning"
                            candidates[term] = _CandidateOccurrence(
                                keyword=term,
                                severity=sev,
                                failure_indicator=f"Denotes specific {term.split()[0]} hardware or subsystem malfunction observed in failure log lines.",
                                sample_line=clean_line[:300],
                                sample_line_number=line_idx,
                                sample_file=filename,
                                count=1,
                            )
                        else:
                            candidates[term].count += 1

                    # Extract error codes e.g. "error 0x12a", "error 204", "err -3"
                    code_matches = re.finditer(r"\b(error\s+(?:0x[0-9a-fA-F]+|-?\d{2,6}))\b", line_lower)
                    for m in code_matches:
                        code_term = m.group(1).strip()
                        if code_term not in candidates:
                            candidates[code_term] = _CandidateOccurrence(
                                keyword=code_term,
                                severity="critical",
                                failure_indicator=f"Specific numeric or hex diagnostic error code logged during instrument failure.",
                                sample_line=clean_line[:300],
                                sample_line_number=line_idx,
                                sample_file=filename,
                                count=1,
                            )
                        else:
                            candidates[code_term].count += 1

        # Check existing accepted or rejected keywords if repository is provided
        reviewed_keywords = set()
        if self.learned_keyword_repository:
            try:
                if hasattr(self.learned_keyword_repository, "get_reviewed_keywords"):
                    reviewed_list = await self.learned_keyword_repository.get_reviewed_keywords()
                    reviewed_keywords = set(reviewed_list)
                else:
                    top_existing = await self.learned_keyword_repository.list_accepted_keywords()
                    reviewed_keywords = {k.keyword.lower() for k in top_existing}
            except Exception:
                pass

        # Build output schemas, excluding terms already reviewed by humans
        result_items: List[DiscoveredKeywordSchema] = []
        for term, occ in candidates.items():
            if term.lower() in reviewed_keywords:
                continue

            # Confidence score based on occurrence count and severity
            confidence = 0.85
            if occ.severity == "critical":
                confidence += 0.08
            if occ.count > 1:
                confidence += min(0.05, occ.count * 0.01)
            confidence = min(0.99, round(confidence, 2))

            result_items.append(
                DiscoveredKeywordSchema(
                    keyword=occ.keyword,
                    severity=occ.severity,
                    failure_indicator=occ.failure_indicator,
                    occurrence_count=occ.count,
                    sample_line=occ.sample_line,
                    sample_line_number=occ.sample_line_number,
                    sample_file=occ.sample_file,
                    confidence_score=confidence,
                )
            )

        # Sort: critical first, then highest occurrence count
        sev_order = {"critical": 0, "error": 1, "warning": 2}
        result_items.sort(key=lambda x: (sev_order.get(x.severity, 3), -x.occurrence_count))

        return DiscoverKeywordsResponse(
            keywords=result_items,
            total_discovered=len(result_items),
            files_scanned=len(files),
        )
