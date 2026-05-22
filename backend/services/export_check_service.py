from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.drawing_issue import DrawingIssue
from backend.models.drawing_sheet import DrawingSheet
from backend.schemas.export import ExportCheckResult


def check_project_export(db: Session, project_id: int) -> ExportCheckResult:
    sheet_count = db.scalar(
        select(func.count()).select_from(DrawingSheet).where(DrawingSheet.project_id == project_id)
    ) or 0
    unconfirmed_count = db.scalar(
        select(func.count())
        .select_from(DrawingSheet)
        .where(DrawingSheet.project_id == project_id, DrawingSheet.review_status != "confirmed")
    ) or 0
    open_error_count = db.scalar(
        select(func.count())
        .select_from(DrawingIssue)
        .where(
            DrawingIssue.project_id == project_id,
            DrawingIssue.status == "open",
            DrawingIssue.severity == "error",
        )
    ) or 0
    open_warning_count = db.scalar(
        select(func.count())
        .select_from(DrawingIssue)
        .where(
            DrawingIssue.project_id == project_id,
            DrawingIssue.status == "open",
            DrawingIssue.severity == "warning",
        )
    ) or 0
    open_error_sheet_count = issue_sheet_count(db, project_id, "error")
    open_warning_sheet_count = issue_sheet_count(db, project_id, "warning")
    failed_count = db.scalar(
        select(func.count())
        .select_from(DrawingSheet)
        .where(DrawingSheet.project_id == project_id, DrawingSheet.status == "failed")
    ) or 0
    empty_drawing_no_count = db.scalar(
        select(func.count())
        .select_from(DrawingSheet)
        .where(
            DrawingSheet.project_id == project_id,
            (DrawingSheet.drawing_no.is_(None)) | (DrawingSheet.drawing_no == ""),
        )
    ) or 0
    empty_drawing_name_count = db.scalar(
        select(func.count())
        .select_from(DrawingSheet)
        .where(
            DrawingSheet.project_id == project_id,
            (DrawingSheet.drawing_name.is_(None)) | (DrawingSheet.drawing_name == ""),
        )
    ) or 0
    empty_discipline_count = db.scalar(
        select(func.count())
        .select_from(DrawingSheet)
        .where(
            DrawingSheet.project_id == project_id,
            (DrawingSheet.discipline.is_(None)) | (DrawingSheet.discipline == ""),
        )
    ) or 0
    trust_level_d_count = db.scalar(
        select(func.count())
        .select_from(DrawingSheet)
        .where(DrawingSheet.project_id == project_id, DrawingSheet.trust_level == "D")
    ) or 0
    duplicate_drawing_no_count = duplicate_count(db, project_id)
    warnings = build_warnings(
        sheet_count,
        unconfirmed_count,
        open_error_count,
        failed_count,
        empty_drawing_no_count,
        empty_drawing_name_count,
        trust_level_d_count,
        duplicate_drawing_no_count,
    )
    summary_message = build_summary_message(
        sheet_count,
        unconfirmed_count,
        empty_drawing_no_count,
        empty_drawing_name_count,
        open_error_count,
        open_warning_count,
        trust_level_d_count,
    )
    return ExportCheckResult(
        can_export=sheet_count > 0,
        is_complete_ledger=len(warnings) == 0,
        summary_message=summary_message,
        sheet_count=sheet_count,
        unconfirmed_count=unconfirmed_count,
        open_error_count=open_error_count,
        open_warning_count=open_warning_count,
        open_error_sheet_count=open_error_sheet_count,
        open_warning_sheet_count=open_warning_sheet_count,
        failed_count=failed_count,
        empty_drawing_no_count=empty_drawing_no_count,
        empty_drawing_name_count=empty_drawing_name_count,
        empty_discipline_count=empty_discipline_count,
        trust_level_d_count=trust_level_d_count,
        duplicate_drawing_no_count=duplicate_drawing_no_count,
        warning_count=len(warnings),
        warnings=warnings,
    )


def issue_sheet_count(db: Session, project_id: int, severity: str) -> int:
    return db.scalar(
        select(func.count(func.distinct(DrawingIssue.sheet_id)))
        .where(
            DrawingIssue.project_id == project_id,
            DrawingIssue.status == "open",
            DrawingIssue.severity == severity,
        )
    ) or 0


def duplicate_count(db: Session, project_id: int) -> int:
    rows = db.execute(
        select(DrawingSheet.drawing_no, func.count(DrawingSheet.id))
        .where(
            DrawingSheet.project_id == project_id,
            DrawingSheet.drawing_no.is_not(None),
            DrawingSheet.drawing_no != "",
        )
        .group_by(DrawingSheet.drawing_no)
        .having(func.count(DrawingSheet.id) > 1)
    ).all()
    return sum(count for _, count in rows)


def build_warnings(
    sheet_count: int,
    unconfirmed_count: int,
    open_error_count: int,
    failed_count: int,
    empty_drawing_no_count: int,
    empty_drawing_name_count: int,
    trust_level_d_count: int,
    duplicate_drawing_no_count: int,
) -> list[str]:
    warnings = []
    if sheet_count == 0:
        warnings.append("当前项目没有任何图纸，无法导出")
    if unconfirmed_count:
        warnings.append(f"当前仍有 {unconfirmed_count} 张图纸未确认")
    if open_error_count:
        warnings.append(f"当前仍有 {open_error_count} 个 open error 问题")
    if failed_count:
        warnings.append(f"当前仍有 {failed_count} 张识别失败图纸")
    if empty_drawing_no_count:
        warnings.append(f"当前仍有 {empty_drawing_no_count} 张图纸图号为空")
    if empty_drawing_name_count:
        warnings.append(f"当前仍有 {empty_drawing_name_count} 张图纸图名为空")
    if trust_level_d_count:
        warnings.append(f"当前仍有 {trust_level_d_count} 张 D 级低可信图纸")
    if duplicate_drawing_no_count:
        warnings.append(f"当前存在 {duplicate_drawing_no_count} 张重复图号图纸")
    return warnings


def build_summary_message(
    sheet_count: int,
    unconfirmed_count: int,
    empty_drawing_no_count: int,
    empty_drawing_name_count: int,
    open_error_count: int,
    open_warning_count: int,
    trust_level_d_count: int,
) -> str:
    if sheet_count == 0:
        return "当前项目没有图纸，无法导出 Excel 台账。"
    parts = [
        f"当前项目共有 {sheet_count} 张图纸",
        f"其中 {unconfirmed_count} 张未校核",
        f"{empty_drawing_no_count} 张缺图号",
        f"{empty_drawing_name_count} 张缺图名",
        f"{open_error_count} 个错误",
        f"{open_warning_count} 个警告",
        f"{trust_level_d_count} 张 D 级图纸",
    ]
    if any([unconfirmed_count, empty_drawing_no_count, empty_drawing_name_count, open_error_count, open_warning_count, trust_level_d_count]):
        return "，".join(parts) + "。仍可导出 Excel，但建议在正式使用前复核上述图纸。"
    return f"当前项目共有 {sheet_count} 张图纸，未发现导出前风险提示。"
