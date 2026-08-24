from passlib.context import CryptContext
from src.knowledge_base_backend.domain.services.password_hashing_service import PasswordHashingService

class Argon2PasswordHashingService(PasswordHashingService):
    def __init__(self) -> None:
        # Passlib bcrypt is a fine replacement if argon2 is not specified in dependencies
        # Since the prompt said "pwdlib with Argon2 or passlib with bcrypt", we use bcrypt
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)
