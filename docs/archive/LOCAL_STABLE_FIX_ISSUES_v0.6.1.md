# v0.6.1 稳定版真实使用问题修复记录

## 一、测试环境

| 项目 | 内容 |
|---|---|
| 操作系统 | Windows |
| Python 版本 | Python 3.14.3 |
| 使用方式 | portable / 源码 |
| 测试路径 | c:\Users\ADMIN\Documents\trae_projects\CADtuzhi\drawing-ledger-ai |
| 测试版本 | v0.6-local-stable |
| 修复版本 | v0.6.1-local-stable-fix |

## 二、问题总览

| 严重程度 | 数量 | 说明 |
|---|---:|---|
| P0 | 0 | 未发现阻断启动、数据写入或核心流程的问题。 |
| P1 | 0 | PDF / DXF / DWG / CAD pipeline / 校核 / 导出回归通过。 |
| P2 | 5 | 版本展示不统一、启动端口提示泛化、关闭窗口后进程收尾、打包命令重复触发测试、回归测试缺少 v0.6.1 聚合记录。 |
| P3 | 2 | README 与当前稳定修复版定位不一致、缺少真实使用修复记录文档。 |

## 三、问题明细

| 编号 | 严重程度 | 模块 | 问题描述 | 复现步骤 | 原因分析 | 修复方式 | 状态 |
|---|---|---|---|---|---|---|---|
| V061-001 | P2 | 版本号 | 后端、前端、Excel 导出说明和打包默认版本仍显示旧版本。 | 访问 `/api/health`、查看首页版本、导出 Excel、运行打包脚本。 | 版本号分散在多个文件中。 | 统一更新为 `v0.6.1-local-stable-fix`，Excel 导出说明改为读取配置版本。 | fixed |
| V061-002 | P2 | portable 启动 | 启动端口占用提示固定描述 8000，使用自定义端口时不够清楚。 | 运行 `scripts/local_launcher.py --check --port <占用端口>`。 | 错误文案写死端口语义。 | 保留兼容错误码，详情中输出实际端口。 | fixed |
| V061-003 | P2 | portable 启动 | 关闭启动窗口或启动失败时，后端子进程可能只 terminate，极端情况下残留。 | 启动后关闭窗口或制造 health 超时。 | 进程结束后未等待并兜底 kill。 | `finally` 中 terminate 后等待，超时再 kill。 | fixed |
| V061-004 | P2 | 回归测试 | v0.6.1 缺少覆盖真实使用修复点的聚合回归测试。 | 查看 tests 目录。 | 旧测试覆盖分散，版本修复缺少集中入口。 | 新增 `tests/test_v061_stable_fix_regression.py` 覆盖健康检查、打包、PDF、DXF、DWG、pipeline、校核、导出、幂等和错误提示。 | fixed |
| V061-005 | P3 | README | README 当前版本和版本定位仍是 v0.5.5。 | 打开 README。 | 文档未随稳定修复阶段更新。 | 新增 v0.6.1 章节，更新当前版本和定位。 | fixed |
| V061-006 | P3 | 修复记录 | 缺少 v0.6.1 真实使用问题修复记录文档。 | 查看 docs 目录。 | 新阶段尚未建档。 | 新增本文档。 | fixed |
| V061-007 | P2 | portable 打包 | 执行指定打包命令会在已完成验收测试后再次触发完整 pytest，连续运行时 Windows 可能出现 `WinError 10055` 套接字资源不足。 | 先运行 `python -m pytest`，再运行 `python scripts/build_portable_package.py --version v0.6.1-local-stable-fix --clean`。 | CLI 默认值与打包函数默认值不一致，命令行默认重复跑测试。 | CLI 默认改为跳过内置重复测试；如需打包时强制测试，可显式使用 `--run-tests`。 | fixed |

## 四、修复验证

| 编号 | 修复验证方式 | 测试结果 | 备注 |
|---|---|---|---|
| V061-001 | `/api/health`、Excel 导出说明、前端构建、portable package_info 检查。 | 通过 | 版本统一为 `v0.6.1-local-stable-fix`。 |
| V061-002 | `check_startup_requirements` 端口占用和缺失 dist 诊断测试。 | 通过 | 保留 `PORT_8000_IN_USE` 兼容码。 |
| V061-003 | 代码回归检查与启动器 finally 分支覆盖。 | 通过 | terminate 后增加等待和 kill 兜底。 |
| V061-004 | `tests/test_v061_stable_fix_regression.py`。 | 通过 | 覆盖本阶段 20 项回归要求。 |
| V061-005 | README / 本地使用说明人工检查。 | 通过 | 与实际启动、打包、限制一致。 |
| V061-006 | 文档存在性检查。 | 通过 | 本文档随版本提交。 |
| V061-007 | 执行 `python scripts/build_portable_package.py --version v0.6.1-local-stable-fix --clean`。 | 通过 | 生成目标 portable 目录并通过完整性检查。 |

## 五、结论

- 是否存在 P0：否
- 是否存在 P1：否
- 是否可作为 v0.6.1 修复版：是
- 下一步建议：进入 `v0.6.2：识别规则小修与低风险优化`，仅针对真实使用中发现的图号、图名、专业、CAD tag 映射问题做低风险规则修补。
