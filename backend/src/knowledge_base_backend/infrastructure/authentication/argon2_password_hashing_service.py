import bcrypt
from src.knowledge_base_backend.domain.services.password_hashing_service import PasswordHashingService

class Argon2PasswordHashingService(PasswordHashingService):
    def hash_password(self, password: str) -> str:
        pwd_bytes = password.encode('utf-8')[:72]
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        try:
            pwd_bytes = plain_password.encode('utf-8')[:72]
            return bcrypt.checkpw(pwd_bytes, hashed_password.encode('utf-8'))
        except Exception:
            return False
