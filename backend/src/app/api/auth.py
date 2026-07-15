"""Authentication routes."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis import Redis
from sqlalchemy.orm import Session

from src.app.core.database import get_db
from src.app.core.redis import redis_client
from src.app.models.auth import (
    AuthResponse,
    LoginRequest,
    LogoutRequest,
    OAuthAuthorizeResponse,
    OAuthProvider,
    RefreshRequest,
    RegisterRequest,
)
from src.app.models.db import User
from src.app.services.auth_service import (
    get_user_by_access_token,
    login_with_oauth_account,
    login_with_password,
    logout,
    refresh_tokens,
    register_user,
)
from src.app.services.oauth_service import build_authorization_url, fetch_oauth_profile

router = APIRouter(prefix="/auth", tags=["auth"])


def get_redis() -> Redis:
    return redis_client


auth_scheme = HTTPBearer(auto_error=False)


def require_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(auth_scheme),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> User:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态已失效，请重新登录。")

    return get_user_by_access_token(db=db, redis=redis, access_token=credentials.credentials)


@router.post("/register", response_model=AuthResponse)
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> AuthResponse:
    return register_user(
        db=db,
        redis=redis,
        display_name=payload.display_name,
        password=payload.password,
        email=payload.email,
        username=payload.username,
        request=request,
    )


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> AuthResponse:
    return login_with_password(db=db, redis=redis, account=payload.account, password=payload.password, request=request)


@router.get("/oauth/{provider}/authorize", response_model=OAuthAuthorizeResponse)
def oauth_authorize(
    provider: OAuthProvider,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> OAuthAuthorizeResponse:
    authorization_url, state = build_authorization_url(db=db, redis=redis, provider=provider)
    return OAuthAuthorizeResponse(authorization_url=authorization_url, state=state)


@router.get("/oauth/{provider}/callback", response_model=AuthResponse)
async def oauth_callback(
    provider: OAuthProvider,
    code: str,
    state: str,
    request: Request,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> AuthResponse:
    profile = await fetch_oauth_profile(db=db, redis=redis, provider=provider, code=code, state=state)
    return login_with_oauth_account(
        db=db,
        redis=redis,
        provider=provider,
        open_id=profile["open_id"],
        union_id=profile.get("union_id"),
        nickname=profile.get("nickname"),
        avatar_url=profile.get("avatar_url"),
        raw_profile=profile.get("raw_profile"),
        request=request,
    )


@router.post("/refresh", response_model=AuthResponse)
def refresh(
    payload: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> AuthResponse:
    return refresh_tokens(db=db, redis=redis, refresh_token=payload.refresh_token, request=request)


@router.post("/logout")
def logout_route(
    payload: LogoutRequest,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> dict[str, str]:
    return logout(db=db, redis=redis, access_token=payload.access_token, refresh_token=payload.refresh_token)
