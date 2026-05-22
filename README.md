# 工程图纸智能台账识别系统

当前版本：v0.6.2-rule-fix

版本定位：识别规则小修与低风险优化版本。

本项目用于本地化识别工程图纸台账信息，覆盖从项目管理、图纸导入、PDF 拆页识别、DXF 解析、候选值生成、字段融合、人工校核到 Excel 导出的闭环流程。

## 一、已支持功能

- 项目管理
- PDF 上传
- PDF 拆页
- PDF 预览 / 缩略图
- 标题栏裁剪
- PDF 文本提取
- 标题栏 OCR 原始结果
- PDF 候选值生成
- DXF 上传
- DWG 上传与原始文件保存
- 外部 DWG 转 DXF 工具路径配置
- 转换工具检测
- 单个 / 批量 DWG 转 DXF
- CAD 批量处理流水线
- 转换历史记录
- DXF 图纸页创建
- DXF TEXT 解析
- DXF MTEXT 解析
- DXF INSERT / ATTRIB 解析
- DXF LAYER 解析
- DXF CAD JSON 保存
- DXF 候选值生成
- cad_* 来源字段融合
- 问题规则
- 图纸台账页
- 校核工作台
- 校核工作台筛选 / 排序
- 批量确认高可信或当前筛选图纸
- 快速采用候选值
- 字段来源说明
- 问题聚合展示
- 人工修改字段
- 人工确认图纸
- 审计日志
- Excel 导出
- Excel 图纸总台账 / 问题清单 / 专业汇总 / 校核状态汇总 / 导出说明
- 导出前检查
- 一键本地启动
- 前端静态文件托管
- 本地环境检查
- Windows 便携包生成
- Windows 便携包换机测试记录
- Windows 便携包发布检查清单
- portable 启动诊断与内测问题记录
- Windows 便携版稳定发布包
- 真实项目试用问题清单与试用报告

## 二、v0.6.2-rule-fix 识别规则小修与低风险优化

v0.6.2 是识别规则小修与低风险优化版本。本版本不新增功能，只针对真实使用中发现的图号、图名、专业、CAD tag、日期和低可信提示问题做小修。

- 小幅增强图号识别和标准化规则，补充 `建施-A01`、`JG-01`、`A101`、`S101` 等格式。
- 小幅增强图名关键词，补充系统图、综合管线图、平法施工图、节点大样图等常见标题。
- 增强说明文字、构件编号和轴号过滤，降低误判为图号或图名的风险。
- 小幅增强专业判断关键词和 CAD tag 映射。
- 补充年月、紧凑日期等日期格式标准化，非法日期保持低可信。
- 优化低可信、仅文件名来源、OCR/PDF 空文本和日期异常提示。
- 新增规则小修案例表和质量复测报告：`docs/RULE_FIX_CASES_v0.6.2.md`、`docs/RULE_FIX_REPORT_v0.6.2.md`。

生成 v0.6.2 便携包：

```bash
python scripts/build_portable_package.py --version v0.6.2-rule-fix --clean
```

输出目录：

```text
release/工程图纸智能台账识别系统-v0.6.2-rule-fix/
```

## 三、v0.6.1-local-stable-fix 稳定版真实使用问题修复

v0.6.1 是个人本地稳定版真实使用问题修复版本。本版本不新增功能，主要修复启动、路径、识别流程、校核、导出中的真实使用问题。

- 修复启动器关闭时后端进程残留风险。
- 统一 `/api/health`、前端、Excel 导出说明和 portable 打包版本号。
- 回归 PDF / DXF / DWG 单文件流程。
- 回归 CAD pipeline 批量流程、重复执行幂等性和错误汇总。
- 回归校核工作台保存、确认、批量确认安全规则。
- 回归人工确认字段保护和 Excel 导出一致性。
- 新增稳定版真实使用问题修复记录：`docs/LOCAL_STABLE_FIX_ISSUES_v0.6.1.md`。

## 四、v0.5.5-stability 真实项目全流程稳定性回归

