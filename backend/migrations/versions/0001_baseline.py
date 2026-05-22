"""Baseline schema from create_all + legacy column adds.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-05-22

This baseline assumes the schema is already created by
``Base.metadata.create_all`` (existing behavior). It exists so the Alembic
versioning table is initialised on fresh and upgraded installs alike. The
prior in-process ``ensure_lightweight_migrations`` ALTER chain has been
removed; existing deployments where those columns already exist will be
no-ops here.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DRAWING_FILE_COLUMNS = [
    ("error_code", sa.String(64)),
    ("source_format", sa.String(20)),
    ("parse_status", sa.String(32)),
    ("parse_error_code", sa.String(64)),
    ("parse_error_message", sa.Text()),
    ("converted_format", sa.String(20)),
    ("converted_file_path", sa.Text()),
    ("convert_status", sa.String(32)),
    ("convert_error_code", sa.String(64)),
    ("convert_error_message", sa.Text()),
]

DRAWING_SHEET_COLUMNS = [
    ("title_crop_bbox", sa.Text()),
    ("title_crop_status", sa.String(32)),
    ("title_crop_error_code", sa.String(64)),
    ("title_crop_error_message", sa.Text()),
]


def _add_missing(table: str, columns: list[tuple[str, sa.types.TypeEngine]]) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns(table)}
    for name, type_ in columns:
        if name in existing:
            continue
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(sa.Column(name, type_, nullable=True))


def upgrade() -> None:
    _add_missing("drawing_files", DRAWING_FILE_COLUMNS)
    _add_missing("drawing_sheets", DRAWING_SHEET_COLUMNS)


def downgrade() -> None:
    pass
