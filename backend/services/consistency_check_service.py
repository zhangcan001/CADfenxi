"""跨图纸一致性校验服务。

规则（project 级）：
- CROSS_DRAWING_NO_DUPLICATE: 同 project_id 内两张及以上 confirmed sheet 同 drawing_no
- CROSS_VERSION_SKIP: 同 (project, drawing_no) 版本号集合存在跳号（A,C 缺 B）
- CROSS_DISCIPLINE_PREFIX_MISMATCH: drawing_no 前缀推断的专业与 sheet.discipline 不一致
- CROSS_ISSUE_DATE_INCONSISTENT: 同 (project, drawing_no, version) 下 issue_date 多值
- CROSS_VERSION_DATE_REGRESS: 同 (project, drawing_no) 字典序更大的版本 issue_date 反而更早

每次跑校验前清掉旧的 CROSS_* open issue，避免重复堆积。
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date

from fastapi import HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.core.discipline_codes import infer_discipline_from_drawing_no
from backend.models.drawing_issue import DrawingIssue
from backend.models.drawing_sheet import DrawingSheet
from backend.models.project import Project
from backend.services import issue_service
from recognizer.normalizer.drawing_no import (
    is_blacklisted_drawing_no,
    is_plausible_drawing_no,
    is_supported_drawing_no,
    normalize_drawing_no,
)

logger = logging.getLogger(__name__)


CROSS_ISSUE_CODES = (
    "CROSS_DRAWING_NO_DUPLICATE",
    "CROSS_DRAWING_NAME_CONFLICT",
    "CROSS_VERSION_SKIP",
    "CROSS_DISCIPLINE_PREFIX_MISMATCH",
    "CROSS_ISSUE_DATE_INCONSISTENT",
    "CROSS_VERSION_DATE_REGRESS",
)


class ConsistencyCheckSummary(BaseModel):
    project_id: int
    checked_sheets: int = 0
    issues_created: int = 0
    by_code: dict[str, int] = Field(default_factory=dict)


def run_consistency_check(db: Session, project_id: int) -> ConsistencyCheckSummary:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "PROJECT_NOT_FOUND", "message": "项目不存在。"},
        )

    sheets = db.scalars(
        select(DrawingSheet)
        .where(DrawingSheet.project_id == project_id)
        .where(DrawingSheet.review_status == "confirmed")
        .order_by(DrawingSheet.id.asc())
    ).all()

    # 清掉旧的 CROSS_* open
    db.execute(
        delete(DrawingIssue)
        .where(DrawingIssue.project_id == project_id)
        .where(DrawingIssue.issue_code.in_(CROSS_ISSUE_CODES))
        .where(DrawingIssue.status == "open")
    )
    db.flush()

    by_code: dict[str, int] = {}

    _check_duplicate(db, sheets, by_code)
    _check_drawing_name_conflict(db, sheets, by_code)
    _check_version_skip(db, sheets, by_code)
    _check_discipline_prefix(db, sheets, by_code)
    _check_date_inconsistent(db, sheets, by_code)
    _check_version_date_regress(db, sheets, by_code)

    db.commit()
    return ConsistencyCheckSummary(
        project_id=project_id,
        checked_sheets=len(sheets),
        issues_created=sum(by_code.values()),
        by_code=by_code,
    )


def _check_duplicate(db: Session, sheets: list[DrawingSheet], by_code: dict[str, int]) -> None:
    groups: dict[str, list[DrawingSheet]] = defaultdict(list)
    for sheet in sheets:
        drawing_no = _valid_drawing_no(sheet)
        if drawing_no:
            groups[drawing_no].append(sheet)
    for drawing_no, group in groups.items():
        if len(group) <= 1:
            continue
        for sheet in group:
            issue_service.add_issue(
                db,
                project_id=sheet.project_id,
                batch_id=sheet.batch_id,
                file_id=sheet.file_id,
                sheet_id=sheet.id,
                issue_code="CROSS_DRAWING_NO_DUPLICATE",
                severity="warning",
                message=f"项目内多张图纸使用相同图号「{drawing_no}」，共 {len(group)} 张。",
                suggestion="请核对是否为同一图号不同版本、分册，或图号录入错误。",
            )
            by_code["CROSS_DRAWING_NO_DUPLICATE"] = by_code.get(
                "CROSS_DRAWING_NO_DUPLICATE", 0
            ) + 1


def _check_drawing_name_conflict(
    db: Session, sheets: list[DrawingSheet], by_code: dict[str, int]
) -> None:
    groups: dict[str, list[DrawingSheet]] = defaultdict(list)
    for sheet in sheets:
        drawing_no = _valid_drawing_no(sheet)
        if drawing_no:
            groups[drawing_no].append(sheet)
    for drawing_no, group in groups.items():
        names = sorted({(sheet.drawing_name or "").strip() for sheet in group if sheet.drawing_name})
        if len(names) <= 1:
            continue
        for sheet in group:
            issue_service.add_issue(
                db,
                project_id=sheet.project_id,
                batch_id=sheet.batch_id,
                file_id=sheet.file_id,
                sheet_id=sheet.id,
                issue_code="CROSS_DRAWING_NAME_CONFLICT",
                severity="warning",
                message=f"图号「{drawing_no}」对应多个图名：{' / '.join(names)}。",
                suggestion="请核对同图号图纸是否为不同版本、不同分册或图名录入错误。",
            )
            by_code["CROSS_DRAWING_NAME_CONFLICT"] = by_code.get(
                "CROSS_DRAWING_NAME_CONFLICT", 0
            ) + 1


def _check_version_skip(db: Session, sheets: list[DrawingSheet], by_code: dict[str, int]) -> None:
    """同图号下版本号集合出现跳号（如 A, C 缺 B；或 1, 3 缺 2）。"""
    by_drawing_no: dict[str, list[DrawingSheet]] = defaultdict(list)
    for sheet in sheets:
        drawing_no = _valid_drawing_no(sheet)
        if drawing_no and sheet.version:
            by_drawing_no[drawing_no].append(sheet)
    for drawing_no, group in by_drawing_no.items():
        versions = sorted({(s.version or "").strip().upper() for s in group if s.version})
        if len(versions) < 2:
            continue
        missing = _detect_version_gap(versions)
        if not missing:
            continue
        for sheet in group:
            issue_service.add_issue(
                db,
                project_id=sheet.project_id,
                batch_id=sheet.batch_id,
                file_id=sheet.file_id,
                sheet_id=sheet.id,
                issue_code="CROSS_VERSION_SKIP",
                severity="warning",
                message=(
                    f"图号「{drawing_no}」存在版本 {', '.join(versions)}，"
                    f"疑似缺失中间版本 {', '.join(missing)}。"
                ),
            )
            by_code["CROSS_VERSION_SKIP"] = by_code.get("CROSS_VERSION_SKIP", 0) + 1


def _detect_version_gap(versions: list[str]) -> list[str]:
    """从有序版本列表里检测连续性缺口。

    简化规则：
    - 单字母 A-Z：检查是否连续；
    - 纯数字：检查是否连续。
    """
    if not versions:
        return []
    if all(len(v) == 1 and v.isalpha() for v in versions):
        codes = sorted({ord(v) for v in versions})
        missing = [chr(c) for c in range(codes[0], codes[-1] + 1) if c not in codes]
        return missing
    if all(v.isdigit() for v in versions):
        nums = sorted({int(v) for v in versions})
        missing = [str(n) for n in range(nums[0], nums[-1] + 1) if n not in nums]
        return missing
    return []


def _check_discipline_prefix(
    db: Session, sheets: list[DrawingSheet], by_code: dict[str, int]
) -> None:
    for sheet in sheets:
        drawing_no = _valid_drawing_no(sheet)
        if not drawing_no or not sheet.discipline:
            continue
        inferred = infer_discipline_from_drawing_no(drawing_no)
        if not inferred:
            continue
        if inferred != sheet.discipline.strip():
            issue_service.add_issue(
                db,
                project_id=sheet.project_id,
                batch_id=sheet.batch_id,
                file_id=sheet.file_id,
                sheet_id=sheet.id,
                issue_code="CROSS_DISCIPLINE_PREFIX_MISMATCH",
                severity="warning",
                message=(
                    f"图号「{drawing_no}」前缀对应专业「{inferred}」，"
                    f"但本图专业字段为「{sheet.discipline}」。"
                ),
            )
            by_code["CROSS_DISCIPLINE_PREFIX_MISMATCH"] = by_code.get(
                "CROSS_DISCIPLINE_PREFIX_MISMATCH", 0
            ) + 1


def _check_date_inconsistent(
    db: Session, sheets: list[DrawingSheet], by_code: dict[str, int]
) -> None:
    """同 (drawing_no, version) 下若多个 issue_date 不一致，记 issue。"""
    groups: dict[tuple[str, str], list[DrawingSheet]] = defaultdict(list)
    for sheet in sheets:
        drawing_no = _valid_drawing_no(sheet)
        if drawing_no and sheet.version and sheet.issue_date:
            key = (drawing_no, (sheet.version or "").strip().upper())
            groups[key].append(sheet)
    for (drawing_no, version), group in groups.items():
        distinct_dates = {s.issue_date for s in group if s.issue_date}
        if len(distinct_dates) <= 1:
            continue
        dates_str = ", ".join(sorted(d.isoformat() for d in distinct_dates))
        for sheet in group:
            issue_service.add_issue(
                db,
                project_id=sheet.project_id,
                batch_id=sheet.batch_id,
                file_id=sheet.file_id,
                sheet_id=sheet.id,
                issue_code="CROSS_ISSUE_DATE_INCONSISTENT",
                severity="warning",
                message=(
                    f"图号「{drawing_no}」版本「{version}」下存在不同出图日期：{dates_str}。"
                ),
            )
            by_code["CROSS_ISSUE_DATE_INCONSISTENT"] = by_code.get(
                "CROSS_ISSUE_DATE_INCONSISTENT", 0
            ) + 1


def _check_version_date_regress(
    db: Session, sheets: list[DrawingSheet], by_code: dict[str, int]
) -> None:
    """同 drawing_no 下字典序更大的版本如果 issue_date 反而更早，报警。"""
    by_drawing_no: dict[str, list[DrawingSheet]] = defaultdict(list)
    for sheet in sheets:
        drawing_no = _valid_drawing_no(sheet)
        if drawing_no and sheet.version and sheet.issue_date:
            by_drawing_no[drawing_no].append(sheet)
    for drawing_no, group in by_drawing_no.items():
        if len(group) < 2:
            continue
        # version 升序排，对应 issue_date 应非降序
        ordered = sorted(group, key=lambda s: ((s.version or "").upper(), s.issue_date or date.min))
        max_date_so_far: date | None = None
        max_version_so_far: str | None = None
        for sheet in ordered:
            current_date = sheet.issue_date
            current_version = (sheet.version or "").upper()
            if max_date_so_far is not None and current_date and current_date < max_date_so_far:
                issue_service.add_issue(
                    db,
                    project_id=sheet.project_id,
                    batch_id=sheet.batch_id,
                    file_id=sheet.file_id,
                    sheet_id=sheet.id,
                    issue_code="CROSS_VERSION_DATE_REGRESS",
                    severity="warning",
                    message=(
                        f"图号「{drawing_no}」版本「{current_version}」出图日期 "
                        f"{current_date.isoformat()} 早于此前版本「{max_version_so_far}」的 "
                        f"{max_date_so_far.isoformat()}。"
                    ),
                )
                by_code["CROSS_VERSION_DATE_REGRESS"] = by_code.get(
                    "CROSS_VERSION_DATE_REGRESS", 0
                ) + 1
            if current_date and (max_date_so_far is None or current_date > max_date_so_far):
                max_date_so_far = current_date
                max_version_so_far = current_version


def _valid_drawing_no(sheet: DrawingSheet) -> str | None:
    raw = (sheet.drawing_no or "").strip()
    if not raw or is_blacklisted_drawing_no(raw):
        return None
    normalized = normalize_drawing_no(raw) or raw
    if not (is_supported_drawing_no(normalized) or is_plausible_drawing_no(normalized)):
        return None
    if (sheet.trust_level or "").upper() == "D" or (sheet.confidence_score or 0) < 45:
        return None
    return normalized
