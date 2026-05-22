import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from difflib import SequenceMatcher
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.cad_conversion_run import CadConversionRun
from backend.models.converter_setting import ConverterSetting
from backend.models.drawing_file import DrawingFile
from backend.models.import_batch import ImportBatch
from backend.schemas.cad_converter import (
    BatchDwgConvertResult,
    CadConversionRunRead,
    ConverterCheckResult,
    ConverterSettingCreate,
    ConverterSettingRead,
    ConverterSettingUpdate,
    DwgConvertResult,
)
from backend.services import file_storage_service

AMBIGUOUS_OUTPUT_CODE = "DWG_CONVERT_OUTPUT_AMBIGUOUS"


@dataclass(frozen=True)
class ConvertedOutputMatch:
    path: Path
    warning_code: str | None = None
    warning_message: str | None = None


def list_converter_settings(db: Session) -> list[ConverterSettingRead]:
    settings_rows = db.scalars(select(ConverterSetting).order_by(ConverterSetting.id.asc())).all()
    return [ConverterSettingRead.model_validate(row) for row in settings_rows]


def create_converter_setting(
    db: Session,
    payload: ConverterSettingCreate,
) -> ConverterSettingRead:
    data = payload.model_dump()
    data["converter_exe_path"] = validate_converter_path_string(data["converter_exe_path"])
    setting = ConverterSetting(**data)
    db.add(setting)
    db.commit()
    db.refresh(setting)
    return ConverterSettingRead.model_validate(setting)


def update_converter_setting(
    db: Session,
    setting_id: int,
    payload: ConverterSettingUpdate,
) -> ConverterSettingRead:
    setting = get_setting_or_404(db, setting_id)
    updates = payload.model_dump(exclude_unset=True)
    if "converter_exe_path" in updates and updates["converter_exe_path"] is not None:
        updates["converter_exe_path"] = validate_converter_path_string(updates["converter_exe_path"])
    for key, value in updates.items():
        setattr(setting, key, value)
    db.commit()
    db.refresh(setting)
    return ConverterSettingRead.model_validate(setting)


def validate_converter_path_string(raw_path: str) -> str:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        raise_converter_error(
            "CONVERTER_PATH_INVALID",
            "转换工具路径必须为绝对路径。",
        )
    return str(path)


