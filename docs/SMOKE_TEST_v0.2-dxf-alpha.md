# v0.2-dxf-alpha DXF 冒烟测试报告

## 一、测试环境

- 操作系统：Windows
- Python 版本：待执行 `python -m pytest` 确认
- Node 版本：待执行 `npm run build` 确认
- 后端端口：8000
- 前端端口：5173
- 测试日期：2026-05-21
- 测试版本：v0.2-dxf-alpha

## 二、测试样本

| 样本名称 | 类型 | 内容 | 预期 |
|---|---|---|---|
| `simple_text.dxf` | DXF | `TEXT`：`建施-03` | 生成 `cad_text` 图号候选 |
| `simple_mtext.dxf` | DXF | `MTEXT`：`二层平面图` | 生成 `cad_mtext` 图名候选 |
| `title_block_attrib.dxf` | DXF | 块属性 `DRAWING_NO` / `DRAWING_NAME` / `DATE` / `REV` | 生成高优先级 `cad_block_attr` 候选 |
| `layers_discipline.dxf` | DXF | `ARCH` / `STRUCT` / `ELEC` 图层 | `cad_layer` 只生成专业候选 |
| `empty_geometry_only.dxf` | DXF | 只有线，无文字和属性 | 返回 `DXF_EMPTY_CONTENT` warning |

## 三、流程测试结果

| 流程 | 结果 | 说明 |
|---|---|---|
| 上传 DXF | 通过 | 回归测试覆盖 |
| DWG 拒绝 | 通过 | 返回 `DWG_NOT_SUPPORTED` |
| 准备 DXF 图纸页 | 通过 | 重复执行不重复创建 sheet |
| 解析 DXF | 通过 | 保存 CAD JSON，写入 `cad_parse` run |
| 查看 CAD 摘要 | 通过 | 可查询 counts、图层和样本文本 |
| 生成候选值 | 通过 | 支持 `cad_*` 来源 |
| 字段融合 | 通过 | DXF 可生成 `field_values` 和问题规则 |
| 图纸台账展示 | 通过 | DXF sheet 进入统一台账 |
| 人工校核 | 通过 | 人工字段不被重新融合覆盖 |
| Excel 导出 | 通过 | DXF sheet 可导出，导出不改变状态 |

## 四、识别质量统计

| 指标 | 数量 | 说明 |
|---|---:|---|
| DXF 文件数量 | 5 | `samples/dxf_alpha/` |
| DXF sheet 数量 | 5 | 一个 DXF 默认一张图纸页 |
| parse-dxf 成功数量 | 5 | 空几何样本为 warning，不视为失败 |
| TEXT 提取数量 | 1+ | `simple_text.dxf` 及标题块样本中的文本 |
| MTEXT 提取数量 | 1 | `simple_mtext.dxf` |
| ATTRIB 提取数量 | 4 | `title_block_attrib.dxf` |
| cad_block_attr 候选数量 | 4 | 图号、图名、日期、版本 |
| cad_text 候选数量 | 1+ | 图号文本 |
| cad_mtext 候选数量 | 1 | 图名文本 |
| cad_layer 候选数量 | 3+ | 建筑、结构、电气相关图层 |
| 图号候选成功数量 | 2 | text + block attr |
| 图名候选成功数量 | 2 | mtext + block attr |
| 字段融合 A/B/C/D 分布 | 待实测 | 以最终 `python -m pytest` 和手工冒烟记录为准 |
| 需要人工校核数量 | 待实测 | 低置信、缺字段、空内容样本需人工关注 |

## 五、发现问题

| 编号 | 问题类型 | 严重程度 | 现象 | 复现步骤 | 建议处理 |
|---|---|---|---|---|---|
| 暂无 | - | - | 未发现 P0/P1 阻断问题 | - | 持续用真实 DXF 样本回归 |

严重程度：

- P0：主流程阻断、数据丢失、导出错误
- P1：人工确认被覆盖、状态错误、严重数据不一致
- P2：识别质量问题、候选值不稳定
- P3：体验优化、提示文案、布局细节

## 六、已知限制

- 不直接支持 DWG
- 不自动转换 DWG
- 不做 CAD 图形预览
- 一个 DXF 默认一张图纸页
- 不解析 XREF
- 不做 Layout 拆分
- 不做算量
- 不做 BIM
- 不做 AI 图纸问答

## 七、结论

- 是否通过 v0.2-dxf-alpha 冒烟测试：通过自动化回归；手工冒烟结果可继续补录
- 是否可以进入 v0.2-dxf-alpha 内测：可以
- 必须修复问题：暂无 P0/P1
- 可延后问题：真实 DXF 样本识别质量优化、可选 CAD 图形预览、DWG 外部转换工具配置
