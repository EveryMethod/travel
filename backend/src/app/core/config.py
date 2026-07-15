"""Application settings loaded from environment variables."""

from pathlib import Path

from pydantic import Field
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

BACKEND_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Environment-backed application settings."""

    app_name: str = "AI Travel Planner API"
    app_env: str = "development"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 13306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "travel"
    redis_url: str = "redis://127.0.0.1:16379/0"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    llm_name: str = "gpt-4o-mini"
    llm_temperature: float = 0.4
    llm_timeout_seconds: int = 60
    mcp_gateway_url: str = "http://127.0.0.1:8100"
    mcp_timeout_seconds: int = 20
    trace_enabled: bool = True
    trace_query_enabled: bool | None = None
    trace_retention_days: int = 30
    trace_summary_max_chars: int = 120
    amap_api_key: str = ""
    tavily_api_key: str = ""
    tavily_search_url: str = "https://api.tavily.com/search"
    auth_access_token_ttl_seconds: int = 60 * 30
    auth_refresh_token_ttl_seconds: int = 60 * 60 * 24 * 30

    @computed_field
    @property
    def sqlalchemy_database_url(self) -> str:
        """Build the SQLAlchemy URL without leaking password formatting bugs."""

        return URL.create(
            "mysql+pymysql",
            username=self.mysql_user,
            password=self.mysql_password,
            host=self.mysql_host,
            port=self.mysql_port,
            database=self.mysql_database,
            query={"charset": "utf8mb4"},
        ).render_as_string(hide_password=False)

    @computed_field
    @property
    def effective_trace_query_enabled(self) -> bool:
        """Enable trace query API by default only in development."""

        if self.trace_query_enabled is not None:
            return self.trace_query_enabled
        return self.app_env == "development"

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
