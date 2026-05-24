"""识别准度回归测试。

直测规则层（normalizer / cad_text_rules / filename_parser / text_parser /
discipline / tag_mapper），不走 FastAPI，速度快，方便每次改规则后立刻验证。
覆盖正向命中、反向拒识、边界值三类用例。
"""
from recognizer.cad_engine.cad_text_rules import (
    find_drawing_name,
    infer_candidates_from_text,
    is_note_text,
)
from recognizer.cad_engine.tag_mapper import field_for_tag
from recognizer.filename_parser.parser import parse_filename
from recognizer.normalizer.date import normalize_issue_date
from recognizer.normalizer.discipline import infer_discipline
from recognizer.normalizer.drawing_no import (
    is_component_or_axis_no,
    is_plausible_drawing_no,
    is_supported_drawing_no,
    normalize_drawing_no,
)
from recognizer.normalizer.version import normalize_version
from recognizer.text_parser.parser import parse_text


def candidates_by_field(candidates: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for item in candidates:
        grouped.setdefault(item["field_name"], []).append(item)
    return grouped


# ---------- 图号 (drawing_no) ----------


class TestDrawingNoRecognition:
    def test_white_list_disciplines_hit(self):
        for raw in ["建施-01", "结施-12", "水施-03", "电施-05", "暖施-02"]:
            assert is_supported_drawing_no(raw), f"白名单图号未识别: {raw}"

    def test_letter_code_hit(self):
        # 注意：M/C/D/W 与构件号 (M-门, C-窗) 冲突，原规则按构件号判 → 故意排除
        for raw in ["A-01", "S-12", "E-03", "P-07", "T-09"]:
            assert is_supported_drawing_no(raw), f"字母代码图号未识别: {raw}"

    def test_three_segment_drawing_no_should_be_plausible(self):
        # 真实工程常见：JS-01-01、SJ-01-02、施总-01-01
        for raw in ["JS-01-01", "SJ-01-02", "DQ-01-03", "KT-05"]:
            assert is_plausible_drawing_no(raw), f"宽松规则应认可: {raw}"

    def test_axis_and_component_no_rejected(self):
        for raw in ["KZ-1", "L-12", "KL-3", "M-5", "门-1", "轴1", "A轴"]:
            assert is_component_or_axis_no(raw), f"构件/轴号未被拒识: {raw}"

    def test_normalize_drawing_no_unifies_separator(self):
        assert normalize_drawing_no("建施—01") == "建施-01"
        assert normalize_drawing_no("建施 01") == "建施-01"
        assert normalize_drawing_no("建施_01") == "建施-01"


# ---------- 图名 (drawing_name) ----------


class TestDrawingNameRecognition:
    def test_keyword_hit(self):
        for raw in ["一层平面图", "给排水平面图", "电气系统图"]:
            assert find_drawing_name(raw) == raw

    def test_heuristic_should_catch_non_dict_titles(self):
        # 当前用例：字典外的常见图名，应被启发式捕获（#4 改进后生效）
        for raw in ["卫生间大样图", "病房单元详图", "南立面"]:
            result = find_drawing_name(raw)
            assert result is not None, f"启发式应捕获: {raw}"

    def test_note_text_rejected(self):
        assert is_note_text("本图尺寸以毫米为单位施工时应按规范执行")
        assert is_note_text("详见设计说明")
        # 长度 > 80 应被判定为说明
        assert is_note_text("一" * 81)

    def test_short_pure_number_not_a_name(self):
        # 纯数字 / 太短的应不返回
        assert find_drawing_name("12") is None
        assert find_drawing_name("") is None


# ---------- 专业 (discipline) ----------


class TestDisciplineRecognition:
    def test_basic_disciplines(self):
        assert infer_discipline("建施-01") == "建筑"
        assert infer_discipline("结施-01") == "结构"
        assert infer_discipline("水施-01") == "给排水"
        assert infer_discipline("电施-01") == "电气"
        assert infer_discipline("暖施-01") == "暖通"

    def test_xianggang_branches(self):
        assert infer_discipline("弱电系统图") == "弱电"
        assert infer_discipline("火灾报警平面图") == "消防"

    def test_disambiguation_xiaofang_dianqi(self):
        # 改进 #6 后："消防电气专业说明" 含"电气专业"高分关键词 → 应判电气
        assert infer_discipline("消防电气专业说明") == "电气"

    def test_scored_voting_prefers_higher_weight(self):
        # 关键词多但弱（"消防"=2） vs 关键词少但强（"建筑施工图"=5）
        assert infer_discipline("建筑施工图 消防") == "建筑"


# ---------- 日期 (issue_date) ----------


class TestDateNormalization:
    def test_full_date_yyyy_mm_dd(self):
        assert normalize_issue_date("2024-05-23") == "2024-05-23"
        assert normalize_issue_date("2024年5月23日") == "2024-05-23"
        assert normalize_issue_date("20240523") == "2024-05-23"

    def test_month_only_falls_back_to_first(self):
        assert normalize_issue_date("2024-05") == "2024-05-01"
        assert normalize_issue_date("2024年5月") == "2024-05-01"

    def test_invalid_date_returns_none(self):
        assert normalize_issue_date("2024-13-01") is None
        assert normalize_issue_date("not a date") is None

    def test_full_date_detection(self):
        from recognizer.normalizer.date import is_full_date_text

        assert is_full_date_text("2024-05-23")
        assert is_full_date_text("2024年5月23日")
        assert is_full_date_text("20240523")
        # "2024年5月" 不是完整日期
        assert not is_full_date_text("2024年5月")
        assert not is_full_date_text("2024-05")


# ---------- 版本 (version) ----------


class TestVersionNormalization:
    def test_letter_version(self):
        assert normalize_version("A版") == "A"
        assert normalize_version("版本B") == "B"

    def test_rev_version(self):
        assert normalize_version("Rev.1") == "Rev.1"
        assert normalize_version("Rev-2") == "Rev.2"

    def test_v_version(self):
        assert normalize_version("V1.0") == "V1.0"
        assert normalize_version("v2") == "V2"


# ---------- 文件名 parser ----------


class TestFilenameParser:
    def test_filename_with_drawing_no_and_date(self):
        result = candidates_by_field(parse_filename("建施-05-一层平面图-20240523.dxf"))
        assert "drawing_no" in result
        assert result["drawing_no"][0]["normalized_value"] == "建施-05"
        assert "issue_date" in result
        assert result["issue_date"][0]["normalized_value"] == "2024-05-23"

    def test_filename_letter_code(self):
        result = candidates_by_field(parse_filename("A-101-平面布置图.dwg"))
        assert "drawing_no" in result


# ---------- text_parser（PDF/OCR 路径用） ----------


class TestTextParserLabelExtraction:
    def test_pdf_text_labeled_drawing_no(self):
        text = "图号：建施-12\n图名：二层平面图\n日期：2024-05-23"
        result = candidates_by_field(parse_text(text, "pdf_text"))
        assert "drawing_no" in result
        assert result["drawing_no"][0]["normalized_value"] == "建施-12"
        assert "drawing_name" in result
        assert "issue_date" in result
        assert result["issue_date"][0]["normalized_value"] == "2024-05-23"


# ---------- TAG 映射 ----------


class TestTagMapper:
    def test_exact_tag_match(self):
        assert field_for_tag("DWG_NO") == "drawing_no"
        assert field_for_tag("图号") == "drawing_no"
        assert field_for_tag("DRAWING_TITLE") == "drawing_name"

    def test_tag_with_separator_normalized(self):
        assert field_for_tag("Sheet Number") == "drawing_no"
        assert field_for_tag("图 号") == "drawing_no"

    def test_designer_tags_should_match(self):
        # #9 新增字段：设计/制图/审核
        assert field_for_tag("设计") == "designer"
        assert field_for_tag("DESIGNER") == "designer"
        assert field_for_tag("制图") == "drafter"
        assert field_for_tag("审核") == "reviewer"

    def test_prefixed_tag_with_substring_match(self):
        # 改进 #5：T_DWGNO / TBLK_TITLE 这种前缀变体应命中
        assert field_for_tag("T_DWGNO") == "drawing_no"
        assert field_for_tag("TBLK_DWGNO") == "drawing_no"
        assert field_for_tag("TB_DRAWING_TITLE") == "drawing_name"
        assert field_for_tag("TBL_SHEETNO") == "drawing_no"


# ---------- 端到端：infer_candidates_from_text ----------


class TestInferCandidatesEndToEnd:
    def test_attrib_tagged_drawing_no(self):
        result = candidates_by_field(
            infer_candidates_from_text("建施-05", "cad_block_attr", tagged_field="drawing_no")
        )
        assert "drawing_no" in result
        assert result["drawing_no"][0]["confidence"] >= 80

    def test_free_cad_text_supported_drawing_no(self):
        result = candidates_by_field(infer_candidates_from_text("建施-12", "cad_text"))
        assert "drawing_no" in result

    def test_free_cad_text_axis_no_should_be_suppressed(self):
        result = candidates_by_field(infer_candidates_from_text("KZ-3", "cad_text"))
        # 构件号应不在 drawing_no 候选里
        assert "drawing_no" not in result or all(
            c["confidence"] <= 50 for c in result.get("drawing_no", [])
        )

    def test_note_text_does_not_become_drawing_name(self):
        result = candidates_by_field(
            infer_candidates_from_text("本图尺寸以毫米为单位，施工前应核对现场", "cad_text")
        )
        assert "drawing_name" not in result


# ---------- 标题栏区域定位 (#2) ----------


from recognizer.cad_engine.title_area import (
    find_title_block_bbox,
    is_title_block_name,
    point_in_bbox,
    resolve_title_area,
)


class TestTitleBlockLocator:
    def test_recognize_title_block_name(self):
        assert is_title_block_name("TITLEBLOCK")
        assert is_title_block_name("TBLK_A4")
        assert is_title_block_name("图签")
        assert is_title_block_name("标题栏")
        assert not is_title_block_name("FRAME_LAYER")

    def test_find_title_block_bbox_from_insert(self):
        inserts = [
            {"block_name": "WALL_DETAIL", "insert": [0, 0, 0]},
            {"block_name": "TITLE_BLOCK_A1", "insert": [1000, 200, 0]},
        ]
        bbox = find_title_block_bbox(inserts)
        assert bbox is not None
        assert point_in_bbox([1000, 200, 0], bbox)
        assert not point_in_bbox([0, 0, 0], bbox)

    def test_resolve_title_area_fallback_to_bottom_right(self):
        cad_json = {
            "spaces": [
                {
                    "texts": [
                        {"insert": [0, 0, 0]},
                        {"insert": [1000, 0, 0]},
                        {"insert": [0, 700, 0]},
                        {"insert": [1000, 700, 0]},
                    ],
                    "mtexts": [],
                    "inserts": [],
                }
            ]
        }
        bbox = resolve_title_area(cad_json)
        assert bbox is not None
        # 右下角点应在 bbox 里，左上角点应不在
        assert point_in_bbox([900, 50, 0], bbox)
        assert not point_in_bbox([100, 650, 0], bbox)


# ---------- OCR 引擎选择 (#1) ----------


class TestOcrFactory:
    def test_fallback_to_mock_when_paddle_unavailable_or_disabled(self, monkeypatch):
        from recognizer.ocr_engine import factory
        from recognizer.ocr_engine.mock_ocr import MockOcrEngine

        monkeypatch.setenv("CADFENXI_DISABLE_PADDLEOCR", "1")
        factory.reset_cache()
        engine = factory.get_ocr_engine()
        assert isinstance(engine, MockOcrEngine)
        factory.reset_cache()

    def test_engine_is_cached(self, monkeypatch):
        from recognizer.ocr_engine import factory

        monkeypatch.setenv("CADFENXI_DISABLE_PADDLEOCR", "1")
        factory.reset_cache()
        e1 = factory.get_ocr_engine()
        e2 = factory.get_ocr_engine()
        assert e1 is e2
        factory.reset_cache()
