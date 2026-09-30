class AuthenticationError(Exception):
    pass

class InvalidCredentialsError(AuthenticationError):
    pass

class InactiveUserError(AuthenticationError):
    pass

class UserNotFoundError(AuthenticationError):
    pass

class InvalidResetTokenError(AuthenticationError):
    pass

class ExpiredResetTokenError(AuthenticationError):
    pass

class PasswordValidationError(AuthenticationError):
    pass
