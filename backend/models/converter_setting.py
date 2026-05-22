from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class ConverterSetting(Base):
    __tablename__ = "converter_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    converter_name: Mapped[str] = mapped_column(String(120), nullable=False)
    converter_exe_path: Mapped[str] = mapped_column(Text, nullable=False)
    output_version: Mapped[str] = mapped_column(String(40), nullable=False, default="ACAD2018")
    output_type: Mapped[str] = mapped_column(String(20), nullable=False, default="DXF")
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_check_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_check_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
