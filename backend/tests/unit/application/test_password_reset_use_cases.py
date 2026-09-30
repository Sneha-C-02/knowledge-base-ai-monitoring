import pytest
import hashlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from src.knowledge_base_backend.application.use_cases.forgot_password import ForgotPasswordUseCase
from src.knowledge_base_backend.application.use_cases.reset_password import ResetPasswordUseCase
from src.knowledge_base_backend.application.use_cases.verify_reset_token import VerifyResetTokenUseCase
from src.knowledge_base_backend.domain.entities.user_account import UserAccount
from src.knowledge_base_backend.domain.exceptions.authentication_exceptions import (
    UserNotFoundError,
    InactiveUserError,
    InvalidResetTokenError,
    PasswordValidationError,
)

@pytest.fixture
def mock_user_repo():
    return AsyncMock()

@pytest.fixture
def mock_token_service():
    return MagicMock()

@pytest.fixture
def mock_password_hasher():
    hasher = MagicMock()
    hasher.hash_password.side_effect = lambda pwd: f"hashed_{pwd}"
    return hasher

@pytest.fixture
def mock_activity_repo():
    return AsyncMock()

@pytest.fixture
def mock_date_time_provider():
    dt_provider = MagicMock()
    dt_provider.get_current_utc_time.return_value = datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone.utc)
    return dt_provider

@pytest.fixture
def sample_user():
    return UserAccount(
        id=1,
        username="alice",
        display_name="Alice User",
        password_hash="current_hash_value",
        is_active=True,
        created_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    )

# --- ForgotPasswordUseCase Tests ---

@pytest.mark.asyncio
async def test_forgot_password_success(
    mock_user_repo, mock_token_service, mock_activity_repo, mock_date_time_provider, sample_user
):
    mock_user_repo.get_by_username.return_value = sample_user
    mock_token_service.create_password_reset_token.return_value = "mock_reset_token_xyz"

    use_case = ForgotPasswordUseCase(
        user_repository=mock_user_repo,
        token_service=mock_token_service,
        activity_repository=mock_activity_repo,
        date_time_provider=mock_date_time_provider,
    )

    result = await use_case.execute("alice")

    assert result.username == "alice"
    assert result.reset_token == "mock_reset_token_xyz"
    assert result.expires_in_minutes > 0
    mock_user_repo.get_by_username.assert_called_once_with("alice")
    mock_token_service.create_password_reset_token.assert_called_once()
    mock_activity_repo.save.assert_called_once()

@pytest.mark.asyncio
async def test_forgot_password_user_not_found(
    mock_user_repo, mock_token_service, mock_activity_repo, mock_date_time_provider
):
    mock_user_repo.get_by_username.return_value = None

    use_case = ForgotPasswordUseCase(
        user_repository=mock_user_repo,
        token_service=mock_token_service,
        activity_repository=mock_activity_repo,
        date_time_provider=mock_date_time_provider,
    )

    with pytest.raises(UserNotFoundError, match="User 'unknown' not found"):
        await use_case.execute("unknown")

@pytest.mark.asyncio
async def test_forgot_password_empty_username(
    mock_user_repo, mock_token_service, mock_activity_repo, mock_date_time_provider
):
    use_case = ForgotPasswordUseCase(
        user_repository=mock_user_repo,
        token_service=mock_token_service,
        activity_repository=mock_activity_repo,
        date_time_provider=mock_date_time_provider,
    )

    with pytest.raises(UserNotFoundError, match="Username must not be empty"):
        await use_case.execute("   ")

@pytest.mark.asyncio
async def test_forgot_password_inactive_user(
    mock_user_repo, mock_token_service, mock_activity_repo, mock_date_time_provider, sample_user
):
    sample_user.is_active = False
    mock_user_repo.get_by_username.return_value = sample_user

    use_case = ForgotPasswordUseCase(
        user_repository=mock_user_repo,
        token_service=mock_token_service,
        activity_repository=mock_activity_repo,
        date_time_provider=mock_date_time_provider,
    )

    with pytest.raises(InactiveUserError, match="disabled"):
        await use_case.execute("alice")


# --- ResetPasswordUseCase Tests ---

@pytest.mark.asyncio
async def test_reset_password_success(
    mock_user_repo, mock_password_hasher, mock_token_service, mock_activity_repo, mock_date_time_provider, sample_user
):
    pwh = hashlib.sha256(sample_user.password_hash.encode("utf-8")).hexdigest()[:16]
    mock_token_service.validate_password_reset_token.return_value = {
        "sub": "alice",
        "purpose": "password_reset",
        "pwh": pwh,
    }
    mock_user_repo.get_by_username.return_value = sample_user

    use_case = ResetPasswordUseCase(
        user_repository=mock_user_repo,
        password_hashing_service=mock_password_hasher,
        token_service=mock_token_service,
        activity_repository=mock_activity_repo,
        date_time_provider=mock_date_time_provider,
    )

    result = await use_case.execute(reset_token="valid_token", new_password="new_secure_password_123")

    assert result.username == "alice"
    assert result.success is True
    assert sample_user.password_hash == "hashed_new_secure_password_123"
    mock_user_repo.save.assert_called_once_with(sample_user)
    mock_activity_repo.save.assert_called_once()

