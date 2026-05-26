# v1.1.5 深度提取 + 跨图校验报告

## 目标

v1.1.4 完成 DXF 表格抽取后，监理实际审图还差 4 块：
1. 后端已抽表格，前端无 UI，得手动开 Excel 才看到
2. 无「块/符号」维度统计（灯具/风机/阀门），监理无法做「图上画了 N 个 vs 设备表 M 个」核对
3. 无跨图纸一致性校验（同图号、版本跳号、专业前缀错位、出图日期不一致 / 倒退）
4. 标题栏定位过于刚性（找不到 INSERT title 块就 fallback 到固定右下 1/4），MTEXT 多行没拆开，表格聚类丢字

v1.1.5 一次性补齐。

## 实现概览

### 阶段 3：INSERT 块统计

- **数据模型**：新增 `drawing_block_stats` 表（migration `0007_drawing_block_stats`）
- **算法层**：`recognizer/cad_engine/block_aggregator.py`
  - 按 `(block_name, layer)` 分组聚合
  - 排除 title hint 块、匿名 `*Model_Space` / `*U` / `*X` 类系统块
  - 由 `layer` 调用 `infer_discipline` 推断专业
  - 收集 ATTRIB 属性：每个 tag 去重 + 截断到 10 个值
- **Service**：`block_stats_service.py`，沿用 cad_table_service 的 threading + background_job 模式
- **API**：
  - `POST /api/sheets/{id}/extract-blocks`（同步单页）
  - `POST /api/imports/{batch_id}/extract-blocks`（异步批量）
  - `GET  /api/imports/{batch_id}/extract-blocks/job`
  - `GET  /api/sheets/{id}/block-stats`
  - `GET  /api/projects/{id}/block-stats?discipline=...`
- **自动触发**：`cad_parse_service.parse_prepared_dxf` 成功分支末尾调用，失败仅 warning 不阻塞
- **Excel**：新增「图纸块统计」sheet（列：专业 / 图号 / 图名 / 块名 / 图层 / 推断专业 / 数量 / 关键属性）

### 阶段 4：跨图一致性校验

新增 5 个 issue_code：
| code | severity | 触发条件 |
|---|---|---|
| `CROSS_DRAWING_NO_DUPLICATE` | error | 同 project 内两张以上 confirmed sheet 同 drawing_no |
| `CROSS_VERSION_SKIP` | warning | 同 (project, drawing_no) 版本集合存在跳号（A,C 缺 B） |
| `CROSS_DISCIPLINE_PREFIX_MISMATCH` | warning | drawing_no 前缀映射出的专业与 sheet.discipline 不一致 |
| `CROSS_ISSUE_DATE_INCONSISTENT` | warning | 同 (project, drawing_no, version) 下 issue_date 多值 |
| `CROSS_VERSION_DATE_REGRESS` | warning | 同图号下版本字典序变大但 issue_date 反而更早 |

- **专业前缀映射**：`backend/core/discipline_codes.py`（建施/电施/PD/EE/...）→ 中文专业
- **Service**：`consistency_check_service.py` — 单次扫描所有 confirmed sheet，分 5 个 rule
- **去重**：每次跑前删除 project 内同 issue_code、status=open 的旧 CROSS_* 行，避免重复堆积
- **API**：`POST /api/projects/{id}/consistency-check`（同步，毫秒级）

### 表格 UI（前端）

- 新增 `frontend/src/components/EmbeddedTablesSection.tsx`
- 选中 sheet 时 `listSheetTables(sheetId)`，按 `table_kind` 分组（设备表 / 材料表 / 图纸目录 / 图例 / 其他）
- 折叠卡片渲染前 30 行，剩余显示「+N 行」
- 「复制 CSV」按钮：`navigator.clipboard.writeText`
- 苹果风轻量：圆角 12px / soft shadow / hover translateY / active scale
- 集成到 main.tsx：在「问题清单」之后插入板块

### 标题栏自适应

`recognizer/cad_engine/title_area.py:find_title_block_bbox_adaptive`：
1. 先走原 INSERT 命名匹配
2. 失败时按文字密度启发式：把 texts 落到 10×10 网格，找右下象限文字密度最高的格子簇
3. 该簇 bbox 宽/高比例 ∈ [1.2, 5.0] 且文字数 ≥ 8 → 视为标题栏
4. 否则返回 None（不再 fallback 到固定右下 1/4，避免误判）

`cad_table_service.py` 把 `find_title_block_bbox` 改为 `find_title_block_bbox_adaptive`。

### MTEXT 合并

`recognizer/cad_engine/table_extractor.py:_split_mtext_lines`：
- 含 `\n` 的 MTEXT 拆成多行，y 坐标按 `char_height` 递减
- 表格聚类按 y 聚类时不再把多行 MTEXT 当 1 行

## 限制

- block_aggregator 不区分「设备」和「构件」（墙线、标注块也可能被算进来）；由 `infer_discipline` 推断为 None 的可在 UI 筛选时过滤
- consistency_check 仅扫 `review_status = 'confirmed'` 的 sheet，未确认图纸不参与
- 标题栏自适应阈值偏保守，密度簇 < 8 文字直接返回 None；可调
- MTEXT 拆行未做合并字宽估算，y 步长按 char_height 直接递减；少数倾斜文字可能轻微偏移

## 风险与回滚

- 删除 0007 表 + revert 文件即可回滚后端
- 前端可独立 revert `EmbeddedTablesSection.tsx` + `main.tsx` 引入行

## 版本号

`v1.1.5-deep-extract`（同步 backend / frontend / scripts / 13 个 release 测试）。
