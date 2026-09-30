from typing import Optional
from pydantic import BaseModel, Field

class LoginRequest(BaseModel):
    username: str
    password: str

class UserSchema(BaseModel):
    username: str
    name: str = Field(alias="display_name")

class LoginResponse(BaseModel):
    token: str
    user: UserSchema

class ForgotPasswordRequest(BaseModel):
    username: str

class ForgotPasswordResponse(BaseModel):
    username: str
    reset_token: str
    expires_in_minutes: int
    message: str

class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str
    username: Optional[str] = None

class ResetPasswordResponse(BaseModel):
    username: str
    success: bool
    message: str

class VerifyResetTokenRequest(BaseModel):
    reset_token: str

class VerifyResetTokenResponse(BaseModel):
    username: str
    valid: bool
    expires_at: Optional[int] = None
    message: str
