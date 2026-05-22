# v1.0-local-stable 发布检查清单

## 一、版本检查

| 检查项 | 结果 | 备注 |
|---|---|---|
| /api/health version 正确 | 通过 | v1.0-local-stable |
| 前端版本展示正确 | 通过 | `APP_VERSION = v1.0-local-stable` |
| package_info.txt 版本正确 | 通过 | portable 打包后检查 |
| README 版本正确 | 通过 | 已整理为 v1.0 正式版 |
| README_本地使用说明版本正确 | 通过 | 已整理为 v1.0 用户说明 |
| RELEASE_NOTES 版本正确 | 通过 | 已新增 v1.0 发布说明 |

## 二、portable 包检查

| 检查项 | 结果 | 备注 |
|---|---|---|
| start.bat 存在 | 通过 | |
| check_env.bat 存在 | 通过 | |
| stop.bat 存在 | 通过 | |
| frontend/dist 存在 | 通过 | |
| backend 存在 | 通过 | |
| recognizer 存在 | 通过 | |
| app_data 基础目录存在 | 通过 | projects / database / logs / temp / backups |
| package_info.txt 存在 | 通过 | |
| 不包含 node_modules | 通过 | |
| 不包含 .git | 通过 | |
| 不包含真实项目数据 | 通过 | app_data 仅保留 .gitkeep |
| 不包含真实图纸样本 | 通过 | samples 未打入 portable |

## 三、核心功能检查

| 模块 | 结果 | 备注 |
|---|---|---|
| 项目管理 | 通过 | 自动化回归覆盖 |
| PDF 识别闭环 | 通过 | 自动化回归覆盖 |
| DXF 识别闭环 | 通过 | 自动化回归覆盖 |
| DWG 转 DXF | 通过 | mock 转换回归覆盖 |
| CAD pipeline | 通过 | 混合批次回归覆盖 |
| CAD 预览 | 通过 | 单张、批量、图片接口回归覆盖 |
| 校核工作台 | 通过 | 人工字段保护与确认回归覆盖 |
| Excel 导出 | 通过 | 导出一致性回归覆盖 |
| 项目备份 | 通过 | 备份回归覆盖 |
| 项目恢复 | 通过 | 恢复为新项目回归覆盖 |
| 数据健康检查 | 通过 | 系统、项目、备份、导出、temp 回归覆盖 |
| portable 启动 | 通过 | /api/health 轻量启动验证 |

## 四、可靠性检查

| 检查项 | 结果 | 备注 |
|---|---|---|
| P0 = 0 | 通过 | 未发现 P0 |
| P1 = 0 | 通过 | 已修复前端构建 BOM 问题 |
| 人工确认字段不被覆盖 | 通过 | |
| 导出不改变图纸状态 | 通过 | |
| 导出不改变问题状态 | 通过 | |
| 备份恢复不覆盖原项目 | 通过 | |
| 删除备份不删除项目 | 通过 | |
| CAD 预览失败不影响导出 | 通过 | |
| temp 清理不删除项目数据 | 通过 | |
| 健康检查只诊断 | 通过 | |

## 五、文档检查

| 文档 | 结果 | 备注 |
|---|---|---|
| README.md | 通过 | |
| README_本地使用说明.md | 通过 | |
| RELEASE_NOTES.md | 通过 | |
| app_data 备份迁移指南 | 通过 | `APP_DATA_BACKUP_MIGRATION_GUIDE_v0.7.2.md` |
| 备份恢复 FAQ | 通过 | `BACKUP_RESTORE_FAQ_v0.7.2.md` |
| 数据安全检查清单 | 通过 | `DATA_SAFETY_CHECKLIST_v0.7.2.md` |
| 最终验收报告 | 通过 | `FINAL_ACCEPTANCE_v1.0-local-stable.md` |

## 六、结论

- 是否可作为 v1.0-local-stable 发布：是。
- 必须修复问题：无。
- 可延后问题：真实大样本长期使用反馈可在后续版本继续收集。
