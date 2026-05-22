from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class CadConversionRun(Base):
    __tablename__ = "cad_conversion_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_file_id: Mapped[int] = mapped_column(
        ForeignKey("drawing_files.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_format: Mapped[str] = mapped_column(String(20), nullable=False)
    target_format: Mapped[str] = mapped_column(String(20), nullable=False)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    target_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    converter_name: Mapped[str] = mapped_column(String(120), nullable=False)
    converter_exe_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    stdout_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    stderr_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
