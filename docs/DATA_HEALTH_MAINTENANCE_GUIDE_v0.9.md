# v0.9 数据健康检查与系统维护指南

## 一、版本定位

v0.9-data-health 新增“系统维护 / 数据健康检查”能力，用于长期本地使用后的数据巡检。

本版本重点是只读检查，不会自动修复数据库，不会删除项目文件，不会删除数据库记录。

## 二、系统健康检查会检查什么

- app_data 目录是否存在。
- database、projects、backups、logs、temp 目录是否存在。
- app_data 及关键目录是否可写。
- 数据库文件 app_data/database/app.db 是否存在。
- backup_records 对应的备份 zip 是否存在。
- export_records 对应的 Excel 文件是否存在。
- restore_records 是否指向有效的新项目。
- app_data/temp 中是否有可安全清理的临时文件。

## 三、项目完整性检查会检查什么

- 项目记录是否存在。
- 项目目录 app_data/projects/project_{project_id}/ 是否存在。
- drawing_files.storage_path 指向的原始文件是否存在。
- drawing_files.converted_file_path 指向的 DWG 转换 DXF 是否存在。
- drawing_sheets.preview_path、thumbnail_path 是否存在。
- drawing_sheets.title_crop_path 是否存在。
- drawing_sheets.cad_preview_path 是否存在。
- DXF 解析生成的 CAD JSON 是否存在。
- recognition_runs.output_path 是否存在。
- export_records.file_path 是否存在。
- 当前项目是否存在 open issues。
- 当前项目是否存在 failed 状态图纸。
- 项目目录中是否存在数据库未引用的孤儿文件。

## 四、健康等级说明

- ok：检查项正常。
- warning：需要关注，但通常可以通过重新生成预览、重新导出或人工确认处理。
- error：关键数据缺失，例如原始图纸文件或备份 zip 缺失。

## 五、如何使用前端维护工具

1. 启动系统。
2. 打开任意项目。
3. 找到“系统维护 / 数据健康检查”区域。
4. 点击“运行系统健康检查”查看 app_data、备份、导出和恢复记录状态。
5. 点击“检查当前项目”查看当前项目的文件引用是否完整。
6. 点击“扫描孤儿文件”查看项目目录中数据库未引用的文件。
7. 点击“生成维护报告”查看可复制的 Markdown 报告。
8. 如需清理临时文件，可点击“安全清理 temp”。

## 六、安全清理 temp 的范围

安全清理只处理：

- app_data/temp/ 下的普通临时文件。
- app_data/temp/ 下清空后的空目录。

不会处理：

- app_data/projects/
- app_data/database/
- app_data/backups/
- app_data/logs/
- 任意数据库记录
- 任意项目图纸文件

## 七、常见处理建议

| 问题 | 建议 |
|---|---|
| 原始图纸文件缺失 | 确认是否完整复制 app_data/projects，必要时从全量 app_data 备份恢复 |
| PDF 预览缺失 | 重新生成图纸页预览 |
| 标题栏裁剪图缺失 | 重新生成标题栏裁剪图 |
| CAD JSON 缺失 | 重新执行 DXF 解析 |
| CAD 预览缺失 | 重新生成 CAD 预览 |
| DWG 转换 DXF 缺失 | 重新执行 DWG 转 DXF |
| Excel 文件缺失 | 重新导出 Excel |
| 备份 zip 缺失 | 检查备份文件是否被手动移动或删除 |
| 孤儿文件 | 人工确认后再手动处理，本版本不会自动删除项目文件 |

## 八、重要边界

- 不做自动数据库修复。
- 不做危险删除。
- 不删除项目文件。
- 不删除数据库记录。
- 不做云端同步。
- 不做多人权限。
- 不做 CAD 编辑。
- 不做算量、BIM 或 AI 图纸问答。