def check_converter_setting(db: Session, setting_id: int) -> ConverterCheckResult:
    setting = get_setting_or_404(db, setting_id)
    exe_path = Path(setting.converter_exe_path)
    if not exe_path.exists() or not exe_path.is_file():
        db.execute(
            update(ConverterSetting)
            .where(ConverterSetting.id == setting.id)
            .values(last_check_status="failed", last_check_message="未找到转换工具，请检查路径。")
        )
        db.commit()
        raise_converter_error(
            "CONVERTER_NOT_FOUND",
            "未找到转换工具，请检查路径。",
            http_status=status.HTTP_404_NOT_FOUND,
        )
    if not is_executable_path(exe_path):
        db.execute(
            update(ConverterSetting)
            .where(ConverterSetting.id == setting.id)
            .values(last_check_status="failed", last_check_message="转换工具不可执行，请检查权限或文件类型。")
        )
        db.commit()
        raise_converter_error("CONVERTER_NOT_EXECUTABLE", "转换工具不可执行，请检查权限或文件类型。")

    try:
        result = subprocess.run(
            executable_command_prefix(exe_path),
            shell=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except PermissionError as exc:
        db.execute(
            update(ConverterSetting)
            .where(ConverterSetting.id == setting.id)
            .values(last_check_status="failed", last_check_message="转换工具不可执行，请检查权限。")
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_detail("CONVERTER_NOT_EXECUTABLE", "转换工具不可执行，请检查权限。"),
        ) from exc
    except subprocess.TimeoutExpired:
        result = subprocess.CompletedProcess([str(exe_path)], 0, "", "")
    except OSError as exc:
        db.execute(
            update(ConverterSetting)
            .where(ConverterSetting.id == setting.id)
            .values(last_check_status="failed", last_check_message="转换工具检测失败。")
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_detail("CONVERTER_CHECK_FAILED", "转换工具检测失败。"),
        ) from exc

    if result.returncode not in {0, 1}:
        message = clip_log(result.stderr or result.stdout or "转换工具检测失败。")
        db.execute(
            update(ConverterSetting)
            .where(ConverterSetting.id == setting.id)
            .values(last_check_status="failed", last_check_message=message)
        )
        db.commit()
        raise_converter_error("CONVERTER_CHECK_FAILED", message)

    db.execute(
        update(ConverterSetting)
        .where(ConverterSetting.id == setting.id)
        .values(last_check_status="ok", last_check_message="转换工具路径可用")
    )
    db.commit()
    return ConverterCheckResult(setting_id=setting.id, status="ok", message="转换工具路径可用")


def convert_dwg_file(db: Session, file_id: int) -> DwgConvertResult:
    drawing_file = db.get(DrawingFile, file_id)
    if drawing_file is None:
        raise_converter_error(
            "DWG_FILE_NOT_FOUND",
            "图纸文件不存在。",
            http_status=status.HTTP_404_NOT_FOUND,
        )
    if not is_dwg_file(drawing_file):
        raise_converter_error("DWG_CONVERT_UNSUPPORTED", "该接口仅支持 DWG 文件。")

    setting = active_converter_setting(db)
    validate_exe_path(setting)
    source_path = settings.root_dir / drawing_file.storage_path
    if not source_path.exists() or not source_path.is_file():
        raise_converter_error(
            "DWG_FILE_NOT_FOUND",
            "DWG 原始文件不存在。",
            http_status=status.HTTP_404_NOT_FOUND,
        )

    converted_dir = file_storage_service.project_converted_dir(drawing_file.project_id)
    converted_dir.mkdir(parents=True, exist_ok=True)
    target_path = unique_target_path(converted_dir, drawing_file)
    temp_expected = converted_dir / f"{source_path.stem}.dxf"
    started_at = datetime.now(UTC)

    run = CadConversionRun(
        project_id=drawing_file.project_id,
        batch_id=drawing_file.batch_id,
        source_file_id=drawing_file.id,
        source_format="dwg",
        target_format="dxf",
        source_path=relative_to_root(source_path),
        target_path=relative_to_root(target_path),
        converter_name=setting.converter_name,
        converter_exe_path=setting.converter_exe_path,
        status="running",
        started_at=started_at,
    )
    db.add(run)
    db.flush()
    temp_input_dir = settings.temp_dir / f"cad_conversion_{run.id}"

    try:
        temp_input_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, temp_input_dir / source_path.name)
        command = converter_command(setting, temp_input_dir, converted_dir)
        previous_outputs = snapshot_dxf_outputs(converted_dir)
        result = subprocess.run(
            command,
            shell=False,
            capture_output=True,
            text=True,
            timeout=settings.convert_timeout_seconds,
        )
        run.stdout_log = clip_log(result.stdout)
        run.stderr_log = clip_log(result.stderr)
        if result.returncode != 0:
            return fail_conversion(
                db,
                drawing_file,
                run,
                "DWG_CONVERT_FAILED",
                "DWG 转 DXF 失败，请检查转换工具输出。",
            )

        matched = find_converted_output(
            converted_dir,
            source_path,
            temp_expected,
            started_at,
            previous_outputs,
        )
        if matched is None:
            return fail_conversion(
                db,
                drawing_file,
                run,
                "DWG_CONVERT_OUTPUT_MISSING",
                "转换命令执行完成但未找到 DXF 输出文件。",
            )
        produced = matched.path
        if produced.resolve() != target_path.resolve():
            if target_path.exists():
                return fail_conversion(
                    db,
                    drawing_file,
                    run,
                    "DWG_CONVERT_OUTPUT_MISSING",
                    "转换输出目标已存在，未覆盖已有文件。",
                )
            produced.replace(target_path)

        run.status = "success"
        run.finished_at = datetime.now(UTC)
        run.target_path = relative_to_root(target_path)
        if matched.warning_code:
            run.error_code = matched.warning_code
            run.error_message = matched.warning_message
        drawing_file.convert_status = "success"
        drawing_file.converted_format = "dxf"
        drawing_file.converted_file_path = relative_to_root(target_path)
        drawing_file.convert_error_code = None
        drawing_file.convert_error_message = None
        db.commit()
        db.refresh(run)
        db.refresh(drawing_file)
        write_conversion_log(drawing_file.project_id, run)
        return DwgConvertResult(
            file_id=drawing_file.id,
            status="success",
            run_id=run.id,
            converted_file_path=drawing_file.converted_file_path,
            warning_code=matched.warning_code,
            warning_message=matched.warning_message,
        )
    except subprocess.TimeoutExpired as exc:
        run.stdout_log = clip_log(exc.stdout if isinstance(exc.stdout, str) else "")
        run.stderr_log = clip_log(exc.stderr if isinstance(exc.stderr, str) else "")
        return fail_conversion(
            db,
            drawing_file,
            run,
            "DWG_CONVERT_TIMEOUT",
            "DWG 转 DXF 超时。",
        )
    except OSError as exc:
        return fail_conversion(
            db,
            drawing_file,
            run,
            "DWG_CONVERT_FAILED",
            str(exc)[:500],
        )
    finally:
        shutil.rmtree(temp_input_dir, ignore_errors=True)


