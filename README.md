# 工程图纸智能台账识别系统

## 当前版本

v1.4-fast-real-project-trial

## 版本定位

v1.4 真实项目整体验收试用版本。

v1.4-fast-real-project-trial 是真实项目整体验收试用版本。本版本不新增功能，重点用真实或接近真实项目验证从导入、PDF 拆页、DWG 转 DXF、CAD pipeline、深度抽取、校核、Excel 导出、备份恢复到健康检查的完整流程，并沉淀 v1.4.1 修复清单。

v1.3.3-fast-deep-extract-stable 是深度抽取稳定包整理版本。本版本不新增功能，重点回归 DXF 表格抽取、INSERT 块统计、跨图一致性校验、Excel 安全导出和核心流程，并生成 portable 稳定包。

v1.3.2-fast-excel-safety 是深度抽取 Excel 导出安全收口版本。本版本重点确保图纸表格明细、图纸块统计、跨图一致性问题不污染正式图纸总台账。

v1.3.1-fast-deep-extract-fix 是深度抽取真实问题快速修复版本。本版本不新增大功能，重点修复表格抽取误判、行列错位、标题栏字段污染、INSERT 块统计误报、跨图一致性误报、Excel 明细 sheet 结构不清楚，以及深度抽取异常影响 CAD pipeline 或 Excel 导出的问题。

v1.3-fast-deep-extract-review 是深度抽取能力真实项目回归版本。本版本不新增大功能，重点验证 DXF 表格抽取、INSERT 块统计、跨图纸一致性校验、Excel 新增明细 sheet 是否适合真实项目使用。

v1.2.3-fast-import-stable 是导入体验稳定包整理版本。本版本不新增功能，重点回归 PDF / DXF / DWG 导入统计、重复文件提示、不支持格式提示、导入后下一步建议、项目待办刷新和 portable 打包。

v1.2.2-fast-import-fix 是导入流程真实使用问题快速修复版本。本版本不新增识别能力，重点修复 PDF / DXF / DWG 混合导入统计、重复文件提示、不支持格式提示、DWG 转换工具提示和导入后的下一步建议。

v1.2.1-fast-integrity 是版本、接口、路由、打包一致性快速修复版本。本版本不新增功能，重点修复 v1.2-fast-import 后可能存在的版本号不一致、router 未挂载、README 与实际能力不一致、portable 打包版本不一致等问题。

v1.2-fast-import 是导入流程体验优化版本。本版本不新增识别能力，重点优化 PDF / DXF / DWG 导入前提示、导入结果摘要、重复文件提示、不支持格式提示和导入后的下一步建议。

v1.1.6-deep-extract-stable 是深度抽取能力稳定收口版本。本版本不新增大功能，重点验证并收口 DXF 表格抽取、INSERT 块统计、跨图一致性校验、Excel 新增明细 sheet、前端内嵌表格展示和 portable 打包。

v1.1.5-deep-extract 在 v1.1.4 表格抽取基础上完成 INSERT 块统计、跨图校验、图纸内嵌表格展示和标题栏自适应。

v1.1.4-table-extract 新增 DXF 表格抽取能力，支持 ACAD_TABLE 与文字坐标聚类，并在 Excel 导出中增加图纸表格明细。

v1.1.3-fast-stable 是 v1.1 体验优化稳定包整理版本。本版本不新增功能，重点回归首页快捷工作台、最近项目、项目待办摘要、下一步建议、快捷入口和核心业务流程，并生成 portable 稳定包。

v1.1.2-fast-polish 是界面细节打磨与可用性优化版本。本版本不新增识别能力，重点优化首页、最近项目、项目待办、快捷操作、空状态、错误提示和小屏显示。

v1.1-fast-ux 是真实使用体验优化版本。本版本不新增识别能力，重点优化首页、最近项目、项目待办摘要、快捷操作和下一步建议，让日常使用更快。

v1.1.1-fast-fix 是快捷工作台真实使用问题快速修复版本。本版本不新增功能，重点修复首页、最近项目、项目待办摘要、下一步建议、快捷入口和 portable 打包问题。

用于本地识别 PDF / DXF 图纸，以及 DWG 转 DXF 后的图纸，辅助生成工程图纸台账，支持人工校核、CAD 轻量预览、项目备份恢复、数据健康检查和 Excel 导出。

## 已支持能力

