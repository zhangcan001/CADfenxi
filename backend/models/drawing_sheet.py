from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class DrawingSheet(Base):
    __tablename__ = "drawing_sheets"
    __table_args__ = (UniqueConstraint("file_id", "page_no", name="uq_file_page"),)

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
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    sheet_type: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    drawing_no: Mapped[str | None] = mapped_column(String(200), nullable=True)
    drawing_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    discipline: Mapped[str | None] = mapped_column(String(100), nullable=True)
    version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    trust_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="imported")
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    thumbnail_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    preview_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    title_crop_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    title_crop_bbox: Mapped[str | None] = mapped_column(Text, nullable=True)
    title_crop_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    title_crop_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title_crop_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    file: Mapped["DrawingFile"] = relationship(back_populates="sheets")