def convert_dwg_batch(db: Session, batch_id: int) -> BatchDwgConvertResult:
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise_converter_error(
            "IMPORT_BATCH_NOT_FOUND",
            "导入批次不存在。",
            http_status=status.HTTP_404_NOT_FOUND,
        )
    dwg_files = db.scalars(
        select(DrawingFile)
        .where(DrawingFile.batch_id == batch_id, DrawingFile.source_format == "dwg")
        .order_by(DrawingFile.id.asc())
    ).all()
    items: list[DwgConvertResult] = []
    success_count = 0
    failed_count = 0
    skipped_count = 0
    for drawing_file in dwg_files:
        try:
            item = convert_dwg_file(db, drawing_file.id)
        except HTTPException as exc:
            db.rollback()
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            item = DwgConvertResult(
                file_id=drawing_file.id,
                status="failed",
                error_code=detail.get("error_code", "DWG_CONVERT_FAILED"),
                error_message=detail.get("message", "DWG 转 DXF 失败。"),
            )
        if item.status == "success":
            success_count += 1
        else:
            failed_count += 1
        items.append(item)
    return BatchDwgConvertResult(
        batch_id=batch_id,
        total_count=len(dwg_files),
        success_count=success_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        items=items,
    )


def list_project_conversion_runs(db: Session, project_id: int) -> list[CadConversionRunRead]:
    runs = db.scalars(
        select(CadConversionRun)
        .where(CadConversionRun.project_id == project_id)
        .order_by(CadConversionRun.created_at.desc(), CadConversionRun.id.desc())
    ).all()
    return [CadConversionRunRead.model_validate(run) for run in runs]


def list_file_conversion_runs(db: Session, file_id: int) -> list[CadConversionRunRead]:
    runs = db.scalars(
        select(CadConversionRun)
        .where(CadConversionRun.source_file_id == file_id)
        .order_by(CadConversionRun.created_at.desc(), CadConversionRun.id.desc())
    ).all()
    return [CadConversionRunRead.model_validate(run) for run in runs]


def get_setting_or_404(db: Session, setting_id: int) -> ConverterSetting:
    setting = db.get(ConverterSetting, setting_id)
    if setting is None:
        raise_converter_error(
            "CONVERTER_NOT_CONFIGURED",
            "未配置转换工具。",
            http_status=status.HTTP_404_NOT_FOUND,
        )
    return setting


