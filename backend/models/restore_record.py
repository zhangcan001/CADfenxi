from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class RestoreRecord(Base):
    __tablename__ = "restore_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_backup_id: Mapped[int | None] = mapped_column(
        ForeignKey("backup_records.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_project_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    new_project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    restore_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="new_project")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