v0.5.5 是真实项目全流程稳定性回归版本。重点验证 portable 启动、PDF、DXF、DWG 转换、CAD pipeline、校核工作台和 Excel 导出完整闭环。本版本不新增功能，主要用于为 v0.6 稳定版做准备。

- 回归 PDF 单文件完整流程。
- 回归 DXF 单文件完整流程与重复操作幂等性。
- 回归 DWG mock 转换后进入 DXF 识别流程。
- 回归 CAD pipeline 混合批次处理。
- 回归人工确认字段保护和 Excel 导出一致性。
- 新增全流程稳定性报告：`docs/FULL_FLOW_STABILITY_REPORT_v0.5.5.md`。

## 五、v0.5.4-excel-delivery 真实项目交付台账复核与模板微调

v0.5.4 是真实项目交付台账复核与模板微调版本。重点优化 Excel 图纸总台账、问题清单、专业汇总、校核状态汇总和导出说明。导出结果优先使用人工确认值，适合人工复核后作为项目台账使用。

- 问题清单增加问题类型中文说明，并保留英文 code 便于追溯。
- 图纸编号、图纸名称、原始文件名、问题描述、建议处理、备注等关键列宽按交付使用微调。
- 导出前检查增加汇总式提示文案，说明未校核、缺字段、错误、警告和 D 级图纸数量。
- 新增真实项目交付台账复核报告：`docs/EXCEL_DELIVERY_REVIEW_v0.5.4.md`。

## 六、v0.5.3-excel-template Excel 导出台账模板与交付格式优化

v0.5.3 是 Excel 导出台账模板与交付格式优化版本。优化了图纸总台账、问题清单、专业汇总、校核状态汇总和导出说明。导出结果优先使用人工确认值。导出前会提示未校核、缺字段和低可信图纸。

- 图纸总台账按项目名称、专业、图号、图名、版本、出图日期、格式、来源、可信等级、校核状态、问题数量等字段导出。
- 问题清单中文化展示问题级别、状态、字段名、当前值、候选值和来源。
- 新增专业汇总与校核状态汇总，方便交付前快速复核。
- 导出说明包含系统版本、项目名称、导出时间、数据来源说明和重要限制说明。
- 导出不会修改图纸状态、问题状态或人工确认字段。

## 七、v0.5.2-review-efficiency 校核工作台效率优化

v0.5.2 是校核工作台效率优化版本。新增或优化筛选、排序、批量确认、快速采用候选值、字段来源说明、问题聚合展示，目标是减少真实项目台账人工校核时间。

- 支持按未校核、已确认、有错误、有警告、低可信、缺字段、PDF / DXF / DWG 转换图纸、A/B/C/D 等级筛选。
- 支持问题数量、可信度、图纸编号、专业、文件名、最近修改时间和未确认优先排序。
- 支持当前筛选结果、手动勾选图纸、A 级、A/B 级、字段完整图纸批量确认，并继续禁止确认 open error、缺图号、缺图名和 failed 图纸。
- 字段校核区可查看候选值来源、置信度、原始文本和推荐状态，支持填入候选值、立即采用并保存、清空、恢复机器推荐。
- 人工修改、采用候选值、恢复推荐值、确认和批量确认均写入审计日志。

## 八、v0.5-real-project-trial 真实项目试用与问题闭环

v0.5 是真实项目试用与问题闭环阶段。重点不是新增功能，而是用真实 PDF / DXF / DWG 小项目验证业务价值，记录识别质量、校核体验、Excel 导出一致性和 portable 日常使用问题。

建议试用方式：

- 先使用 10～50 张图纸的小型真实项目。
- 覆盖 PDF / DXF / DWG，DWG 仍需外部工具转 DXF。
- 不建议一次性导入超大项目。
- 发现问题请记录到 `docs/REAL_PROJECT_TRIAL_ISSUES_v0.5.md`。
- 试用统计请记录到 `docs/REAL_PROJECT_TRIAL_REPORT_v0.5.md`。
- 当前仍不做 CAD 图形预览。
- 当前仍不做算量 / BIM / AI 问答。

