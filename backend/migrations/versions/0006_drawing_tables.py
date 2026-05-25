"""Create drawing_tables table for DXF table extraction.

Revision ID: 0006_drawing_tables
Revises: 0005_background_jobs_table
Create Date: 2026-05-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006_drawing_tables"
down_revision: Union[str, None] = "0005_background_jobs_table"
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
    if not _has_table("drawing_tables"):
        op.create_table(
            "drawing_tables",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "project_id",
                sa.Integer(),
                sa.ForeignKey("projects.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "batch_id",
                sa.Integer(),
                sa.ForeignKey("import_batches.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "file_id",
                sa.Integer(),
                sa.ForeignKey("drawing_files.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "sheet_id",
                sa.Integer(),
                sa.ForeignKey("drawing_sheets.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("table_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("extraction_method", sa.String(length=32), nullable=False),
            sa.Column(
                "table_kind",
                sa.String(length=32),
                nullable=False,
                server_default="other",
            ),
            sa.Column("layer_name", sa.String(length=100), nullable=True),
            sa.Column("header_json", sa.Text(), nullable=False),
            sa.Column("rows_json", sa.Text(), nullable=False),
            sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("col_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("source_bbox_json", sa.Text(), nullable=True),
            sa.Column("warnings_json", sa.Text(), nullable=True),
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
    if not _has_index("drawing_tables", "ix_drawing_tables_sheet"):
        op.create_index(
            "ix_drawing_tables_sheet",
            "drawing_tables",
            ["sheet_id"],
        )
    if not _has_index("drawing_tables", "ix_drawing_tables_project_kind"):
        op.create_index(
            "ix_drawing_tables_project_kind",
            "drawing_tables",
            ["project_id", "table_kind"],
        )


def downgrade() -> None:
    pass
