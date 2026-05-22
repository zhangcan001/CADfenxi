# v0.9.2-maintenance-stable 发布检查清单

## 一、版本检查

| 检查项 | 结果 | 备注 |
|---|---|---|
| /api/health version 正确 | 通过 | v0.9.2-maintenance-stable |
| 前端版本展示正确 | 通过 | `frontend/src/constants.ts` |
| package_info.txt 版本正确 | 通过 | 打包时生成 |
| README 版本正确 | 通过 | 已新增 v0.9.2 说明 |
| README_本地使用说明版本正确 | 通过 | 已新增 v0.9.2 使用建议 |
| RELEASE_NOTES 版本正确 | 通过 | 已新增 v0.9.2 发布说明 |

## 二、最终回归检查

| 模块 | 结果 | 备注 |
|---|---|---|
| PDF 全流程 | 通过 | 最小闭环回归 |
| DXF 全流程 | 通过 | CAD JSON / 候选 / 导出 |
| DWG 转 DXF | 通过 | mock 外部转换回归 |
| CAD pipeline | 通过 | 可选 `generate_cad_preview` 不阻断 |
| 校核工作台 | 通过 | 人工确认字段保护 |
| Excel 导出 | 通过 | 导出不改变图纸或问题状态 |
| 备份恢复 | 通过 | 恢复为新项目 |
| CAD 预览 | 通过 | 单张、批量、缓存、图片访问 |
| 数据健康检查 | 通过 | 只诊断，temp 清理范围受控 |
| portable 打包 | 通过 | 输出 v0.9.2 目录 |

## 三、v1.0 准备

| 检查项 | 结果 | 备注 |
|---|---|---|
| V1_0_RELEASE_PRECHECK 已完成 | 通过 | `docs/V1_0_RELEASE_PRECHECK_v0.9.2.md` |
| FINAL_REGRESSION_REPORT 已完成 | 通过 | `docs/FINAL_REGRESSION_REPORT_v0.9.2.md` |
| P0 = 0 | 通过 | 未发现阻断问题 |
| P1 = 0 | 通过 | 未发现必须修复问题 |
| 未新增范围外功能 | 通过 | 仅版本、文档、回归收口 |

## 四、结论

- 是否可作为 v0.9.2 系统维护稳定版：是。
- 是否可进入 v1.0：最终命令全部通过后可进入。
- 必须修复问题：暂无。
- 可延后问题：继续补充真实业务样本人工回归记录。
