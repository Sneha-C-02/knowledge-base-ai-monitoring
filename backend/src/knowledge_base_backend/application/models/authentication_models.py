from dataclasses import dataclass
from src.knowledge_base_backend.domain.entities.user_account import UserAccount

@dataclass
class AuthenticationResult:
    token: str
    user: UserAccount
