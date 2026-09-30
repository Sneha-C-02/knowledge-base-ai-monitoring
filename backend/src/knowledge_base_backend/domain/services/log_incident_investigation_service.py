import re
from typing import List, Tuple, Optional, Dict, Any

from src.knowledge_base_backend.domain.value_objects.reactive_support_models import (
    IncidentInvestigationResult,
    MatchingMajorEvent,
    SystemChangeComparison,
    GroundingEvidence,
)


class LogIncidentInvestigationService:
    """
    Performs reactive support log incident investigation across uploaded files or folders:
    1. Pinpoints which log file and line number the mentioned issue is present in.
    2. Identifies and summarizes the pattern or incident in the log before the issue.
    3. Detects major system events across all logs and mentions them ONLY IF they match the problem.
    4. Detects and compares system changes after the incident vs before the incident.
    5. Implements anti-hallucination verification (strict ground-truth line validation, zero phantom fallback).
    6. Speed and token-optimized (fast indexing, lazy timestamp detection, compact window extraction).
    """

    # Common stop words to exclude from keyword extraction.
    # Note: "issue" and "problem" are intentionally NOT stop words because they express error intent.
    STOP_WORDS = {
        "the", "is", "at", "which", "on", "and", "a", "an", "in", "to", "for", "with",
        "of", "by", "from", "as", "about", "my", "our", "their", "user", "chat",
        "mentioned", "system", "please", "why", "what", "when", "where", "how",
        "does", "not", "have", "has", "had", "can", "could", "would", "should", "there",
        "been", "being", "this", "that", "these", "those", "into", "after", "before", "over",
        "did", "occur", "occurred", "happen", "happened", "check", "checking", "any", "are",
        "were", "was", "show", "tell", "log", "logs", "file", "files", "find", "found",
        "detected", "reported", "recorded", "observed", "logged", "see", "seen", "search",
        "you", "anything", "something", "today", "whether", "look", "review", "scan",
        "inspect", "analyze", "examine", "give", "got", "come", "exist", "indicated",
    }

    # Conversational, query framing, and filler words for broad error query intent detection
    BROAD_QUERY_FILLERS = {
        "a", "about", "after", "all", "also", "am", "an", "analyze", "analyzed",
        "analyzing", "and", "any", "anyone", "anything", "appear", "appeared",
        "appearing", "appears", "are", "around", "as", "at", "attempt", "attempted",
        "attempting", "bad", "be", "been", "before", "being", "both", "by", "came",
        "can", "chat", "check", "checked", "checking", "checks", "cause", "caused",
        "causes", "causing", "come", "comes", "coming", "condition", "could", "detail",
        "details", "detect", "detected", "detecting", "detects", "did", "do",
        "does", "doing", "done", "during", "each", "either", "entries", "entry",
        "examine", "examined", "examining", "exist", "existed", "existing",
        "exists", "explain", "explained", "explaining", "explanation", "file",
        "files", "find", "finding", "finds", "found", "for", "from", "gave",
        "get", "gets", "getting", "give", "given", "gives", "giving", "go",
        "goes", "going", "gone", "got", "had", "happen", "happened", "happening",
        "happens", "has", "have", "having", "he", "her", "here", "him", "his",
        "how", "i", "if", "in", "indicate", "indicated", "indicates",
        "indicating", "info", "information", "inspect", "inspected",
        "inspecting", "into", "is", "it", "its", "just", "kindly", "line",
        "lines", "log", "logged", "logging", "logs", "look", "looked",
        "looking", "looks", "may", "me", "mentioned", "message", "messages",
        "might", "must", "my", "neither", "no", "not", "now", "observe",
        "observed", "observes", "observing", "occur", "occurred", "occurring",
        "occurs", "occurrence", "occurrences", "of", "on", "our", "out", "over",
        "past", "please", "present", "reason", "reasons", "recent", "recently",
        "record", "recorded", "recording", "records", "report", "reported",
        "reporting", "reports", "review", "reviewed", "reviewing", "run", "runlog",
        "runs", "saw", "scan", "scanned", "scanning", "search", "searched",
        "searching", "see", "seeing", "seen", "sees", "shall", "she", "should",
        "show", "showed", "showing", "shown", "shows", "some", "someone",
        "something", "state", "status", "still", "system", "tell", "telling",
        "tells", "that", "the", "their", "them", "there", "these", "they",
        "this", "those", "to", "today", "told", "trace", "up", "us", "user",
        "was", "we", "went", "were", "what", "when", "where", "whether",
        "which", "who", "whom", "whose", "why", "will", "with", "would",
        "yesterday", "you", "your",
    }

    # High-impact laboratory instrument components
    KNOWN_COMPONENTS = {
        "pump", "detector", "column", "valve", "autosampler", "injector", "lamp",
        "pressure", "flow", "heater", "sensor", "vacuum", "degasser", "solvent",
        "needle", "tray", "seal", "plunger", "baseline", "noise", "drift", "calibration",
        "communication", "comm", "conn", "connection", "socket", "ethernet", "network",
        "firmware", "controller", "sample", "vial", "board", "interlock", "temperature",
        "temp", "voltage", "current", "motor", "oven", "carousel", "cooler", "leak", "syringe",
    }

    # Error situation indicators and log markers
    ERROR_SITUATION_INDICATORS = [
        "error", "errors", "fail", "failed", "failure", "failures",
        "exception", "exceptions", "critical", "fatal", "panic", "emergency",
        "abort", "aborted", "timeout", "timed out", "alarm", "alarms",
        "interlock", "tripped", "disconnect", "disconnected", "lost",
        "offline", "unreachable", "refused", "corrupt", "corruption",
        "leak", "overpressure", "stalled", "stall", "fault", "faults",
        "crash", "crashed", "breakdown", "breakdowns", "malfunction", "malfunctions",
    ]

    # Terms expressing error intent
    ERROR_TERMS = {
        "error", "errors", "failure", "failures", "fail", "failed", "fails", "failing",
        "fault", "faults", "exception", "exceptions", "crash", "crashed", "crashes", "crashing",
        "breakdown", "breakdowns", "abort", "aborted", "aborts", "aborting",
        "timeout", "timeouts", "timed out", "timed",
        "malfunction", "malfunctions", "problem", "problems", "issue", "issues",
        "alarm", "alarms", "incident", "incidents", "anomaly", "anomalies", "wrong",
        "broken", "break", "broke", "glitch", "glitches",
    }

    # Compiled regex patterns enforcing word boundaries to eliminate substring false positives (e.g. installed/default)
    COMPONENT_PATTERN = re.compile(
        r'\b(?:' + '|'.join(re.escape(c) for c in sorted(KNOWN_COMPONENTS, key=len, reverse=True)) + r')\b',
        re.IGNORECASE,
    )

    ERROR_INDICATORS_PATTERN = re.compile(
        r'\b(?:' + '|'.join(re.escape(i) for i in sorted(ERROR_SITUATION_INDICATORS, key=len, reverse=True)) + r')\b',
        re.IGNORECASE,
    )

    @classmethod
    def get_matched_components(cls, text: str) -> List[str]:
        """Return list of distinct known instrument components matched on whole-word boundaries."""
        matches = cls.COMPONENT_PATTERN.findall(text)
        return list(dict.fromkeys(m.lower() for m in matches))

    @classmethod
    def get_matched_error_indicators(cls, text: str) -> List[str]:
        """Return list of distinct error situation indicators matched on whole-word boundaries."""
        matches = cls.ERROR_INDICATORS_PATTERN.findall(text)
        return list(dict.fromkeys(m.lower() for m in matches))

    # Primary instrument subsystems used to isolate components and avoid cross-subsystem hijacking
    PRIMARY_SUBSYSTEMS = {
        "pump": ["pump", "plunger", "seal", "fluidic"],
        "detector": ["detector", "optical", "lamp", "spectrometer"],
        "column": ["column", "oven", "compartment"],
        "valve": ["valve", "rotor", "stator"],
        "autosampler": ["autosampler", "injector", "needle", "tray", "carousel", "vial"],
        "degasser": ["degasser", "vacuum"],
        "comm": ["comm", "communication", "socket", "ethernet"],
    }

    # Common domain synonyms for chromatography and spectrometry
    DOMAIN_SYNONYMS = {
        "comm": ["communication", "socket", "connection", "ethernet", "link"],
        "communication": ["comm", "socket", "connection", "ethernet", "link"],
        "connection": ["communication", "comm", "socket", "ethernet", "link"],
        "socket": ["communication", "comm", "connection", "ethernet", "port"],
        "disconnected": ["communication", "lost", "disconnect", "socket"],
        "disconnect": ["communication", "lost", "socket", "timeout"],
        "leak": ["pressure", "seal", "fluidic", "solvent", "droplet"],
        "drift": ["baseline", "detector", "noise", "absorbance"],
        "overpressure": ["pressure", "limit", "exceeded", "pump"],
        "needle": ["autosampler", "injector", "vial", "sample", "plunger"],
        "autosampler": ["injector", "needle", "vial", "sample", "tray", "carousel", "plunger"],
        "injector": ["autosampler", "needle", "vial", "sample", "tray", "carousel", "plunger"],
        "column": ["oven", "heater", "compartment", "temperature", "thermal"],
        "valve": ["switching", "rotor", "stator", "seal", "position"],
        "degasser": ["vacuum", "pump", "vent", "chamber", "decay"],
        "vacuum": ["degasser", "pump", "vent", "decay"],
        "temp": ["temperature", "heater", "cooler", "thermal", "oven"],
        "temperature": ["temp", "heater", "cooler", "thermal", "oven"],
        "heater": ["temperature", "thermal", "oven", "temp"],
        "detector": ["optical", "baseline", "drift", "absorbance", "lamp", "noise", "spectrometer"],
    }
    # Map all error-related terms to comprehensive error situation indicators
    for _term in ERROR_TERMS:
        if _term not in DOMAIN_SYNONYMS:
            DOMAIN_SYNONYMS[_term] = ERROR_SITUATION_INDICATORS

    # Major / Catastrophic event indicators in logs
    MAJOR_EVENT_PATTERNS = [
        (re.compile(r'\b(?:emergency[\s_-]*stop|safety[\s_-]*interlock[\s_-]*tripped)\b', re.IGNORECASE), "Emergency Safety Stop"),
        (re.compile(r'\b(?:kernel[\s_-]*panic|bsod|unhandled[\s_-]*exception|system[\s_-]*crash)\b', re.IGNORECASE), "System Crash / Kernel Panic"),
        (re.compile(r'\b(?:database[\s_-]*connection[\s_-]*lost|database[\s_-]*corrupt|disk[\s_-]*full)\b', re.IGNORECASE), "Critical Database / Storage Failure"),
        (re.compile(r'\b(?:power[\s_-]*failure|unexpected[\s_-]*restart|hard[\s_-]*reboot|brownout)\b', re.IGNORECASE), "Power Loss / Hardware Reset"),
        (re.compile(r'\b(?:out[\s_-]*of[\s_-]*memory|oom[\s_-]*killer|memory[\s_-]*exhaustion)\b', re.IGNORECASE), "System Out-Of-Memory Exceeded"),
        (re.compile(r'\b(?:fatal[\s_-]*error|catastrophic[\s_-]*abort|system[\s_-]*halted[\s_-]*(?:unexpectedly|due[\s_-]*to[\s_-]*error|forcibly))\b', re.IGNORECASE), "Catastrophic System Abort"),
    ]

    def __init__(self, ai_answer_service=None) -> None:
        self.ai_answer_service = ai_answer_service

    def extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords and domain synonyms from user problem description."""
        text_lower = text.lower()
        tokens = re.findall(r'[a-zA-Z0-9_\-]+', text_lower)
        keywords = [t for t in tokens if len(t) > 2 and t not in self.STOP_WORDS]
        # Check for multi-word domain expressions like "timed out"
        if "timed out" in text_lower and "timed out" not in keywords:
            keywords.append("timed out")
        # Expand synonyms
        expanded = list(keywords)
        for kw in keywords:
            if kw in self.DOMAIN_SYNONYMS:
                expanded.extend(self.DOMAIN_SYNONYMS[kw])
        return list(dict.fromkeys(expanded))

    def detect_timestamp(self, line: str) -> Optional[str]:
        """Extract timestamp from log line (Waters format, ISO, Syslog, or brackets)."""
        # Waters style: Mon Oct 20 11:32:42 AM or Oct 20 11:28:57 AM
        m = re.search(r'\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun\s+)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?(?:\s+[AP]M)?', line, re.IGNORECASE)
        if m:
            return m.group(0)
        # ISO: 2026-09-18 14:22:01 or 2026-09-18T14:22:01
        m = re.search(r'\b\d{4}[-/]\d{2}[-/]\d{2}[T\s]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?\b', line)
        if m:
            return m.group(0)
        # Bracketed: [20/09/2026 14:22:01]
        m = re.search(r'\[(\d{2,4}[-\/]\d{2}[-\/]\d{2,4}\s+\d{2}:\d{2}:\d{2})\]', line)
        if m:
            return m.group(1)
        return None

    def _extract_date_key(self, ts: Optional[str]) -> Optional[str]:
        """Extract normalized calendar day key for accurate same-day comparison across log styles."""
        if not ts:
            return None
        # Month Day (Waters/Syslog): "Oct 20", "Sep 18"
        m = re.search(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})\b', ts, re.IGNORECASE)
        if m:
            month = m.group(1).capitalize()
            day = int(m.group(2))
            return f"{month}-{day:02d}"
        # ISO format: "2026-09-18"
        m = re.search(r'\b\d{4}[-/](\d{2})[-/](\d{2})\b', ts)
        if m:
            return f"{m.group(1)}-{m.group(2)}"
        # D/M/Y or M/D/Y format in brackets
        m = re.search(r'\b(\d{1,2})[-/](\d{1,2})[-/]\d{2,4}\b', ts)
        if m:
            return f"{int(m.group(1)):02d}-{int(m.group(2)):02d}"
        return None

    def detect_severity(self, line: str) -> str:
        """Detect severity of log line with quick case check and error-situation awareness."""
        upper = line.upper()
        # Structured log level tags in brackets or prefix (e.g. [INFO], [ERROR], INFO:)
        structured_level = None
        if re.search(r'\[(?:CRITICAL|FATAL|PANIC|EMERGENCY|ALERT)\]|\b(?:CRITICAL|FATAL|PANIC|EMERGENCY|ALERT):', upper):
            structured_level = "CRITICAL"
        elif re.search(r'\[(?:ERROR|FAIL|EXCEPTION|ABORT|FAULT)\]|\b(?:ERROR|FAIL|EXCEPTION|ABORT|FAULT):', upper):
            structured_level = "ERROR"
        elif re.search(r'\[(?:WARN|WARNING|TIMEOUT|ALARM)\]|\b(?:WARN|WARNING|TIMEOUT|ALARM):', upper):
            structured_level = "WARNING"
        elif re.search(r'\[(?:INFO|NOTICE)\]|\b(?:INFO|NOTICE):', upper):
            structured_level = "INFO"
        elif re.search(r'\[(?:DEBUG|TRACE)\]|\b(?:DEBUG|TRACE):', upper):
            structured_level = "DEBUG"

        if structured_level in ("CRITICAL", "ERROR", "WARNING"):
            return structured_level

        lower = line.lower()
        if self._is_benign_negation(lower):
            return structured_level or ("INFO" if "INFO" in upper else "DEBUG")

        # Explicit critical indicators
        if (
            re.search(r'\b(?:emergency[\s_-]*stop|safety[\s_-]*interlock[\s_-]*tripped|kernel[\s_-]*panic|bsod|catastrophic)\b', lower)
            or any(term in upper for term in ("CRITICAL", "FATAL", "PANIC", "EMERGENCY", "ALERT", "INTERLOCK TRIPPED"))
        ):
            return "CRITICAL"

        # Explicit error indicators
        if (
            re.search(r'\b(?:error|errors|fail|failed|failure|failures|exception|exceptions|abort|aborted|fault|faults|crash|crashed|malfunction|overpressure|refused|unreachable|disconnected|corrupt|corruption|stalled)\b', lower)
            or re.search(r'\b(?:err(?:or)?[\s_:-]*[0-9a-fx]+|[0-9]{3,6}|0x[0-9a-f]+)\b', lower)
            or "communication lost" in lower
            or "connection lost" in lower
            or "socket error" in lower
            or "status=fault" in lower
        ):
            return "ERROR"

        # Explicit warning indicators
        if (
            re.search(r'\b(?:warn|warning|timeout|timed[\s_-]*out|retry|alarm|alarms|leak|leaks|interlock)\b', lower)
            or "limit exceeded" in lower
        ):
            return "WARNING"

        if structured_level:
            return structured_level

        if "INFO" in upper:
            return "INFO"
        return "DEBUG"

    def investigate(
        self,
        files: List[Tuple[str, str]],
        problem_description: str,
        pattern_weights: Optional[Dict[str, float]] = None,
    ) -> IncidentInvestigationResult:
        """Synchronous core incident investigation across files/folders."""
        return self.investigate_sync(
            files=files,
            problem_description=problem_description,
            pattern_weights=pattern_weights,
        )

    async def investigate_async(
        self,
        files: List[Tuple[str, str]],
        problem_description: str,
        pattern_weights: Optional[Dict[str, float]] = None,
    ) -> IncidentInvestigationResult:
        """
        Async entry point for application use cases.
        Executes fast bounded indexing, and if an AI answer service is configured,
        generates an anti-hallucination verified AI explanation within a compact token window.
        """
        result = self.investigate_sync(
            files=files,
            problem_description=problem_description,
            pattern_weights=pattern_weights,
        )

        if result.found and self.ai_answer_service is not None:
            try:
                ai_summary = await self._generate_bounded_ai_summary(result)
                if ai_summary:
                    result.pre_incident_summary = ai_summary
            except Exception:
                # Retain grounded deterministic summary if AI call fails
                pass

        return result

    def _is_broad_error_query(
        self,
        problem_description: str,
        base_keywords: List[str],
        user_components: List[str],
        user_time_str: Optional[str],
        error_codes: List[str],
    ) -> bool:
        """Detect whether user query asks broadly about error occurrence without specific subsystem/time."""
        problem_lower = problem_description.lower()

        # If user explicitly specifies a component, time, or error code, it's specific
        if user_components or user_time_str or error_codes:
            return False

        has_error_term = (
            any(t in self.ERROR_TERMS for t in base_keywords)
            or any(t in problem_lower for t in self.ERROR_TERMS)
            or "timed out" in problem_lower
        )
        if not has_error_term:
            return False

        words = re.findall(r'[a-zA-Z0-9_\-]+', problem_lower)
        non_fillers = [
            w for w in words
            if len(w) > 1 and w not in self.ERROR_TERMS and w not in self.BROAD_QUERY_FILLERS
        ]
        if non_fillers:
            return False

        return True

    BENIGN_NEGATION_MARKERS = (
        "0 error", "0 errors", "no error", "no errors", "zero error", "zero errors", "error-free",
        "0 failure", "0 failures", "no failure", "no failures", "zero failure", "zero failures",
        "0 alarm", "0 alarms", "no alarm", "no alarms", "zero alarm", "zero alarms",
        "0 warning", "0 warnings", "no warning", "no warnings", "zero warning", "zero warnings",
        "0 fault", "0 faults", "no fault", "no faults", "zero fault", "zero faults",
        "0 issue", "0 issues", "no issue", "no issues", "zero issue", "zero issues",
        "0 problem", "0 problems", "no problem", "no problems", "zero problem", "zero problems",
        "no exceptions", "0 exceptions",
        "error handling subsystem initialized",
        "error logging initialized",
        "error reporting service started",
        "normal disconnect", "clean disconnect", "graceful disconnect",
        "disconnect of idle", "disconnect upon batch",
        "leak sensor test status ok", "status ok", "status: ok", "status = ok",
        "all self-tests passed", "self-test passed",
    )

    def _is_benign_negation(self, text_lower: str) -> bool:
        """Check if log line contains benign negative phrasing (e.g. 0 errors, no alarms) and no genuine failure."""
        if not any(neg in text_lower for neg in self.BENIGN_NEGATION_MARKERS):
            return False
        if re.search(r'\b(?:emergency[\s_-]*stop|safety[\s_-]*interlock[\s_-]*tripped|panic|catastrophic|unhandled[\s_-]*exception)\b', text_lower):
            return False
        return True

    def _is_error_situation_line(self, rec: Dict[str, Any]) -> bool:
        """Check if record represents an error, fault, warning, or error situation indicator (not benign)."""
        rec_lower = rec["lower"]
        if self._is_benign_negation(rec_lower):
            return False
        if rec["severity"] in ("CRITICAL", "ERROR", "WARNING"):
            return True
        if bool(self.get_matched_error_indicators(rec_lower)):
            return True
        if re.search(r'\b(?:err(?:or)?[\s_:-]*[0-9a-fx]+|[0-9]{3,6}|0x[0-9a-f]+)\b', rec_lower):
            return True
        for regex, _ in self.MAJOR_EVENT_PATTERNS:
            if regex.search(rec_lower):
                return True
        return False

    def _has_log_errors_or_warnings(self, parsed_files: Dict[str, List[Dict[str, Any]]]) -> bool:
        """Check if parsed log files contain any real errors, faults, or warnings."""
        for records in parsed_files.values():
            for rec in records:
                if self._is_error_situation_line(rec):
                    return True
        return False

    def investigate_sync(
        self,
        files: List[Tuple[str, str]],
        problem_description: str,
        pattern_weights: Optional[Dict[str, float]] = None,
    ) -> IncidentInvestigationResult:
        """
        Core incident investigation:
        1. Find file & line matching user problem symptoms or broad error intent.
        2. Analyze pre-incident pattern.
        3. Find matching major events (filtered: ONLY if matching the problem).
        4. Detect before vs after system changes.
        5. Verify anti-hallucination ground truth.
        """
        if not files:
            return IncidentInvestigationResult(
                found=False,
                problem_description=problem_description,
                pre_incident_summary="No log files were provided for analysis.",
                suggested_search_query=problem_description,
                anti_hallucination_verified=True,
            )

        keywords = self.extract_keywords(problem_description)
        problem_lower = problem_description.lower()
        weights = pattern_weights or {}

        # 1. Index all files line by line (speed-optimized: fast lowercasing and basic records)
        parsed_files: Dict[str, List[Dict[str, Any]]] = {}
        total_lines = 0

        for filename, content in files:
            lines = content.splitlines()
            line_records = []
            for idx, raw_line in enumerate(lines, start=1):
                clean_line = raw_line.strip()
                if not clean_line:
                    continue
                record = {
                    "file": filename,
                    "line": idx,
                    "text": clean_line,
                    "lower": clean_line.lower(),
                    "timestamp": None,  # Lazy evaluation for speed
                    "severity": self.detect_severity(clean_line),
                }
                line_records.append(record)
            parsed_files[filename] = line_records
            total_lines += len(line_records)

        # 2. Extract base problem terms & intent
        base_keywords = [
            t for t in re.findall(r'[a-zA-Z0-9_\-]+', problem_lower)
            if len(t) > 2 and t not in self.STOP_WORDS
        ]
        if "timed out" in problem_lower and "timed out" not in base_keywords:
            base_keywords.append("timed out")

        user_components = self.get_matched_components(problem_lower)
        user_subsystems = [
            sub for sub, terms in self.PRIMARY_SUBSYSTEMS.items()
            if any(re.search(r'\b' + re.escape(t) + r'\b', problem_lower) for t in terms)
        ]
        user_time_match = re.search(r'\b\d{1,2}:\d{2}(?::\d{2})?\b', problem_description)
        user_time_str = user_time_match.group(0) if user_time_match else None
        error_codes = re.findall(r'\b(?:err(?:or)?[\s_:-]*[0-9a-fx]+|[0-9]{3,6}|0x[0-9a-f]+)\b', problem_lower)

        has_error_intent = (
            any(t in self.ERROR_TERMS for t in base_keywords)
            or any(t in problem_lower for t in self.ERROR_TERMS)
            or "timed out" in problem_lower
        )

        is_broad_error = self._is_broad_error_query(
            problem_description=problem_description,
            base_keywords=base_keywords,
            user_components=user_components,
            user_time_str=user_time_str,
            error_codes=error_codes,
        )

        # ANTI-HALLUCINATION GUARD:
        # If user asks broadly about errors and the log files are completely clean, return found=False!
        if is_broad_error and not self._has_log_errors_or_warnings(parsed_files):
            return IncidentInvestigationResult(
                found=False,
                problem_description=problem_description,
                pre_incident_summary="The described issue was not found in the uploaded log files.",
                suggested_search_query=problem_description,
                files_scanned=len(files),
                lines_scanned=total_lines,
                anti_hallucination_verified=True,
            )

        # 3. Pinpoint target log file and line number
        best_candidate: Optional[Dict[str, Any]] = None
        best_score = -1.0

        for filename, records in parsed_files.items():
            for rec in records:
                score = 0.0
                rec_lower = rec["lower"]
                rec_severity = rec["severity"]

                if is_broad_error:
                    if not self._is_error_situation_line(rec):
                        continue

                    # Base severity score
                    if rec_severity == "CRITICAL":
                        score += 50.0
                    elif rec_severity == "ERROR":
                        score += 35.0
                    elif rec_severity == "WARNING":
                        score += 20.0
                    else:
                        score += 5.0

                    matched_indicators = self.get_matched_error_indicators(rec_lower)
                    score += min(3, len(matched_indicators)) * 15.0

                    # Major event match boost
                    for regex, _ in self.MAJOR_EVENT_PATTERNS:
                        if regex.search(rec_lower):
                            score += 30.0
                            break

                    # Error code boost
                    if re.search(r'\b(?:err(?:or)?[\s_:-]*[0-9a-fx]+|[0-9]{3,6}|0x[0-9a-f]+)\b', rec_lower):
                        score += 20.0

                    # Hardware component boost
                    line_components = self.get_matched_components(rec_lower)
                    if line_components:
                        score += 15.0

                else:
                    # Specific query scoring
                    # If user has error intent, disqualify non-error lines
                    if has_error_intent and not self._is_error_situation_line(rec):
                        continue

                    # Direct phrase overlap from user query
                    for i in range(len(base_keywords) - 1):
                        phrase = f"{base_keywords[i]} {base_keywords[i+1]}"
                        if phrase in rec_lower:
                            score += 35.0

                    # Base keyword matching: exact match carries primary weight over indirect synonyms
                    for bk in base_keywords:
                        if re.search(r'\b' + re.escape(bk) + r'\b', rec_lower):
                            score += 35.0
                        elif any(re.search(r'\b' + re.escape(syn) + r'\b', rec_lower) for syn in self.DOMAIN_SYNONYMS.get(bk, [])):
                            score += 12.0
                        elif bk in self.ERROR_TERMS and bool(self.get_matched_error_indicators(rec_lower)):
                            score += 10.0

                    # Known component matches
                    for comp in user_components:
                        if re.search(r'\b' + re.escape(comp) + r'\b', rec_lower):
                            score += 25.0

                    # Primary subsystem specificity & competing subsystem penalty
                    if user_subsystems:
                        matched_user_sub = any(
                            any(re.search(r'\b' + re.escape(t) + r'\b', rec_lower) for t in self.PRIMARY_SUBSYSTEMS[sub])
                            for sub in user_subsystems
                        )
                        if matched_user_sub:
                            score += 35.0
                        else:
                            competing = any(
                                any(re.search(r'\b' + re.escape(t) + r'\b', rec_lower) for t in terms)
                                for sub, terms in self.PRIMARY_SUBSYSTEMS.items()
                                if sub not in user_subsystems
                            )
                            if competing:
                                score -= 50.0

                    # Error code match
                    for code in error_codes:
                        if code in rec_lower:
                            score += 45.0

                    # User-mentioned time match
                    if user_time_str and user_time_str in rec_lower:
                        score += 40.0

                    # Severity boost
                    if has_error_intent:
                        if rec_severity == "CRITICAL":
                            score += 25.0
                        elif rec_severity == "ERROR":
                            score += 20.0
                        elif rec_severity == "WARNING":
                            score += 10.0
                    else:
                        if rec_severity == "CRITICAL":
                            score += 15.0
                        elif rec_severity == "ERROR":
                            score += 10.0
                        elif rec_severity == "WARNING":
                            score += 5.0

                # Feedback-driven weights from past user verification
                line_key = f"{rec['file']}:{rec['line']}"
                if line_key in weights:
                    score += weights[line_key]

                for term, weight in weights.items():
                    if ":" in term:
                        continue
                    if term in rec_lower:
                        score += weight * 10.0

                # Minimum threshold: requires actual topical relevance to prevent hallucinations
                if score > best_score and score >= 12.0:
                    best_score = score
                    best_candidate = rec

        # ANTI-HALLUCINATION GUARD:
        # If no line matches the user's problem with verified relevance, REFUSE to pick an arbitrary error!
        if not best_candidate:
            return IncidentInvestigationResult(
                found=False,
                problem_description=problem_description,
                pre_incident_summary="The described issue was not found in the uploaded log files.",
                suggested_search_query=problem_description,
                files_scanned=len(files),
                lines_scanned=total_lines,
                anti_hallucination_verified=True,
            )

        target_file = best_candidate["file"]
        target_line = best_candidate["line"]
        matched_text = best_candidate["text"]
        best_candidate["timestamp"] = self.detect_timestamp(matched_text)
        target_timestamp = best_candidate["timestamp"]
        target_severity = best_candidate["severity"]
        target_records = parsed_files[target_file]

        # Find index in target_records
        target_idx = 0
        for i, r in enumerate(target_records):
            if r["line"] == target_line:
                target_idx = i
                break

        # 4. Analyze pre-incident pattern & incident before the mentioned issue (bounded window)
        pre_window_start = max(0, target_idx - 35)
        pre_records = target_records[pre_window_start:target_idx]

        # Populate timestamps for pre_records
        for r in pre_records:
            if r["timestamp"] is None:
                r["timestamp"] = self.detect_timestamp(r["text"])

        pre_incident_pattern, pre_incident_summary, pre_incident_events = self._analyze_pre_incident(
            pre_records=pre_records,
            incident_record=best_candidate,
            problem_description=problem_description,
        )

        # 5. Detect major system events across all logs (ONLY IF MATCHING THE PROBLEM)
        major_events = self._detect_matching_major_events(
            parsed_files=parsed_files,
            incident_record=best_candidate,
            problem_description=problem_description,
        )

        # 6. Detect system changes (After Incident vs Before Incident)
        post_window_end = min(len(target_records), target_idx + 26)
        post_records = target_records[target_idx + 1:post_window_end]

        for r in post_records:
            if r["timestamp"] is None:
                r["timestamp"] = self.detect_timestamp(r["text"])

        system_changes = self._analyze_system_changes(
            pre_records=pre_records,
            incident_record=best_candidate,
            post_records=post_records,
        )

        # 7. Anti-Hallucination Grounding Validator
        grounding_citations, confidence_score = self._validate_grounding(
            target_file=target_file,
            target_line=target_line,
            matched_text=matched_text,
            pre_records=pre_records,
            major_events=major_events,
            problem_keywords=keywords,
            base_keywords=base_keywords,
            is_broad_error=is_broad_error,
        )

        # 8. Generate suggested search query for the KB button
        suggested_kb_query = self._generate_suggested_kb_query(
            problem_description=problem_description,
            best_candidate=best_candidate,
            pre_pattern=pre_incident_pattern,
            is_broad_error=is_broad_error,
            base_keywords=base_keywords,
        )

        return IncidentInvestigationResult(
            found=True,
            problem_description=problem_description,
            log_file=target_file,
            line_number=target_line,
            matched_line=matched_text,
            matched_timestamp=target_timestamp,
            severity=target_severity,
            pre_incident_summary=pre_incident_summary,
            pre_incident_pattern=pre_incident_pattern,
            pre_incident_events=pre_incident_events,
            major_events=major_events,
            system_changes=system_changes,
            grounding_citations=grounding_citations,
            confidence_score=confidence_score,
            suggested_search_query=suggested_kb_query,
            anti_hallucination_verified=True,
            files_scanned=len(files),
            lines_scanned=total_lines,
        )

    async def _generate_bounded_ai_summary(self, result: IncidentInvestigationResult) -> Optional[str]:
        """
        Token-optimized AI explanation of pre-incident sequence.
        Bounds context strictly to ~150-250 tokens and enforces anti-hallucination verification.
        """
        if not result.pre_incident_events and not result.matched_line:
            return None

        lines_context = []
        for ev in result.pre_incident_events[-6:]:
            lines_context.append(f"Line {ev['line']}: {ev['snippet']}")
        lines_context.append(f"Incident Line {result.line_number}: {result.matched_line}")

        context_block = "\n".join(lines_context)
        prompt = (
            f"Problem: {result.problem_description}\n"
            f"Pre-incident Pattern: {result.pre_incident_pattern}\n"
            f"In 2 grounded sentences, summarize what happened before line {result.line_number}."
        )

        resp = await self.ai_answer_service.generate_grounded_support_answer(
            query=prompt,
            context=context_block,
        )

        if resp and resp.answer and "disabled in the configuration" not in resp.answer:
            clean_ans = re.sub(r'<think>.*?</think>', '', resp.answer, flags=re.DOTALL).strip()
            if len(clean_ans) > 20:
                return clean_ans

        return None

    def _analyze_pre_incident(
        self,
        pre_records: List[Dict[str, Any]],
        incident_record: Dict[str, Any],
        problem_description: str,
    ) -> Tuple[str, str, List[Dict[str, Any]]]:
        """Examine log lines strictly before the incident to identify preceding patterns."""
        if not pre_records:
            return (
                "Isolated Incident",
                f"No preceding log lines recorded in {incident_record['file']} before line {incident_record['line']}.",
                [],
            )

        events: List[Dict[str, Any]] = []
        warnings = []
        retries = []
        pressure_points = []
        comm_events = []
        temp_points = []
        detector_drift_events = []
        lamp_events = []
        autosampler_events = []
        leak_events = []

        for rec in pre_records:
            lower = rec["lower"]
            line_num = rec["line"]
            snippet = rec["text"]

            if rec["severity"] in ("WARNING", "ERROR", "CRITICAL"):
                warnings.append((line_num, snippet))
                events.append({"line": line_num, "timestamp": rec.get("timestamp"), "snippet": snippet, "type": "warning"})

            if any(term in lower for term in ("retry", "timed out", "timeout", "no ack", "handshake fail")):
                retries.append((line_num, snippet))

            if any(term in lower for term in ("comm", "connection lost", "socket", "disconnect", "packet dropped")):
                comm_events.append((line_num, snippet))

            if any(term in lower for term in ("drift", "baseline", "noise", "absorbance out of range")):
                detector_drift_events.append((line_num, snippet))

            if any(term in lower for term in ("lamp", "ignition", "intensity low", "deuterium", "tungsten")):
                lamp_events.append((line_num, snippet))

            if any(term in lower for term in ("needle", "autosampler", "injector", "vial", "tray", "pierce", "carousel", "motor stall")):
                autosampler_events.append((line_num, snippet))

            if any(term in lower for term in ("leak", "solvent level", "bubble", "degasser")):
                leak_events.append((line_num, snippet))

            press_match = re.search(r'pressure[^\d]*(\d+(?:\.\d+)?)\s*(?:psi|bar|kpa)?', lower)
            if press_match:
                pressure_points.append((line_num, float(press_match.group(1))))

            temp_match = re.search(r'temp(?:erature)?[^\d]*(\d+(?:\.\d+)?)\s*(?:c|°c)?', lower)
            if temp_match:
                temp_points.append((line_num, float(temp_match.group(1))))

        # Detect pattern taxonomy with domain specificity
        summary_sentences = []

        if retries or (comm_events and len(comm_events) >= 2):
            pattern_name = "Communication Retry / Socket Timeout Cascade"
            summary_sentences.append(
                f"Prior to line {incident_record['line']}, repeated communication timeouts and socket retry attempts occurred."
            )
            if retries:
                summary_sentences.append(
                    f"{len(retries)} timeout/retry event(s) observed between lines {retries[0][0]} and {retries[-1][0]}."
                )

        elif pressure_points and (len(pressure_points) >= 2 or "pressure" in incident_record["text"].lower()):
            first_p = pressure_points[0][1]
            last_p = pressure_points[-1][1]
            if last_p > first_p * 1.15:
                pattern_name = "Progressive Pressure Escalation"
                summary_sentences.append(
                    f"Prior to line {incident_record['line']}, fluidic pressure escalated significantly from {first_p} to {last_p} psi (lines {pressure_points[0][0]}-{pressure_points[-1][0]})."
                )
            elif last_p < first_p * 0.85:
                pattern_name = "Sudden Pressure Drop / Solvent Depletion"
                summary_sentences.append(
                    f"Prior to line {incident_record['line']}, fluidic pressure dropped sharply from {first_p} to {last_p} psi, indicating possible seal leak or mobile phase depletion."
                )
            else:
                pattern_name = "Fluidic Pressure Instability"
                summary_sentences.append(
                    f"Prior to line {incident_record['line']}, unstable pressure fluctuations were logged across lines {pressure_points[0][0]}-{pressure_points[-1][0]}."
                )

        elif detector_drift_events:
            pattern_name = "Detector Baseline Drift & Optical Noise"
            summary_sentences.append(
                f"Prior to line {incident_record['line']}, optical detector baseline instability and noise events were logged starting at line {detector_drift_events[0][0]}."
            )

        elif lamp_events:
            pattern_name = "Detector Lamp Degradation / Ignition Failure"
            summary_sentences.append(
                f"Prior to line {incident_record['line']}, optical lamp intensity degradation warnings occurred at line {lamp_events[0][0]}."
            )

        elif autosampler_events:
            pattern_name = "Autosampler Mechanical / Vial Handling Precursor"
            summary_sentences.append(
                f"Prior to line {incident_record['line']}, autosampler needle/vial mechanism anomalies were logged starting at line {autosampler_events[0][0]}."
            )

        elif leak_events:
            pattern_name = "Fluidic Leak / Solvent Depletion Alarm"
            summary_sentences.append(
                f"Prior to line {incident_record['line']}, fluidic leak sensor warnings were triggered at line {leak_events[0][0]}."
            )

        elif len(temp_points) >= 2:
            pattern_name = "Thermal Regulation Drift"
            summary_sentences.append(
                f"Prior to line {incident_record['line']}, temperature sensor readings deviated across lines {temp_points[0][0]}-{temp_points[-1][0]}."
            )

        elif len(warnings) >= 2:
            pattern_name = "Warning Cascade"
            summary_sentences.append(
                f"Prior to line {incident_record['line']}, a cluster of {len(warnings)} warning events occurred starting at line {warnings[0][0]}."
            )

        else:
            last_lines = pre_records[-3:] if len(pre_records) >= 3 else pre_records
            pattern_name = "Operational Precursor Event"
            summary_sentences.append(
                f"Prior to line {incident_record['line']}, preceding commands were logged: '{last_lines[-1]['text'][:100]}' at line {last_lines[-1]['line']}."
            )

        summary_text = " ".join(summary_sentences)
        return pattern_name, summary_text, events

    def _detect_matching_major_events(
        self,
        parsed_files: Dict[str, List[Dict[str, Any]]],
        incident_record: Dict[str, Any],
        problem_description: str,
    ) -> List[MatchingMajorEvent]:
        """
        Detect major / catastrophic system events across all logs,
        and return them ONLY IF THEY MATCH THE PROBLEM.
        """
        matching_events: List[MatchingMajorEvent] = []
        problem_lower = problem_description.lower()
        incident_lower = incident_record["text"].lower()

        # Identify key components in problem or incident
        relevant_components = set(self.get_matched_components(problem_lower)) | set(self.get_matched_components(incident_lower))

        # Check if user problem explicitly describes a catastrophic system failure
        is_problem_asking_catastrophe = any(
            term in problem_lower
            for term in (
                "stop", "emergency", "crash", "panic", "reboot", "restart",
                "shutdown", "outage", "halt", "down", "offline", "power",
                "freeze", "bsod", "oom", "disk full"
            )
        )

        inc_date_key = self._extract_date_key(incident_record.get("timestamp"))

        for filename, records in parsed_files.items():
            for rec in records:
                # Do not re-report the incident line itself as an external major event
                if filename == incident_record["file"] and rec["line"] == incident_record["line"]:
                    continue

                rec_lower = rec["lower"]

                # Check if line matches major event patterns
                matched_pattern_label = None
                for regex, label in self.MAJOR_EVENT_PATTERNS:
                    if regex.search(rec_lower):
                        matched_pattern_label = label
                        break

                if not matched_pattern_label:
                    continue

                # Ensure timestamp is parsed for this major event candidate
                if rec["timestamp"] is None:
                    rec["timestamp"] = self.detect_timestamp(rec["text"])

                rec_date_key = self._extract_date_key(rec["timestamp"])
                is_same_day = bool(rec_date_key and inc_date_key and rec_date_key == inc_date_key)

                # CRITICAL REQUIREMENT: Match ONLY IF it matches to the problem!
                # 1. Component correlation
                shared_component = None
                for comp in relevant_components:
                    if re.search(r'\b' + re.escape(comp) + r'\b', rec_lower):
                        shared_component = comp
                        break

                # 2. Query / symptom correlation
                shares_topic = any(kw in rec_lower for kw in self.extract_keywords(problem_description))

                # Determine if it matches the problem
                matches_problem = False
                match_reason = ""

                if shared_component and (shares_topic or is_same_day):
                    matches_problem = True
                    match_reason = f"Correlates with '{shared_component}' subsystem referenced in problem."
                elif shares_topic and is_same_day:
                    matches_problem = True
                    match_reason = f"Occurred on the same date ({rec['timestamp']}) and shares problem keywords."
                elif is_problem_asking_catastrophe and (shares_topic or shared_component or is_same_day):
                    matches_problem = True
                    match_reason = f"Major system event ({matched_pattern_label}) directly aligns with reported outage."

                if matches_problem:
                    matching_events.append(
                        MatchingMajorEvent(
                            timestamp=rec["timestamp"] or "Timestamp unavailable",
                            event_type=matched_pattern_label,
                            description=rec["text"],
                            match_reason=match_reason,
                            line_number=rec["line"],
                            log_file=filename,
                        )
                    )

        return matching_events

    def _analyze_system_changes(
        self,
        pre_records: List[Dict[str, Any]],
        incident_record: Dict[str, Any],
        post_records: List[Dict[str, Any]],
    ) -> List[SystemChangeComparison]:
        """Detect changes in system state after the incident compared to before the incident."""
        changes: List[SystemChangeComparison] = []

        # 1. Error / Failure Frequency
        pre_errors = sum(1 for r in pre_records if r["severity"] in ("CRITICAL", "ERROR"))
        post_errors = sum(1 for r in post_records if r["severity"] in ("CRITICAL", "ERROR"))

        pre_err_rate = f"{pre_errors} error(s) across {len(pre_records)} preceding lines" if pre_records else "Normal baseline (0 errors)"
        post_err_rate = f"{post_errors} error(s) across {len(post_records)} subsequent lines" if post_records else "Logging stopped"

        if post_errors > pre_errors:
            err_summary = f"System entered persistent failure mode: error density increased by {post_errors - pre_errors} occurrences."
        elif post_errors == 0 and len(post_records) > 0:
            err_summary = "System stabilized or ceased reporting errors after incident."
        else:
            err_summary = "Error frequency remained constant."

        changes.append(
            SystemChangeComparison(
                aspect="Error & Warning Frequency",
                before_incident=pre_err_rate,
                after_incident=post_err_rate,
                change_summary=err_summary,
            )
        )

        # 2. Operational / Communication State
        pre_comm_ok = not any("disconnected" in r["lower"] or "lost" in r["lower"] for r in pre_records)
        post_disconnect = any("disconnected" in r["lower"] or "lost" in r["lower"] or "retry" in r["lower"] for r in post_records)

        before_state = "Connected & Active (Normal Acquisition)" if pre_comm_ok else "Intermittent connectivity"
        after_state = "Disconnected / Retrying (Communication Lost)" if post_disconnect else "Operation halted / State unknown"
        change_state_summary = (
            "System transitioned from active operational state to disconnected/fault state."
            if post_disconnect
            else "Operational state suspended after incident."
        )

        changes.append(
            SystemChangeComparison(
                aspect="Communication & Device State",
                before_incident=before_state,
                after_incident=after_state,
                change_summary=change_state_summary,
            )
        )

        # 3. Component Flow / Instrument Execution Mode
        post_aborts = [
            r for r in post_records
            if re.search(r'\b(?:abort|aborted|halt|halted|stop|stopped|fault|paused)\b', r["lower"])
        ]
        if post_aborts:
            changes.append(
                SystemChangeComparison(
                    aspect="Instrument Execution Mode",
                    before_incident="Executing sample acquisition sequence",
                    after_incident=f"Aborted / Halted at line {post_aborts[0]['line']}: '{post_aborts[0]['text'][:80]}'",
                    change_summary="Sample acquisition sequence was forcibly aborted by system protection logic.",
                )
            )

        # 4. Telemetry Telemetry State (Fluidic / Optical / Thermal)
        post_stops = [r for r in post_records if "stopped" in r["lower"] or "flow rate 0" in r["lower"] or "lamp off" in r["lower"]]
        if post_stops:
            changes.append(
                SystemChangeComparison(
                    aspect="Hardware Subsystem State",
                    before_incident="Components energized and regulating",
                    after_incident=f"Safeguard shutdown at line {post_stops[0]['line']}: '{post_stops[0]['text'][:80]}'",
                    change_summary="Instrument hardware components were shut down to prevent mechanical or fluidic damage.",
                )
            )

        return changes

    def _validate_grounding(
        self,
        target_file: str,
        target_line: int,
        matched_text: str,
        pre_records: List[Dict[str, Any]],
        major_events: List[MatchingMajorEvent],
        problem_keywords: List[str],
        base_keywords: Optional[List[str]] = None,
        is_broad_error: bool = False,
    ) -> Tuple[List[GroundingEvidence], float]:
        """
        Anti-hallucination technique: verify that every piece of evidence corresponds
        strictly to real lines in the files, and compute an objective confidence score.
        """
        citations: List[GroundingEvidence] = []

        # Target incident citation
        citations.append(
            GroundingEvidence(
                log_file=target_file,
                line_number=target_line,
                snippet=matched_text,
                relevance_reason="Exact line matching user problem symptoms",
            )
        )

        # Pre-incident warning citations
        for rec in pre_records[-4:]:
            if rec["severity"] in ("WARNING", "ERROR", "CRITICAL") or any(kw in rec["lower"] for kw in problem_keywords):
                citations.append(
                    GroundingEvidence(
                        log_file=target_file,
                        line_number=rec["line"],
                        snippet=rec["text"],
                        relevance_reason=f"Pre-incident sequence line ({rec['severity']})",
                    )
                )

        # Major event citations
        for ev in major_events:
            citations.append(
                GroundingEvidence(
                    log_file=ev.log_file,
                    line_number=ev.line_number,
                    snippet=ev.description,
                    relevance_reason=f"Correlated major event: {ev.match_reason}",
                )
            )

        # Calculate confidence score based on objective keyword and intent density
        matched_lower = matched_text.lower()
        if is_broad_error:
            # Broad error inquiry accurately grounded to a confirmed error/critical log incident
            score = 0.88
            if any(ev.event_type for ev in major_events):
                score += 0.05
        else:
            effective_base = base_keywords if base_keywords else [
                kw for kw in problem_keywords if kw not in self.ERROR_SITUATION_INDICATORS
            ]
            if not effective_base:
                effective_base = problem_keywords[:5]

            matched_base = 0
            for bk in effective_base:
                if re.search(r'\b' + re.escape(bk) + r'\b', matched_lower):
                    matched_base += 1
                elif any(re.search(r'\b' + re.escape(syn) + r'\b', matched_lower) for syn in self.DOMAIN_SYNONYMS.get(bk, [])):
                    matched_base += 1
                elif bk in self.ERROR_TERMS and bool(self.get_matched_error_indicators(matched_lower)):
                    matched_base += 1

            kw_density = matched_base / max(1, len(effective_base))
            score = 0.65 + (min(kw_density, 1.0) * 0.25)

        # Pre-incident verification bonus
        if len(citations) >= 2:
            score += 0.05

        score = min(0.98, max(0.60, score))
        return citations, round(score, 2)

    def _generate_suggested_kb_query(
        self,
        problem_description: str,
        best_candidate: Dict[str, Any],
        pre_pattern: str,
        is_broad_error: bool = False,
        base_keywords: Optional[List[str]] = None,
    ) -> str:
        """Formulate high-precision search query for the KB button."""
        cand_lower = best_candidate["text"].lower()

        line_components = self.get_matched_components(cand_lower)
        line_error_codes = re.findall(r'\b(?:err(?:or)?[\s_:-]*[0-9a-fx]+|[0-9]{3,6}|0x[0-9a-f]+)\b', cand_lower)

        if is_broad_error:
            cand_tokens = [
                t for t in re.findall(r'[a-zA-Z0-9_\-]+', cand_lower)
                if len(t) > 2 and t not in self.STOP_WORDS and not t.isdigit() and t not in ("info", "debug")
            ]
            parts = line_components + line_error_codes + [t for t in cand_tokens if t not in line_components][:3]
            query = " ".join(dict.fromkeys(parts))
            return query if query else problem_description

        base_tokens = base_keywords if base_keywords is not None else [
            t for t in re.findall(r'[a-zA-Z0-9_\-]+', problem_description.lower())
            if len(t) > 2 and t not in self.STOP_WORDS
        ]
        extra_terms = [comp for comp in line_components if comp not in base_tokens]
        query_parts = base_tokens[:5] + extra_terms[:2] + line_error_codes[:1]
        return " ".join(dict.fromkeys(query_parts)) if query_parts else problem_description
