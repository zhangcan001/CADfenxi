"""Add CAD preview fields to drawing sheets.

Revision ID: 0003_cad_preview_fields
Revises: 0002_backup_restore_records
Create Date: 2026-05-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_cad_preview_fields"
down_revision: Union[str, None] = "0002_backup_restore_records"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _has_column("drawing_sheets", "cad_preview_path"):
        op.add_column("drawing_sheets", sa.Column("cad_preview_path", sa.Text(), nullable=True))
    if not _has_column("drawing_sheets", "cad_preview_status"):
        op.add_column(
            "drawing_sheets",
            sa.Column("cad_preview_status", sa.String(length=32), nullable=False, server_default="pending"),
        )
    if not _has_column("drawing_sheets", "cad_preview_error_code"):
        op.add_column("drawing_sheets", sa.Column("cad_preview_error_code", sa.String(length=64), nullable=True))
    if not _has_column("drawing_sheets", "cad_preview_error_message"):
        op.add_column("drawing_sheets", sa.Column("cad_preview_error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    pass
