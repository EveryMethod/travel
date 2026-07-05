"""Upsert a QQ or WeChat OAuth provider config."""

import argparse

from sqlalchemy import select

from src.app.core.database import SessionLocal
from src.app.models.db import OAuthProviderConfig


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("provider", choices=["qq", "wechat"])
    parser.add_argument("--app-id", required=True)
    parser.add_argument("--app-secret", required=True)
    parser.add_argument("--redirect-uri", required=True)
    parser.add_argument("--scope", default=None)
    parser.add_argument("--disabled", action="store_true")
    args = parser.parse_args()

    with SessionLocal() as db:
        config = db.scalar(select(OAuthProviderConfig).where(OAuthProviderConfig.provider == args.provider))
        if not config:
            config = OAuthProviderConfig(provider=args.provider)
            db.add(config)

        config.app_id = args.app_id
        config.app_secret = args.app_secret
        config.redirect_uri = args.redirect_uri
        config.scope = args.scope
        config.enabled = 0 if args.disabled else 1
        db.commit()

    print(f"{args.provider} OAuth config saved.")


if __name__ == "__main__":
    main()
