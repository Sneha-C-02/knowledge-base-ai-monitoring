import asyncio
import time
from collections import deque
import httpx
from src.knowledge_base_backend.domain.services.grounded_answer_generation_service import GroundedAnswerGenerationService, GeneratedSupportAnswer

class GroqAnswerGenerationService(GroundedAnswerGenerationService):
    def __init__(self, api_key: str, model_name: str, timeout: int, calls_per_minute: int) -> None:
        self.api_key = api_key
        self.model_name = model_name or "llama3-8b-8192"
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        self.calls_per_minute = calls_per_minute
        
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

    async def generate_grounded_support_answer(self, query: str, context: str) -> GeneratedSupportAnswer:
        await self._wait_for_rate_limit()
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        system_prompt = (
            "You are a highly knowledgeable support assistant for a laboratory equipment company. "
            "Use the provided context to answer the user's question accurately. "
            "Even if the context is just a parts list or incomplete, synthesize a helpful response summarizing what is there. "
            "You MUST respond in JSON format with exactly two keys: 'answer' and 'related_article_number'. "
            "If you use information from a specific article in the context, you MUST put its exact Article Number (e.g. 'WKB114299' or '205002305') in the 'related_article_number' field as a string. Otherwise, set it to null."
        )
        
        user_prompt = f"Context:\n{context}\n\nQuestion:\n{query}"
        
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.2
        }
        
        response = await self.client.post(url, headers=headers, json=payload)
        if response.status_code >= 400: import sys; sys.stderr.write('GROQ ERROR: ' + response.text + '\n'); sys.stderr.flush()
        response.raise_for_status()
        
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        import json
        import re
        
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        content = re.sub(r'^`json\s*', '', content, flags=re.IGNORECASE)
        content = re.sub(r'^`\s*', '', content)
        content = re.sub(r'\s*`$', '', content)
        
        try:
            parsed_content = json.loads(content)
            answer = parsed_content.get("answer", content)
            raw_article_number = parsed_content.get("related_article_number")
            related_article_number = str(raw_article_number) if raw_article_number is not None and str(raw_article_number).lower() != "null" else None
        except json.JSONDecodeError:
            print(f"Failed to parse model output: {content}")
            answer = "Unable to generate a grounded response from the available knowledge due to a parsing error."
            related_article_number = None
        
        return GeneratedSupportAnswer(
            answer=answer,
            related_article_number=related_article_number,
            related_article_url=None,
            confidence_score=0.9
        )
