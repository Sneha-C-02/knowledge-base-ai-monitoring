import asyncio
import time
from collections import deque
import httpx
from src.knowledge_base_backend.domain.services.grounded_answer_generation_service import GroundedAnswerGenerationService, GeneratedSupportAnswer

class GroqAnswerGenerationService(GroundedAnswerGenerationService):
    def __init__(self, api_key: str, model_name: str, timeout: int, calls_per_minute: int) -> None:
        self.api_key = api_key
        # Default to a lightweight/low-level model if none provided
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
            # Remove timestamps older than 60 seconds
            while self._call_timestamps and self._call_timestamps[0] <= now - 60:
                self._call_timestamps.popleft()
                
            if len(self._call_timestamps) >= self.calls_per_minute:
                # Need to wait until the oldest call is older than 60 seconds
                oldest_call = self._call_timestamps[0]
                wait_time = 60 - (now - oldest_call)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
            
            # Record this call
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
            "If the answer is not in the context, state that clearly."
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
        response.raise_for_status()
        
        data = response.json()
        answer = data["choices"][0]["message"]["content"]
        
        return GeneratedSupportAnswer(
            answer=answer,
            related_article_number=None,
            related_article_url=None,
            confidence_score=0.9
        )
