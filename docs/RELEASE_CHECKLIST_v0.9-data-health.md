# v0.9-data-health 发布检查清单

## 一、版本检查

| 检查项 | 结果 | 备注 |
|---|---|---|
| /api/health version 正确 | 通过/失败 | |
| 前端版本展示正确 | | |
| package_info.txt 版本正确 | | |
| README 版本正确 | | |
| README_本地使用说明版本正确 | | |
| RELEASE_NOTES 版本正确 | | |

v0.9.1 发布检查清单见：`docs/RELEASE_CHECKLIST_v0.9.1-health-check-polish.md`。

## 二、系统健康检查

| 检查项 | 结果 | 备注 |
|---|---|---|
| app_data 目录检查 | | |
| database 目录检查 | | |
| projects 目录检查 | | |
| backups 目录检查 | | |
| logs 目录检查 | | |
| temp 目录检查 | | |
| app_data 可写性检查 | | |
| 维护报告可生成 | | |

## 三、项目完整性检查

| 检查项 | 结果 | 备注 |
|---|---|---|
| 项目目录检查 | | |
| drawing_files 原始文件检查 | | |
| drawing_sheets 预览检查 | | |
| title crop 检查 | | |
| CAD JSON 检查 | | |
| CAD 预览图检查 | | |
| DWG converted_file_path 检查 | | |
| export_records 文件检查 | | |
| open issues 数量检查 | | |
| failed 图纸数量检查 | | |

## 四、维护工具检查

| 检查项 | 结果 | 备注 |
|---|---|---|
| 孤儿文件扫描可用 | | |
| 孤儿文件不自动删除 | | |
| temp 安全清理可用 | | |
| temp 清理不影响项目文件 | | |
| 错误响应包含 error_code | | |

## 五、旧流程回归

| 流程 | 结果 | 备注 |
|---|---|---|
| PDF 预览 | | |
| PDF 识别 | | |
| DXF 识别 | | |
| DWG 转换 | | |
| CAD pipeline | | |
| CAD 预览 | | |
| 校核工作台 | | |
| Excel 导出 | | |
| 备份恢复 | | |
| portable 启动 | | |

## 六、结论

- 是否可作为 v0.9-data-health 发布：
- 必须修复问题：
- 可延后问题：
