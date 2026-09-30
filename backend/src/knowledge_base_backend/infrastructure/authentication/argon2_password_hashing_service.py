from typing import Optional
from src.knowledge_base_backend.domain.services.password_hashing_service import PasswordHashingService

try:
    import bcrypt
    _USE_NATIVE_BCRYPT = True
except ImportError:
    _USE_NATIVE_BCRYPT = False

class Argon2PasswordHashingService(PasswordHashingService):
    def __init__(self) -> None:
        if not _USE_NATIVE_BCRYPT:
            from passlib.context import CryptContext
            self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        else:
            self.pwd_context = None

    def hash_password(self, password: str) -> str:
        if _USE_NATIVE_BCRYPT:
            pw_bytes = password.encode("utf-8")[:72]
            return bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode("utf-8")
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        if _USE_NATIVE_BCRYPT:
            try:
                pw_bytes = plain_password.encode("utf-8")[:72]
                hash_bytes = hashed_password.encode("utf-8")
                return bcrypt.checkpw(pw_bytes, hash_bytes)
            except Exception:
                return False
        return self.pwd_context.verify(plain_password, hashed_password)
