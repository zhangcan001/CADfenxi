"""Create generic background_jobs table.

Revision ID: 0005_background_jobs_table
Revises: 0004_import_batch_ocr_job
Create Date: 2026-05-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005_background_jobs_table"
down_revision: Union[str, None] = "0004_import_batch_ocr_job"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _has_index(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    if not _has_table("background_jobs"):
        op.create_table(
            "background_jobs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("job_type", sa.String(length=32), nullable=False),
            sa.Column("scope_type", sa.String(length=16), nullable=False),
            sa.Column("scope_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("processed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("current_step", sa.String(length=64), nullable=True),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("payload_json", sa.Text(), nullable=True),
            sa.Column("result_summary_json", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
    if not _has_index("background_jobs", "ix_background_jobs_scope"):
        op.create_index(
            "ix_background_jobs_scope",
            "background_jobs",
            ["job_type", "scope_type", "scope_id"],
        )
    if not _has_index("background_jobs", "ix_background_jobs_status"):
        op.create_index(
            "ix_background_jobs_status",
            "background_jobs",
            ["status"],
        )


def downgrade() -> None:
    pass
