"""create call traces table."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "20260715_0002"
down_revision: str | None = "20260704_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "call_traces",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False, comment="调用追踪ID"),
        sa.Column("trace_id", sa.String(length=36), nullable=False, comment="请求链路ID"),
        sa.Column("span_id", sa.String(length=36), nullable=False, comment="当前调用ID"),
        sa.Column("parent_span_id", sa.String(length=36), nullable=True, comment="上级调用ID"),
        sa.Column("kind", sa.Enum("agent.llm", "mcp.client", "tool.execute"), nullable=False, comment="调用类型"),
        sa.Column("name", sa.String(length=128), nullable=False, comment="模型名或工具名"),
        sa.Column("status", sa.Enum("ok", "error"), nullable=False, comment="调用状态"),
        sa.Column("started_at", sa.DateTime(), nullable=False, comment="开始时间"),
        sa.Column("ended_at", sa.DateTime(), nullable=False, comment="结束时间"),
        sa.Column("duration_ms", sa.Integer(), nullable=False, comment="耗时毫秒"),
        sa.Column("input_summary", mysql.JSON(), nullable=True, comment="输入摘要"),
        sa.Column("output_summary", mysql.JSON(), nullable=True, comment="输出摘要"),
        sa.Column("error_type", sa.String(length=128), nullable=True, comment="异常类型"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="异常信息"),
        sa.Column("metadata", mysql.JSON(), nullable=True, comment="补充元数据"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False, comment="创建时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("span_id"),
        comment="智能体、MCP和工具调用追踪表",
    )
    op.create_index("idx_call_traces_trace_id", "call_traces", ["trace_id"])
    op.create_index("idx_call_traces_kind_started_at", "call_traces", ["kind", "started_at"])


def downgrade() -> None:
    op.drop_index("idx_call_traces_kind_started_at", table_name="call_traces")
    op.drop_index("idx_call_traces_trace_id", table_name="call_traces")
    op.drop_table("call_traces")
