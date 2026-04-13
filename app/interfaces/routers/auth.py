from fastapi import APIRouter, HTTPException
from app.application.user_use_cases import UserUseCases
from app.domain.exceptions import InvalidCredentials
from app.infrastructure.jwt_handler import create_access_token
from app.infrastructure.repositories.user_repository import SQLiteUserRepository
from app.interfaces.schemas import LoginRequest, LoginResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _use_cases() -> UserUseCases:
    return UserUseCases(user_repo=SQLiteUserRepository())


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest):
    try:
        user = _use_cases().login(email=body.email, password=body.password)
        return LoginResponse(
            access_token=create_access_token(user.id),
            token_type="bearer",
            user=UserResponse.from_entity(user),
        )
    except InvalidCredentials as exc:
        raise HTTPException(status_code=401, detail=str(exc))