## 九、v0.5.1-real-project-quality 真实项目识别质量专项优化

v0.5.1 是真实项目识别质量专项优化版本。重点优化图号、图名、专业、CAD tag 映射、误判过滤、低可信提示。

- 当前仍不做 CAD 图形预览。
- 当前仍不直接解析 DWG。
- 当前仍不做算量 / BIM / AI 图纸问答。

质量优化报告：

```text
docs/REAL_PROJECT_QUALITY_OPTIMIZATION_v0.5.1.md
```

真实样本本地目录：

```text
samples/real_project_trial_v0_5/
```

该目录已通过 `.gitignore` 排除真实图纸文件，请只提交 README，不要提交涉密图纸。

生成 v0.5 trial 便携包：

```bash
python scripts/build_portable_package.py --version v0.5-real-project-trial --clean
```

输出目录：

```text
release/工程图纸智能台账识别系统-v0.5-real-project-trial/
```

## 十、v0.4.5-portable-stable Windows 便携版稳定发布包

v0.4.5-portable-stable 是个人本地稳定使用版，重点整理 stable portable 发布包、最终用户说明、数据备份迁移说明、DWG 外部转换工具说明和最终发布检查清单。

生成 stable 便携包：

```bash
python scripts/build_portable_package.py --version v0.4.5-portable-stable --clean
```

输出目录：

```text
release/工程图纸智能台账识别系统-v0.4.5-portable-stable/
```

最终发布检查清单：

```text
docs/RELEASE_CHECKLIST_v0.4.5-portable-stable.md
```

最终验收报告：

```text
docs/FINAL_ACCEPTANCE_v0.4.5-portable-stable.md
```

## 十一、v0.4.4-portable-rc-fix 真实用户内测问题修复

v0.4.4 重点修复 portable-rc 真实内测启动问题，不新增识别能力。

- 增强启动诊断。
- 增强 check_env。
- 增强 app_data 权限检查。
- 增强端口占用提示。
- 增强 portable 包完整性检查。
- 所有数据保存在 app_data。
- 备份 app_data 即可备份数据。
- 仍未打包为 exe。
- 仍不内置 Python / Node / ODA。
- 仍不做 CAD 图形预览。
- 仍不做算量 / BIM / AI 问答。

用户内测问题记录：

```text
docs/PORTABLE_USER_TEST_ISSUES_v0.4.4.md
```

生成修复版便携包：

```bash
python scripts/build_portable_package.py --version v0.4.4-portable-rc-fix --clean
```

## 十一、v0.4.3-portable-rc Windows 便携包发布候选版

v0.4.3-portable-rc 是 Windows 便携包发布候选版，重点是统一版本号、清理 portable 包、完善本地使用说明和发布检查清单，准备进入 portable 内测交付。

生成 RC 便携包：

```bash
python scripts/build_portable_package.py --version v0.4.3-portable-rc --clean
```

输出目录：

```text
release/工程图纸智能台账识别系统-v0.4.3-portable-rc/
```

发布检查清单：

```text
docs/RELEASE_CHECKLIST_v0.4.3-portable-rc.md
```

## 十二、v0.4.2 Windows 便携包真实换机测试与启动问题修复

v0.4.2 不新增识别功能，重点验证 v0.4.1 portable 包复制到其他 Windows 电脑、中文路径和空格路径后的启动表现。测试记录见：

```text
docs/PORTABLE_REAL_MACHINE_TEST_v0.4.2.md
```

本阶段继续保持以下边界：

- 不打包 exe
- 不内置 Python / Node / ODA File Converter
- 不引入 Electron / Tauri
- 不做 CAD 图形预览
- 不直接解析 DWG

## 十三、v0.4.1 Windows 便携版目录结构与轻量打包

v0.4.1 在 v0.4 一键本地启动的基础上，新增 Windows portable 目录生成能力。该版本不会打包 exe，不内置 Python、Node 或 ODA File Converter，目标是把已构建前端、后端代码、启动脚本和空数据目录整理成可复制目录。

