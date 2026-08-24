from jose import jwt
from datetime import datetime, timedelta, timezone
from src.knowledge_base_backend.domain.services.authentication_token_service import AuthenticationTokenService
from src.knowledge_base_backend.configuration.application_settings import settings
from src.knowledge_base_backend.domain.exceptions.authentication_exceptions import AuthenticationError

class JwtAuthenticationTokenService(AuthenticationTokenService):
    def create_access_token(self, subject: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expiration_minutes)
        to_encode = {"sub": subject, "exp": expire}
        encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_signing_algorithm)
        return encoded_jwt
        
    def validate_access_token(self, token: str) -> str:
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_signing_algorithm])
            subject = payload.get("sub")
            if subject is None:
                raise AuthenticationError("Token missing subject")
            return subject
        except jwt.JWTError as e:
            raise AuthenticationError(f"Invalid token: {e}")
