TAG_FIELD_MAP = {
    "drawing_no": [
        "DRAWING_NO",
        "DWG_NO",
        "SHEET_NO",
        "SHEETNUMBER",
        "SHEET_NUMBER",
        "图号",
        "图纸编号",
        "图纸号",
        "编号",
        "图纸编码",
        "施工图号",
        "施工图编号",
        "专业图号",
        "子项图号",
        "图纸代号",
        "DWGNO",
        "DWG_NO.",
        "SHEETNO",
        "SHEET_NO.",
        "DRAWINGNUMBER",
        "DRAWING_NUMBER",
        "DrawingNo",
        "DwgNo",
        "SheetNo",
        "Sheet Number",
        "工程图号",
        "图 号",
        "图　号",
        "NO.",
        "No",
        "NO",
        "图别编号",
    ],
    "drawing_name": [
        "DRAWING_NAME",
        "DRAWING_TITLE",
        "SHEET_TITLE",
        "TITLE",
        "NAME",
        "图名",
        "图纸名称",
        "图纸名",
        "名称",
        "工程图名",
        "图纸标题",
        "图纸内容",
        "子项名称",
        "图纸名称及内容",
        "DRAWINGTITLE",
        "DRAWING_TITLE",
        "SHEETTITLE",
        "SHEET_TITLE",
        "DrawingTitle",
        "SheetTitle",
        "图 名",
        "图　名",
    ],
    "version": [
        "REV",
        "REVISION",
        "VERSION",
        "REV_NO",
        "版本",
        "版次",
        "变更",
        "修订",
        "版号",
        "修改号",
        "修订号",
        "修改版",
        "阶段",
        "出图阶段",
        "REVISION_NO",
        "REVNO",
        "RevNo",
        "RevisionNo",
        "Rev.",
        "REV.",
        "设计阶段",
        "图纸阶段",
    ],
    "issue_date": [
        "DATE",
        "ISSUE_DATE",
        "DRAWING_DATE",
        "PLOT_DATE",
        "出图日期",
        "日期",
        "设计日期",
        "制图日期",
        "校对日期",
        "审核日期",
        "审定日期",
        "发布日期",
        "出图时间",
        "签发日期",
        "PLOTDATE",
        "DRAWINGDATE",
        "ISSUEDATE",
        "DrawingDate",
        "IssueDate",
        "PlotDate",
        "日 期",
        "日　期",
    ],
    "discipline": ["DISCIPLINE", "专业", "专业名称", "图别", "子项专业", "专业类别", "SUBJECT"],
    "designer": [
        "DESIGNER",
        "DESIGN",
        "DESIGN_BY",
        "DESIGNED_BY",
        "设计",
        "设计人",
        "设计者",
        "Designer",
    ],
    "drafter": [
        "DRAFTER",
        "DRAWN",
        "DRAWN_BY",
        "DRAW_BY",
        "制图",
        "制图人",
        "绘图",
        "绘图人",
        "Drafter",
        "Drawn",
    ],
    "reviewer": [
        "REVIEWER",
        "REVIEW",
        "REVIEW_BY",
        "REVIEWED_BY",
        "审核",
        "审核人",
        "审图",
        "Reviewer",
    ],
    "checker": [
        "CHECKER",
        "CHECKED",
        "CHECK_BY",
        "CHECKED_BY",
        "校对",
        "校对人",
        "校核",
        "校核人",
        "Checker",
    ],
    "approver": [
        "APPROVER",
        "APPROVED",
        "APPROVED_BY",
        "审定",
        "审定人",
        "批准",
        "批准人",
        "Approver",
    ],
}

# 子串匹配候选词（只用于长度 >= 4 的归一化 tag，避免 NO/RD 等误命中）
SUBSTRING_HINTS = {
    "drawing_no": ["DWGNO", "SHEETNO", "DRAWINGNO", "DRAWINGNUMBER", "SHEETNUMBER", "图号", "编号"],
    "drawing_name": ["DRAWINGTITLE", "SHEETTITLE", "DRAWINGNAME", "SHEETNAME", "TITLE", "图名", "名称"],
    "version": ["REVISION", "VERSION", "REVNO", "版本", "版次", "阶段"],
    "issue_date": ["DRAWINGDATE", "ISSUEDATE", "PLOTDATE", "日期"],
    "designer": ["DESIGNER", "DESIGNBY", "DESIGNEDBY", "设计"],
    "drafter": ["DRAFTER", "DRAWNBY", "DRAWBY", "制图", "绘图"],
    "reviewer": ["REVIEWER", "REVIEWBY", "REVIEWEDBY", "审核", "审图"],
    "checker": ["CHECKER", "CHECKEDBY", "CHECKBY", "校对", "校核"],
    "approver": ["APPROVER", "APPROVEDBY", "审定", "批准"],
    "discipline": ["DISCIPLINE", "SUBJECT", "专业"],
}


def normalize_tag(tag: str | None) -> str:
    return (
        (tag or "")
        .strip()
        .replace(" ", "")
        .replace("\t", "")
        .replace("\n", "")
        .replace("_", "")
        .replace("-", "")
        .replace("－", "")
        .replace("—", "")
        .replace("　", "")
        .replace(":", "")
        .replace("：", "")
        .replace(".", "")
        .upper()
    )


def field_for_tag(tag: str | None) -> str | None:
    normalized = normalize_tag(tag)
    if not normalized:
        return None
    # 1) 精确匹配优先
    for field_name, tags in TAG_FIELD_MAP.items():
        if normalized in {normalize_tag(item) for item in tags}:
            return field_name
    # 2) 子串匹配兜底：tag 长度 >= 4 才允许，避免 "NO" 等短 token 误命中
    if len(normalized) < 4:
        return None
    for field_name, hints in SUBSTRING_HINTS.items():
        for hint in hints:
            hint_norm = normalize_tag(hint)
            if len(hint_norm) >= 3 and hint_norm in normalized:
                return field_name
    return None
