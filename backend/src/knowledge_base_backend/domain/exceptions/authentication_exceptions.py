class AuthenticationError(Exception):
    pass

class InvalidCredentialsError(AuthenticationError):
    pass

class InactiveUserError(AuthenticationError):
    pass
