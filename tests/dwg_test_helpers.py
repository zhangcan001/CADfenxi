import io
import time
from pathlib import Path

import ezdxf
from fastapi.testclient import TestClient

from backend.core.database import SessionLocal, init_database
from backend.models.cad_conversion_run import CadConversionRun
from backend.models.converter_setting import ConverterSetting


DWG_BYTES = b"mock dwg bytes"
DXF_TEXT = "0\nSECTION\n2\nENTITIES\n0\nTEXT\n8\n0\n10\n0\n20\n0\n30\n0\n40\n2.5\n1\nA-001\n0\nENDSEC\n0\nEOF\n"


def create_project(client: TestClient, name: str = "DWG 转换测试") -> int:
    response = client.post("/api/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def upload_dwg(client: TestClient, project_id: int, name: str = "sample.dwg") -> dict:
    response = client.post(
        f"/api/projects/{project_id}/imports",
        files=[("files", (name, DWG_BYTES, "application/acad"))],
    )
    assert response.status_code == 201
    return response.json()


def upload_dxf(client: TestClient, project_id: int, name: str = "sample.dxf") -> dict:
    response = client.post(
        f"/api/projects/{project_id}/imports",
        files=[("files", (name, DXF_TEXT.encode("utf-8"), "application/dxf"))],
    )
    assert response.status_code == 201
    return response.json()


def clear_converter_tables() -> None:
    init_database()
    with SessionLocal() as db:
        db.query(CadConversionRun).delete()
        db.query(ConverterSetting).delete()
        db.commit()


def write_mock_converter(tmp_path: Path, mode: str = "success") -> Path:
    script = tmp_path / f"mock_converter_{mode}.py"
    if mode == "success":
        body = f"""
import sys
from pathlib import Path

if len(sys.argv) == 1:
    raise SystemExit(0)
input_dir = Path(sys.argv[1])
output_dir = Path(sys.argv[2])
output_dir.mkdir(parents=True, exist_ok=True)
for source in input_dir.glob("*.dwg"):
    (output_dir / (source.stem + ".dxf")).write_text({DXF_TEXT!r}, encoding="utf-8")
raise SystemExit(0)
"""
    elif mode == "failed":
        body = """
import sys

if len(sys.argv) == 1:
    raise SystemExit(0)
print("mock converter failed", file=sys.stderr)
raise SystemExit(2)
"""
    else:
        body = """
import sys

if len(sys.argv) == 1:
    raise SystemExit(0)
raise SystemExit(0)
"""
    script.write_text(body.strip() + "\n", encoding="utf-8")
    return script


def wait_for_cad_pipeline_job(
    client: TestClient, batch_id: int, timeout_s: float = 120.0
) -> dict:
    """Poll /cad-pipeline/job until the job leaves the running state."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        response = client.get(f"/api/imports/{batch_id}/cad-pipeline/job")
        assert response.status_code == 200, response.text
        job = response.json()
        if job is None:
            time.sleep(0.05)
            continue
        if job["status"] != "running":
            return job
        time.sleep(0.05)
    raise AssertionError(f"cad-pipeline job did not finish within {timeout_s}s")


def run_cad_pipeline_blocking(
    client: TestClient, batch_id: int, payload: dict, timeout_s: float = 120.0
) -> dict:
    """POST /cad-pipeline + 等待 job 完成，返回 result_summary（与旧同步路由一致的 shape）。"""
    start = client.post(f"/api/imports/{batch_id}/cad-pipeline", json=payload)
    assert start.status_code == 200, start.text
    job = wait_for_cad_pipeline_job(client, batch_id, timeout_s=timeout_s)
    summary = job.get("result_summary")
    assert summary is not None, f"missing result_summary on job: {job}"
    return summary


def create_converter_setting(client: TestClient, converter_path: Path) -> dict:
    response = client.post(
        "/api/cad/converter-settings",
        json={
            "converter_name": "Mock Converter",
            "converter_exe_path": str(converter_path),
            "output_version": "ACAD2018",
            "output_type": "DXF",
            "is_enabled": True,
        },
    )
    assert response.status_code == 200
    return response.json()


def equipment_schedule_dxf(
    rows: list[list[str]] | None = None,
    *,
    header: list[str] | None = None,
    row_height: float = 8.0,
    col_widths: list[float] | None = None,
    origin: tuple[float, float] = (0.0, 1000.0),
    text_height: float = 2.5,
) -> bytes:
    """合成一个 N×M 文字伪表格 DXF。

    默认 header = ["设备名", "型号", "数量", "备注"]，rows 行高 8 单位。
    每个 cell 都用 TEXT 实体落在 (x, y)，跨行 y 递减。
    """
    if header is None:
        header = ["设备名", "型号", "数量", "备注"]
    if rows is None:
        rows = [
            ["送风机", "FJ-1", "2", "备用 1 台"],
            ["排风机", "FJ-2", "3", ""],
            ["照明配电箱", "AL-1", "5", "嵌入式"],
            ["动力配电箱", "AP-1", "4", "明装"],
        ]
    cols = len(header)
    if col_widths is None:
        col_widths = [60.0] * cols
    elif len(col_widths) < cols:
        col_widths = list(col_widths) + [60.0] * (cols - len(col_widths))

    x0, y_top = origin
    xs: list[float] = []
    cursor = x0
    for w in col_widths:
        xs.append(cursor)
        cursor += w

    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    grid = [header, *rows]
    for r_idx, row in enumerate(grid):
        y = y_top - r_idx * row_height
        for c_idx, cell in enumerate(row):
            text_value = str(cell)
            if not text_value:
                continue
            msp.add_text(
                text_value,
                dxfattribs={
                    "layer": "TABLE",
                    "insert": (xs[c_idx], y, 0),
                    "height": text_height,
                },
            )
    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")


def acad_table_dxf(
    cells: list[list[str]] | None = None,
    *,
    origin: tuple[float, float] = (0.0, 0.0),
) -> bytes:
    """合成一个含真正 ACAD_TABLE 实体的 DXF。

    ezdxf 1.x 暴露 modelspace().add_table()。若当前环境 add_table 不可用，
    退化为 equipment_schedule_dxf 文字表（让伪表格路径接管）。
    """
    if cells is None:
        cells = [
            ["材料名", "规格", "数量", "单位"],
            ["镀锌钢管", "DN25", "100", "米"],
            ["镀锌钢管", "DN32", "80", "米"],
            ["闸阀", "DN25", "10", "个"],
        ]
    doc = ezdxf.new("R2018")
    msp = doc.modelspace()
    try:
        add_table = getattr(msp, "add_table", None)
        if add_table is None:
            raise AttributeError("modelspace has no add_table")
        n_rows = len(cells)
        n_cols = len(cells[0]) if cells else 0
        table = add_table(
            insert=origin,
            nrows=n_rows,
            ncols=n_cols,
            cell_width=40.0,
            cell_height=8.0,
        )
        for r, row in enumerate(cells):
            for c, value in enumerate(row):
                try:
                    table.set_text(r, c, str(value))
                except Exception:  # noqa: BLE001
                    pass
    except (AttributeError, TypeError):
        return equipment_schedule_dxf(cells[1:], header=cells[0])
    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")


def wait_for_extract_tables_job(
    client: TestClient, batch_id: int, timeout_s: float = 60.0
) -> dict:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        response = client.get(f"/api/imports/{batch_id}/extract-tables/job")
        assert response.status_code == 200, response.text
        job = response.json()
        if job is None:
            time.sleep(0.05)
            continue
        if job["status"] != "running":
            return job
        time.sleep(0.05)
    raise AssertionError(f"extract-tables job did not finish within {timeout_s}s")