生成便携包：

```bash
python scripts/build_portable_package.py
```

输出目录：

```text
release/工程图纸智能台账识别系统-v0.4.5-portable-stable/
```

便携包用户入口：

```text
start.bat
check_env.bat
stop.bat
README_本地使用说明.md
```

便携包不包含 `node_modules`、`.git`、真实 `app_data` 项目数据或真实样本文件。备份项目数据时复制 `app_data/` 即可，建议关闭系统后再备份。

## 十四、v0.3.3 CAD 批量处理体验优化

v0.3.3 继续优化 CAD 批量处理体验，重点是真实样本压力测试后的稳定性和可用性。

- 支持批量 DWG 转 DXF。
- 支持批量 DXF 解析。
- 支持批量候选值生成。
- 支持批量字段融合。
- 支持跳过已完成步骤。
- 支持单个失败继续处理。
- 支持查看批量结果摘要和错误列表。

当前仍为本地同步处理。  
建议单批次 5～50 个文件。  
超大批量可能耗时较长。  
当前仍不直接解析 DWG。  
当前仍不做 CAD 图形预览。  
当前仍不做算量 / BIM / AI 问答。

## 十五、v0.3.2 CAD 批量处理流水线

v0.3.2 新增 CAD 批量处理流水线，用于把现有 DWG / DXF 能力串成更顺畅的本地小批量处理流程。

- 支持批量 DWG 转 DXF。
- 支持批量准备 DXF 图纸页。
- 支持批量解析 DXF。
- 支持批量生成候选值。
- 支持批量生成推荐字段。
- 支持跳过已完成步骤。
- 支持单个文件失败后继续处理。
- 支持批量处理结果汇总和错误汇总。

系统仍不直接解析 DWG。  
系统仍不内置 DWG 转 DXF 转换工具。  
当前 API 同步执行，建议个人本地单批次处理 5～50 个文件。  
当前仍不做 CAD 图形预览。  
当前仍不做算量 / BIM / AI 图纸问答。

## 十六、v0.3.1 DWG 转换兼容性优化

v0.3.1 优化 DWG 转 DXF 转换兼容性。系统仍不直接解析 DWG，也不内置转换器；用户需要自行安装 ODA File Converter 或其他可命令行转换 DWG 到 DXF 的工具，并在系统中配置路径。

- 支持保存 DWG 原始文件到 original。
- 支持配置外部转换工具路径。
- 支持检测转换工具是否可用。
- 支持调用外部工具将 DWG 转换为 DXF。
- 支持 converted 目录保存转换后的 DXF。
- 支持转换运行记录和 stdout / stderr 摘要。
- 支持转换日志和转换历史。
- 优化中文路径、空格路径和中文文件名处理。
- 优化大写 .DXF、相近文件名和多候选输出查找。
- 优化转换超时和失败错误码。
- 转换成功后，DXF 继续进入现有 DXF 识别流程。

当前仍不直接解析 DWG。  
当前仍不内置 ODA File Converter 或其他转换器。  
转换质量取决于用户本机外部转换工具。  
当前仍不做 CAD 图形预览。

## 十七、明确不支持功能

- 不直接解析 DWG
- 不内置 DWG 转换工具
- 不做 CAD 图形预览
- 不做 CAD 编辑器
- 不做 Layout 拆分
- 不解析 XREF 外部参照
- 不做算量
- 不做 BIM
- 不做 AI 图纸问答
- 不做图纸目录识别
- 不做门窗表识别
- 不做设备表识别
- 不做材料表识别
- 不做多人权限
- 不做云端协同

## 十八、DWG 推荐使用方式

当前版本不直接解析 DWG。  
如需处理 DWG，请自行安装 ODA File Converter、CAD 软件或其他可命令行转换工具，在 CAD 转换设置中配置路径，然后上传 DWG 并执行转换。转换成功后，转换得到的 DXF 会继续复用现有 DXF 识别流程。

