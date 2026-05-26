from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class DrawingBlockStat(Base):
    __tablename__ = "drawing_block_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_id: Mapped[int] = mapped_column(
        ForeignKey("drawing_files.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sheet_id: Mapped[int] = mapped_column(
        ForeignKey("drawing_sheets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    block_name: Mapped[str] = mapped_column(String(100), nullable=False)
    layer_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    discipline_guess: Mapped[str | None] = mapped_column(String(32), nullable=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sample_bbox_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    attribs_summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_block_stats_sheet", "sheet_id"),
        Index("ix_block_stats_project_block", "project_id", "block_name"),
    )
