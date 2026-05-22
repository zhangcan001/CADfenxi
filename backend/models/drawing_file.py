from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class DrawingFile(Base):
    __tablename__ = "drawing_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_ext: Mapped[str] = mapped_column(String(20), nullable=False)
    source_format: Mapped[str] = mapped_column(String(20), nullable=False, default="pdf")
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="imported")
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    parse_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    parse_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    converted_format: Mapped[str | None] = mapped_column(String(20), nullable=True)
    converted_file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    convert_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    convert_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    convert_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    batch: Mapped["ImportBatch"] = relationship(back_populates="files")
    sheets: Mapped[list["DrawingSheet"]] = relationship(
        back_populates="file", cascade="all, delete-orphan"
    )