## 十九、v0.4 / v0.4.1 / v0.4.2 / v0.4.3 / v0.4.4 / v0.4.5 / v0.5 本地启动说明

### 一、首次使用

1. 安装后端依赖：

```bat
scripts\install_backend_deps.bat
```

2. 安装并构建前端：

```bat
scripts\build_frontend.bat
```

3. 启动系统：

```bat
scripts\start_local.bat
```

4. 浏览器自动打开：

```text
http://127.0.0.1:8000
```

### 二、日常使用

以后只需运行：

```bat
scripts\start_local.bat
```

启动脚本会检查 `frontend/dist`、8000 端口、`app_data` 目录，并在后端 `/api/health` 可访问后自动打开浏览器。

### 三、停止系统

关闭启动窗口即可。

也可以运行：

```bat
scripts\stop_local.bat
```

该脚本只提示停止方式，不会强制结束不确定进程。

### 四、环境检查

如需单独检查本机环境：

```bat
scripts\check_env.bat
```

检查内容包括 Python、pip、Node、npm、后端目录、前端目录、依赖文件、前端构建目录和 `app_data` 可写性。

### 五、常见问题

1. 8000 端口被占用怎么办。

   关闭旧的 `start_local.bat` 窗口，或手动检查占用 8000 端口的进程后再启动。本版本不会自动换端口，避免前端访问地址混乱。

2. Python 未安装怎么办。

   请安装 Python 3，并确认 `python` 命令已加入系统 PATH。安装后可运行 `scripts\check_env.bat` 复查。

3. Node / npm 未安装怎么办。

   请安装 Node.js。安装完成后确认 `node --version` 和 `npm --version` 可正常输出，再运行 `scripts\build_frontend.bat`。

4. `frontend/dist` 不存在怎么办。

   运行 `scripts\build_frontend.bat`。构建成功后会生成 `frontend/dist/index.html`。

5. `app_data` 不可写怎么办。

   请检查项目目录权限，确保当前 Windows 用户可以创建和写入 `app_data`、`app_data/projects`、`app_data/database`、`app_data/logs`、`app_data/temp`。

6. 启动后页面空白怎么办。

   先重新运行 `scripts\build_frontend.bat`，再运行 `scripts\start_local.bat`。如果仍为空白，请查看浏览器刷新后是否能访问 `http://127.0.0.1:8000/api/health`，并检查 `app_data/logs/local_launcher.log`。

7. 后端未连接怎么办。

   访问 `http://127.0.0.1:8000/api/health`。如果无法访问，说明后端未启动成功，请查看启动窗口提示和 `app_data/logs/local_launcher.log`。

## 二十、开发启动方式

后端：

```bash
python -m uvicorn backend.main:app --reload --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

开发模式下 Vite 会将 `/api` 代理到 `http://127.0.0.1:8000`。本地使用模式下，前端构建产物由 FastAPI 托管并使用同源 `/api`。

## 二十一、测试与构建

测试命令：

```bash
python -m pytest
```

前端构建命令：

```bash
cd frontend
npm run build
```

便携包构建命令：

```bash
python scripts/build_portable_package.py --version v0.5-real-project-trial --clean
```

## 二十二、推荐使用流程

PDF 流程：

1. 新建项目
2. 上传 PDF
3. 拆页生成图纸页、预览图和缩略图
4. 标题栏裁剪
5. PDF 文本提取 / 标题栏 OCR
6. 生成候选值
7. 生成推荐字段
8. 进入图纸台账和校核工作台
9. 人工校核
10. 导出 Excel

DXF 流程：

1. 新建项目
2. 上传 DXF
3. 准备 DXF 图纸页
4. 解析 DXF
5. 查看 CAD 摘要
6. 生成 cad_* 候选值
7. 生成推荐字段
8. 进入图纸台账和校核工作台
9. 人工校核
10. 导出 Excel

DWG 流程：

