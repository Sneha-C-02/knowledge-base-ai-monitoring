from fastapi.security import HTTPBearer
from fastapi import Request
from typing import Optional

class CustomHTTPBearer(HTTPBearer):
    async def __call__(self, request: Request):
        return await super().__call__(request)

bearer_scheme = CustomHTTPBearer(auto_error=False)
