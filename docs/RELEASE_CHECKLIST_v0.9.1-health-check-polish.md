# v0.9.1-health-check-polish 发布检查清单

## 一、版本检查

| 检查项 | 结果 | 备注 |
|---|---|---|
| /api/health version 正确 | 通过 | v0.9.1-health-check-polish |
| 前端版本展示正确 | 通过 | 首页 / 页眉显示当前版本 |
| package_info.txt 版本正确 | 通过 | 打包时写入版本号 |
| README 版本正确 | 通过 | 已新增 v0.9.1 说明 |
| README_本地使用说明版本正确 | 通过 | 已新增健康检查优化说明 |
| RELEASE_NOTES 版本正确 | 通过 | 已新增 v0.9.1 发布说明 |

## 二、健康检查准确性

| 检查项 | 结果 | 备注 |
|---|---|---|
| 正常项目不误报大量文件 | 通过 | 以数据库引用路径为准 |
| 缺失原始图纸可识别 | 通过 | `DRAWING_FILE_MISSING` / error |
| 缺失预览图可识别 | 通过 | `SHEET_PREVIEW_MISSING` / warning |
| 缺失 CAD JSON 可识别 | 通过 | `CAD_JSON_MISSING` / warning |
| 缺失 CAD 预览图可识别 | 通过 | `CAD_PREVIEW_MISSING` / warning |
| 缺失 Excel 导出可识别 | 通过 | `EXPORT_FILE_MISSING` / warning |
| 缺失备份 zip 可识别 | 通过 | `BACKUP_FILE_MISSING` / warning |

## 三、孤儿文件与路径检查

| 检查项 | 结果 | 备注 |
|---|---|---|
| 反斜杠路径不误报 | 通过 | Windows 路径归一化 |
| 绝对路径不误报 | 通过 | 支持 `Path.resolve` |
| 中文和空格路径不误报 | 通过 | 保留用户可读路径展示 |
| README.md 不判定为孤儿 | 通过 | 已排除 |
| .gitkeep 不判定为孤儿 | 通过 | 已排除 |
| 数据库已引用文件不判定为孤儿 | 通过 | 使用规范化 key |

## 四、维护体验检查

| 检查项 | 结果 | 备注 |
|---|---|---|
| Error / Warning / Info 分级清楚 | 通过 | 前端展示三类指标 |
| grouped_summary 返回正常 | 通过 | storage / project_files / backup / export / restore / temp |
| 前端分组摘要显示正常 | 通过 | 问题集中展示 |
| 建议处理文案清楚 | 通过 | error_code 对应建议 |
| temp 清理仅限 app_data/temp | 通过 | 不触碰项目文件 |

## 五、旧流程回归

| 流程 | 结果 | 备注 |
|---|---|---|
| PDF 识别 | 通过 | 不受健康检查影响 |
| DXF 识别 | 通过 | 不受健康检查影响 |
| DWG 转 DXF | 通过 | 不直接解析 DWG |
| CAD 预览 | 通过 | 不受健康检查影响 |
| 校核工作台 | 通过 | 不受健康检查影响 |
| Excel 导出 | 通过 | 不修改导出结构 |
| 备份恢复 | 通过 | 不修改备份恢复主流程 |

## 六、结论

- 是否可作为 v0.9.1-health-check-polish 发布：是。
- 必须修复问题：无。
- 可延后问题：更多只读诊断项和报告导出增强。
