"""Add OCR job tracking columns to import_batches.

Revision ID: 0004_import_batch_ocr_job
Revises: 0003_cad_preview_fields
Create Date: 2026-05-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004_import_batch_ocr_job"
down_revision: Union[str, None] = "0003_cad_preview_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _has_column("import_batches", "ocr_job_status"):
        op.add_column("import_batches", sa.Column("ocr_job_status", sa.String(length=16), nullable=True))
    if not _has_column("import_batches", "ocr_job_total"):
        op.add_column("import_batches", sa.Column("ocr_job_total", sa.Integer(), nullable=True))
    if not _has_column("import_batches", "ocr_job_processed"):
        op.add_column("import_batches", sa.Column("ocr_job_processed", sa.Integer(), nullable=True))
    if not _has_column("import_batches", "ocr_job_started_at"):
        op.add_column("import_batches", sa.Column("ocr_job_started_at", sa.DateTime(timezone=True), nullable=True))
    if not _has_column("import_batches", "ocr_job_finished_at"):
        op.add_column("import_batches", sa.Column("ocr_job_finished_at", sa.DateTime(timezone=True), nullable=True))
    if not _has_column("import_batches", "ocr_job_message"):
        op.add_column("import_batches", sa.Column("ocr_job_message", sa.Text(), nullable=True))


def downgrade() -> None:
    pass
