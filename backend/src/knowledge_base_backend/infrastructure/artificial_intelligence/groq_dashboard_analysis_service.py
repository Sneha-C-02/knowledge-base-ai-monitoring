import json
import httpx
import re
import asyncio
import time
import random
from collections import deque
from typing import List, Optional
from src.knowledge_base_backend.domain.value_objects.log_dashboard_result import (
    LogDashboardResult, DashboardSummaryBullet, DashboardFinding
)
from src.knowledge_base_backend.domain.entities.instrument_memory_entry import InstrumentMemoryEntry
from src.knowledge_base_backend.domain.services.log_chunker_service import LogChunkerService
from src.knowledge_base_backend.domain.services.log_selection_service import LogSelectionService, SelectedLogContent
from src.knowledge_base_backend.domain.repositories.ai_learning_feedback_repository import AiLearningFeedbackRepository


def robust_parse_json(content: str) -> dict:
    """
    Extracts and parses JSON object from LLM response text reliably.
    Handles markdown code blocks, reasoning traces (<think>),
    preceding/trailing conversational text, and trailing commas.
    """
    if not content or not content.strip():
        raise ValueError("Empty response content")

    text = content.strip()
    if "<think>" in text and "</think>" in text:
        text = text.split("</think>")[-1].strip()

    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except Exception:
            cleaned = re.sub(r',\s*([\}\]])', r'\1', json_str)
            return json.loads(cleaned)

    raise json.JSONDecodeError("No valid JSON object found in text", content, 0)


