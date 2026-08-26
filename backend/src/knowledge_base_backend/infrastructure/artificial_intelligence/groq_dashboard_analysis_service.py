import asyncio
import time
from collections import deque
import httpx
import json
from typing import List, Optional

from src.knowledge_base_backend.domain.entities.instrument_memory_entry import InstrumentMemoryEntry
from src.knowledge_base_backend.domain.value_objects.log_dashboard_result import LogDashboardResult, DashboardSummaryBullet


class GroqDashboardAnalysisService:
    """
    AI-powered log analysis service that:
    1. Reads the COMPLETE log file on first add (initial context mapping)
    2. On re-upload, analyzes only NEW lines with stored context
    3. Incorporates historical instrument memory
    4. Returns a structured dashboard result matching the required format
    
    This service is designed as an independent module that can be
    replaced or extracted into its own microservice.
    """

    def __init__(
        self,
        api_key: str,
        model_name: str,
        timeout: int,
        calls_per_minute: int
    ) -> None:
        self.api_key = api_key
        self.model_name = model_name or "llama3-8b-8192"
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        self.calls_per_minute = calls_per_minute

        # Rate limiting state
        self._call_timestamps = deque()
        self._lock = asyncio.Lock()

    async def _wait_for_rate_limit(self) -> None:
        async with self._lock:
            now = time.time()
            while self._call_timestamps and self._call_timestamps[0] <= now - 60:
                self._call_timestamps.popleft()

            if len(self._call_timestamps) >= self.calls_per_minute:
                oldest_call = self._call_timestamps[0]
                wait_time = 60 - (now - oldest_call)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)

            self._call_timestamps.append(time.time())

    def _build_memory_context(self, memory_entries: List[InstrumentMemoryEntry]) -> str:
        """Build a textual summary of past analyses for this instrument."""
        if not memory_entries:
            return "No previous analysis history available for this instrument."

        lines = ["=== INSTRUMENT ANALYSIS HISTORY (most recent first) ==="]
        for entry in memory_entries[:10]:  # Last 10 analyses
            lines.append(
                f"\n--- Analysis on {entry.analysis_timestamp.strftime('%Y-%m-%d %H:%M:%S')} "
                f"(File: {entry.log_filename}) ---\n"
                f"Critical: {entry.critical_incidents} | Warnings: {entry.warnings} | "
                f"Errors: {entry.errors} | Healthy: {entry.healthy_apps}\n"
                f"Summary: {entry.ai_summary}"
            )
        return "\n".join(lines)

    async def _call_groq(self, system_prompt: str, user_prompt: str) -> str:
        """Make a rate-limited call to the Groq API and return raw content."""
        await self._wait_for_rate_limit()

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

        response = await self.client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()

        # Clean up LLM output artifacts
        if "<think>" in content and "</think>" in content:
            content = content.split("</think>")[-1].strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()

    def _parse_dashboard_result(
        self, content: str, instrument_id: int, instrument_name: str
    ) -> LogDashboardResult:
        """Parse JSON content from Groq into a LogDashboardResult."""
        parsed = json.loads(content)

        bullets = []
        for b in parsed.get("daily_summary_bullets", []):
            if isinstance(b, dict):
                bullets.append(DashboardSummaryBullet(
                    text=b.get("text", ""),
                    severity=b.get("severity", "info")
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
        self, log_content: str, instrument_id: int, instrument_name: str, error: Exception
    ) -> LogDashboardResult:
        """Produce a basic keyword-counted result when AI fails."""
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
            files_analyzed=1
        )

    # =========================================================================
    # PRIMARY METHOD: Initial full-file analysis (first time a file is added)
    # =========================================================================
    async def analyze_full_log_with_memory(
        self,
        log_content: str,
        log_filename: str,
        instrument_id: int,
        instrument_name: str,
        memory_entries: List[InstrumentMemoryEntry]
    ) -> LogDashboardResult:
        """
        Analyze the COMPLETE log file content with instrument history context.
        Used when a file is first added for monitoring.
        """
        memory_context = self._build_memory_context(memory_entries)

        system_prompt = (
            "You are an advanced AI diagnostics engineer for laboratory instrument monitoring. "
            "You must analyze the COMPLETE log file provided and produce a monitoring dashboard summary.\n\n"
            "CRITICAL RULES:\n"
            "1. Read and consider EVERY line of the log file before making conclusions.\n"
            "2. Use the instrument's analysis history to detect TRENDS — are issues getting worse, "
            "improving, or recurring?\n"
            "3. Count and categorize all issues found.\n"
            "4. Generate concise, actionable daily summary bullet points.\n\n"
            "You MUST respond with ONLY a raw JSON object (no markdown, no explanation) with these exact keys:\n"
            "{\n"
            '  "critical_incidents": <integer count of CRITICAL severity issues>,\n'
            '  "warnings": <integer count of WARNING severity issues>,\n'
            '  "errors": <integer count of ERROR level log entries>,\n'
            '  "healthy_apps": <integer count of systems/components that appear healthy>,\n'
            '  "overall_status": "CRITICAL" or "WARNING" or "OK",\n'
            '  "daily_summary_bullets": [\n'
            '    {"text": "concise finding or trend", "severity": "critical" or "warning" or "info"},\n'
            '    ...\n'
            "  ]\n"
            "}\n\n"
            "The daily_summary_bullets should include:\n"
            "- Specific failure patterns and their frequency\n"
            "- Time ranges when issues occurred\n"
            "- Comparisons with historical data (improving/worsening trends)\n"
            "- Memory leak or resource exhaustion patterns\n"
            "- Recurring authentication or connection failures\n"
            "Keep each bullet point concise (under 80 characters)."
        )

        user_prompt = (
            f"INSTRUMENT: {instrument_name} (ID: {instrument_id})\n"
            f"LOG FILE: {log_filename}\n\n"
            f"{memory_context}\n\n"
            f"=== COMPLETE LOG FILE CONTENT ===\n"
            f"{log_content}\n"
            f"=== END OF LOG FILE ==="
        )

        try:
            content = await self._call_groq(system_prompt, user_prompt)
            return self._parse_dashboard_result(content, instrument_id, instrument_name)
        except Exception as e:
            return self._fallback_result(log_content, instrument_id, instrument_name, e)

    # =========================================================================
    # INCREMENTAL METHOD: Analyze only NEW lines with stored context
    # =========================================================================
    async def analyze_incremental_log(
        self,
        new_lines_content: str,
        stored_context_summary: str,
        log_filename: str,
        instrument_id: int,
        instrument_name: str,
        memory_entries: List[InstrumentMemoryEntry]
    ) -> LogDashboardResult:
        """
        Analyze only the NEW lines of a log file, using the stored AI context
        from previous analysis as background knowledge.
        Used when a previously-monitored file is re-uploaded with new content.
        """
        memory_context = self._build_memory_context(memory_entries)

        system_prompt = (
            "You are an advanced AI diagnostics engineer for laboratory instrument monitoring. "
            "You have PREVIOUSLY analyzed an earlier portion of this log file. "
            "Your previous understanding is provided as 'STORED CONTEXT'. "
            "Now you must analyze ONLY the NEW log lines that have been added since your last analysis.\n\n"
            "CRITICAL RULES:\n"
            "1. Use the STORED CONTEXT to understand what happened before these new lines.\n"
            "2. Analyze the NEW LINES in context — detect if previous issues are continuing, "
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
            '    {"text": "concise finding or trend", "severity": "critical" or "warning" or "info"},\n'
            '    ...\n'
            "  ]\n"
            "}\n\n"
            "The daily_summary_bullets should include:\n"
            "- Whether previous issues are continuing or resolved\n"
            "- New failure patterns in the recent lines\n"
            "- Trend comparisons with the stored context\n"
            "Keep each bullet point concise (under 80 characters)."
        )

        user_prompt = (
            f"INSTRUMENT: {instrument_name} (ID: {instrument_id})\n"
            f"LOG FILE: {log_filename}\n\n"
            f"{memory_context}\n\n"
            f"=== STORED CONTEXT (AI's understanding of previously analyzed content) ===\n"
            f"{stored_context_summary}\n"
            f"=== END STORED CONTEXT ===\n\n"
            f"=== NEW LOG LINES (analyze these) ===\n"
            f"{new_lines_content}\n"
            f"=== END OF NEW LINES ==="
        )

        try:
            content = await self._call_groq(system_prompt, user_prompt)
            return self._parse_dashboard_result(content, instrument_id, instrument_name)
        except Exception as e:
            return self._fallback_result(new_lines_content, instrument_id, instrument_name, e)

    # =========================================================================
    # CONTEXT SUMMARY: Generate a compressed summary for storage
    # =========================================================================
    async def generate_context_summary(
        self,
        log_content: str,
        existing_summary: Optional[str],
        log_filename: str,
        instrument_name: str
    ) -> str:
        """
        Generate a concise context summary of the log content for storage.
        If an existing summary is provided, this merges the new content into it.
        This summary is stored in monitored_log_files.full_context_summary
        and used as context for future incremental analyses.
        """
        if existing_summary:
            system_prompt = (
                "You are a log analysis assistant. You have a PREVIOUS SUMMARY of a log file's content. "
                "New lines have been added to the file. Produce an UPDATED SUMMARY that incorporates "
                "the new information while keeping the summary concise (max 500 words).\n\n"
                "The summary should capture:\n"
                "- Key error patterns and their frequencies\n"
                "- Time ranges of issues\n"
                "- System components mentioned and their health\n"
                "- Any recurring themes or escalating problems\n\n"
                "Respond with ONLY the updated summary text. No JSON, no markdown."
            )
            user_prompt = (
                f"INSTRUMENT: {instrument_name}\n"
                f"LOG FILE: {log_filename}\n\n"
                f"=== PREVIOUS SUMMARY ===\n{existing_summary}\n=== END PREVIOUS SUMMARY ===\n\n"
                f"=== NEW LOG CONTENT ===\n{log_content}\n=== END NEW CONTENT ==="
            )
        else:
            system_prompt = (
                "You are a log analysis assistant. Produce a concise SUMMARY of the entire log file "
                "content (max 500 words). This summary will be stored and used as context for future "
                "incremental analyses when new lines are added to the same file.\n\n"
                "The summary should capture:\n"
                "- Key error patterns and their frequencies\n"
                "- Time ranges of issues\n"
                "- System components mentioned and their health\n"
                "- Any recurring themes or escalating problems\n"
                "- Overall system status\n\n"
                "Respond with ONLY the summary text. No JSON, no markdown."
            )
            user_prompt = (
                f"INSTRUMENT: {instrument_name}\n"
                f"LOG FILE: {log_filename}\n\n"
                f"=== COMPLETE LOG FILE ===\n{log_content}\n=== END OF LOG FILE ==="
            )

        try:
            summary = await self._call_groq(system_prompt, user_prompt)
            return summary
        except Exception as e:
            # Fallback: generate a basic summary from keywords
            lines = log_content.split("\n")
            error_lines = [l for l in lines if "error" in l.lower()][:5]
            return (
                f"[Auto-generated fallback summary — AI call failed: {type(e).__name__}]\n"
                f"Total lines: {len(lines)}\n"
                f"Sample error lines:\n" + "\n".join(error_lines)
            )
