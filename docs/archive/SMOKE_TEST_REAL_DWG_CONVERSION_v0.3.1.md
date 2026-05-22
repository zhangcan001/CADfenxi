# v0.3.1 真实 DWG 转 DXF 冒烟测试报告

## 一、测试环境

- 操作系统：Windows，本地开发环境
- Python 版本：Python 3.14.3
- Node 版本：以本机 `npm run build` 环境为准
- 转换工具名称：自动化使用 mock converter；真实 ODA 需手工配置
- 转换工具路径：本地配置，示例 `C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe`
- 后端端口：8000
- 前端端口：5173
- 测试日期：2026-05-21
- 测试版本：v0.3.1

## 二、测试样本

| 样本名称 | DWG 版本 | 是否中文路径 | 是否中文文件名 | 是否含空格 | 是否转换成功 | 备注 |
|---|---|---|---|---|---|---|
| mock same-name.dwg | 模拟 | 是 | 否 | 是 | 是 | 同名 .dxf 输出 |
| mock upper-output.dwg | 模拟 | 是 | 否 | 是 | 是 | 大写 .DXF 输出 |
| mock similar-name.dwg | 模拟 | 是 | 否 | 是 | 是 | 相近文件名输出 |
| mock ambiguous.dwg | 模拟 | 是 | 否 | 是 | 是 | 多候选，记录 DWG_CONVERT_OUTPUT_AMBIGUOUS |
| mock missing.dwg | 模拟 | 是 | 否 | 是 | 否 | 无输出，返回 DWG_CONVERT_OUTPUT_MISSING |
| mock failed.dwg | 模拟 | 是 | 否 | 是 | 否 | 非 0 退出，返回 DWG_CONVERT_FAILED |
| mock timeout.dwg | 模拟 | 是 | 否 | 是 | 否 | 超时，返回 DWG_CONVERT_TIMEOUT |

## 三、流程测试结果

| 流程 | 结果 | 说明 |
|---|---|---|
| 配置转换工具 | 通过 | 支持中文和空格路径 mock converter |
| 检测转换工具 | 通过 | 不存在路径返回 CONVERTER_NOT_FOUND |
| 上传 DWG | 通过 | source_format=dwg，convert_status=pending |
| 单个转换 | 通过 | converted/ 下生成 DXF |
| 批量转换 | 通过 | 单个失败不影响其他文件 |
| 转换后 parse-dxf | 通过 | 使用 converted_file_path |
| 转换后候选值生成 | 通过 | cad_* candidates 正常生成 |
| 转换后字段融合 | 通过 | field_values 正常生成 |
| 转换后人工校核 | 通过 | 人工字段可保存并保护 |
| 转换后 Excel 导出 | 通过 | 导出文件生成成功 |

## 四、转换质量统计

| 指标 | 数量 | 说明 |
|---|---:|---|
| DWG 文件数量 | 16 | 自动化 mock 场景 |
| 转换成功数量 | 8+ | 覆盖同名、大写、相近、多候选、批量成功 |
| 转换失败数量 | 4+ | 覆盖无输出、非 0、超时、批量单失败 |
| parse-dxf 成功数量 | 2+ | 覆盖转换后 DWG 解析 |
| 候选值生成成功数量 | 1+ | 完整流程测试覆盖 |
| 字段融合成功数量 | 1+ | 完整流程测试覆盖 |
| Excel 导出成功数量 | 1+ | 完整流程测试覆盖 |

## 五、发现问题

| 编号 | 问题 | 严重程度 | 是否修复 | 备注 |
|---|---|---|---|---|
| DWG-001 | 批量转换时可能误拾取上一文件输出 | P1 | 已修复 | 改为每文件临时输入目录，并基于输出快照查找 |
| DWG-002 | 大写 .DXF 不被识别 | P1 | 已修复 | 输出查找改为大小写不敏感 |
| DWG-003 | 多候选输出无提示 | P2 | 已修复 | 记录 DWG_CONVERT_OUTPUT_AMBIGUOUS |

## 六、已知限制

- 系统不直接解析 DWG
- 系统不内置转换工具
- DWG 转换质量取决于用户本机转换工具
- 复杂 DWG、缺字体、外部参照、代理实体可能影响转换结果
- 当前不做 CAD 图形预览
- 当前不做算量 / BIM / AI 问答

## 七、结论

- 是否通过 v0.3.1 DWG 转换冒烟测试：通过自动化 mock 冒烟；真实 ODA 样本需用户本机继续执行
- 是否可以进入 v0.3.1 内测：可以
- 必须修复问题：暂无
- 可延后问题：真实 ODA 输出兼容矩阵、更多 DWG 版本样本统计
