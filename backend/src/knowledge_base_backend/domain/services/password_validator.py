import re
from src.knowledge_base_backend.domain.exceptions.validation_exceptions import ValidationError

class PasswordValidator:
    """
    Domain service to enforce password security requirements:
    - Minimum 8 characters
    - Must contain at least one letter
    - Must contain at least one number
    - Symbols are optional
    """

    MINIMUM_LENGTH = 8

    def validate(self, password: str) -> None:
        if not password:
            raise ValidationError("Password cannot be empty.")

        if len(password) < self.MINIMUM_LENGTH:
            raise ValidationError(f"Password must be at least {self.MINIMUM_LENGTH} characters long.")

        if not re.search(r"[A-Za-z]", password):
            raise ValidationError("Password must contain at least one letter.")

        if not re.search(r"[0-9]", password):
            raise ValidationError("Password must contain at least one number.")
