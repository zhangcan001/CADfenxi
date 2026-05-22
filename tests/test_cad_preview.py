import zipfile
from pathlib import Path

import ezdxf
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.core.config import settings
from backend.core.database import SessionLocal
from backend.main import app
from backend.models.drawing_file import DrawingFile
from backend.models.drawing_sheet import DrawingSheet
from backend.services import cad_preview_service
from dwg_test_helpers import DWG_BYTES, clear_converter_tables, create_converter_setting, write_mock_converter
from test_full_flow_stability_v055 import make_pdf_bytes, title_block_dxf
from test_project_backup_restore import backup_project, create_project, upload_files


def prepare_dxf_sheet(client: TestClient, project_id: int, name: str = "cad-preview.dxf") -> tuple[int, int, int]:
    upload = upload_files(client, project_id, [(name, title_block_dxf("建施-80", "CAD 预览"), "application/dxf")])
    file_id = upload["files"][0]["id"]
    prepare = client.post(f"/api/files/{file_id}/prepare-dxf-sheet")
    assert prepare.status_code == 200, prepare.text
    return file_id, prepare.json()["sheet_id"], upload["id"]


def dxf_bytes_with_entities(draw) -> bytes:
    document = ezdxf.new("R2010")
    modelspace = document.modelspace()
    draw(modelspace)
    import io

    buffer = io.StringIO()
    document.write(buffer)
    return buffer.getvalue().encode("utf-8")


def test_dxf_sheet_can_generate_cad_preview_and_download_image():
    with TestClient(app) as client:
        project_id = create_project(client, "CAD 预览 DXF")
        _file_id, sheet_id, _batch_id = prepare_dxf_sheet(client, project_id)
        preview = client.post(f"/api/sheets/{sheet_id}/cad-preview")
        image = client.get(f"/api/sheets/{sheet_id}/cad-preview-image")
        sheet = client.get(f"/api/sheets/{sheet_id}").json()

    assert preview.status_code == 200, preview.text
    data = preview.json()
    assert data["status"] == "success"
    assert data["duration_seconds"] >= 0
    assert data["skipped_entity_count"] >= 0
    assert data["cad_preview_path"].endswith(f"cad/previews/sheet_{sheet_id}_cad_preview.png")
    assert (settings.root_dir / data["cad_preview_path"]).exists()
    assert image.status_code == 200
    assert image.content.startswith(b"\x89PNG")
    assert sheet["cad_preview_status"] == "success"
    assert sheet["cad_preview_url"] == f"/api/sheets/{sheet_id}/cad-preview-image"


def test_pdf_sheet_cad_preview_is_unsupported():
    with TestClient(app) as client:
        project_id = create_project(client, "CAD 预览 PDF 不支持")
        upload = upload_files(client, project_id, [("pdf-preview.pdf", make_pdf_bytes("图号 建施-81"), "application/pdf")])
        split = client.post(f"/api/files/{upload['files'][0]['id']}/split")
        sheet_id = split.json()["sheets"][0]["id"]
        response = client.post(f"/api/sheets/{sheet_id}/cad-preview")

    assert response.status_code == 400
    assert response.json()["detail"]["error_code"] == "CAD_PREVIEW_UNSUPPORTED_FORMAT"


def test_missing_sheet_and_missing_dxf_file_return_structured_errors():
    with TestClient(app) as client:
        missing_sheet = client.post("/api/sheets/999999999/cad-preview")
        project_id = create_project(client, "CAD 预览缺文件")
        file_id, sheet_id, _batch_id = prepare_dxf_sheet(client, project_id)
        with SessionLocal() as db:
            drawing_file = db.get(DrawingFile, file_id)
            assert drawing_file is not None
            (settings.root_dir / drawing_file.storage_path).unlink(missing_ok=True)
            db.commit()
        missing_file = client.post(f"/api/sheets/{sheet_id}/cad-preview")

    assert missing_sheet.status_code == 404
    assert missing_sheet.json()["detail"]["error_code"] == "SHEET_NOT_FOUND"
    assert missing_file.status_code == 404
    assert missing_file.json()["detail"]["error_code"] == "CAD_PREVIEW_FILE_NOT_FOUND"


