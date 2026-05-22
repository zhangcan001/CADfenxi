"""Add project backup and restore record tables.

Revision ID: 0002_backup_restore_records
Revises: 0001_baseline
Create Date: 2026-05-22
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_backup_restore_records"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not _has_table("backup_records"):
        op.create_table(
            "backup_records",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("project_id", sa.Integer(), nullable=False),
            sa.Column("backup_type", sa.String(length=32), nullable=False),
            sa.Column("file_name", sa.String(length=255), nullable=False),
            sa.Column("file_path", sa.Text(), nullable=False),
            sa.Column("file_size", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("error_code", sa.String(length=64), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_backup_records_id"), "backup_records", ["id"], unique=False)
        op.create_index(op.f("ix_backup_records_project_id"), "backup_records", ["project_id"], unique=False)

    if not _has_table("restore_records"):
        op.create_table(
            "restore_records",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("source_backup_id", sa.Integer(), nullable=True),
            sa.Column("source_project_name", sa.String(length=200), nullable=True),
            sa.Column("new_project_id", sa.Integer(), nullable=True),
            sa.Column("restore_mode", sa.String(length=32), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("error_code", sa.String(length=64), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["new_project_id"], ["projects.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["source_backup_id"], ["backup_records.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_restore_records_id"), "restore_records", ["id"], unique=False)
        op.create_index(op.f("ix_restore_records_new_project_id"), "restore_records", ["new_project_id"], unique=False)
        op.create_index(op.f("ix_restore_records_source_backup_id"), "restore_records", ["source_backup_id"], unique=False)


def downgrade() -> None:
    pass
