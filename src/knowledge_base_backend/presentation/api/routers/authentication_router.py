from fastapi import APIRouter, Depends
from dependency_injector.wiring import inject, Provide
from src.knowledge_base_backend.presentation.api.schemas.authentication_schemas import LoginRequest, LoginResponse
from src.knowledge_base_backend.application.use_cases.authenticate_user import AuthenticateUserUseCase
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
        user={"username": result.user.username, "display_name": result.user.display_name}
    )
