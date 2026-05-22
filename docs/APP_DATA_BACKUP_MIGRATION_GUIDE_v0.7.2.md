# app_data 全量备份与迁移指南

## 一、什么是 app_data

app_data 是系统的本地数据目录，里面保存所有项目数据、数据库、上传图纸、转换文件、CAD 解析结果、Excel 导出文件和日志。

## 二、app_data 包含哪些内容

- app_data/database/：SQLite 数据库。
- app_data/projects/：项目图纸文件、预览、裁剪、OCR、CAD JSON、转换结果。
- app_data/backups/：项目备份包。
- app_data/logs/：启动日志和运行日志。
- app_data/temp/：临时文件。
- app_data/exports/：如果项目中存在独立导出目录，导出文件会保存在这里。

## 三、什么时候需要全量备份

- 升级 portable 包前。
- 换电脑前。
- 大量导入图纸前。
- 执行重要恢复操作前。
- 删除项目或清理数据前。
- 长期使用后定期备份。

## 四、如何全量备份

1. 关闭系统。
2. 确认 start.bat 窗口已经关闭。
3. 复制整个 app_data 目录。
4. 粘贴到安全位置，例如移动硬盘、网盘目录、本机其他盘。
5. 建议重命名为：app_data_backup_YYYYMMDD_HHMMSS。

## 五、如何恢复全量 app_data

1. 关闭系统。
2. 备份当前 app_data，防止覆盖错误。
3. 将备份的 app_data 复制回软件根目录。
4. 确认目录名称为 app_data。
5. 重新运行 start.bat。
6. 打开项目列表检查项目是否存在。

## 六、如何换电脑迁移

1. 在旧电脑关闭系统。
2. 复制整个 portable 包目录，或至少复制 app_data。
3. 在新电脑解压或复制 portable 包。
4. 安装 Python 依赖。
5. 将旧 app_data 放入新包根目录。
6. 运行 check_env.bat。
7. 运行 start.bat。
8. 检查项目列表、台账、导出功能。

## 七、如何升级 portable 包并保留数据

1. 下载或生成新版 portable 包。
2. 不要直接覆盖旧包。
3. 先关闭旧系统。
4. 复制旧包中的 app_data。
5. 放入新版 portable 根目录。
6. 运行 check_env.bat。
7. 运行 start.bat。
8. 确认项目列表正常。
9. 确认图纸台账和 Excel 导出正常。

## 八、常见错误

- 只复制了 database，没有复制 projects，导致图纸文件缺失。
- 只复制了 projects，没有复制 database，导致项目列表为空。
- 系统运行时复制 app_data，可能导致数据库未完全写入。
- 把 app_data 放错目录。
- 新电脑缺少 Python 依赖。
- 端口 8000 被占用。
- 没有写入权限。

## 九、推荐备份策略

- 每次真实项目导入前备份一次。
- 每次大批量识别完成后备份一次。
- 每次升级 portable 包前备份一次。
- 每周或每个项目节点备份一次。
- 重要项目保留至少两个备份版本。
