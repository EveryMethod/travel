"""create trips table."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "20260715_0003"
down_revision: str | None = "20260715_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trips",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False, comment="行程ID"),
        sa.Column("user_id", mysql.BIGINT(unsigned=True), nullable=False, comment="关联用户ID"),
        sa.Column("trace_id", sa.String(length=36), nullable=True, comment="生成链路ID"),
        sa.Column("destination", sa.String(length=120), nullable=False, comment="目的地"),
        sa.Column("days", sa.Integer(), nullable=False, comment="行程天数"),
        sa.Column("status", sa.Enum("completed"), server_default="completed", nullable=False, comment="行程状态"),
        sa.Column("request_json", mysql.JSON(), nullable=False, comment="原始规划请求"),
        sa.Column("plan_json", mysql.JSON(), nullable=False, comment="生成行程结果"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), nullable=False, comment="更新时间"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment="用户保存的旅行行程表",
    )
    op.create_index("idx_trips_user_created_at", "trips", ["user_id", "created_at"])
    op.create_index("idx_trips_trace_id", "trips", ["trace_id"])


def downgrade() -> None:
    op.drop_index("idx_trips_trace_id", table_name="trips")
    op.drop_index("idx_trips_user_created_at", table_name="trips")
    op.drop_table("trips")
