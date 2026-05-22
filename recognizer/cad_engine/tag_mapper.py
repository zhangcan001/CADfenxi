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
    for field_name, tags in TAG_FIELD_MAP.items():
        if normalized in {normalize_tag(item) for item in tags}:
            return field_name
    return None