def active_converter_setting(db: Session) -> ConverterSetting:
    setting = db.scalar(
        select(ConverterSetting)
        .where(ConverterSetting.is_enabled.is_(True))
        .order_by(ConverterSetting.id.desc())
    )
    if setting is None:
        raise_converter_error("CONVERTER_NOT_CONFIGURED", "未配置转换工具。")
    return setting


def validate_exe_path(setting: ConverterSetting) -> None:
    exe_path = Path(setting.converter_exe_path)
    if not exe_path.exists() or not exe_path.is_file():
        raise_converter_error(
            "CONVERTER_NOT_FOUND",
            "未找到转换工具，请检查路径。",
            http_status=status.HTTP_404_NOT_FOUND,
        )
    if not is_executable_path(exe_path):
        raise_converter_error("CONVERTER_NOT_EXECUTABLE", "转换工具不可执行，请检查权限或文件类型。")


def converter_command(setting: ConverterSetting, input_dir: Path, output_dir: Path) -> list[str]:
    return [
        *executable_command_prefix(Path(setting.converter_exe_path)),
        str(input_dir),
        str(output_dir),
        setting.output_version,
        setting.output_type,
        "0",
        "1",
    ]


def executable_command_prefix(exe_path: Path) -> list[str]:
    if exe_path.suffix.lower() == ".py":
        return [sys.executable, str(exe_path)]
    return [str(exe_path)]


def is_executable_path(exe_path: Path) -> bool:
    if exe_path.suffix.lower() == ".py":
        return True
    if sys.platform.startswith("win"):
        return exe_path.suffix.lower() in {".exe", ".com", ".bat", ".cmd"}
    return exe_path.stat().st_mode & 0o111 != 0


def find_converted_output(
    converted_dir: Path,
    source_path: Path,
    expected: Path,
    started_at: datetime,
    previous_outputs: dict[Path, float] | None = None,
) -> ConvertedOutputMatch | None:
    if expected.exists() and expected.is_file() and output_is_new_or_updated(expected, previous_outputs):
        return ConvertedOutputMatch(expected)

    candidates = safe_dxf_candidates(converted_dir, started_at, previous_outputs)
    if not candidates:
        return None

    same_name = [
        item for item in candidates if item.stem.casefold() == source_path.stem.casefold()
    ]
    if len(same_name) == 1:
        return ConvertedOutputMatch(same_name[0])
    if len(same_name) > 1:
        return ambiguous_match(same_name, "发现多个同名 DXF 输出，已选择最近生成的文件。")

    prefixed = [
        item for item in candidates if item.stem.casefold().startswith(source_path.stem.casefold())
    ]
    if len(prefixed) == 1:
        return ConvertedOutputMatch(prefixed[0])
    if len(prefixed) > 1:
        return ambiguous_match(prefixed, "发现多个相近 DXF 输出，已选择最近生成的文件。")

    scored = sorted(
        (
            (SequenceMatcher(None, source_path.stem.casefold(), item.stem.casefold()).ratio(), item)
            for item in candidates
        ),
        key=lambda pair: (pair[0], pair[1].stat().st_mtime),
        reverse=True,
    )
    if scored and scored[0][0] >= 0.55:
        close = [item for score, item in scored if score >= max(scored[0][0] - 0.05, 0.55)]
        if len(close) == 1:
            return ConvertedOutputMatch(close[0])
        return ambiguous_match(close, "发现多个相似 DXF 输出，已选择最近生成的文件。")

    recent = sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True)
    if len(recent) == 1:
        return ConvertedOutputMatch(recent[0])
    return ambiguous_match(recent, "未找到同名 DXF，已选择最近生成的 DXF 文件。")


def snapshot_dxf_outputs(converted_dir: Path) -> dict[Path, float]:
    if not converted_dir.exists():
        return {}
    return {
        item.resolve(): item.stat().st_mtime
        for item in converted_dir.iterdir()
        if item.is_file() and item.suffix.casefold() == ".dxf"
    }


