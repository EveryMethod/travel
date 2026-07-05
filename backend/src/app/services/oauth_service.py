"""QQ and WeChat OAuth helpers."""

import secrets
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx
from fastapi import HTTPException, status
from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.models.db import OAuthProviderConfig

STATE_TTL_SECONDS = 600


def build_authorization_url(*, db: Session, redis: Redis, provider: str) -> tuple[str, str]:
    config = _get_config(db, provider)
    state = secrets.token_urlsafe(24)
    redis.setex(_state_key(provider, state), STATE_TTL_SECONDS, "1")
    params = {
        "response_type": "code",
        "client_id": config.app_id,
        "redirect_uri": _redirect_uri(config.redirect_uri, provider),
        "state": state,
    }
    if config.scope:
        params["scope"] = config.scope
    base_url = "https://graph.qq.com/oauth2.0/authorize" if provider == "qq" else "https://open.weixin.qq.com/connect/qrconnect"
    return f"{base_url}?{urlencode(params)}", state


async def fetch_oauth_profile(*, db: Session, redis: Redis, provider: str, code: str, state: str) -> dict:
    if not redis.delete(_state_key(provider, state)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state.")
    config = _get_config(db, provider)
    if provider == "qq":
        return await _fetch_qq_profile(config, code)
    return await _fetch_wechat_profile(config, code)


def _get_config(db: Session, provider: str) -> OAuthProviderConfig:
    config = db.scalar(
        select(OAuthProviderConfig).where(
            OAuthProviderConfig.provider == provider,
            OAuthProviderConfig.enabled == 1,
        )
    )
    if not config:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{provider} OAuth is not configured.")
    return config


async def _fetch_qq_profile(config: OAuthProviderConfig, code: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        token_response = await client.get(
            "https://graph.qq.com/oauth2.0/token",
            params={
                "grant_type": "authorization_code",
                "client_id": config.app_id,
                "client_secret": config.app_secret,
                "code": code,
                "redirect_uri": _redirect_uri(config.redirect_uri, "qq"),
                "fmt": "json",
            },
        )
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to fetch QQ access token.")

        openid_response = await client.get(
            "https://graph.qq.com/oauth2.0/me",
            params={"access_token": access_token, "fmt": "json"},
        )
        openid_data = openid_response.json()
        open_id = openid_data.get("openid")
        if not open_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to fetch QQ openid.")

        profile_response = await client.get(
            "https://graph.qq.com/user/get_user_info",
            params={
                "access_token": access_token,
                "oauth_consumer_key": config.app_id,
                "openid": open_id,
            },
        )
        profile = profile_response.json()
        return {
            "open_id": open_id,
            "union_id": openid_data.get("unionid"),
            "nickname": profile.get("nickname"),
            "avatar_url": profile.get("figureurl_qq_2") or profile.get("figureurl_qq_1"),
            "raw_profile": profile,
        }


async def _fetch_wechat_profile(config: OAuthProviderConfig, code: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        token_response = await client.get(
            "https://api.weixin.qq.com/sns/oauth2/access_token",
            params={
                "appid": config.app_id,
                "secret": config.app_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        open_id = token_data.get("openid")
        if not access_token or not open_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to fetch WeChat openid.")

        profile_response = await client.get(
            "https://api.weixin.qq.com/sns/userinfo",
            params={"access_token": access_token, "openid": open_id, "lang": "zh_CN"},
        )
        profile = profile_response.json()
        return {
            "open_id": open_id,
            "union_id": token_data.get("unionid") or profile.get("unionid"),
            "nickname": profile.get("nickname"),
            "avatar_url": profile.get("headimgurl"),
            "raw_profile": profile,
        }


def _state_key(provider: str, state: str) -> str:
    return f"oauth:state:{provider}:{state}"


def _redirect_uri(value: str, provider: str) -> str:
    parts = urlsplit(value)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.setdefault("provider", provider)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
