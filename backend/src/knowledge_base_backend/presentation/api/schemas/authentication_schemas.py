from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    confirm_password: str
    display_name: Optional[str] = None

class UserSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    username: str
    name: str = Field(alias="display_name")
    group_id: int

class LoginResponse(BaseModel):
    token: str
    user: UserSchema

class RegisterResponse(BaseModel):
    message: str = "User registered successfully"
    token: str
    user: UserSchema
