from dataclasses import dataclass
from typing import Optional
from src.knowledge_base_backend.domain.entities.user_account import UserAccount

@dataclass
class AuthenticationResult:
    token: str
    user: UserAccount

@dataclass
class ForgotPasswordResult:
    username: str
    reset_token: str
    expires_in_minutes: int
    message: str

@dataclass
class ResetPasswordResult:
    username: str
    success: bool
    message: str

@dataclass
class VerifyResetTokenResult:
    username: str
    valid: bool
    expires_at: Optional[int]
    message: str