def test_broken_and_empty_dxf_preview_fail_without_blocking_candidate_fusion_and_export():
    with TestClient(app) as client:
        project_id = create_project(client, "CAD 预览失败保护")
        upload = upload_files(client, project_id, [("broken.dxf", b"broken dxf", "application/dxf")])
        file_id = upload["files"][0]["id"]
        prepare = client.post(f"/api/files/{file_id}/prepare-dxf-sheet")
        sheet_id = prepare.json()["sheet_id"]
        preview = client.post(f"/api/sheets/{sheet_id}/cad-preview")

        ok_file_id, ok_sheet_id, _batch_id = prepare_dxf_sheet(client, project_id, "ok.dxf")
        ok_preview = client.post(f"/api/sheets/{ok_sheet_id}/cad-preview")
        ok_parse = client.post(f"/api/files/{ok_file_id}/parse-dxf")
        candidates = client.post(f"/api/sheets/{ok_sheet_id}/generate-candidates")
        fusion = client.post(f"/api/sheets/{ok_sheet_id}/fuse-fields")
        export = client.post(
            f"/api/projects/{project_id}/exports/excel",
            json={"confirm_incomplete": True, "include_issues": True, "filter": None},
        )

    assert preview.status_code == 200
    assert preview.json()["status"] == "failed"
    assert preview.json()["error_code"] in {"CAD_PREVIEW_DXF_OPEN_FAILED", "CAD_PREVIEW_RENDER_FAILED"}
    assert ok_preview.status_code == 200
    assert ok_preview.json()["status"] == "success"
    assert ok_parse.status_code == 200
    assert candidates.status_code == 200
    assert fusion.status_code == 200
    assert export.status_code == 200


def test_empty_dxf_returns_empty_drawing_failure():
    empty_dxf = b"0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nSECTION\n2\nENTITIES\n0\nENDSEC\n0\nEOF\n"
    with TestClient(app) as client:
        project_id = create_project(client, "CAD 预览空 DXF")
        upload = upload_files(client, project_id, [("empty.dxf", empty_dxf, "application/dxf")])
        prepare = client.post(f"/api/files/{upload['files'][0]['id']}/prepare-dxf-sheet")
        response = client.post(f"/api/sheets/{prepare.json()['sheet_id']}/cad-preview")

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["error_code"] == "CAD_PREVIEW_EMPTY_DRAWING"


def test_chinese_text_records_font_fallback_warning_and_renders(monkeypatch):
    monkeypatch.setattr(cad_preview_service, "resolve_cjk_font_file", lambda: None)
    dxf_bytes = dxf_bytes_with_entities(
        lambda msp: (
            msp.add_line((0, 0), (100, 0)),
            msp.add_text("中文图纸名称", dxfattribs={"height": 5}).set_placement((10, 10)),
        )
    )
    with TestClient(app) as client:
        project_id = create_project(client, "CAD 预览中文")
        upload = upload_files(client, project_id, [("中文.dxf", dxf_bytes, "application/dxf")])
        prepare = client.post(f"/api/files/{upload['files'][0]['id']}/prepare-dxf-sheet")
        response = client.post(f"/api/sheets/{prepare.json()['sheet_id']}/cad-preview")

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "CAD_PREVIEW_FONT_FALLBACK" in response.json()["warnings"]


def test_large_offset_and_tiny_extents_are_fitted_without_blank_preview():
    dxf_bytes = dxf_bytes_with_entities(
        lambda msp: (
            msp.add_line((10_000_000, 10_000_000), (10_000_001, 10_000_000)),
            msp.add_circle((10_000_000.5, 10_000_000.5), 0.2),
        )
    )
    with TestClient(app) as client:
        project_id = create_project(client, "CAD 预览偏移")
        upload = upload_files(client, project_id, [("offset.dxf", dxf_bytes, "application/dxf")])
        prepare = client.post(f"/api/files/{upload['files'][0]['id']}/prepare-dxf-sheet")
        response = client.post(f"/api/sheets/{prepare.json()['sheet_id']}/cad-preview")
        image = client.get(f"/api/sheets/{prepare.json()['sheet_id']}/cad-preview-image")

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert image.status_code == 200
    assert image.content.startswith(b"\x89PNG")


def test_invalid_extents_returns_structured_failure():
    dxf_bytes = dxf_bytes_with_entities(lambda msp: msp.add_line((1e13, 0), (1e13 + 1, 0)))
    with TestClient(app) as client:
        project_id = create_project(client, "CAD 预览异常范围")
        upload = upload_files(client, project_id, [("invalid-extents.dxf", dxf_bytes, "application/dxf")])
        prepare = client.post(f"/api/files/{upload['files'][0]['id']}/prepare-dxf-sheet")
        response = client.post(f"/api/sheets/{prepare.json()['sheet_id']}/cad-preview")

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["error_code"] == "CAD_PREVIEW_INVALID_EXTENTS"


