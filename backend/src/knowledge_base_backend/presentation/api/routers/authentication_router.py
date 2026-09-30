from fastapi import APIRouter, Depends
from dependency_injector.wiring import inject, Provide
from src.knowledge_base_backend.presentation.api.schemas.authentication_schemas import (
    LoginRequest,
    LoginResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    VerifyResetTokenRequest,
    VerifyResetTokenResponse,
)
from src.knowledge_base_backend.application.use_cases.authenticate_user import AuthenticateUserUseCase
from src.knowledge_base_backend.application.use_cases.forgot_password import ForgotPasswordUseCase
from src.knowledge_base_backend.application.use_cases.reset_password import ResetPasswordUseCase
from src.knowledge_base_backend.application.use_cases.verify_reset_token import VerifyResetTokenUseCase
from src.knowledge_base_backend.bootstrap.dependency_container import ApplicationContainer

router = APIRouter(prefix="/auth", tags=["Authentication", "User Management"])

@router.post("/login", response_model=LoginResponse)
@inject
async def login(
    request: LoginRequest,
    use_case: AuthenticateUserUseCase = Depends(Provide[ApplicationContainer.authenticate_user_use_case])
):
    result = await use_case.execute(request.username, request.password)
    return LoginResponse(
        token=result.token,
        user={"username": result.user.username, "display_name": result.user.display_name}
    )

@router.post("/forgot-password", response_model=ForgotPasswordResponse)
@inject
async def forgot_password(
    request: ForgotPasswordRequest,
    use_case: ForgotPasswordUseCase = Depends(Provide[ApplicationContainer.forgot_password_use_case])
):
    result = await use_case.execute(request.username)
    return ForgotPasswordResponse(
        username=result.username,
        reset_token=result.reset_token,
        expires_in_minutes=result.expires_in_minutes,
        message=result.message
    )

@router.post("/reset-password", response_model=ResetPasswordResponse)
@inject
async def reset_password(
    request: ResetPasswordRequest,
    use_case: ResetPasswordUseCase = Depends(Provide[ApplicationContainer.reset_password_use_case])
):
    result = await use_case.execute(request.reset_token, request.new_password, request.username)
    return ResetPasswordResponse(
        username=result.username,
        success=result.success,
        message=result.message
    )

@router.post("/verify-reset-token", response_model=VerifyResetTokenResponse)
@inject
async def verify_reset_token(
    request: VerifyResetTokenRequest,
    use_case: VerifyResetTokenUseCase = Depends(Provide[ApplicationContainer.verify_reset_token_use_case])
):
    result = await use_case.execute(request.reset_token)
    return VerifyResetTokenResponse(
        username=result.username,
        valid=result.valid,
        expires_at=result.expires_at,
        message=result.message
    )
