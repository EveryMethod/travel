"""create auth tables."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "20260704_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False, comment="用户ID"),
        sa.Column("display_name", sa.String(length=80), nullable=False, comment="用户展示名称"),
        sa.Column("avatar_url", sa.String(length=512), nullable=True, comment="用户头像地址"),
        sa.Column("status", sa.Enum("active", "disabled"), server_default="active", nullable=False, comment="用户状态"),
        sa.Column("last_login_at", sa.DateTime(), nullable=True, comment="最后登录时间"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), nullable=False, comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        comment="用户主表",
    )
    op.create_index("idx_users_status", "users", ["status"])

    op.create_table(
        "oauth_provider_configs",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False, comment="第三方登录配置ID"),
        sa.Column("provider", sa.Enum("qq", "wechat"), nullable=False, comment="第三方登录平台"),
        sa.Column("app_id", sa.String(length=128), nullable=False, comment="应用ID"),
        sa.Column("app_secret", sa.String(length=255), nullable=False, comment="应用密钥"),
        sa.Column("redirect_uri", sa.String(length=512), nullable=False, comment="OAuth回调地址"),
        sa.Column("enabled", mysql.TINYINT(display_width=1), server_default="1", nullable=False, comment="是否启用"),
        sa.Column("scope", sa.String(length=255), nullable=True, comment="授权范围"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), nullable=False, comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider"),
        comment="第三方登录应用配置表",
    )

    op.create_table(
        "auth_sessions",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False, comment="登录会话ID"),
        sa.Column("user_id", mysql.BIGINT(unsigned=True), nullable=False, comment="关联用户ID"),
        sa.Column("refresh_token_hash", sa.String(length=255), nullable=False, comment="刷新令牌哈希值"),
        sa.Column("user_agent", sa.String(length=512), nullable=True, comment="登录设备 User-Agent"),
        sa.Column("ip_address", sa.String(length=45), nullable=True, comment="登录IP地址"),
        sa.Column("expires_at", sa.DateTime(), nullable=False, comment="会话过期时间"),
        sa.Column("revoked_at", sa.DateTime(), nullable=True, comment="会话撤销时间"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False, comment="创建时间"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("refresh_token_hash"),
        comment="登录会话表",
    )
    op.create_index("idx_sessions_expires_at", "auth_sessions", ["expires_at"])
    op.create_index("idx_sessions_user_id", "auth_sessions", ["user_id"])

    op.create_table(
        "user_oauth_accounts",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False, comment="第三方账号绑定ID"),
        sa.Column("user_id", mysql.BIGINT(unsigned=True), nullable=False, comment="关联用户ID"),
        sa.Column("provider", sa.Enum("qq", "wechat"), nullable=False, comment="第三方登录平台"),
        sa.Column("provider_open_id", sa.String(length=128), nullable=False, comment="第三方平台 OpenID"),
        sa.Column("provider_union_id", sa.String(length=128), nullable=True, comment="第三方平台 UnionID"),
        sa.Column("nickname", sa.String(length=80), nullable=True, comment="第三方平台昵称"),
        sa.Column("avatar_url", sa.String(length=512), nullable=True, comment="第三方平台头像地址"),
        sa.Column("raw_profile", mysql.JSON(), nullable=True, comment="第三方平台原始用户资料"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), nullable=False, comment="更新时间"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment="第三方登录账号绑定表",
    )
    op.create_index("idx_oauth_provider_union_id", "user_oauth_accounts", ["provider", "provider_union_id"])
    op.create_index("idx_oauth_user_id", "user_oauth_accounts", ["user_id"])
    op.create_index("uq_oauth_provider_open_id", "user_oauth_accounts", ["provider", "provider_open_id"], unique=True)

    op.create_table(
        "user_password_credentials",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False, comment="账号密码凭据ID"),
        sa.Column("user_id", mysql.BIGINT(unsigned=True), nullable=False, comment="关联用户ID"),
        sa.Column("email", sa.String(length=255), nullable=True, comment="登录邮箱"),
        sa.Column("username", sa.String(length=64), nullable=True, comment="登录用户名"),
        sa.Column("password_hash", sa.String(length=255), nullable=False, comment="密码哈希值"),
        sa.Column("password_algo", sa.String(length=32), server_default="bcrypt", nullable=False, comment="密码哈希算法"),
        sa.Column("password_updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False, comment="密码更新时间"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), nullable=False, comment="更新时间"),
        sa.CheckConstraint("email IS NOT NULL OR username IS NOT NULL", name="ck_password_email_or_username"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("username"),
        comment="账号密码登录凭据表",
    )


def downgrade() -> None:
    op.drop_table("user_password_credentials")
    op.drop_index("uq_oauth_provider_open_id", table_name="user_oauth_accounts")
    op.drop_index("idx_oauth_user_id", table_name="user_oauth_accounts")
    op.drop_index("idx_oauth_provider_union_id", table_name="user_oauth_accounts")
    op.drop_table("user_oauth_accounts")
    op.drop_index("idx_sessions_user_id", table_name="auth_sessions")
    op.drop_index("idx_sessions_expires_at", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_table("oauth_provider_configs")
    op.drop_index("idx_users_status", table_name="users")
    op.drop_table("users")