def output_is_new_or_updated(path: Path, previous_outputs: dict[Path, float] | None) -> bool:
    if previous_outputs is None:
        return True
    previous_mtime = previous_outputs.get(path.resolve())
    return previous_mtime is None or path.stat().st_mtime > previous_mtime


def safe_dxf_candidates(
    converted_dir: Path,
    started_at: datetime,
    previous_outputs: dict[Path, float] | None,
) -> list[Path]:
    start_ts = started_at.timestamp()
    candidates: list[Path] = []
    converted_root = converted_dir.resolve()
    for item in converted_dir.iterdir():
        if not item.is_file() or item.suffix.casefold() != ".dxf":
            continue
        try:
            item.resolve().relative_to(converted_root)
        except ValueError:
            continue
        if item.stat().st_mtime >= start_ts and output_is_new_or_updated(item, previous_outputs):
            candidates.append(item)
    return sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True)


def ambiguous_match(candidates: list[Path], message: str) -> ConvertedOutputMatch:
    chosen = sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True)[0]
    names = ", ".join(item.name for item in candidates[:5])
    return ConvertedOutputMatch(
        chosen,
        warning_code=AMBIGUOUS_OUTPUT_CODE,
        warning_message=f"{message}候选：{names}",
    )


def unique_target_path(converted_dir: Path, drawing_file: DrawingFile) -> Path:
    safe_name = file_storage_service.safe_filename(drawing_file.original_name, ".dxf")
    base = converted_dir / f"{drawing_file.id}_{safe_name}"
    if not base.exists():
        return base
    index = 1
    while True:
        candidate = converted_dir / f"{drawing_file.id}_{index}_{safe_name}"
        if not candidate.exists():
            return candidate
        index += 1


def fail_conversion(
    db: Session,
    drawing_file: DrawingFile,
    run: CadConversionRun,
    error_code: str,
    message: str,
) -> DwgConvertResult:
    run.status = "failed"
    run.finished_at = datetime.now(UTC)
    run.error_code = error_code
    run.error_message = message
    drawing_file.convert_status = "failed"
    drawing_file.convert_error_code = error_code
    drawing_file.convert_error_message = message
    db.commit()
    db.refresh(run)
    write_conversion_log(drawing_file.project_id, run)
    return DwgConvertResult(
        file_id=drawing_file.id,
        status="failed",
        run_id=run.id,
        error_code=error_code,
        error_message=message,
    )


def write_conversion_log(project_id: int, run: CadConversionRun) -> None:
    log_dir = file_storage_service.project_cad_log_dir(project_id)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"conversion_{run.id}.log"
    log_path.write_text(
        "\n".join(
            [
                f"status={run.status}",
                f"source={run.source_path}",
                f"target={run.target_path or ''}",
                f"error_code={run.error_code or ''}",
                f"error_message={run.error_message or ''}",
                "stdout:",
                run.stdout_log or "",
                "stderr:",
                run.stderr_log or "",
            ]
        ),
        encoding="utf-8",
    )


def is_dwg_file(drawing_file: DrawingFile) -> bool:
    return drawing_file.source_format == "dwg" or drawing_file.file_ext.lower() == ".dwg"


def relative_to_root(path: Path) -> str:
    return path.relative_to(settings.root_dir).as_posix()


def clip_log(value: str | None) -> str:
    return (value or "")[: settings.converter_log_limit]


def raise_converter_error(
    error_code: str,
    message: str,
    http_status: int = status.HTTP_400_BAD_REQUEST,
    extra: dict | None = None,
) -> None:
    raise HTTPException(
        status_code=http_status,
        detail=error_detail(error_code, message, extra),
    )


def error_detail(error_code: str, message: str, extra: dict | None = None) -> dict:
    return {"error_code": error_code, "message": message, "extra": extra or {}}
