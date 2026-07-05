"""Authentication service helpers."""

from datetime import datetime, timedelta
import hashlib
import secrets

import bcrypt
from fastapi import HTTPException, Request, status
from redis import Redis
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.app.core.config import settings
from src.app.models.auth import AuthResponse, AuthTokens, AuthUser
from src.app.models.db import AuthSession, User, UserOAuthAccount, UserPasswordCredential


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def register_user(
    *,
    db: Session,
    redis: Redis,
    display_name: str,
    password: str,
    email: str | None,
    username: str | None,
    request: Request,
) -> AuthResponse:
    user = User(display_name=display_name)
    user.password_credential = UserPasswordCredential(
        email=email,
        username=username,
        password_hash=hash_password(password),
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email or username already exists.") from exc
    return _login_user(db=db, redis=redis, user=user, request=request)


def login_with_password(*, db: Session, redis: Redis, account: str, password: str, request: Request) -> AuthResponse:
    credential = db.scalar(
        select(UserPasswordCredential)
        .join(User)
        .where(or_(UserPasswordCredential.email == account, UserPasswordCredential.username == account))
    )
    if not credential or credential.user.status != "active" or not verify_password(password, credential.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid account or password.")
    return _login_user(db=db, redis=redis, user=credential.user, request=request)


def login_with_oauth_account(
    *,
    db: Session,
    redis: Redis,
    provider: str,
    open_id: str,
    union_id: str | None,
    nickname: str | None,
    avatar_url: str | None,
    raw_profile: dict | None,
    request: Request,
) -> AuthResponse:
    oauth_account = db.scalar(
        select(UserOAuthAccount).where(
            UserOAuthAccount.provider == provider,
            UserOAuthAccount.provider_open_id == open_id,
        )
    )
    if oauth_account:
        if oauth_account.user.status != "active":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is disabled.")
        return _login_user(db=db, redis=redis, user=oauth_account.user, request=request)

    user = User(display_name=nickname or f"{provider}_user", avatar_url=avatar_url)
    user.oauth_accounts.append(
        UserOAuthAccount(
            provider=provider,
            provider_open_id=open_id,
            provider_union_id=union_id,
            nickname=nickname,
            avatar_url=avatar_url,
            raw_profile=raw_profile,
        )
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="OAuth account already exists.") from exc
    return _login_user(db=db, redis=redis, user=user, request=request)


def refresh_tokens(*, db: Session, redis: Redis, refresh_token: str, request: Request) -> AuthResponse:
    session_id = redis.get(_refresh_key(refresh_token))
    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")
    session = db.get(AuthSession, int(session_id))
    if not session or session.revoked_at or session.expires_at <= datetime.utcnow():
        redis.delete(_refresh_key(refresh_token))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.")
    _delete_session_tokens(redis, session.id)
    return _issue_tokens(db=db, redis=redis, user=session.user, auth_session=session, request=request)


def logout(*, db: Session, redis: Redis, access_token: str | None, refresh_token: str | None) -> dict[str, str]:
    session_ids = []
    if access_token:
        session_id = redis.get(_access_key(access_token))
        if session_id:
            session_ids.append(int(session_id))
    if refresh_token:
        session_id = redis.get(_refresh_key(refresh_token))
        if session_id:
            session_ids.append(int(session_id))

    for session_id in set(session_ids):
        auth_session = db.get(AuthSession, session_id)
        if auth_session and not auth_session.revoked_at:
            auth_session.revoked_at = datetime.utcnow()
        _delete_session_tokens(redis, session_id)
    db.commit()
    return {"status": "ok"}


def _login_user(*, db: Session, redis: Redis, user: User, request: Request) -> AuthResponse:
    expires_at = datetime.utcnow() + timedelta(seconds=settings.auth_refresh_token_ttl_seconds)
    auth_session = AuthSession(
        user=user,
        refresh_token_hash=_sha256(secrets.token_urlsafe(32)),
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
        expires_at=expires_at,
    )
    user.last_login_at = datetime.utcnow()
    db.add(auth_session)
    db.flush()
    return _issue_tokens(db=db, redis=redis, user=user, auth_session=auth_session, request=request)


def _issue_tokens(*, db: Session, redis: Redis, user: User, auth_session: AuthSession, request: Request) -> AuthResponse:
    access_token = secrets.token_urlsafe(32)
    refresh_token = secrets.token_urlsafe(48)
    auth_session.refresh_token_hash = _sha256(refresh_token)
    db.commit()
    db.refresh(user)
    redis.setex(_access_key(access_token), settings.auth_access_token_ttl_seconds, auth_session.id)
    redis.setex(_refresh_key(refresh_token), settings.auth_refresh_token_ttl_seconds, auth_session.id)
    redis.sadd(_session_key(auth_session.id), _access_key(access_token), _refresh_key(refresh_token))
    redis.expire(_session_key(auth_session.id), settings.auth_refresh_token_ttl_seconds)
    return AuthResponse(
        user=AuthUser(id=user.id, display_name=user.display_name, avatar_url=user.avatar_url),
        tokens=AuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.auth_access_token_ttl_seconds,
        ),
    )


def _delete_session_tokens(redis: Redis, session_id: int) -> None:
    keys = list(redis.smembers(_session_key(session_id)))
    if keys:
        redis.delete(*keys)
    redis.delete(_session_key(session_id))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _access_key(token: str) -> str:
    return f"auth:access:{token}"


def _refresh_key(token: str) -> str:
    return f"auth:refresh:{token}"


def _session_key(session_id: int) -> str:
    return f"auth:session:{session_id}:tokens"
