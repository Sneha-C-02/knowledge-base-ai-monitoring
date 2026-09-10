import unittest
from src.knowledge_base_backend.domain.services.password_validator import PasswordValidator
from src.knowledge_base_backend.domain.exceptions.validation_exceptions import ValidationError

class TestPasswordValidator(unittest.TestCase):
    def setUp(self):
        self.validator = PasswordValidator()

    def test_valid_password_with_letters_and_numbers(self):
        # Should not raise
        self.validator.validate("Password123")
        self.validator.validate("securePass1")
        self.validator.validate("waters2024")

    def test_valid_password_with_symbols(self):
        # Symbols are optional but allowed
        self.validator.validate("Pass@word123!")

    def test_too_short_password_fails(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("Pass1")
        self.assertIn("at least 8 characters", str(ctx.exception))

    def test_password_without_numbers_fails(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("PasswordOnly")
        self.assertIn("at least one number", str(ctx.exception))

    def test_password_without_letters_fails(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("123456789")
        self.assertIn("at least one letter", str(ctx.exception))

    def test_empty_password_fails(self):
        with self.assertRaises(ValidationError) as ctx:
            self.validator.validate("")
        self.assertIn("cannot be empty", str(ctx.exception))

if __name__ == "__main__":
    unittest.main()