class GroqDashboardAnalysisService:
    def __init__(
        self,
        api_key: str,
        model_name: str = "groq/compound-mini",
        timeout: int = 60,
        calls_per_minute: int = 30,
        tokens_per_minute: int = 7000,
        max_analyzed_log_lines: int = 600,
        max_ai_chunks: int = 4,
        log_reduction_context_lines: int = 2,
        log_reduction_tail_lines: int = 100,
        feedback_repository: AiLearningFeedbackRepository = None
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout
        self.calls_per_minute = calls_per_minute
        self.tokens_per_minute = tokens_per_minute
        self.max_analyzed_log_lines = max_analyzed_log_lines
        self.max_ai_chunks = max_ai_chunks
        
        self.log_selection_service = LogSelectionService(
            max_lines=max_analyzed_log_lines,
            context_lines=log_reduction_context_lines,
            tail_lines=log_reduction_tail_lines
        )
        self.feedback_repository = feedback_repository

        self._call_timestamps = deque()
        self._token_timestamps = deque()
        self._rate_limit_lock = asyncio.Lock()
        self.client = httpx.AsyncClient(timeout=timeout)

    async def _wait_for_rate_limit(self, estimated_tokens: int = 0) -> None:
        """
        Sliding-window rate limiter checking both RPM (Requests Per Minute)
        and TPM (Tokens Per Minute). Sleeps cleanly if budget is exceeded.
        """
        while True:
            async with self._rate_limit_lock:
                now = time.time()
                cutoff = now - 60.0

                while self._call_timestamps and self._call_timestamps[0] < cutoff:
                    self._call_timestamps.popleft()
                while self._token_timestamps and self._token_timestamps[0][0] < cutoff:
                    self._token_timestamps.popleft()

                rpm_wait = 0.0
                if len(self._call_timestamps) >= self.calls_per_minute:
                    rpm_wait = 60.0 - (now - self._call_timestamps[0])

                tpm_wait = 0.0
                current_tokens = sum(t for _, t in self._token_timestamps)
                if current_tokens + estimated_tokens > self.tokens_per_minute:
                    tokens_to_free = (current_tokens + estimated_tokens) - self.tokens_per_minute
                    freed = 0
                    for ts, count in self._token_timestamps:
                        if count > 0:
                            freed += count
                            if freed >= tokens_to_free:
                                tpm_wait = 60.0 - (now - ts)
                                break
                    if tpm_wait <= 0:
                        tpm_wait = 1.0

                wait_time = max(rpm_wait, tpm_wait)

                if wait_time <= 0:
                    self._call_timestamps.append(time.time())
                    self._token_timestamps.append((time.time(), estimated_tokens))
                    return

            if wait_time > 0:
                await asyncio.sleep(wait_time + 0.1)

    def _refund_tokens(self, estimated_tokens: int) -> None:
        """Refund tokens if a request fails before consuming them."""
        self._token_timestamps.append((time.time(), -estimated_tokens))

    def _build_memory_context(self, memory_entries: List[InstrumentMemoryEntry]) -> str:
        if not memory_entries:
            return "No previous analysis history available for this instrument."

        lines = ["=== INSTRUMENT ANALYSIS HISTORY (most recent first) ==="]
        for entry in memory_entries[:10]:
            lines.append(
                f"\n--- Analysis on {entry.analysis_timestamp.strftime('%Y-%m-%d %H:%M:%S')} "
                f"(File: {entry.log_filename}) ---\n"
                f"Critical: {entry.critical_incidents} | Warnings: {entry.warnings} | "
                f"Errors: {entry.errors} | Healthy: {entry.healthy_apps}\n"
                f"Summary: {entry.ai_summary}"
            )
        return "\n".join(lines)

    async def _call_groq(self, system_prompt: str, user_prompt: str, estimated_tokens: int = 0) -> str:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.15
        }

        max_retries = 6
        attempt = 0
        
        while attempt < max_retries:
            attempt += 1
            await self._wait_for_rate_limit(estimated_tokens)

            try:
                response = await self.client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()
                return content

            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status in [429, 500, 502, 503, 504]:
                    self._refund_tokens(estimated_tokens)
                    if attempt >= max_retries:
                        raise e
                    
                    wait_time = 15.0 * attempt + random.uniform(0, 2)
                    try:
                        err_json = e.response.json()
                        msg = err_json.get("error", {}).get("message", "")
                        match = re.search(r'try again in ([0-9]+(?:\.[0-9]+)?)s', msg)
                        if match:
                            wait_time = float(match.group(1)) + 0.5
                    except Exception:
                        pass
                        
                    await asyncio.sleep(wait_time)
                else:
                    self._refund_tokens(estimated_tokens)
                    raise e
            except Exception as e:
                self._refund_tokens(estimated_tokens)
                raise e

    async def classify_keyword_findings(self, findings: List[dict]) -> List[dict]:
        """Classify explicit keyword matches by analyzing surrounding lines, identifying error type, problem summary, and KB search query."""
        if not findings:
            return []

        classifications: List[dict] = []
        fallback_pattern = re.compile(
            r"\b(error|fail(?:ed|ure|ing)?|fatal|critical|exception|timeout|disconnect(?:ed|ion)?)\b",
            re.IGNORECASE,
        )

        for start in range(0, len(findings), 15):
            batch = findings[start:start + 15]
            payload = [
                {
                    "index": index,
                    "keyword": item["keyword"],
                    "matched_text": item["matched_text"],
                    "context": item["context"],
                }
                for index, item in enumerate(batch)
            ]
            system_prompt = (
                "You are an expert diagnostic log analysis assistant for Waters analytical and laboratory instruments. "
                "You analyze keyword occurrences using their supplied surrounding context lines.\n"
                "For every item:\n"
                "1. Decide whether it represents an actual error or failure (is_error: true), or benign/normal operational text (is_error: false).\n"
                "2. State clearly WHAT THE ERROR IS (error_type, e.g. 'Low Mass Resolution Setting Write Failure', 'RioStatus Negative Error Code', 'Pump Pressure Transducer Timeout', 'Autosampler Missing Vial'). If not an error, use 'Informational / Benign Operation'.\n"
                "3. Summarize the problem concisely in 1-2 clear technical sentences explaining what happened based on the surrounding lines (problem_summary).\n"
                "4. Provide a focused search_query to locate the matching Knowledge Base article (e.g. 'EngineerServer Low Mass Resolution Setting failed write RioStatus').\n"
                "5. Provide practical next troubleshooting steps (recommended_action).\n"
                "6. Provide diagnostic rationale citing evidence from the surrounding lines (rationale).\n"
                "7. Provide a confidence_score between 0 and 100.\n"
                "Respond ONLY with valid JSON in this structure:\n"
                '{"matches":[{"index":0,"is_error":true,"error_type":"...","problem_summary":"...","search_query":"...","recommended_action":"...","rationale":"...","confidence_score":95}]}'
            )
            user_prompt = "EXPLICIT KEYWORD MATCHES WITH SURROUNDING CONTEXT:\n" + json.dumps(payload)
            try:
                response = await self._call_groq(
                    system_prompt, user_prompt, int((len(system_prompt) + len(user_prompt)) * 0.25) + 300
                )
                parsed = robust_parse_json(response)
                by_index = {item.get("index"): item for item in parsed.get("matches", []) if isinstance(item, dict)}
                for index, item in enumerate(batch):
                    answer = by_index.get(index, {})
                    is_err = bool(answer.get("is_error", False))
                    err_type = str(answer.get("error_type") or ("Detected Error / Failure" if is_err else "Informational / Benign Operation"))
                    prob_summary = str(answer.get("problem_summary") or answer.get("rationale") or ("An error was identified in the surrounding lines." if is_err else "Normal operational text."))
                    s_query = str(answer.get("search_query") or f"{item['keyword']} {item['matched_text']}")
                    rec_action = str(answer.get("recommended_action")) if answer.get("recommended_action") else None
                    classifications.append({
                        "is_error": is_err,
                        "error_type": err_type,
                        "problem_summary": prob_summary,
                        "search_query": s_query,
                        "recommended_action": rec_action,
                        "rationale": str(answer.get("rationale") or "AI classification analyzed the surrounding lines."),
                        "confidence_score": max(0, min(100, int(answer.get("confidence_score", 85 if is_err else 70)))),
                        "classification_source": "ai",
                    })
            except Exception:
                for item in batch:
                    lines = item.get("context", [])
                    text = "\n".join(lines)
                    matched_text = item.get("matched_text", "")
                    keyword = item.get("keyword", "")

                    target_line = ""
                    for line in lines:
                        if matched_text.lower() in line.lower() or keyword.lower() in line.lower():
                            target_line = line
                            break
                    if not target_line and lines:
                        target_line = lines[len(lines) // 2]

                    is_err = bool(fallback_pattern.search(text))
                    comp_match = re.search(r'(\[(?:EPC|System|Pump|Autosampler|Detector|MS)\]|\([A-Za-z0-9_]+\):)', target_line or text)
                    comp = comp_match.group(0).strip("[](): ") if comp_match else ""

                    if is_err:
                        cleaned_line = re.sub(r'^(?:[A-Za-z]{3}\s+[A-Za-z]{3}\s+\d+\s+[\d:]+(?:\s+[A-Z]+)?(?:\s+[A-Za-z\s]+)?:\s*)?', '', target_line).strip()
                        if comp and cleaned_line:
                            err_type = f"{comp}: {cleaned_line[:65]}"
                        elif cleaned_line:
                            err_type = cleaned_line[:75]
                        else:
                            err_type = f"{keyword.capitalize()} Error"
                        prob_summary = f"The log indicates a failure around line {item.get('line_number', '')}: '{cleaned_line or matched_text}'. Surrounding context reports an operational error."
                        s_query = f"{comp} {keyword} {cleaned_line[:40]}".strip()
                        rec_action = f"Check {comp or 'subsystem'} operational state and verify hardware registers/connections."
                        rationale = "Deterministic fallback: error-level wording was detected in the local context lines."
                        confidence = 75
                    else:
                        err_type = "Informational / Benign Operation"
                        prob_summary = f"Keyword '{keyword}' appears in standard configuration or normal status context."
                        s_query = f"{comp} {keyword}".strip()
                        rec_action = None
                        rationale = "Deterministic fallback: no error-level wording was found in the local context."
                        confidence = 65

                    classifications.append({
                        "is_error": is_err,
                        "error_type": err_type,
                        "problem_summary": prob_summary,
                        "search_query": s_query,
                        "recommended_action": rec_action,
                        "rationale": rationale,
                        "confidence_score": confidence,
                        "classification_source": "deterministic_fallback",
                    })
        return classifications

    def _parse_dashboard_result(
        self, content: str, instrument_id: int, instrument_name: str
    ) -> LogDashboardResult:
        parsed = robust_parse_json(content)

        bullets = []
        for b in parsed.get("daily_summary_bullets", []):
            if isinstance(b, dict):
                bullets.append(DashboardSummaryBullet(
                    text=b.get("text", ""),
                    severity=b.get("severity", "info"),
                    confidence_score=b.get("confidence_score"),
                    possible_root_causes=b.get("possible_root_causes"),
                    pattern_name=b.get("pattern_name")
                ))
            elif isinstance(b, str):
                bullets.append(DashboardSummaryBullet(text=b, severity="info"))

        return LogDashboardResult(
            instrument_id=instrument_id,
            instrument_name=instrument_name,
            critical_incidents=int(parsed.get("critical_incidents", 0)),
            warnings=int(parsed.get("warnings", 0)),
            errors=int(parsed.get("errors", 0)),
            healthy_apps=int(parsed.get("healthy_apps", 0)),
            daily_summary_bullets=bullets,
            overall_status=parsed.get("overall_status", "OK"),
            files_analyzed=1
        )

    def _fallback_result(
        self, log_content: str, instrument_id: int, instrument_name: str, error: Exception,
        original_line_count: Optional[int] = None, analyzed_line_count: Optional[int] = None, was_log_reduced: bool = False
    ) -> LogDashboardResult:
        error_count = log_content.lower().count("error")
        warn_count = log_content.lower().count("warn")
        critical_count = log_content.lower().count("critical") + log_content.lower().count("fatal")

        return LogDashboardResult(
            instrument_id=instrument_id,
            instrument_name=instrument_name,
            critical_incidents=critical_count,
            warnings=warn_count,
            errors=error_count,
            healthy_apps=0,
            daily_summary_bullets=[
                DashboardSummaryBullet(
                    text=f"AI analysis failed ({type(error).__name__}), showing keyword counts",
                    severity="warning"
                ),
                DashboardSummaryBullet(
                    text=f"Found {error_count} error mentions, {warn_count} warning mentions",
                    severity="info"
                )
            ],
            overall_status="CRITICAL" if critical_count > 0 else ("WARNING" if error_count > 0 else "OK"),
            files_analyzed=1,
            original_line_count=original_line_count,
            analyzed_line_count=analyzed_line_count,
            was_log_reduced=was_log_reduced
        )

    def _select_for_analysis(self, log_content: str, analysis_mode: str) -> SelectedLogContent:
        """Exhaustive mode deliberately keeps every line; fast mode retains focused sampling."""
        if analysis_mode == "exhaustive":
            line_count = len(log_content.split("\n")) if log_content else 0
            return SelectedLogContent(
                content=log_content,
                original_line_count=line_count,
                analyzed_line_count=line_count,
                was_reduced=False,
            )
        return self.log_selection_service.select_log_content(log_content)

    def _attach_complete_findings(
        self, result: LogDashboardResult, content: str, filename: str, analysis_mode: str
    ) -> LogDashboardResult:
        """Expose every deterministic error-level line that was visible to this analysis mode."""
        severe = re.compile(r"\b(fatal|critical|panic)\b", re.IGNORECASE)
        warning = re.compile(r"\b(warn|warning)\b", re.IGNORECASE)
        error = re.compile(
            r"\b(error|exception|fail(?:ed|ure|ing)?|timeout|disconnect(?:ed|ion)?|lost)\b",
            re.IGNORECASE,
        )
        findings = []
        for line_number, line in enumerate(content.splitlines(), start=1):
            severity = "critical" if severe.search(line) else ("error" if error.search(line) else None)
            if not severity and warning.search(line):
                severity = "warning"
            if severity:
                findings.append(DashboardFinding(
                    filename=filename,
                    line_number=line_number,
                    snippet=line[:1000],
                    severity=severity,
                    explanation="Detected severity wording in the analyzed log line.",
                    detected_by="rule",
                ))
        result.complete_findings = findings
        result.coverage_mode = analysis_mode
        return result

    async def analyze_log_chunk(
        self,
        chunk_content: str,
        chunk_id: int,
        instrument_id: int,
        instrument_name: str
    ) -> dict:
        system_prompt = (
            "You are an expert AI diagnostic engineer for Waters laboratory instruments (e.g. mass spectrometers). "
            "Analyze this log chunk for ALL anomalies, errors, and failures.\n\n"
            "CRITICAL: Flag ALL of the following as errors/incidents:\n"
            "- Any line containing 'RioStatus => -1' (hardware communication failure)\n"
            "- EngineerServer 'failed to write' any value\n"
            "- SetRioValue returning an error code\n"
            "- Resolution, voltage, or pressure settings that failed to apply\n"
            "- Any line with 'error', 'fail', 'FATAL', 'exception', 'timeout', 'lost', 'disconnect'\n"
            "- Repeated failed operations on the same setting (pattern of failure)\n\n"
            "Respond with ONLY a raw JSON object (no markdown, no explanation) with these keys:\n"
            "{\n"
            '  "chunk_id": <integer>,\n'
            '  "critical_incidents": <integer count of CRITICAL issues>,\n'
            '  "warnings": <integer count of WARNINGs>,\n'
            '  "errors": <integer count of ERRORs — include RioStatus -1, write failures etc>,\n'
            '  "patterns": ["string array of recurring issues, e.g. RioStatus=-1 on LOW_MASS_RESOLUTION_MS1"],\n'
            '  "important_events": ["string array of other notable events with timestamps if available"]\n'
            "}\n"
        )

        user_prompt = (
            f"INSTRUMENT: {instrument_name} (ID: {instrument_id})\n"
            f"CHUNK ID: {chunk_id}\n\n"
            f"=== CHUNK CONTENT ===\n{chunk_content}\n=== END CHUNK ==="
        )

        input_chars = len(chunk_content) + len(system_prompt) + len(user_prompt)
        estimated_tokens = int(input_chars * 0.25) + 300

        try:
            raw_result = await self._call_groq(system_prompt, user_prompt, estimated_tokens)
            parsed = robust_parse_json(raw_result)
            parsed["chunk_id"] = chunk_id
            parsed["is_fallback"] = False
            return parsed
        except Exception as e:
            error_count = chunk_content.lower().count("error")
            warn_count = chunk_content.lower().count("warn")
            critical_count = chunk_content.lower().count("critical") + chunk_content.lower().count("fatal")
            
            error_details = str(e)
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                error_details += " - " + e.response.text
            
            return {
                "chunk_id": chunk_id,
                "critical_incidents": critical_count,
                "warnings": warn_count,
                "errors": error_count,
                "patterns": [f"Chunk analysis failed: {type(e).__name__} - {error_details}"],
                "important_events": [],
                "is_fallback": True
            }

    async def synthesize_chunk_findings(
        self,
        chunk_results: List[dict],
        stored_context_summary: str,
        log_filename: str,
        instrument_id: int,
        instrument_name: str,
        memory_entries: List[InstrumentMemoryEntry]
    ) -> LogDashboardResult:
        # Exhaustive runs can contain thousands of chunks. Fold them in bounded batches
        # before the final synthesis so no log section is discarded or overflows context.
        if len(chunk_results) > self.max_ai_chunks:
            folded_results = []
            for offset in range(0, len(chunk_results), self.max_ai_chunks):
                batch_result = await self.synthesize_chunk_findings(
                    chunk_results=chunk_results[offset:offset + self.max_ai_chunks],
                    stored_context_summary=stored_context_summary,
                    log_filename=log_filename,
                    instrument_id=instrument_id,
                    instrument_name=instrument_name,
                    memory_entries=memory_entries,
                )
                folded_results.append({
                    "critical_incidents": batch_result.critical_incidents,
                    "warnings": batch_result.warnings,
                    "errors": batch_result.errors,
                    "patterns": [bullet.text for bullet in batch_result.daily_summary_bullets],
                    "important_events": [],
                    "is_fallback": batch_result.analysis_status != "FULL_AI_ANALYSIS",
                })
            return await self.synthesize_chunk_findings(
                chunk_results=folded_results,
                stored_context_summary=stored_context_summary,
                log_filename=log_filename,
                instrument_id=instrument_id,
                instrument_name=instrument_name,
                memory_entries=memory_entries,
            )

        memory_context = self._build_memory_context(memory_entries)
        
        feedback_context = ""
        if self.feedback_repository:
            # Note: Because this is an async operation inside a synchronous-looking function (wait, synthesize is async)
            recent_feedbacks = await self.feedback_repository.get_recent_successful_feedback(limit=10)
            if recent_feedbacks:
                feedback_lines = ["\nLEARNED PATTERNS FROM HUMAN FEEDBACK:"]
                for fb in recent_feedbacks:
                    feedback_lines.append(
                        f"- Pattern: {fb.pattern_number} | "
                        f"Actual Root Cause/Action taken by engineer: {fb.actual_action} | "
                        f"Notes: {fb.helpful_points or 'None'}"
                    )
                feedback_context = "\n".join(feedback_lines)

        system_prompt = (
            "You are an advanced AI diagnostics engineer. "
            "A large log file was split into chunks and analyzed individually. "
            "You are provided with the JSON findings from all chunks. "
            "You must synthesize these findings into a final global monitoring dashboard summary.\n\n"
            "CRITICAL RULES:\n"
            "1. Aggregate the total counts of errors, warnings, and critical incidents across all chunks.\n"
            "2. Identify global patterns that span multiple chunks.\n"
            "3. Reference historical 'STORED CONTEXT' to detect if issues are resolving or worsening.\n"
            "4. Do NOT recount issues if they appear to be duplicates spanning chunk boundaries, but generally trust the chunk counts.\n\n"
            "You MUST respond with ONLY a raw JSON object (no markdown, no explanation) with these exact keys:\n"
            "{\n"
            '  "critical_incidents": <total integer count>,\n'
            '  "warnings": <total integer count>,\n'
            '  "errors": <total integer count>,\n'
            '  "healthy_apps": <integer count of healthy components>,\n'
            '  "overall_status": "CRITICAL" or "WARNING" or "OK",\n'
            '  "daily_summary_bullets": [\n'
            '    {"text": "concise synthesized finding", "severity": "critical" or "warning" or "info", "confidence_score": <1-100 integer>, "possible_root_causes": ["reason 1", "reason 2"], "pattern_name": "short pattern name"},\n'
            '    ...\n'
            '  ]\n'
            "}\n"
            f"{feedback_context}"
        )

        chunks_json = json.dumps(chunk_results, indent=2)

        user_prompt = (
            f"INSTRUMENT: {instrument_name} (ID: {instrument_id})\n"
            f"LOG FILE: {log_filename}\n\n"
            f"{memory_context}\n\n"
            f"=== STORED CONTEXT ===\n{stored_context_summary}\n=== END STORED CONTEXT ===\n\n"
            f"=== CHUNK FINDINGS ===\n{chunks_json}\n=== END CHUNK FINDINGS ==="
        )

        input_chars = len(chunks_json) + len(system_prompt) + len(user_prompt)
        estimated_tokens = int(input_chars * 0.25) + 500

        try:
            content = await self._call_groq(system_prompt, user_prompt, estimated_tokens)
            return self._parse_dashboard_result(content, instrument_id, instrument_name)
        except Exception as e:
            total_critical = sum(c.get("critical_incidents", 0) for c in chunk_results)
            total_errors = sum(c.get("errors", 0) for c in chunk_results)
            total_warnings = sum(c.get("warnings", 0) for c in chunk_results)
            
            return LogDashboardResult(
                instrument_id=instrument_id,
                instrument_name=instrument_name,
                critical_incidents=total_critical,
                warnings=total_warnings,
                errors=total_errors,
                healthy_apps=0,
                daily_summary_bullets=[
                    DashboardSummaryBullet(
                        text=f"Global synthesis failed ({type(e).__name__}). Showing aggregated chunk counts.",
                        severity="warning"
                    )
                ],
                overall_status="CRITICAL" if total_critical > 0 else ("WARNING" if total_errors > 0 else "OK"),
                files_analyzed=1
            )

    async def analyze_full_log_with_memory(
        self,
        log_content: str,
        log_filename: str,
        instrument_id: int,
        instrument_name: str,
        memory_entries: List[InstrumentMemoryEntry],
        analysis_mode: str = "exhaustive"
    ) -> LogDashboardResult:
        selected = self._select_for_analysis(log_content, analysis_mode)
        content_to_analyze = selected.content

        input_chars = len(content_to_analyze)
        estimated_tokens = int(input_chars * 0.25) + 500
        
        if estimated_tokens > 7000 or selected.was_reduced:
            chunker = LogChunkerService()
            target_tokens = min(1500, max(800, estimated_tokens // self.max_ai_chunks + 1))
            chunks = chunker.chunk_log(content_to_analyze, target_tokens)
            
            if analysis_mode == "fast" and len(chunks) > self.max_ai_chunks:
                chunks = chunks[:self.max_ai_chunks]
            
            # Analyze chunks sequentially to guarantee accurate rate limit tracking without race conditions
            valid_results = []
            for idx, chunk_text in enumerate(chunks):
                res = await self.analyze_log_chunk(
                    chunk_content=chunk_text,
                    chunk_id=idx + 1,
                    instrument_id=instrument_id,
                    instrument_name=instrument_name
                )
                valid_results.append(res)
            
            total_chunks = len(chunks)
            failed_chunks = len(chunks) - len(valid_results)
            fallback_chunks = sum(1 for res in valid_results if res.get('is_fallback', False))
            successful_ai_chunks = len(valid_results) - fallback_chunks

            result = await self.synthesize_chunk_findings(
                chunk_results=valid_results,
                stored_context_summary="Initial upload (no previous context).",
                log_filename=log_filename,
                instrument_id=instrument_id,
                instrument_name=instrument_name,
                memory_entries=memory_entries
            )
            synthesis_success = 'failed' not in str(result.daily_summary_bullets[0].text).lower() if result.daily_summary_bullets else False
            
            if synthesis_success and fallback_chunks == 0 and failed_chunks == 0:
                final_status = 'FULL_AI_ANALYSIS'
            elif successful_ai_chunks > 0:
                final_status = 'PARTIAL_AI_ANALYSIS'
            elif fallback_chunks > 0:
                final_status = 'DETERMINISTIC_FALLBACK'
            else:
                final_status = 'AI_ANALYSIS_FAILED'
                
            result.analysis_status = final_status
            result.total_chunks = total_chunks
            result.successful_ai_chunks = successful_ai_chunks
            result.fallback_chunks = fallback_chunks
            result.failed_chunks = failed_chunks
            result.original_line_count = selected.original_line_count
            result.analyzed_line_count = selected.analyzed_line_count
            result.was_log_reduced = selected.was_reduced
            return self._attach_complete_findings(result, content_to_analyze, log_filename, analysis_mode)

        memory_context = self._build_memory_context(memory_entries)

        system_prompt = (
            "You are an advanced AI diagnostics engineer for laboratory instrument monitoring. "
            "Analyze the entire uploaded log file in the context of the instrument's historical memory. "
            "Extract critical incidents, warnings, errors, and healthy sub-systems. "
            "Generate concise, actionable daily summary bullet points for the operations dashboard.\n\n"
            "CRITICAL RULES:\n"
            "1. Count ALL issues in the log file accurately.\n"
            "2. Cross-reference with historical memory: detect recurring issues, worsening trends, or resolved problems.\n"
            "3. If previous analysis showed the same error, note it as RECURRING in the summary bullets.\n"
            "4. Output MUST be ONLY valid JSON matching the exact schema below, with NO extra text or markdown formatting.\n\n"
            "You MUST respond with ONLY a raw JSON object (no markdown, no explanation) with these exact keys:\n"
            "{\n"
            '  "critical_incidents": <integer count of CRITICAL / FATAL severity issues>,\n'
            '  "warnings": <integer count of WARNING severity issues>,\n'
            '  "errors": <integer count of ERROR level entries>,\n'
            '  "healthy_apps": <integer count of systems/components that appear healthy>,\n'
            '  "overall_status": "CRITICAL" or "WARNING" or "OK",\n'
            '  "daily_summary_bullets": [\n'
            '    {"text": "concise finding or trend", "severity": "critical" or "warning" or "info"},\n'
            '    ...\n'
            '  ]\n'
            "}\n"
        )

        user_prompt = (
            f"INSTRUMENT: {instrument_name} (ID: {instrument_id})\n"
            f"LOG FILE: {log_filename}\n\n"
            f"{memory_context}\n\n"
            f"=== COMPLETE LOG FILE CONTENT ===\n{content_to_analyze}\n=== END OF LOG FILE ==="
        )

        call_tokens = int((len(system_prompt) + len(user_prompt)) * 0.25) + 500

        try:
            content = await self._call_groq(system_prompt, user_prompt, call_tokens)
            result = self._parse_dashboard_result(content, instrument_id, instrument_name)
            result.analysis_status = "FULL_AI_ANALYSIS"
            result.total_chunks = 1
            result.successful_ai_chunks = 1
            result.fallback_chunks = 0
            result.failed_chunks = 0
            result.original_line_count = selected.original_line_count
            result.analyzed_line_count = selected.analyzed_line_count
            result.was_log_reduced = selected.was_reduced
            return self._attach_complete_findings(result, content_to_analyze, log_filename, analysis_mode)
        except Exception as e:
            res = self._fallback_result(content_to_analyze, instrument_id, instrument_name, e)
            res.analysis_status = "AI_ANALYSIS_FAILED"
            res.total_chunks = 1
            res.successful_ai_chunks = 0
            res.fallback_chunks = 1
            res.failed_chunks = 0
            res.original_line_count = selected.original_line_count
            res.analyzed_line_count = selected.analyzed_line_count
            res.was_log_reduced = selected.was_reduced
            return self._attach_complete_findings(res, content_to_analyze, log_filename, analysis_mode)

    async def analyze_incremental_log(
        self,
        new_lines_content: str,
        stored_context_summary: str,
        log_filename: str,
        instrument_id: int,
        instrument_name: str,
        memory_entries: List[InstrumentMemoryEntry],
        analysis_mode: str = "exhaustive"
    ) -> LogDashboardResult:
        selected = self._select_for_analysis(new_lines_content, analysis_mode)
        content_to_analyze = selected.content

        input_chars = len(content_to_analyze)
        estimated_tokens = int(input_chars * 0.25) + 500
        
        if estimated_tokens > 7000 or selected.was_reduced:
            chunker = LogChunkerService()
            target_tokens = min(1500, max(800, estimated_tokens // self.max_ai_chunks + 1))
            chunks = chunker.chunk_log(content_to_analyze, target_tokens)
            
            if analysis_mode == "fast" and len(chunks) > self.max_ai_chunks:
                chunks = chunks[:self.max_ai_chunks]
            
            # Analyze chunks sequentially to guarantee accurate rate limit tracking without race conditions
            valid_results = []
            for idx, chunk_text in enumerate(chunks):
                res = await self.analyze_log_chunk(
                    chunk_content=chunk_text,
                    chunk_id=idx + 1,
                    instrument_id=instrument_id,
                    instrument_name=instrument_name
                )
                valid_results.append(res)
                
            total_chunks = len(chunks)
            failed_chunks = len(chunks) - len(valid_results)
            fallback_chunks = sum(1 for res in valid_results if res.get('is_fallback', False))
            successful_ai_chunks = len(valid_results) - fallback_chunks

            result = await self.synthesize_chunk_findings(
                chunk_results=valid_results,
                stored_context_summary=stored_context_summary,
                log_filename=log_filename,
                instrument_id=instrument_id,
                instrument_name=instrument_name,
                memory_entries=memory_entries
            )
            synthesis_success = 'failed' not in str(result.daily_summary_bullets[0].text).lower() if result.daily_summary_bullets else False
            
            if synthesis_success and fallback_chunks == 0 and failed_chunks == 0:
                final_status = 'FULL_AI_ANALYSIS'
            elif successful_ai_chunks > 0:
                final_status = 'PARTIAL_AI_ANALYSIS'
            elif fallback_chunks > 0:
                final_status = 'DETERMINISTIC_FALLBACK'
            else:
                final_status = 'AI_ANALYSIS_FAILED'
                
            result.analysis_status = final_status
            result.total_chunks = total_chunks
            result.successful_ai_chunks = successful_ai_chunks
            result.fallback_chunks = fallback_chunks
            result.failed_chunks = failed_chunks
            result.original_line_count = selected.original_line_count
            result.analyzed_line_count = selected.analyzed_line_count
            result.was_log_reduced = selected.was_reduced
            return self._attach_complete_findings(result, content_to_analyze, log_filename, analysis_mode)

        memory_context = self._build_memory_context(memory_entries)

        system_prompt = (
            "You are an advanced AI diagnostics engineer for laboratory instrument monitoring. "
            "You have PREVIOUSLY analyzed an earlier portion of this log file. "
            "Your previous understanding is provided as 'STORED CONTEXT'. "
            "Now you must analyze ONLY the NEW log lines that have been added since your last analysis.\n\n"
            "CRITICAL RULES:\n"
            "1. Use the STORED CONTEXT to understand what happened before these new lines.\n"
            "2. Analyze the NEW LINES in context - detect if previous issues are continuing, "
            "resolving, or if new issues are appearing.\n"
            "3. Count issues ONLY from the new lines, but reference the stored context for trends.\n"
            "4. Generate concise, actionable daily summary bullet points.\n\n"
            "You MUST respond with ONLY a raw JSON object (no markdown, no explanation) with these exact keys:\n"
            "{\n"
            '  "critical_incidents": <integer count of CRITICAL severity issues in NEW lines>,\n'
            '  "warnings": <integer count of WARNING severity issues in NEW lines>,\n'
            '  "errors": <integer count of ERROR level entries in NEW lines>,\n'
            '  "healthy_apps": <integer count of systems/components that appear healthy>,\n'
            '  "overall_status": "CRITICAL" or "WARNING" or "OK",\n'
            '  "daily_summary_bullets": [\n'
            '    {"text": "concise finding or trend", "severity": "critical" or "warning" or "info"}\n'
            '  ]\n'
            "}\n"
        )

        user_prompt = (
            f"INSTRUMENT: {instrument_name} (ID: {instrument_id})\n"
            f"LOG FILE: {log_filename}\n\n"
            f"{memory_context}\n\n"
            f"=== STORED CONTEXT ===\n{stored_context_summary}\n=== END STORED CONTEXT ===\n\n"
            f"=== NEW LOG LINES ===\n{content_to_analyze}\n=== END OF NEW LINES ==="
        )

        call_tokens = int((len(system_prompt) + len(user_prompt)) * 0.25) + 500

        try:
            content = await self._call_groq(system_prompt, user_prompt, call_tokens)
            result = self._parse_dashboard_result(content, instrument_id, instrument_name)
            result.analysis_status = "FULL_AI_ANALYSIS"
            result.total_chunks = 1
            result.successful_ai_chunks = 1
            result.fallback_chunks = 0
            result.failed_chunks = 0
            result.original_line_count = selected.original_line_count
            result.analyzed_line_count = selected.analyzed_line_count
            result.was_log_reduced = selected.was_reduced
            return self._attach_complete_findings(result, content_to_analyze, log_filename, analysis_mode)
        except Exception as e:
            res = self._fallback_result(content_to_analyze, instrument_id, instrument_name, e)
            res.analysis_status = "AI_ANALYSIS_FAILED"
            res.total_chunks = 1
            res.successful_ai_chunks = 0
            res.fallback_chunks = 1
            res.failed_chunks = 0
            res.original_line_count = selected.original_line_count
            res.analyzed_line_count = selected.analyzed_line_count
            res.was_log_reduced = selected.was_reduced
            return self._attach_complete_findings(res, content_to_analyze, log_filename, analysis_mode)

    async def generate_context_summary(
        self,
        log_content: str,
        existing_summary: Optional[str],
        log_filename: str = '', 
        instrument_name: str = '', 
        **kwargs
    ) -> str:
        selected = self.log_selection_service.select_log_content(log_content)
        content_to_summarize = selected.content

        if existing_summary:
            system_prompt = (
                "You are a log analysis assistant. You have a PREVIOUS SUMMARY of a log file's content. "
                "New lines have been added to the file. Produce an UPDATED SUMMARY that incorporates "
                "the new information while keeping the summary concise (max 500 words)."
            )
            user_prompt = (
                f"INSTRUMENT: {instrument_name}\n"
                f"LOG FILE: {log_filename}\n\n"
                f"=== PREVIOUS SUMMARY ===\n{existing_summary}\n=== END PREVIOUS SUMMARY ===\n\n"
                f"=== NEW LOG CONTENT ===\n{content_to_summarize}\n=== END NEW CONTENT ==="
            )
        else:
            system_prompt = (
                "You are a log analysis assistant. Produce a concise SUMMARY of the entire log file "
                "content (max 500 words). This summary will be stored and used as context for future "
                "incremental analyses."
            )
            user_prompt = (
                f"INSTRUMENT: {instrument_name}\n"
                f"LOG FILE: {log_filename}\n\n"
                f"=== COMPLETE LOG FILE ===\n{content_to_summarize}\n=== END OF LOG FILE ==="
            )

        call_tokens = int((len(system_prompt) + len(user_prompt)) * 0.25) + 500

        try:
            summary = await self._call_groq(system_prompt, user_prompt, call_tokens)
            return summary
        except Exception as e:
            lines = content_to_summarize.split("\n")
            error_lines = [l for l in lines if "error" in l.lower()][:5]
            return (
                f"[Auto-generated fallback summary - AI call failed: {type(e).__name__}]\n"
                f"Total lines: {len(lines)}\n"
                f"Sample error lines:\n" + "\n".join(error_lines)
            )
