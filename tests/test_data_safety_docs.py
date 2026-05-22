from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_v072_data_safety_documents_exist():
    assert (ROOT / "docs" / "APP_DATA_BACKUP_MIGRATION_GUIDE_v0.7.2.md").exists()
    assert (ROOT / "docs" / "DATA_SAFETY_CHECKLIST_v0.7.2.md").exists()
    assert (ROOT / "docs" / "BACKUP_RESTORE_FAQ_v0.7.2.md").exists()


def test_local_readme_contains_app_data_backup_migration_and_upgrade_guidance():
    content = read_text("README_本地使用说明.md")

    assert "## 数据备份与迁移" in content
    assert "全量 app_data 备份" in content
    assert "换电脑迁移" in content
    assert "升级 portable 保留数据" in content
    assert "关闭系统后复制整个 `app_data` 目录" in content


def test_release_notes_and_readme_include_v072_data_safety():
    release_notes = read_text("RELEASE_NOTES.md")
    readme = read_text("README.md")

    assert "v0.7.2-data-safety 发布说明" in release_notes
    assert "v0.7.2 是数据安全收口与全量 app_data 备份迁移指南版本" in release_notes
    assert "## v0.7.2 数据安全收口与全量 app_data 备份迁移指南" in readme
    assert "如果要备份全部数据，请关闭系统后复制整个 app_data 目录" in readme
