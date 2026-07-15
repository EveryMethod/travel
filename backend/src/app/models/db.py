"""SQLAlchemy auth models."""

from datetime import datetime
from typing import Literal

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.mysql import BIGINT, JSON, TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.app.core.database import Base

UserStatus = Literal["active", "disabled"]
OAuthProviderName = Literal["qq", "wechat"]
TripStatus = Literal["completed"]


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True, comment="用户ID")
    display_name: Mapped[str] = mapped_column(String(80), comment="用户展示名称")
    avatar_url: Mapped[str | None] = mapped_column(String(512), comment="用户头像地址")
    status: Mapped[str] = mapped_column(Enum("active", "disabled"), default="active", server_default="active", comment="用户状态")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, comment="最后登录时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment="更新时间",
    )

    password_credential: Mapped["UserPasswordCredential | None"] = relationship(back_populates="user")
    oauth_accounts: Mapped[list["UserOAuthAccount"]] = relationship(back_populates="user")
    sessions: Mapped[list["AuthSession"]] = relationship(back_populates="user")
    trips: Mapped[list["Trip"]] = relationship(back_populates="user")

    __table_args__ = (Index("idx_users_status", "status"), {"comment": "用户主表"})


class UserPasswordCredential(Base):
    __tablename__ = "user_password_credentials"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True, comment="账号密码凭据ID")
    user_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), ForeignKey("users.id"), unique=True, comment="关联用户ID")
    email: Mapped[str | None] = mapped_column(String(255), unique=True, comment="登录邮箱")
    username: Mapped[str | None] = mapped_column(String(64), unique=True, comment="登录用户名")
    password_hash: Mapped[str] = mapped_column(String(255), comment="密码哈希值")
    password_algo: Mapped[str] = mapped_column(String(32), default="bcrypt", server_default="bcrypt", comment="密码哈希算法")
    password_updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), comment="密码更新时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment="更新时间",
    )

    user: Mapped[User] = relationship(back_populates="password_credential")

    __table_args__ = (
        CheckConstraint("email IS NOT NULL OR username IS NOT NULL", name="ck_password_email_or_username"),
        {"comment": "账号密码登录凭据表"},
    )


class UserOAuthAccount(Base):
    __tablename__ = "user_oauth_accounts"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True, comment="第三方账号绑定ID")
    user_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), ForeignKey("users.id"), index=True, comment="关联用户ID")
    provider: Mapped[str] = mapped_column(Enum("qq", "wechat"), comment="第三方登录平台")
    provider_open_id: Mapped[str] = mapped_column(String(128), comment="第三方平台 OpenID")
    provider_union_id: Mapped[str | None] = mapped_column(String(128), comment="第三方平台 UnionID")
    nickname: Mapped[str | None] = mapped_column(String(80), comment="第三方平台昵称")
    avatar_url: Mapped[str | None] = mapped_column(String(512), comment="第三方平台头像地址")
    raw_profile: Mapped[dict | None] = mapped_column(JSON, comment="第三方平台原始用户资料")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment="更新时间",
    )

    user: Mapped[User] = relationship(back_populates="oauth_accounts")

    __table_args__ = (
        Index("uq_oauth_provider_open_id", "provider", "provider_open_id", unique=True),
        Index("idx_oauth_provider_union_id", "provider", "provider_union_id"),
        {"comment": "第三方登录账号绑定表"},
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True, comment="登录会话ID")
    user_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), ForeignKey("users.id"), index=True, comment="关联用户ID")
    refresh_token_hash: Mapped[str] = mapped_column(String(255), unique=True, comment="刷新令牌哈希值")
    user_agent: Mapped[str | None] = mapped_column(String(512), comment="登录设备 User-Agent")
    ip_address: Mapped[str | None] = mapped_column(String(45), comment="登录IP地址")
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True, comment="会话过期时间")
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, comment="会话撤销时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), comment="创建时间")

    user: Mapped[User] = relationship(back_populates="sessions")

    __table_args__ = ({"comment": "登录会话表"},)


class OAuthProviderConfig(Base):
    __tablename__ = "oauth_provider_configs"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True, comment="第三方登录配置ID")
    provider: Mapped[str] = mapped_column(Enum("qq", "wechat"), unique=True, comment="第三方登录平台")
    app_id: Mapped[str] = mapped_column(String(128), comment="应用ID")
    app_secret: Mapped[str] = mapped_column(String(255), comment="应用密钥")
    redirect_uri: Mapped[str] = mapped_column(String(512), comment="OAuth回调地址")
    enabled: Mapped[int] = mapped_column(TINYINT(1), default=1, server_default="1", comment="是否启用")
    scope: Mapped[str | None] = mapped_column(String(255), comment="授权范围")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment="更新时间",
    )

    __table_args__ = ({"comment": "第三方登录应用配置表"},)


class CallTrace(Base):
    __tablename__ = "call_traces"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True, comment="调用追踪ID")
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False, comment="请求链路ID")
    span_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, comment="当前调用ID")
    parent_span_id: Mapped[str | None] = mapped_column(String(36), nullable=True, comment="上级调用ID")
    kind: Mapped[str] = mapped_column(Enum("agent.llm", "mcp.client", "tool.execute"), nullable=False, comment="调用类型")
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="模型名或工具名")
    status: Mapped[str] = mapped_column(Enum("ok", "error"), nullable=False, comment="调用状态")
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="开始时间")
    ended_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="结束时间")
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, comment="耗时毫秒")
    input_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="输入摘要")
    output_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="输出摘要")
    error_type: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="异常类型")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="异常信息")
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True, comment="补充元数据")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), comment="创建时间")

    __table_args__ = (
        Index("idx_call_traces_trace_id", "trace_id"),
        Index("idx_call_traces_kind_started_at", "kind", "started_at"),
        {"comment": "智能体、MCP和工具调用追踪表"},
    )


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True, comment="行程ID")
    user_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), ForeignKey("users.id"), nullable=False, comment="关联用户ID")
    trace_id: Mapped[str | None] = mapped_column(String(36), nullable=True, comment="生成链路ID")
    destination: Mapped[str] = mapped_column(String(120), nullable=False, comment="目的地")
    days: Mapped[int] = mapped_column(Integer, nullable=False, comment="行程天数")
    status: Mapped[TripStatus] = mapped_column(Enum("completed"), default="completed", server_default="completed", nullable=False, comment="行程状态")
    request_json: Mapped[dict] = mapped_column(JSON, nullable=False, comment="原始规划请求")
    plan_json: Mapped[dict] = mapped_column(JSON, nullable=False, comment="生成行程结果")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment="更新时间",
    )

    user: Mapped[User] = relationship(back_populates="trips")

    __table_args__ = (
        Index("idx_trips_user_created_at", "user_id", "created_at"),
        Index("idx_trips_trace_id", "trace_id"),
        {"comment": "用户保存的旅行行程表"},
    )
