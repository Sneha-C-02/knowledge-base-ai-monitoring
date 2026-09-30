import pytest
from datetime import datetime, timezone, timedelta
from jose import jwt
from src.knowledge_base_backend.infrastructure.authentication.jwt_authentication_token_service import (
    JwtAuthenticationTokenService,
)
from src.knowledge_base_backend.configuration.application_settings import settings
from src.knowledge_base_backend.domain.exceptions.authentication_exceptions import (
    AuthenticationError,
    InvalidResetTokenError,
    ExpiredResetTokenError,
)

@pytest.fixture
def token_service():
    return JwtAuthenticationTokenService()

def test_create_and_validate_access_token(token_service):
    token = token_service.create_access_token("testuser")
    subject = token_service.validate_access_token(token)
    assert subject == "testuser"

def test_access_token_cannot_be_used_as_password_reset_token(token_service):
    access_token = token_service.create_access_token("testuser")
    with pytest.raises(InvalidResetTokenError, match="not a password reset token"):
        token_service.validate_password_reset_token(access_token)

def test_create_and_validate_password_reset_token(token_service):
    token = token_service.create_password_reset_token(
        subject="testuser",
        token_hash_salt="abc12345",
        expires_delta_minutes=15,
    )
    payload = token_service.validate_password_reset_token(token)
    assert payload["sub"] == "testuser"
    assert payload["purpose"] == "password_reset"
    assert payload["pwh"] == "abc12345"

def test_password_reset_token_cannot_be_used_as_access_token(token_service):
    reset_token = token_service.create_password_reset_token(
        subject="testuser",
        token_hash_salt="abc12345",
    )
    with pytest.raises(AuthenticationError, match="not an access token"):
        token_service.validate_access_token(reset_token)

def test_expired_password_reset_token_raises_expired_error(token_service):
    expired_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    to_encode = {
        "sub": "testuser",
        "purpose": "password_reset",
        "pwh": "abc",
        "exp": expired_time,
    }
    expired_token = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_signing_algorithm)
    with pytest.raises(ExpiredResetTokenError):
        token_service.validate_password_reset_token(expired_token)

def test_tampered_password_reset_token_raises_invalid_error(token_service):
    token = token_service.create_password_reset_token("testuser", token_hash_salt="salt123")
    tampered_token = token + "xyz"
    with pytest.raises(InvalidResetTokenError):
        token_service.validate_password_reset_token(tampered_token)

def test_reset_token_missing_subject_raises_invalid_error(token_service):
    to_encode = {
        "purpose": "password_reset",
        "pwh": "salt123",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    token = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_signing_algorithm)
    with pytest.raises(InvalidResetTokenError, match="missing subject"):
        token_service.validate_password_reset_token(token)

def test_reset_token_missing_fingerprint_raises_invalid_error(token_service):
    to_encode = {
        "sub": "testuser",
        "purpose": "password_reset",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    token = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_signing_algorithm)
    with pytest.raises(InvalidResetTokenError, match="missing security fingerprint"):
        token_service.validate_password_reset_token(token)

def test_reset_token_signed_with_different_key_is_rejected(token_service):
    to_encode = {
        "sub": "testuser",
        "purpose": "password_reset",
        "pwh": "salt123",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    attacker_token = jwt.encode(to_encode, "different-unauthorized-secret-key-99999", algorithm=settings.jwt_signing_algorithm)
    with pytest.raises(InvalidResetTokenError, match="Invalid password reset token"):
        token_service.validate_password_reset_token(attacker_token)

def test_create_reset_token_empty_subject_raises_value_error(token_service):
    with pytest.raises(ValueError, match="Subject is required"):
        token_service.create_password_reset_token("   ")
