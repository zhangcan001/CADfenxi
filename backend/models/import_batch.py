from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    batch_name: Mapped[str] = mapped_column(String(200), nullable=False)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sheet_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recognized_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confirmed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    ocr_job_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    ocr_job_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ocr_job_processed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ocr_job_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ocr_job_finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ocr_job_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    files: Mapped[list["DrawingFile"]] = relationship(
        back_populates="batch", cascade="all, delete-orphan"
    )
