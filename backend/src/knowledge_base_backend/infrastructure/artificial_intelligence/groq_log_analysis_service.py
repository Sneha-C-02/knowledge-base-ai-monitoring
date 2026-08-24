import asyncio
import time
from collections import deque
import httpx
import json
import uuid
from typing import List, Tuple

from src.knowledge_base_backend.domain.services.log_analysis_service import LogAnalysisService
from src.knowledge_base_backend.domain.services.log_content_parser import LogContentParser
from src.knowledge_base_backend.domain.entities.monitoring_issue import MonitoringIssue
from src.knowledge_base_backend.domain.entities.monitoring_event import MonitoringEvent
from src.knowledge_base_backend.domain.services.date_time_provider import DateTimeProvider
from src.knowledge_base_backend.domain.services.hybrid_article_retrieval_service import HybridArticleRetrievalService

class GroqLogAnalysisService(LogAnalysisService):
    def __init__(
        self, 
        api_key: str, 
        model_name: str, 
        timeout: int, 
        calls_per_minute: int,
        parser: LogContentParser, 
        date_time_provider: DateTimeProvider,
        retrieval_service: HybridArticleRetrievalService
    ) -> None:
        self.api_key = api_key
        self.model_name = model_name or "llama3-8b-8192"
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        self.calls_per_minute = calls_per_minute
        self.parser = parser
        self.date_time_provider = date_time_provider
        self.retrieval_service = retrieval_service
        
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

    async def analyze_log_file_contents(
        self, file_path: str, monitoring_run_id: int
    ) -> Tuple[List[MonitoringIssue], List[MonitoringEvent], str]:
        events_data = await self.parser.parse(file_path)
        
        issues = []
        events = []
        overall_status = "OK"
        current_time = self.date_time_provider.get_current_utc_time()
        
        # Keep track of events
        for data in events_data:
            msg = data.get("message", "")
            lvl = data.get("level", "INFO")
            ev = MonitoringEvent(timestamp=current_time, level=lvl, message=msg)
            events.append(ev)
            
        # We will package the logs and ask AI to analyze
        # Limit to the last 100 log lines to avoid context window explosion
        log_lines_for_ai = [
            f"[{ev.level}] {ev.message}" for ev in events[-100:]
        ]
        logs_text = "\n".join(log_lines_for_ai)
        
        await self._wait_for_rate_limit()
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        system_prompt = (
            "You are an advanced AI diagnostics engineer analyzing machine log files. "
            "Your job is to thoroughly analyze the provided logs and identify any anomalies, failures, warnings, or unexpected behaviors. "
            "Perform HIGH-LEVEL MONITORING: detect both explicit errors (e.g. ERROR, WARNING, Connection Lost) AND hidden anomalies (e.g. process taking longer than usual, weird INFO logs). "
            "Return a JSON array of issues under the key 'issues'. "
            "For each issue, include exactly these fields: "
            "'severity' (WARNING or CRITICAL), 'pattern' (a short 3-5 word name of the issue), 'description' (detailed explanation of what happened), 'recommended_action' (actionable advice), and 'search_query' (a concise search string to query the knowledge base for this issue, e.g. 'Pressure error troubleshooting'). "
            "If the logs are perfectly normal, return an empty array for 'issues'. "
            "You MUST respond ONLY with a raw JSON object containing the 'issues' array. Do NOT wrap the JSON in markdown blocks (e.g. `json). Just the raw JSON."
        )
        
        user_prompt = f"Logs:\n{logs_text}"
        
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2,
            # "response_format": {"type": "json_object"}
        }
        
        try:
            response = await self.client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            
            # Remove <think> blocks if present (for reasoning models)
            if "<think>" in content and "</think>" in content:
                content = content.split("</think>")[-1].strip()
                
            if content.startswith("`json"):
                content = content[7:]
            elif content.startswith("`"):
                content = content[3:]
            if content.endswith("`"):
                content = content[:-3]
            content = content.strip()
            
            parsed_content = json.loads(content)
            ai_issues = parsed_content.get("issues", [])
            
            for ai_issue in ai_issues:
                severity = ai_issue.get("severity", "WARNING")
                if severity == "CRITICAL":
                    overall_status = "CRITICAL"
                elif overall_status != "CRITICAL":
                    overall_status = "WARNING"
                    
                search_query = ai_issue.get("search_query", "")
                related_article_number = None
                
                # Perform search if a search query was generated
                if search_query:
                    # Request top 1 article
                    retrieved_articles = await self.retrieval_service.retrieve_relevant_articles(search_query, None, 1)
                    if retrieved_articles:
                        related_article_number = retrieved_articles[0].article.article_number
                
                iss = MonitoringIssue(
                    id=0,
                    issue_identifier=f"ISS-{uuid.uuid4().hex[:8]}",
                    monitoring_run_id=monitoring_run_id,
                    severity=severity,
                    pattern=ai_issue.get("pattern", "Unknown Anomaly"),
                    description=ai_issue.get("description", "An anomaly was detected."),
                    recommended_action=ai_issue.get("recommended_action", "Investigate the logs."),
                    event_timestamp=current_time,
                    related_article_number=str(related_article_number) if related_article_number else None,
                    related_article_url=None
                )
                issues.append(iss)
                
        except Exception as e:
            with open('/tmp/ai_error.log', 'w') as f: f.write(str(e) + '\n' + (e.response.text if hasattr(e, 'response') else ''))
            # Fallback to rule-based logic if AI fails
            for ev in events:
                if ev.level == "ERROR":
                    overall_status = "CRITICAL"
                    iss = MonitoringIssue(
                        id=0,
                        issue_identifier=f"ISS-{uuid.uuid4().hex[:8]}",
                        monitoring_run_id=monitoring_run_id,
                        severity="CRITICAL",
                        pattern="Error Pattern Detected",
                        description=ev.message[:250],
                        recommended_action="Review log context and consult documentation.",
                        event_timestamp=current_time,
                        related_article_number=None,
                        related_article_url=None
                    )
                    issues.append(iss)
        
        return issues, events[:100], overall_status