1. 新建项目
2. 在 CAD 转换设置中配置本机转换工具路径
3. 上传 DWG
4. 执行单个或批量 DWG 转 DXF
5. 转换成功后准备 DXF 图纸页
6. 解析 DXF
7. 生成 cad_* 候选值
8. 生成推荐字段
9. 进入图纸台账和校核工作台
10. 导出 Excel

CAD 批量流水线：

1. 新建项目
2. 配置 DWG 转 DXF 工具路径
3. 上传 DWG / DXF 文件
4. 进入 CAD 批量处理
5. 选择转换、准备 sheet、解析、候选值、推荐字段步骤
6. 开始批量处理
7. 查看每一步成功数、失败数、跳过数和错误列表
8. 进入台账 / 校核 / 导出

## 二十三、app_data 目录说明

- original：原始 PDF / DXF / DWG
- converted：DWG 转换后的 DXF
- previews：PDF 预览图
- thumbnails：PDF 缩略图
- crops：PDF 标题栏裁剪图
- text：PDF 文本提取结果
- ocr：OCR 原始结果
- cad/parsed：DXF 原始解析 JSON
- cad/logs：DWG 转换日志
- exports：Excel 导出文件

## 二十四、主要 API

- GET /api/health
- POST /api/projects
- GET /api/projects
- GET /api/projects/{project_id}
- POST /api/projects/{project_id}/imports
- POST /api/files/{file_id}/split
- POST /api/files/{file_id}/prepare-dxf-sheet
- POST /api/imports/{batch_id}/prepare-dxf-sheets
- POST /api/files/{file_id}/parse-dxf
- POST /api/imports/{batch_id}/parse-dxf
- GET /api/sheets/{sheet_id}/cad-parse
- GET /api/cad/converter-settings
- POST /api/cad/converter-settings
- PATCH /api/cad/converter-settings/{setting_id}
- POST /api/cad/converter-settings/{setting_id}/check
- POST /api/files/{file_id}/convert-dwg-to-dxf
- POST /api/imports/{batch_id}/convert-dwg-to-dxf
- POST /api/imports/{batch_id}/cad-pipeline
- GET /api/projects/{project_id}/cad-conversion-runs
- GET /api/files/{file_id}/cad-conversion-runs
- GET /api/projects/{project_id}/sheets
- POST /api/sheets/{sheet_id}/title-crop
- POST /api/sheets/{sheet_id}/extract-text
- POST /api/sheets/{sheet_id}/ocr-title
- POST /api/sheets/{sheet_id}/generate-candidates
- POST /api/sheets/{sheet_id}/fuse-fields
- GET /api/sheets/{sheet_id}/field-values
- PATCH /api/sheets/{sheet_id}/fields
- POST /api/sheets/{sheet_id}/confirm
- POST /api/projects/{project_id}/exports/check
- POST /api/projects/{project_id}/exports/excel

## 二十五、可靠性原则

- 机器识别结果只是推荐值。
- 人工确认字段不会被 PDF / DXF 重新融合覆盖。
- cad_layer 只用于专业判断，不用于图号、图名、版本或日期。
- 重复准备 DXF 图纸页不会重复创建 drawing_sheet。
- 重复生成候选值不会无限堆积机器候选。
- 重复字段融合不会无限堆积 open 机器问题。
- 导出 Excel 不改变图纸状态、校核状态或问题状态。

## 二十六、已知限制

- 当前不直接解析 DWG。
- 当前不内置 DWG 转换器。
- 当前不做 CAD 图形预览。
- 一个 DXF 默认对应一张图纸页。
- 当前不拆分 Layout。
- 当前不解析 XREF。
- 当前不做算量。
- 当前不做 BIM。
- 当前不做 AI 图纸问答。
- CAD 批量流水线当前同步执行，超大批量可能耗时较长。
- 当前不做图纸目录识别。
- 当前不做门窗表识别、设备表识别、材料表识别。
- DXF 识别质量依赖文字、块属性和图层命名规范。
- 复杂块、代理实体、字体缺失、编码异常可能影响 DXF 解析质量。
- 扫描型 PDF 候选值生成能力仍依赖 OCR 质量。
