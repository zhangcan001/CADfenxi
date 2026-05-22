# v0.5.5 真实项目全流程稳定性回归报告

## 一、测试环境

| 项目 | 内容 |
|---|---|
| 操作系统 | Windows |
| Python 版本 | Python 3.14.3 |
| Node 版本 | 以本机 npm run build 环境为准 |
| 启动方式 | 源码；portable 相关自动化回归覆盖启动脚本与打包结构 |
| 测试路径 | `c:\Users\ADMIN\Documents\trae_projects\CADtuzhi\drawing-ledger-ai` |
| 测试版本 | v0.5.5 |
| 测试日期 | 2026-05-21 |

## 二、测试资料

| 类型 | 数量 | 说明 |
|---|---:|---|
| PDF 文件 | 1+ | 自动化生成最小 PDF |
| PDF 页数 | 1+ | 覆盖拆页、文本提取、OCR、候选、融合、校核、导出 |
| DXF 文件 | 1+ | 自动化生成标题栏 DXF |
| DWG 文件 | 1+ | 使用 mock converter 转 DXF |
| 最终图纸页数 | 多批次动态生成 | 覆盖 PDF / DXF / DWG 混合批次 |

## 三、流程回归结果

| 场景 | 结果 | 说明 |
|---|---|---|
| portable 启动 | 通过 | `/api/health`、存储目录、启动脚本、portable 相关测试均通过。 |
| PDF 单文件流程 | 通过 | 覆盖上传、拆页、裁剪、文本提取、OCR、候选、融合、校核、Excel。 |
| DXF 单文件流程 | 通过 | 覆盖 prepare、parse、CAD 摘要、候选、融合、幂等、Excel。 |
| DWG 转换流程 | 通过 | 使用 mock converter；真实外部转换工具未在本轮自动化中验证。 |
| CAD pipeline 批量流程 | 通过 | 覆盖 PDF + DXF + DWG 混合批次，PDF 不被误处理。 |
| 重复操作幂等性 | 通过 | prepare、parse、generate-candidates、fuse-fields、pipeline、Excel 重复操作稳定。 |
| 人工确认保护 | 通过 | 修复并验证已确认图纸再次 fuse / pipeline 后不被重置为未校核。 |
| Excel 导出一致性 | 通过 | Excel 行数、人工确认值、问题状态和 review_status 一致。 |
| 异常错误提示 | 通过 | 覆盖无图纸导出、损坏 DXF、未配置 converter、不支持格式。 |

## 四、稳定性问题

| 编号 | 严重程度 | 模块 | 问题描述 | 是否修复 | 备注 |
|---|---|---|---|---|---|
| 1 | P1 | 字段融合 / 校核状态 | 已确认图纸再次执行 fuse-fields 或 CAD pipeline 后可能被重置为未校核 | 是 | `fusion_service.sync_sheet` 已保留 confirmed 状态。 |

## 五、数据一致性检查

| 检查项 | 结果 | 说明 |
|---|---|---|
| drawing_sheets 数量一致 | 通过 | 重复 prepare-dxf-sheet 不重复创建 sheet。 |
| candidates 未异常堆积 | 通过 | 重复 generate-candidates 后候选数量保持稳定。 |
| open issues 未异常堆积 | 通过 | 重复 fuse-fields 后 open issues 数量保持稳定。 |
| 人工确认字段未被覆盖 | 通过 | generate-candidates、fuse-fields、cad-pipeline 后人工图号保持。 |
| Excel 台账行数一致 | 通过 | 导出行数与 drawing_sheets 数量一致。 |
| Excel 问题清单一致 | 通过 | 导出不改变 drawing_issues.status。 |

## 六、结论

- 是否存在 P0：否。
- 是否存在 P1：无未修复 P1。
- 是否可进入 v0.6 稳定版准备：可以。
- 必须修复问题：暂无。
- 可延后问题：真实外部 DWG 转换工具仍建议在 v0.6 发布前人工烟测一次。