- 项目管理
- PDF 上传
- PDF 拆页
- PDF 缩略图 / 预览
- PDF 标题栏裁剪
- PDF 文本提取
- OCR 原始结果
- PDF 候选值生成
- PDF 字段融合
- DXF 上传
- DXF 图纸页创建
- DXF TEXT / MTEXT / INSERT / ATTRIB / LAYER 解析
- DXF CAD JSON 保存
- DXF 表格抽取
- 图纸内嵌表格展示
- INSERT 块统计
- 跨图纸一致性校验
- DXF 候选值生成
- DXF 字段融合
- 外部 DWG 转 DXF 工具配置
- DWG 上传
- DWG 转 DXF
- DWG 转换后进入 DXF 流程
- CAD 批量处理流水线
- CAD 轻量图形预览
- CAD 预览缩放 / 拖拽 / 下载 / 批量生成
- 图纸台账
- 校核工作台
- 筛选 / 排序 / 批量确认
- 快速采用候选值
- 人工修改字段
- 人工确认字段保护
- 审计日志
- Excel 导出
- 图纸总台账
- 问题清单
- 专业汇总
- 图纸表格明细
- 图纸块统计
- 校核状态汇总
- 导出说明
- 项目级备份
- 项目恢复为新项目
- 备份校验
- 备份删除
- app_data 全量备份迁移说明
- 系统健康检查
- 项目完整性检查
- 备份文件检查
- 导出文件检查
- 临时文件安全清理
- Windows portable 本地启动
- 首页快捷工作台
- 最近项目
- 当前项目待办摘要
- 下一步建议
- 校核快捷筛选入口

## 明确不支持能力

- 不直接解析 DWG
- 不内置 ODA File Converter
- 不内置 Python
- 不内置 Node
- 不做 CAD 编辑
- 不做图层编辑
- 不做标注修改
- 不做算量
- 不做 BIM
- 不做 AI 图纸问答
- 不保证复杂表格、嵌套表格、合并单元格 100% 准确
- 不做跨 sheet 表格自动拼接
- 不做多人协同
- 不做云端同步
- 不做自动修复数据库
- 不做覆盖恢复
- CAD 预览仅用于辅助查看，不保证与专业 CAD 软件完全一致

## 推荐使用流程

PDF：

PDF 上传
→ 拆页
→ 预览 / 缩略图
→ 标题栏裁剪
→ 文本提取 / OCR
→ 候选值
→ 字段融合
→ 校核
→ Excel 导出
→ 项目备份

DXF：

DXF 上传
→ 准备图纸页
→ 解析 DXF
→ 抽取表格 / 统计块
→ 生成 CAD 预览
→ 候选值
→ 字段融合
→ 校核
→ 跨图一致性校验
→ Excel 导出
→ 项目备份

DWG：

DWG 上传
→ 配置外部转换工具
→ DWG 转 DXF
→ 进入 DXF 流程
→ 生成 CAD 预览
→ 校核
→ Excel 导出
→ 项目备份

数据安全：

项目备份
→ 下载备份包
→ 必要时恢复为新项目
→ 定期复制 app_data 全量备份

系统维护：

系统健康检查
→ 项目完整性检查
→ 备份检查
→ 导出检查
→ 必要时清理 app_data/temp

## 便携包

生成 v1.4 真实项目试用包：

```bash
python scripts/build_portable_package.py --version v1.4-fast-real-project-trial --clean
```

输出目录：

```text
release/工程图纸智能台账识别系统-v1.4-fast-real-project-trial/
```

## 发布材料

- `docs/RELEASE_CHECKLIST_v1.0-local-stable.md`
- `docs/FINAL_ACCEPTANCE_v1.0-local-stable.md`
- `docs/V1_0_1_REAL_USE_FIX_REPORT.md`
- `docs/FAST_RELEASE_REPORT_v1.0.2.md`
- `docs/FAST_RELEASE_REPORT_v1.1.3.md`
- `docs/FAST_RELEASE_REPORT_v1.3.3.md`
- `docs/REAL_PROJECT_TRIAL_REPORT_v1.4.md`
- `RELEASE_NOTES.md`

## 历史版本摘要

### v1.4-fast-real-project-trial 真实项目整体验收试用

v1.4-fast-real-project-trial 是真实项目整体验收试用版本。本版本不新增功能，重点验证真实项目从导入到导出的完整链路、深度抽取、校核效率、Excel 交付质量、备份恢复和健康检查，并形成 v1.4.1 修复清单。

### v1.3.3-fast-deep-extract-stable 深度抽取稳定包整理

v1.3.3-fast-deep-extract-stable 是深度抽取稳定包整理版本。本版本不新增功能，重点回归 DXF 表格抽取、INSERT 块统计、跨图一致性校验、Excel 安全导出和核心流程，并生成 portable 稳定包。

### v1.3.2-fast-excel-safety Excel 深度抽取导出安全收口

v1.3.2-fast-excel-safety 是深度抽取 Excel 导出安全收口版本。本版本重点确保图纸表格明细、图纸块统计、跨图一致性问题不污染正式图纸总台账。

### v1.3.1-fast-deep-extract-fix 深度抽取真实问题快速修复

v1.3.1-fast-deep-extract-fix 是深度抽取真实问题快速修复版本。本版本不新增大功能，重点修复表格抽取误判、行列错位、标题栏字段污染、INSERT 块统计误报、跨图一致性误报、Excel 明细 sheet 结构不清楚，以及深度抽取异常影响 CAD pipeline 或 Excel 导出的问题。

