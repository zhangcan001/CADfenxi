# v0.6.2 识别规则小修报告

## 一、修复范围

| 类型 | 数量 | 说明 |
|---|---:|---|
| 图号规则 | 5 | 补充中文专业前缀带字母、JG、紧凑英文图号标准化，并保持构件编号/轴号过滤 |
| 图名规则 | 7 | 补充系统图、综合管线、平法施工图、节点大样等关键词 |
| 专业规则 | 6 | 补充防雷接地、动力、排烟、综合布线、监控、消防水/电等关键词 |
| CAD tag | 16 | 补充 drawing_no、drawing_name、version、issue_date 常见中英文 tag |
| 日期规则 | 8 | 补充年月、紧凑年月、紧凑年月日、两位年日期；非法日期低可信 |
| 问题提示 | 6 | 优化 ONLY_FROM_FILENAME、OCR_TEXT_EMPTY、PDF_TEXT_EMPTY、LOW_CONFIDENCE_NEED_REVIEW、ISSUE_DATE_INVALID 等中文提示 |

## 二、案例修复明细

| 编号 | 类型 | 原识别结果 | 修复后结果 | 测试用例 |
|---|---|---|---|---|
| V062-001 | 图号漏识别 | 建施-A01 未稳定标准化 | 建施-A-01 | `test_v062_drawing_no_formats_normalization_and_misread_filters` |
| V062-002 | 图号漏识别 | JG-01 未覆盖 | JG-01 | `test_v062_drawing_no_formats_normalization_and_misread_filters` |
| V062-003 | 图号漏识别 | A101 上下文识别不稳定 | A-101 | `test_v062_drawing_no_formats_normalization_and_misread_filters` |
| V062-004 | 图号误识别 | KZ-1 可能高可信 | 不作为高可信图号 | `test_v062_drawing_no_formats_normalization_and_misread_filters` |
| V062-005 | 图名漏识别 | 喷淋系统图未覆盖 | 图名候选生成 | `test_v062_drawing_name_keywords_and_note_text_filtering` |
| V062-006 | 图名误识别 | 说明文字可能高可信 | 不作为高可信图名 | `test_v062_drawing_name_keywords_and_note_text_filtering` |
| V062-007 | 专业误判 | 防雷接地/综合布线未稳定识别 | 电气/弱电 | `test_v062_discipline_keywords_and_priority` |
| V062-008 | CAD tag 未覆盖 | DWG_NO./图纸名称及内容/PLOTDATE 未映射 | 正确映射字段 | `test_v062_cad_tag_mapping_and_normalization` |
| V062-009 | 日期格式未识别 | 2024.6/202406 未标准化 | 2024-06-01 | `test_v062_date_formats_and_invalid_dates` |
| V062-010 | 日期非法 | 2024-02-31 可能可信偏高 | normalized_value 为空且 confidence <= 50 | `test_v062_date_formats_and_invalid_dates` |
| V062-011 | 低可信提示 | 文件名/OCR/低可信提示不够聚合 | 生成对应提示 | `test_v062_filename_only_ocr_empty_and_low_confidence_issues_are_generated` |
| V062-012 | 流程回归 | 重复执行可能堆积 | 候选与 open issues 不堆积 | `test_v062_manual_review_protection_and_repeated_steps_are_idempotent` |

## 三、回归结果

| 流程 | 结果 | 说明 |
|---|---|---|
| PDF | 通过 | `test_v062_pdf_dxf_dwg_pipeline_and_excel_regression` 覆盖 PDF 拆页、文本提取、候选和导出 |
| DXF | 通过 | 覆盖 DXF 解析、CAD 候选、融合和导出 |
| DWG 转换 | 通过 | 使用 mock converter 回归 DWG 转 DXF 后识别 |
| CAD pipeline | 通过 | 覆盖混合批次 pipeline |
| 校核工作台 | 通过 | 覆盖人工字段保护 |
| Excel 导出 | 通过 | 覆盖导出行数和版本说明 |

## 四、结论

- 是否可作为 v0.6.2-rule-fix：是
- 是否存在 P0：否
- 是否存在 P1：否
- 可延后问题：真实涉密样本未入库，后续仍需在本地真实项目中持续补充案例表。