@pytest.mark.asyncio
async def test_reset_password_rejects_short_password(
    mock_user_repo, mock_password_hasher, mock_token_service, mock_activity_repo, mock_date_time_provider
):
    use_case = ResetPasswordUseCase(
        user_repository=mock_user_repo,
        password_hashing_service=mock_password_hasher,
        token_service=mock_token_service,
        activity_repository=mock_activity_repo,
        date_time_provider=mock_date_time_provider,
    )

    with pytest.raises(PasswordValidationError, match="at least 6 characters"):
        await use_case.execute(reset_token="any_token", new_password="123")

@pytest.mark.asyncio
async def test_reset_password_rejects_already_used_or_invalidated_token(
    mock_user_repo, mock_password_hasher, mock_token_service, mock_activity_repo, mock_date_time_provider, sample_user
):
    # Old fingerprint does not match sample_user.password_hash fingerprint
    mock_token_service.validate_password_reset_token.return_value = {
        "sub": "alice",
        "purpose": "password_reset",
        "pwh": "stale_fingerprint",
    }
    mock_user_repo.get_by_username.return_value = sample_user

    use_case = ResetPasswordUseCase(
        user_repository=mock_user_repo,
        password_hashing_service=mock_password_hasher,
        token_service=mock_token_service,
        activity_repository=mock_activity_repo,
        date_time_provider=mock_date_time_provider,
    )

    with pytest.raises(InvalidResetTokenError, match="already been used or has been invalidated"):
        await use_case.execute(reset_token="old_token", new_password="valid_new_password_123")

@pytest.mark.asyncio
async def test_reset_password_rejects_username_mismatch(
    mock_user_repo, mock_password_hasher, mock_token_service, mock_activity_repo, mock_date_time_provider
):
    mock_token_service.validate_password_reset_token.return_value = {
        "sub": "alice",
        "purpose": "password_reset",
        "pwh": "any",
    }

    use_case = ResetPasswordUseCase(
        user_repository=mock_user_repo,
        password_hashing_service=mock_password_hasher,
        token_service=mock_token_service,
        activity_repository=mock_activity_repo,
        date_time_provider=mock_date_time_provider,
    )

    with pytest.raises(InvalidResetTokenError, match="not issued for this user"):
        await use_case.execute(
            reset_token="valid_token", new_password="valid_new_password_123", username="bob"
        )


# --- VerifyResetTokenUseCase Tests ---

@pytest.mark.asyncio
async def test_verify_reset_token_success(
    mock_user_repo, mock_token_service, sample_user
):
    pwh = hashlib.sha256(sample_user.password_hash.encode("utf-8")).hexdigest()[:16]
    mock_token_service.validate_password_reset_token.return_value = {
        "sub": "alice",
        "purpose": "password_reset",
        "pwh": pwh,
        "exp": 1800000000,
    }
    mock_user_repo.get_by_username.return_value = sample_user

    use_case = VerifyResetTokenUseCase(
        user_repository=mock_user_repo,
        token_service=mock_token_service,
    )

    result = await use_case.execute("valid_token")
    assert result.username == "alice"
    assert result.valid is True
    assert result.expires_at == 1800000000

@pytest.mark.asyncio
async def test_reset_password_rejects_missing_or_empty_fingerprint(
    mock_user_repo, mock_password_hasher, mock_token_service, mock_activity_repo, mock_date_time_provider, sample_user
):
    mock_token_service.validate_password_reset_token.return_value = {
        "sub": "alice",
        "purpose": "password_reset",
        "pwh": "",  # Missing/empty fingerprint
    }
    mock_user_repo.get_by_username.return_value = sample_user

    use_case = ResetPasswordUseCase(
        user_repository=mock_user_repo,
        password_hashing_service=mock_password_hasher,
        token_service=mock_token_service,
        activity_repository=mock_activity_repo,
        date_time_provider=mock_date_time_provider,
    )

    with pytest.raises(InvalidResetTokenError, match="already been used or has been invalidated"):
        await use_case.execute(reset_token="token_without_pwh", new_password="valid_new_password_123")

@pytest.mark.asyncio
async def test_verify_reset_token_rejects_missing_or_empty_fingerprint(
    mock_user_repo, mock_token_service, sample_user
):
    mock_token_service.validate_password_reset_token.return_value = {
        "sub": "alice",
        "purpose": "password_reset",
        "pwh": "",  # Empty fingerprint
    }
    mock_user_repo.get_by_username.return_value = sample_user

    use_case = VerifyResetTokenUseCase(
        user_repository=mock_user_repo,
        token_service=mock_token_service,
    )

    with pytest.raises(InvalidResetTokenError, match="already been used or has been invalidated"):
        await use_case.execute("token_without_pwh")

@pytest.mark.asyncio
async def test_reset_password_preserves_exact_password_without_stripping(
    mock_user_repo, mock_password_hasher, mock_token_service, mock_activity_repo, mock_date_time_provider, sample_user
):
    pwh = hashlib.sha256(sample_user.password_hash.encode("utf-8")).hexdigest()[:16]
    mock_token_service.validate_password_reset_token.return_value = {
        "sub": "alice",
        "purpose": "password_reset",
        "pwh": pwh,
    }
    mock_user_repo.get_by_username.return_value = sample_user

    use_case = ResetPasswordUseCase(
        user_repository=mock_user_repo,
        password_hashing_service=mock_password_hasher,
        token_service=mock_token_service,
        activity_repository=mock_activity_repo,
        date_time_provider=mock_date_time_provider,
    )

    password_with_space = "  secure phrase 123  "
    await use_case.execute(reset_token="valid_token", new_password=password_with_space)

    # Hasher must receive the unstripped password so login verification succeeds
    mock_password_hasher.hash_password.assert_called_once_with(password_with_space)
