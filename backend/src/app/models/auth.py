"""Authentication request and response models."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

OAuthProvider = Literal["qq", "wechat"]


class AuthTokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthUser(BaseModel):
    id: int
    display_name: str
    avatar_url: str | None = None


class AuthResponse(BaseModel):
    user: AuthUser
    tokens: AuthTokens


class RegisterRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=80)
    password: str = Field(..., min_length=8, max_length=128)
    email: str | None = Field(default=None, max_length=255)
    username: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def require_email_or_username(self) -> "RegisterRequest":
        if not self.email and not self.username:
            raise ValueError("email or username is required")
        return self


class LoginRequest(BaseModel):
    account: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=32)


class LogoutRequest(BaseModel):
    access_token: str | None = Field(default=None, min_length=32)
    refresh_token: str | None = Field(default=None, min_length=32)


class OAuthAuthorizeResponse(BaseModel):
    authorization_url: str
    state: str
