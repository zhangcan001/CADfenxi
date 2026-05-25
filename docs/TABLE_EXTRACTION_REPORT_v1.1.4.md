# DXF 表格抽取报告 — v1.1.4

## 背景

监理日常使用图纸时除了"封皮 5 字段"外，最高频的需求是图纸内嵌的
**设备表 / 材料表 / 图纸目录 / 图例表**。这些是结构化数据，可直接进入
台账与质量核验流程。v1.1.4 引入完整的 DXF 表格抽取能力，覆盖两类
载体：

1. **ACAD_TABLE 实体** — AutoCAD 表格工具画的标准表，使用 ezdxf 的
   `read_acad_table_content()` 直接抽出。优点：结构化清晰；缺点：
   国内施工图很少用，命中率偏低。
2. **TEXT / MTEXT 坐标聚类** — 国内多数表是用直线 + 文字"画"出来的
   伪表。沿 y/x 坐标做行/列聚类还原出表格。命中率主战场。

两条路径并行运行、结果合并写入同一张 `drawing_tables`。

## 数据模型

`drawing_tables`：

| 列 | 类型 | 说明 |
| ---- | ---- | ---- |
| id | int PK | |
| project_id, batch_id, file_id, sheet_id | FK | 全链路 cascade delete |
| table_index | int | 同 sheet 内的序号 |
| extraction_method | str | `acad_table` / `text_cluster` |
| table_kind | str | `equipment` / `material` / `drawing_index` / `legend` / `other` |
| layer_name | str? | |
| header_json, rows_json | text | JSON 列表 |
| row_count, col_count | int | |
| source_bbox_json | text? | `[xmin, ymin, xmax, ymax]` |
| warnings_json | text? | 截断 / 噪声标记 |
| created_at, updated_at | datetime | |

索引：`sheet_id`、`(project_id, table_kind)`。

迁移：[`0006_drawing_tables`](../backend/migrations/versions/0006_drawing_tables.py)，
`down_revision = "0005_background_jobs_table"`。

## API

| 方法 | 路径 | 用途 |
| ---- | ---- | ---- |
| POST | `/api/sheets/{sheet_id}/extract-tables` | 单 sheet 同步抽取 |
| POST | `/api/imports/{batch_id}/extract-tables` | batch 异步抽取（沿用 `background_jobs`） |
| GET | `/api/imports/{batch_id}/extract-tables/job` | 任务进度 / 终态 |
| GET | `/api/sheets/{sheet_id}/tables` | 单 sheet 列表 |
| GET | `/api/projects/{project_id}/tables?kind=equipment` | 项目维度，按类型筛选 |

## 自动触发

`cad_parse_service.parse_prepared_dxf` 解析成功后自动调用
`cad_table_service.extract_tables_from_sheet(...)`，失败只记
`warning`，不阻塞解析链路。这样老的 parse-dxf 调用路径也能拿到
表格结果。

## Excel 导出

`build_excel` 增加「**图纸表格明细**」sheet，每行 = 一张表的一个
数据行：

```
序号 | 专业 | 图号 | 图名 | 表格类型 | 表格序号 | 抽取方式 | 行号 | 表头(JSON) | 数据(JSON) | 列数
```

监理在 Excel 用「表格类型 = 设备表」自动筛选，即可拿到全项目的
设备清单，无需再开图。

## 算法关键阈值

`recognizer/cad_engine/table_extractor.py`：

| 常量 | 默认值 | 说明 |
| ---- | ---- | ---- |
| MIN_ROWS | 3 | 候选表最小行数 |
| MIN_COLS | 2 | 候选表最小列数 |
| MIN_TOTAL_TEXTS | 6 | 文字数下限，低于则跳过 |
| ROW_Y_THRESHOLD_FACTOR | 1.5 | 同行 y 差阈值 = median_h × 1.5 |
| ROW_GAP_MAX_FACTOR | 4.0 | 跨行 y 间距上限 = median_h × 4.0 |
| COL_X_THRESHOLD_FACTOR | 0.6 | x 聚类阈值因子 |
| MAX_ROWS | 200 | 超出截断，加 `TABLE_ROW_TRUNCATED_TO_200` warning |
| MAX_COLS | 30 | 超出截断，加 `TABLE_COL_TRUNCATED_TO_30` warning |

## 分类启发式

`recognizer/cad_engine/table_classifier.py`：

- 命中 ≥2 个关键词 → 该 kind；命中强指示词（如"设备表"）≥1 → 直接命中
- 多 kind 同分时按 `KIND_PRIORITY = [equipment, material, drawing_index, legend]` 取
- 全部 miss → `other`

## 已知限制

1. **多页跨页表**：当前一张 sheet 内连续聚类即截断，不跨 sheet 拼接
2. **合并单元格**：被合并的单元格读出的内容会落到最近列，可能错位
3. **嵌套表/复杂表头**：第一行始终被当作 header
4. **超大表**：> 200 行 / 30 列会被截断并标 warning
5. **ACAD_TABLE 老版本**：依赖 ezdxf 1.x `read_acad_table_content`，
   早期版本不可用时静默跳过

## 测试覆盖

[`tests/test_cad_table_extraction.py`](../tests/test_cad_table_extraction.py)
包含：

- 算法纯函数单测 5 个：3x3 表 / 标题栏排除 / 行数阈值 / 分类命中 / fallback
- 集成测试 5 个：单 sheet 抽取 / 自动触发 / batch 异步完成 / 409 重复 / Excel 含明细 sheet

新增 1 个 v1.1.4 烟雾测试集成进 `test_fast_stable_release.py`。

## 版本与回滚

- `app_version` 升级到 `v1.1.4-table-extract`
- 回滚：drop `drawing_tables` + revert migration 0006 + 删除新文件
- Excel 多一个 sheet 不影响下游消费（按名取 sheet 的工具继续可用）
