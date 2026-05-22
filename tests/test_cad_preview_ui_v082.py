from pathlib import Path

from fastapi.testclient import TestClient

from backend.core.config import settings
from backend.main import app
from scripts.build_portable_package import DEFAULT_VERSION


ROOT = Path(__file__).resolve().parents[1]
VERSION = "v1.0-local-stable"


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_v082_health_and_portable_version_are_updated():
    with TestClient(app) as client:
        health = client.get("/api/health")

    assert health.status_code == 200
    assert health.json()["version"] == VERSION
    assert settings.version == VERSION
    assert DEFAULT_VERSION == VERSION


def test_cad_preview_viewer_component_contains_required_controls():
    content = read_text("frontend/src/components/CadPreviewViewer.tsx")

    for text in ["放大", "缩小", "适应窗口", "100%", "重置", "重新生成", "下载预览图", "缩放："]:
        assert text in content
    assert "onWheel" in content
    assert "onPointerDown" in content
    assert "onPointerMove" in content
    assert "imageVersion" in content
    assert "displayImageUrl" in content


def test_cad_preview_viewer_is_used_in_sheet_detail_and_ledger_entry():
    content = read_text("frontend/src/main.tsx")

    assert "CadPreviewViewer" in content
    assert "查看 CAD 预览" in content
    assert "getCadPreviewImageUrl(previewSheet.id)" in content


def test_v082_docs_include_frontend_interaction_guidance():
    readme = read_text("README.md")
    local_readme = read_text("README_本地使用说明.md")
    release_notes = read_text("RELEASE_NOTES.md")

    assert "## v0.8.2 CAD 预览前端交互优化" in readme
    assert "CAD 预览查看操作" in local_readme
    assert "v1.0-local-stable 发布说明" in release_notes
    assert "拖拽平移" in release_notes


def test_v083_docs_and_frontend_include_batch_preview_guidance():
    readme = read_text("README.md")
    local_readme = read_text("README_本地使用说明.md")
    release_notes = read_text("RELEASE_NOTES.md")
    main = read_text("frontend/src/main.tsx")

    assert "## v0.8.3 CAD 预览批量生成与性能优化" in readme
    assert "CAD 批量预览说明" in local_readme
    assert "v0.8.3 是 CAD 预览批量生成与性能优化版本" in release_notes
    assert "批量预览跳过已生成" in main
    assert "强制重新生成预览" in main
    assert "项目级批量生成 CAD 预览" in main


def test_v084_docs_include_stable_release_materials():
    readme = read_text("README.md")
    local_readme = read_text("README_本地使用说明.md")
    release_notes = read_text("RELEASE_NOTES.md")

    assert "## v0.8.4 CAD 预览稳定版收口与真实项目回归" in readme
    assert "CAD 预览稳定版说明" in local_readme
    assert "v1.0-local-stable 发布说明" in release_notes
    assert (ROOT / "docs" / "CAD_PREVIEW_STABILITY_REPORT_v0.8.4.md").exists()
    assert (ROOT / "docs" / "RELEASE_CHECKLIST_v1.0-local-stable.md").exists()
    assert (ROOT / "samples" / "cad_preview_stability_v0_8_4" / "README.md").exists()
