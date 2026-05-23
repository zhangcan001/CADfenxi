# 工程图纸智能台账识别系统

## 当前版本

v1.0.2-fast-stable

## 版本定位

个人本地正式版快速稳定发布版本。

v1.0.2-fast-stable 是正式版快速稳定发布版本。本版本不新增功能，重点保证启动、旧数据兼容、PDF / DXF / DWG / CAD pipeline / CAD 预览 / 校核 / Excel 导出 / 备份恢复 / 健康检查流程稳定。

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
- 不做图纸目录识别
- 不做材料表 / 设备表 / 门窗表识别
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
→ 生成 CAD 预览
→ 候选值
→ 字段融合
→ 校核
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

生成 v1.0.2 快速稳定版便携包：

```bash
python scripts/build_portable_package.py --version v1.0.2-fast-stable --clean
```

输出目录：

```text
release/工程图纸智能台账识别系统-v1.0.2-fast-stable/
```

## 发布材料

- `docs/RELEASE_CHECKLIST_v1.0-local-stable.md`
- `docs/FINAL_ACCEPTANCE_v1.0-local-stable.md`
- `docs/V1_0_1_REAL_USE_FIX_REPORT.md`
- `docs/FAST_RELEASE_REPORT_v1.0.2.md`
- `RELEASE_NOTES.md`

## 历史版本摘要

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
