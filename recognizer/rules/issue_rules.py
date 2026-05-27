CONFLICT_CODES = {
    frozenset(["filename", "pdf_text"]): "FILENAME_PDFTEXT_CONFLICT",
    frozenset(["filename", "title_ocr"]): "FILENAME_OCR_CONFLICT",
    frozenset(["pdf_text", "title_ocr"]): "PDFTEXT_OCR_CONFLICT",
}


def conflict_code(field_name: str, sources: list[str]) -> str:
    source_set = set(sources)
    if "cad_block_attr" in source_set and source_set.intersection({"cad_text", "cad_mtext", "cad_filename"}):
        return "CAD_FIELD_CONFLICT"
    if field_name == "discipline":
        return "DISCIPLINE_CONFLICT"
    for pair, code in CONFLICT_CODES.items():
        if pair.issubset(source_set):
            return code
    return "FIELD_CONFLICT_HIGH"


def issue_template(issue_code: str, value: str | None = None) -> tuple[str, str, str]:
    templates = {
        "DRAWING_NO_EMPTY": ("error", "图纸编号为空", "请在后续校核阶段补充图纸编号。"),
        "DRAWING_NAME_EMPTY": ("error", "图纸名称为空", "请在后续校核阶段补充图纸名称。"),
        "DRAWING_NO_DUPLICATE": (
            "error",
            f"发现重复图号：{value}",
            "请检查是否为不同版本图纸，或在后续校核阶段修正图号/版本。",
        ),
        "DISCIPLINE_EMPTY": ("warning", "专业为空", "请检查图号、图名或标题栏信息。"),
        "VERSION_EMPTY": ("warning", "版本为空", "如图纸确无版本可忽略，否则请后续补充。"),
        "ISSUE_DATE_EMPTY": ("warning", "出图日期为空", "请在后续校核阶段补充出图日期。"),
        "ISSUE_DATE_INVALID": ("warning", f"日期格式异常：{value}", "请检查原始日期是否真实有效，并修正为 YYYY-MM-DD。"),
        "LOW_CONFIDENCE": ("warning", "综合评分偏低", "请在校核工作台重点检查该页推荐字段。"),
        "LOW_CONFIDENCE_NEED_REVIEW": ("warning", "低可信图纸需要人工校核", "请优先核对图号、图名、专业和日期来源。"),
        "FIELD_ONLY_FROM_FILENAME": ("info", f"{value} 仅来自文件名", "建议结合 PDF 文本、OCR 或 CAD 标题栏复核。"),
        "ONLY_FROM_FILENAME": ("warning", f"{value} 仅来自文件名", "请结合 PDF 文本、OCR 或 CAD 块属性确认后再批量确认。"),
        "PDF_TEXT_EMPTY": ("info", "PDF 文本为空", "可继续使用 OCR 或人工校核，不阻断导出。"),
        "OCR_TEXT_EMPTY": ("info", "OCR 未识别到有效文字", "请检查标题栏裁剪区域，必要时结合文件名或 PDF 文本复核。"),
        "DISCIPLINE_LOW_CONFIDENCE": ("warning", "专业候选置信度较低", "请结合图号前缀、图名和图层再确认专业。"),
        "CAD_FIELD_CONFLICT": (
            "warning",
            "CAD 块属性与 CAD 普通文字识别结果不一致，已优先采用块属性值。",
            "请在校核工作台中核对该字段是否为标题栏中的正式值。",
        ),
        "CAD_TEXT_LOW_CONFIDENCE": (
            "warning",
            "CAD 普通文字候选置信度较低",
            "请确认该文字是否来自标题栏，说明文字或构件编号不要直接采用。",
        ),
        "CAD_ONLY_FROM_LAYER": (
            "info",
            "专业仅来自 CAD 图层",
            "请结合图号、图名或标题栏信息复核专业。",
        ),
        "CAD_PARSE_EMPTY_CONTENT": (
            "warning",
            "CAD 解析未提取到有效文字或块属性",
            "请确认 DXF 内容或在校核工作台中人工补充字段。",
        ),
        "CAD_DRAWING_NO_SUSPECT": (
            "warning",
            "CAD 图号候选疑似构件编号或格式不完整",
            "请在校核工作台中核对图号是否来自标题栏正式字段。",
        ),
        "CAD_DRAWING_NAME_SUSPECT": (
            "warning",
            "CAD 图名候选疑似说明文字或文本过长",
            "请在校核工作台中核对图名是否为正式图纸名称。",
        ),
        "CAD_BLOCK_ATTR_MISSING": (
            "info",
            "DXF 未发现块属性标题栏",
            "当前候选主要来自普通 TEXT / MTEXT，建议核对标题栏文字是否完整。",
        ),
        "CAD_TABLE_EXTRACT_WARNING": (
            "warning",
            "DXF 表格抽取失败或结果低可信",
            "表格抽取仅作为辅助信息，不影响主台账识别；请在图纸表格明细中复核。",
        ),
        "CAD_BLOCK_STATS_WARNING": (
            "warning",
            "DXF 块统计失败或结果异常",
            "块统计仅作为辅助统计，不影响主台账识别和 Excel 导出。",
        ),
        "CAD_ONLY_FROM_FILENAME": (
            "info",
            "CAD 字段仅来自文件名",
            "建议结合 DXF 标题栏文字或人工校核确认字段值。",
        ),
        "CROSS_DRAWING_NO_DUPLICATE": (
            "error",
            f"跨图重复图号：{value}",
            "项目内多张已确认图纸使用相同图号，请核对版本或修正其中一份。",
        ),
        "CROSS_DRAWING_NAME_CONFLICT": (
            "warning",
            f"同图号图名不一致：{value}",
            "请核对同图号图纸是否为不同版本、不同分册或图名录入错误。",
        ),
        "CROSS_VERSION_SKIP": (
            "warning",
            f"版本号疑似跳号：{value}",
            "请核对是否缺失中间版本图纸，或在校核阶段补齐版本号。",
        ),
        "CROSS_DISCIPLINE_PREFIX_MISMATCH": (
            "warning",
            f"专业与图号前缀不一致：{value}",
            "请核对图号前缀（如建施/电施/PD/EE）与专业字段是否对应。",
        ),
        "CROSS_ISSUE_DATE_INCONSISTENT": (
            "warning",
            f"同图号同版本出图日期不一致：{value}",
            "请核对同图号同版本的出图日期是否应为同一天。",
        ),
        "CROSS_VERSION_DATE_REGRESS": (
            "warning",
            f"新版本出图日期早于旧版本：{value}",
            "通常新版本应当晚于旧版本，请核对版本号或出图日期。",
        ),
    }
    return templates.get(issue_code, ("warning", issue_code, "请在后续校核阶段复核该问题。"))
