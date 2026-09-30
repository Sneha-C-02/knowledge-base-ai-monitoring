import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from src.knowledge_base_backend.main import app
from src.knowledge_base_backend.domain.entities.user_account import UserAccount
from src.knowledge_base_backend.infrastructure.authentication.argon2_password_hashing_service import (
    Argon2PasswordHashingService,
)

@pytest.fixture
def password_hasher():
    return Argon2PasswordHashingService()

@pytest.fixture
def mock_user_database(password_hasher):
    users = {
        "admin": UserAccount(
            id=1,
            username="admin",
            display_name="Admin User",
            password_hash=password_hasher.hash_password("password123"),
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
        "disabled_user": UserAccount(
            id=2,
            username="disabled_user",
            display_name="Disabled User",
            password_hash=password_hasher.hash_password("password123"),
            is_active=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        ),
    }

    mock_repo = AsyncMock()

    async def fake_get_by_username(username: str):
        return users.get(username)

    async def fake_get_by_id(user_id: int):
        for u in users.values():
            if u.id == user_id:
                return u
        return None

    async def fake_save(user: UserAccount):
        users[user.username] = user
        return user

    mock_repo.get_by_username.side_effect = fake_get_by_username
    mock_repo.get_by_id.side_effect = fake_get_by_id
    mock_repo.save.side_effect = fake_save

    mock_activity_repo = AsyncMock()

    with (
        app.container.user_repository.override(mock_repo),
        app.container.activity_repository.override(mock_activity_repo),
    ):
        yield users

@pytest.mark.asyncio
async def test_login_success(mock_user_database):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/auth/login", json={"username": "admin", "password": "password123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert data["user"]["username"] == "admin"

@pytest.mark.asyncio
async def test_login_invalid_password(mock_user_database):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/auth/login", json={"username": "admin", "password": "wrongpassword"})
        assert resp.status_code == 401

@pytest.mark.asyncio
async def test_forgot_password_success(mock_user_database):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/auth/forgot-password", json={"username": "admin"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "admin"
        assert "reset_token" in data
        assert len(data["reset_token"]) > 20
        assert data["expires_in_minutes"] == 15

@pytest.mark.asyncio
async def test_forgot_password_user_not_found(mock_user_database):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/auth/forgot-password", json={"username": "nonexistent"})
        assert resp.status_code == 404
        data = resp.json()
        assert data["error"]["code"] == "USER_NOT_FOUND"

@pytest.mark.asyncio
async def test_forgot_password_disabled_user(mock_user_database):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/auth/forgot-password", json={"username": "disabled_user"})
        assert resp.status_code == 401
        data = resp.json()
        assert "disabled" in data["error"]["message"].lower()

@pytest.mark.asyncio
async def test_verify_reset_token_endpoint(mock_user_database):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Request token
        forgot_resp = await client.post("/api/auth/forgot-password", json={"username": "admin"})
        token = forgot_resp.json()["reset_token"]

        # Verify valid token
        verify_resp = await client.post("/api/auth/verify-reset-token", json={"reset_token": token})
        assert verify_resp.status_code == 200
        data = verify_resp.json()
        assert data["valid"] is True
        assert data["username"] == "admin"

        # Verify invalid token
        invalid_resp = await client.post("/api/auth/verify-reset-token", json={"reset_token": "invalid_jwt_token"})
        assert invalid_resp.status_code == 400

@pytest.mark.asyncio
async def test_reset_password_end_to_end(mock_user_database):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Request forgot password
        forgot_resp = await client.post("/api/auth/forgot-password", json={"username": "admin"})
        assert forgot_resp.status_code == 200
        reset_token = forgot_resp.json()["reset_token"]

        # 2. Try reset with too short password
        short_resp = await client.post(
            "/api/auth/reset-password",
            json={"reset_token": reset_token, "new_password": "123"}
        )
        assert short_resp.status_code == 422

        # 3. Reset password successfully
        reset_resp = await client.post(
            "/api/auth/reset-password",
            json={"reset_token": reset_token, "new_password": "new_secret_password_2026"}
        )
        assert reset_resp.status_code == 200
        assert reset_resp.json()["success"] is True

        # 4. Old password should now fail login
        old_login = await client.post("/api/auth/login", json={"username": "admin", "password": "password123"})
        assert old_login.status_code == 401

        # 5. New password should succeed login
        new_login = await client.post("/api/auth/login", json={"username": "admin", "password": "new_secret_password_2026"})
        assert new_login.status_code == 200
        assert "token" in new_login.json()

        # 6. Reusing the reset token should now fail (invalidated token)
        reused_resp = await client.post(
            "/api/auth/reset-password",
            json={"reset_token": reset_token, "new_password": "yet_another_password"}
        )
        assert reused_resp.status_code == 400
        assert reused_resp.json()["error"]["code"] == "INVALID_RESET_TOKEN"

@pytest.mark.asyncio
async def test_reset_password_mismatched_username_rejected(mock_user_database):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        forgot_resp = await client.post("/api/auth/forgot-password", json={"username": "admin"})
        token = forgot_resp.json()["reset_token"]

        resp = await client.post(
            "/api/auth/reset-password",
            json={"reset_token": token, "new_password": "new_password_123", "username": "someone_else"}
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_RESET_TOKEN"

@pytest.mark.asyncio
async def test_reset_password_tampered_token_rejected(mock_user_database):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/auth/reset-password",
            json={"reset_token": "tampered.jwt.signature", "new_password": "new_password_123"}
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "INVALID_RESET_TOKEN"
