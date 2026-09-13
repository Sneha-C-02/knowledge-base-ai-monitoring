from fastapi import APIRouter, Depends, status
from dependency_injector.wiring import inject, Provide
from src.knowledge_base_backend.presentation.api.schemas.authentication_schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    UserSchema
)
from src.knowledge_base_backend.application.use_cases.authenticate_user import AuthenticateUserUseCase
from src.knowledge_base_backend.application.use_cases.register_user import RegisterUserUseCase
from src.knowledge_base_backend.bootstrap.dependency_container import ApplicationContainer

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=LoginResponse)
@inject
async def login(
    request: LoginRequest,
    use_case: AuthenticateUserUseCase = Depends(Provide[ApplicationContainer.authenticate_user_use_case])
):
    result = await use_case.execute(request.username, request.password)
    return LoginResponse(
        token=result.token,
        user=UserSchema(
            username=result.user.username,
            display_name=result.user.display_name,
            group_id=result.user.group_id
        )
    )

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
@inject
async def register(
    request: RegisterRequest,
    use_case: RegisterUserUseCase = Depends(Provide[ApplicationContainer.register_user_use_case])
):
    result = await use_case.execute(
        username=request.username,
        password=request.password,
        confirm_password=request.confirm_password,
        display_name=request.display_name
    )
    return RegisterResponse(
        message="User registered successfully",
        token=result.token,
        user=UserSchema(
            username=result.user.username,
            display_name=result.user.display_name,
            group_id=result.user.group_id
        )
    )
