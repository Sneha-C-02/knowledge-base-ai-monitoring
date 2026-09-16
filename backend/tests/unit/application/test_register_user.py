import unittest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from src.knowledge_base_backend.application.use_cases.register_user import RegisterUserUseCase
from src.knowledge_base_backend.domain.services.password_validator import PasswordValidator
from src.knowledge_base_backend.domain.entities.user_account import UserAccount
from src.knowledge_base_backend.domain.exceptions.authentication_exceptions import UserAlreadyExistsError
from src.knowledge_base_backend.domain.exceptions.validation_exceptions import ValidationError

class TestRegisterUserUseCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.user_repo = AsyncMock()
        self.activity_repo = AsyncMock()
        self.hashing_service = MagicMock()
        self.token_service = MagicMock()
        self.date_time_provider = MagicMock()
        self.password_validator = PasswordValidator()

        self.hashing_service.hash_password.return_value = "hashed_pw_abc123"
        self.token_service.create_access_token.return_value = "jwt_token_sample"
        self.date_time_provider.get_current_utc_time.return_value = datetime(2026, 1, 1, tzinfo=timezone.utc)

        # Mock user repo saving
        async def mock_save(user):
            user.id = 42
            return user
        self.user_repo.save.side_effect = mock_save

        self.use_case = RegisterUserUseCase(
            user_repository=self.user_repo,
            password_hashing_service=self.hashing_service,
            password_validator=self.password_validator,
            token_service=self.token_service,
            activity_repository=self.activity_repo,
            date_time_provider=self.date_time_provider,
        )

    async def test_register_user_success(self):
        self.user_repo.get_by_username.return_value = None

        result = await self.use_case.execute(
            username="john_doe",
            password="SecurePassword1",
            confirm_password="SecurePassword1",
            display_name="John Doe"
        )

        self.assertEqual(result.token, "jwt_token_sample")
        self.assertEqual(result.user.username, "john_doe")
        self.assertEqual(result.user.display_name, "John Doe")
        self.assertEqual(result.user.password_hash, "hashed_pw_abc123")
        self.assertTrue(result.user.is_active)
        self.user_repo.save.assert_called_once()
        self.activity_repo.save.assert_called_once()

    async def test_register_mismatched_passwords_fails(self):
        with self.assertRaises(ValidationError) as ctx:
            await self.use_case.execute(
                username="john_doe",
                password="SecurePassword1",
                confirm_password="DifferentPassword2"
            )
        self.assertIn("do not match", str(ctx.exception))

    async def test_register_weak_password_fails(self):
        with self.assertRaises(ValidationError) as ctx:
            await self.use_case.execute(
                username="john_doe",
                password="weak",
                confirm_password="weak"
            )
        self.assertIn("at least 8 characters", str(ctx.exception))

    async def test_register_duplicate_username_fails(self):
        self.user_repo.get_by_username.return_value = UserAccount(
            id=1,
            username="existing_user",
            display_name="Existing",
            password_hash="hash",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        with self.assertRaises(UserAlreadyExistsError) as ctx:
            await self.use_case.execute(
                username="existing_user",
                password="SecurePassword1",
                confirm_password="SecurePassword1"
            )
        self.assertIn("already taken", str(ctx.exception))

if __name__ == "__main__":
    unittest.main()