def test_complex_entities_are_skipped_with_warning():
    dxf_bytes = dxf_bytes_with_entities(
        lambda msp: (
            msp.add_line((0, 0), (100, 100)),
            msp.add_hatch(color=7),
        )
    )
    with TestClient(app) as client:
        project_id = create_project(client, "CAD 预览复杂实体")
        upload = upload_files(client, project_id, [("complex.dxf", dxf_bytes, "application/dxf")])
        prepare = client.post(f"/api/files/{upload['files'][0]['id']}/prepare-dxf-sheet")
        response = client.post(f"/api/sheets/{prepare.json()['sheet_id']}/cad-preview")

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["skipped_entity_count"] >= 1
    assert any("CAD_PREVIEW_ENTITY_SKIPPED:HATCH" in item for item in response.json()["warnings"])


def test_only_complex_entities_returns_no_renderable_entity():
    dxf_bytes = dxf_bytes_with_entities(lambda msp: msp.add_hatch(color=7))
    with TestClient(app) as client:
        project_id = create_project(client, "CAD 预览无可渲染实体")
        upload = upload_files(client, project_id, [("no-renderable.dxf", dxf_bytes, "application/dxf")])
        prepare = client.post(f"/api/files/{upload['files'][0]['id']}/prepare-dxf-sheet")
        response = client.post(f"/api/sheets/{prepare.json()['sheet_id']}/cad-preview")

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["error_code"] == "CAD_PREVIEW_NO_RENDERABLE_ENTITY"
    assert response.json()["skipped_entity_count"] >= 1


def test_batch_cad_preview_continues_after_single_failure():
    with TestClient(app) as client:
        project_id = create_project(client, "CAD 预览批量")
        good_upload = upload_files(client, project_id, [("good.dxf", title_block_dxf("建施-82", "批量"), "application/dxf")])
        bad_upload = upload_files(client, project_id, [("bad.dxf", b"broken dxf", "application/dxf")])
        batch_id = good_upload["id"]
        good_prepare = client.post(f"/api/files/{good_upload['files'][0]['id']}/prepare-dxf-sheet")
        bad_prepare = client.post(f"/api/files/{bad_upload['files'][0]['id']}/prepare-dxf-sheet")
        with SessionLocal() as db:
            bad_sheet = db.get(DrawingSheet, bad_prepare.json()["sheet_id"])
            assert bad_sheet is not None
            bad_sheet.batch_id = batch_id
            bad_file = db.get(DrawingFile, bad_upload["files"][0]["id"])
            assert bad_file is not None
            bad_file.batch_id = batch_id
            db.commit()
        response = client.post(f"/api/imports/{batch_id}/cad-preview")

    assert good_prepare.status_code == 200
    assert bad_prepare.status_code == 200
    assert response.status_code == 200
    assert response.json()["summary"]["total_count"] == 2
    assert response.json()["summary"]["success_count"] == 1
    assert response.json()["summary"]["failed_count"] == 1


def test_dwg_converted_dxf_can_generate_cad_preview(tmp_path: Path):
    clear_converter_tables()
    converter = write_mock_converter(tmp_path)
    with TestClient(app) as client:
        create_converter_setting(client, converter)
        project_id = create_project(client, "CAD 预览 DWG")
        upload = upload_files(client, project_id, [("cad-preview.dwg", DWG_BYTES, "application/acad")])
        file_id = upload["files"][0]["id"]
        assert client.post(f"/api/files/{file_id}/convert-dwg-to-dxf").status_code == 200
        prepare = client.post(f"/api/files/{file_id}/prepare-dxf-sheet")
        preview = client.post(f"/api/sheets/{prepare.json()['sheet_id']}/cad-preview")

    assert preview.status_code == 200
    assert preview.json()["status"] == "success"


def test_backup_restore_keeps_cad_preview_file_and_remaps_path():
    with TestClient(app) as client:
        project_id = create_project(client, "CAD 预览备份恢复")
        _file_id, sheet_id, _batch_id = prepare_dxf_sheet(client, project_id)
        preview = client.post(f"/api/sheets/{sheet_id}/cad-preview")
        backup = backup_project(client, project_id)
        with zipfile.ZipFile(settings.root_dir / backup["file_path"]) as archive:
            names = archive.namelist()
        restore = client.post(f"/api/backups/{backup['backup_id']}/restore", json={"restore_mode": "new_project"})
        restored_project_id = restore.json()["new_project_id"]
        restored_sheets = client.get(f"/api/projects/{restored_project_id}/sheets?page_size=100").json()["items"]
        restored_sheet_id = restored_sheets[0]["id"]
        image = client.get(f"/api/sheets/{restored_sheet_id}/cad-preview-image")

    assert preview.status_code == 200
    assert any("files/cad/previews/" in name for name in names)
    assert restore.status_code == 200
    restored_path = restored_sheets[0]["cad_preview_path"]
    assert f"project_{restored_project_id}" in restored_path
    assert f"project_{project_id}" not in restored_path
    assert image.status_code == 200
    assert image.content.startswith(b"\x89PNG")