### v1.3-fast-deep-extract-review 深度抽取能力真实项目回归

v1.3-fast-deep-extract-review 是深度抽取能力真实项目回归版本。本版本不新增大功能，重点验证 DXF 表格抽取、INSERT 块统计、跨图纸一致性校验、Excel 新增明细 sheet 是否适合真实项目使用。

### v1.2.3-fast-import-stable 导入体验稳定包整理

v1.2.3-fast-import-stable 是导入体验稳定包整理版本。本版本不新增功能，重点回归 PDF / DXF / DWG 导入统计、重复文件提示、不支持格式提示、导入后下一步建议、项目待办刷新和 portable 打包。

### v1.2.2-fast-import-fix 导入流程真实使用问题快速修复

v1.2.2-fast-import-fix 是导入流程真实使用问题快速修复版本。本版本不新增识别能力，重点修复 PDF / DXF / DWG 混合导入统计、重复文件提示、不支持格式提示、DWG 转换工具提示和导入后的下一步建议。

### v1.2.1-fast-integrity 版本、接口、路由、打包一致性快速修复

v1.2.1-fast-integrity 是版本、接口、路由、打包一致性快速修复版本。本版本不新增功能，重点修复 v1.2-fast-import 后可能存在的版本号不一致、router 未挂载、README 与实际能力不一致、portable 打包版本不一致等问题。

### v1.2-fast-import 导入流程体验优化

v1.2-fast-import 是导入流程体验优化版本。本版本不新增识别能力，重点优化 PDF / DXF / DWG 导入前提示、导入结果摘要、重复文件提示、不支持格式提示和导入后的下一步建议。

### v1.1.6-deep-extract-stable 深度抽取稳定收口

v1.1.6-deep-extract-stable 是深度抽取能力稳定收口版本。本版本不新增大功能，重点验证 DXF 表格抽取、INSERT 块统计、跨图一致性校验、Excel 新增 sheet 和 portable 打包，确保旧流程不回归。

### v1.1.5-deep-extract 深度提取与跨图校验

v1.1.5-deep-extract 在 v1.1.4 表格抽取基础上完成 INSERT 块统计、跨图纸一致性校验、图纸内嵌表格展示、标题栏定位自适应和 MTEXT 多行拆分。

### v1.1.4-table-extract DXF 表格抽取

v1.1.4-table-extract 新增 DXF 表格抽取能力，覆盖 ACAD_TABLE 实体和文字坐标聚类，并在 Excel 导出新增“图纸表格明细”sheet。

### v1.1.3-fast-stable v1.1 体验优化稳定包

v1.1.3-fast-stable 是 v1.1 体验优化稳定包整理版本。本版本不新增功能，重点回归首页快捷工作台、最近项目、项目待办摘要、下一步建议、快捷入口和核心业务流程，并生成 portable 稳定包。

### v1.1.2-fast-polish 界面细节打磨与可用性优化

v1.1.2-fast-polish 是界面细节打磨与可用性优化版本。本版本不新增识别能力，重点优化首页、最近项目、项目待办、快捷操作、空状态、错误提示和小屏显示。

### v1.1.1-fast-fix 快捷工作台真实使用修复

v1.1.1-fast-fix 是快捷工作台真实使用问题快速修复版本。本版本不新增功能，重点修复首页、最近项目、项目待办摘要、下一步建议、快捷入口和 portable 打包问题。

### v1.1-fast-ux 真实使用体验优化

v1.1-fast-ux 是真实使用体验优化版本，不新增识别能力，重点优化首页、最近项目、项目待办摘要、快捷操作和下一步建议，让日常使用更快。

### v1.0.1 正式版真实使用问题修复

v1.0.1 是个人本地正式稳定版真实使用问题修复版本。本版本不新增功能，主要修复正式版使用中发现的启动、识别、CAD 预览、校核、导出、备份恢复和健康检查问题。

### v0.7.2 数据安全收口与全量 app_data 备份迁移指南

如果要备份全部数据，请关闭系统后复制整个 app_data 目录。不要只复制 database 或只复制 projects，避免数据库记录和项目文件不一致。

### v0.8.2 CAD 预览前端交互优化

支持 CAD 预览缩放、拖拽、适应窗口、100% 显示、重置、重新生成和下载预览图。

### v0.8.3 CAD 预览批量生成与性能优化

支持项目级、批次级批量生成 CAD 预览，支持跳过已生成预览、强制重新生成、失败统计和耗时统计。

### v0.8.4 CAD 预览稳定版收口与真实项目回归

回归 DXF、DWG 转 DXF 后预览、批量预览、前端交互、备份恢复和旧流程，确认 CAD 预览仅用于辅助查看。
