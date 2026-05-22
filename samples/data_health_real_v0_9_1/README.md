# v0.9.1 数据健康检查真实 app_data 样本说明

本目录用于放置本机手工回归样本说明，不提交真实图纸、不提交真实 app_data。

建议在本机准备以下场景：

1. 正常项目：PDF / DXF / DWG / CAD 预览 / Excel 导出均正常。
2. 缺失原始文件项目：手动移除某个 original 文件，验证 `DRAWING_FILE_MISSING`。
3. 缺失预览文件项目：手动移除 preview / thumbnail，验证 `SHEET_PREVIEW_MISSING` / `SHEET_THUMBNAIL_MISSING`。
4. 缺失 CAD 文件项目：手动移除 CAD JSON 或 CAD 预览图，验证 `CAD_JSON_MISSING` / `CAD_PREVIEW_MISSING`。
5. 缺失导出文件项目：删除某个 Excel 导出文件，验证 `EXPORT_FILE_MISSING`。
6. 缺失备份包：删除某个 backup zip，验证 `BACKUP_FILE_MISSING`。
7. 孤儿文件项目：在项目目录中放入数据库未引用的文件，验证 `ORPHAN_FILE_FOUND`。

注意：

- 不要提交涉密图纸。
- 不要提交真实 `app_data`。
- 构造样本前先全量备份 `app_data`。
- v0.9.1 只提示问题，不会自动修改数据库或删除项目文件。
