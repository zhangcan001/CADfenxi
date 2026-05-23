from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CADFENXI_",
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "工程图纸智能台账识别系统"
    app_version: str = "v1.0.2-fast-stable"

    root_dir: Path = ROOT_DIR
    frontend_dist_dir: Path = ROOT_DIR / "frontend" / "dist"
    app_data_dir: Path = ROOT_DIR / "app_data"
    projects_dir: Path = ROOT_DIR / "app_data" / "projects"
    backups_dir: Path = ROOT_DIR / "app_data" / "backups"
    database_dir: Path = ROOT_DIR / "app_data" / "database"
    logs_dir: Path = ROOT_DIR / "app_data" / "logs"
    temp_dir: Path = ROOT_DIR / "app_data" / "temp"
    database_path: Path = ROOT_DIR / "app_data" / "database" / "app.db"
    log_path: Path = ROOT_DIR / "app_data" / "logs" / "app.log"

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    upload_max_bytes: int = 200 * 1024 * 1024
    convert_timeout_seconds: int = 120
    converter_log_limit: int = 5000
    preview_max_width: int = 1800
    thumbnail_max_width: int = 320

    @property
    def version(self) -> str:
        return self.app_version

    @property
    def APP_VERSION(self) -> str:
        return self.app_version

    @property
    def storage_dirs(self) -> tuple[Path, ...]:
        return (
            self.projects_dir,
            self.backups_dir,
            self.database_dir,
            self.logs_dir,
            self.temp_dir,
        )

    def ensure_storage(self) -> None:
        for directory in self.storage_dirs:
            directory.mkdir(parents=True, exist_ok=True)

    def check_storage(self) -> bool:
        try:
            self.ensure_storage()
            test_file = self.temp_dir / ".storage_check"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink(missing_ok=True)
            return True
        except OSError:
            return False


settings = Settings()
