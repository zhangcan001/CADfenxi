from pathlib import Path


class Settings:
    app_name = "工程图纸智能台账识别系统"
    APP_VERSION = "v0.6.2-rule-fix"
    version = APP_VERSION

    root_dir = Path(__file__).resolve().parents[2]
    frontend_dist_dir = root_dir / "frontend" / "dist"
    app_data_dir = root_dir / "app_data"
    projects_dir = app_data_dir / "projects"
    database_dir = app_data_dir / "database"
    logs_dir = app_data_dir / "logs"
    temp_dir = app_data_dir / "temp"
    database_path = database_dir / "app.db"
    log_path = logs_dir / "app.log"

    cors_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @property
    def storage_dirs(self) -> tuple[Path, ...]:
        return (
            self.projects_dir,
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
