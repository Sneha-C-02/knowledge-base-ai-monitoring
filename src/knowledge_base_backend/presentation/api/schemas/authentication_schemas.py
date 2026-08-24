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
