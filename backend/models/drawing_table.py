from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class DrawingTable(Base):
    __tablename__ = "drawing_tables"

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
    table_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extraction_method: Mapped[str] = mapped_column(String(32), nullable=False)
    table_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="other")
    layer_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    header_json: Mapped[str] = mapped_column(Text, nullable=False)
    rows_json: Mapped[str] = mapped_column(Text, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    col_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_bbox_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    warnings_json: Mapped[str | None] = mapped_column(Text, nullable=True)
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
        Index("ix_drawing_tables_sheet", "sheet_id"),
        Index("ix_drawing_tables_project_kind", "project_id", "table_kind"),
    )
