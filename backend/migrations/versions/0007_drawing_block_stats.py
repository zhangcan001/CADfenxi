"""Create drawing_block_stats table for INSERT block aggregation.

Revision ID: 0007_drawing_block_stats
Revises: 0006_drawing_tables
Create Date: 2026-05-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007_drawing_block_stats"
down_revision: Union[str, None] = "0006_drawing_tables"
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
    if not _has_table("drawing_block_stats"):
        op.create_table(
            "drawing_block_stats",
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
            sa.Column("block_name", sa.String(length=100), nullable=False),
            sa.Column("layer_name", sa.String(length=100), nullable=True),
            sa.Column("discipline_guess", sa.String(length=32), nullable=True),
            sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("sample_bbox_json", sa.Text(), nullable=True),
            sa.Column("attribs_summary_json", sa.Text(), nullable=True),
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
    if not _has_index("drawing_block_stats", "ix_block_stats_sheet"):
        op.create_index(
            "ix_block_stats_sheet",
            "drawing_block_stats",
            ["sheet_id"],
        )
    if not _has_index("drawing_block_stats", "ix_block_stats_project_block"):
        op.create_index(
            "ix_block_stats_project_block",
            "drawing_block_stats",
            ["project_id", "block_name"],
        )


def downgrade() -> None:
    pass
