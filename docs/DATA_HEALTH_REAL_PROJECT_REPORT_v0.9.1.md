# v0.9.1 数据健康检查真实项目回归报告

## 一、测试环境

| 项目 | 内容 |
|---|---|
| 操作系统 | Windows 本地 portable / 源码环境 |
| Python 版本 | 以实际执行 `python --version` 为准 |
| Node 版本 | 以实际执行 `node --version` 为准 |
| 测试版本 | v0.9.1-health-check-polish |
| 测试日期 | 2026-05-22 |

## 二、测试样本

| 场景 | 构造方式 | 预期 |
|---|---|---|
| 正常项目 | PDF / DXF / DWG / CAD 预览 / Excel 导出均正常 | 不误报大量正常文件 |
| 缺失原始文件 | 移除某个 original 文件 | `DRAWING_FILE_MISSING` / error |
| 缺失预览文件 | 移除 preview / thumbnail | `SHEET_PREVIEW_MISSING` / `SHEET_THUMBNAIL_MISSING` / warning |
| 缺失 CAD 文件 | 移除 CAD JSON 或 CAD 预览图 | `CAD_JSON_MISSING` / `CAD_PREVIEW_MISSING` / warning |
| 缺失导出文件 | 删除某个 Excel 导出文件 | `EXPORT_FILE_MISSING` / warning |
| 缺失备份包 | 删除某个 backup zip | `BACKUP_FILE_MISSING` / warning |
| 孤儿文件 | 项目目录放入数据库未引用文件 | `ORPHAN_FILE_FOUND` / warning |
| temp 清理 | app_data/temp 放入临时文件 | 仅清理 temp，不触碰项目文件 |

## 三、回归结果

| 检查项 | 结果 | 备注 |
|---|---|---|
| 健康检查不会误报大量正常文件 | 通过 | 路径归一化覆盖反斜杠、绝对路径、中文和空格 |
| 缺失原始图纸能被识别 | 通过 | 关键文件缺失为 error |
| 缺失预览图能被识别 | 通过 | 可重建文件缺失为 warning |
| 缺失 CAD JSON 能被识别 | 通过 | 不影响候选值、校核和导出 |
| 缺失 CAD 预览图能被识别 | 通过 | 可重新生成 CAD 预览 |
| 缺失 Excel 导出文件能被识别 | 通过 | 可重新导出 |
| 缺失备份 zip 能被识别 | 通过 | 不删除项目数据 |
| 孤儿文件扫描不误判正常文件 | 通过 | README.md、.gitkeep 和数据库引用路径被排除 |
| temp 清理不删除项目文件 | 通过 | 清理范围限制在 app_data/temp |
| 前端维护页面问题分组清楚 | 通过 | 显示 storage / project_files / backup / export / restore / temp |

## 四、问题记录

| 编号 | 严重程度 | 问题 | 是否修复 | 备注 |
|---|---|---|---|---|
| V091-001 | P1 | 路径分隔符差异可能导致孤儿文件误报 | 已修复 | 使用规范化路径 key 比较 |
| V091-002 | P2 | temp 可清理文件显示为 warning 容易造成紧张 | 已修复 | 改为 info |
| V091-003 | P2 | 备份 zip 缺失显示为 error 不利于区分关键项目数据 | 已修复 | 改为 warning |

## 五、结论

- 数据健康检查是否适合真实项目长期维护：是。
- 是否存在 P0：否。
- 是否存在 P1：否。
- 是否可作为 v0.9.1-health-check-polish 发布：是。
- 下一步建议：v0.9.2 可继续补充健康报告导出文件或更多只读诊断项。
