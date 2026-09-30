from jose import jwt, JWTError, ExpiredSignatureError
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from src.knowledge_base_backend.domain.services.authentication_token_service import AuthenticationTokenService
from src.knowledge_base_backend.configuration.application_settings import settings
from src.knowledge_base_backend.domain.exceptions.authentication_exceptions import (
    AuthenticationError,
    InvalidResetTokenError,
    ExpiredResetTokenError,
)

class JwtAuthenticationTokenService(AuthenticationTokenService):
    def create_access_token(self, subject: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expiration_minutes)
        to_encode = {"sub": subject, "purpose": "access", "exp": expire}
        encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_signing_algorithm)
        return encoded_jwt
        
    def validate_access_token(self, token: str) -> str:
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_signing_algorithm])
            if payload.get("purpose") and payload.get("purpose") != "access":
                raise AuthenticationError("Invalid token purpose: not an access token")
            subject = payload.get("sub")
            if subject is None:
                raise AuthenticationError("Token missing subject")
            return subject
        except ExpiredSignatureError:
            raise AuthenticationError("Access token has expired")
        except JWTError as e:
            raise AuthenticationError(f"Invalid token: {e}")

    def create_password_reset_token(
        self, subject: str, token_hash_salt: Optional[str] = None, expires_delta_minutes: Optional[int] = None
    ) -> str:
        if not subject or not subject.strip():
            raise ValueError("Subject is required for password reset token")
        minutes = expires_delta_minutes or settings.jwt_password_reset_token_expiration_minutes
        expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        to_encode = {
            "sub": subject.strip(),
            "purpose": "password_reset",
            "pwh": token_hash_salt or "",
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }
        encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_signing_algorithm)
        return encoded_jwt

    def validate_password_reset_token(self, token: str) -> Dict[str, Any]:
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_signing_algorithm])
            purpose = payload.get("purpose")
            if purpose != "password_reset":
                raise InvalidResetTokenError("Invalid token purpose: not a password reset token")
            subject = payload.get("sub")
            if not subject:
                raise InvalidResetTokenError("Token missing subject")
            pwh = payload.get("pwh")
            if not pwh:
                raise InvalidResetTokenError("Token missing security fingerprint")
            return payload
        except ExpiredSignatureError:
            raise ExpiredResetTokenError("Password reset token has expired")
        except JWTError as e:
            raise InvalidResetTokenError(f"Invalid password reset token: {e}")
