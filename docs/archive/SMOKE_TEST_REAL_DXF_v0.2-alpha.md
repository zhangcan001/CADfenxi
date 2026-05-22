# v0.2-dxf-alpha 真实 DXF 小样本冒烟测试报告

## 一、测试环境

- 操作系统：Windows
- Python 版本：3.14.3
- Node 版本：v24.14.0
- 后端端口：TestClient 自动化冒烟；建议手工环境使用 8000
- 前端端口：建议手工环境使用 5173
- 测试日期：2026-05-21
- 测试版本：v0.2-dxf-alpha

## 二、测试样本

| 样本名称 | 来源 | 是否由 DWG 转换 | 是否含块属性 | 是否含普通文字 | 是否含多图层 | 备注 |
|---|---|---|---|---|---|---|
| `01_cad_export_arch_title_block.dxf` | ezdxf 模拟 CAD 导出 | 否 | 是 | 是 | 是 | 建筑标题栏块属性 |
| `02_converted_from_dwg_struct_title_block.dxf` | ezdxf 模拟 DWG 转 DXF | 是 | 是 | 是 | 是 | 结构标题栏块属性 |
| `03_text_title_no_block_JS-07_floor2_A_20260522.dxf` | ezdxf 模拟普通文字标题栏 | 否 | 否 | 是 | 是 | TEXT / MTEXT 标题栏 |
| `04_multilayer_mep_filename_bad.dxf` | ezdxf 模拟多图层机电图 | 否 | 否 | 是 | 是 | 文件名不规范 |
| `05_empty_geometry_only.dxf` | ezdxf 模拟空文字几何图 | 否 | 否 | 否 | 是 | 验证 `DXF_EMPTY_CONTENT` |
| `06_heavy_notes_with_title_block.dxf` | ezdxf 模拟大量说明文字 | 否 | 是 | 是 | 是 | 验证说明文字误识别 |
| `07_filename_only_DS-02_lighting_D_20260524.dxf` | ezdxf 模拟文件名线索样本 | 否 | 否 | 是 | 是 | 主要依赖文件名和图层 |

## 三、流程测试结果

| 流程 | 结果 | 问题说明 |
|---|---|---|
| 上传 DXF | 通过 | 7 个样本全部上传，`source_format = dxf` |
| DWG 拒绝 | 通过 | 返回 `DWG_NOT_SUPPORTED` |
| 准备 DXF 图纸页 | 通过 | 7 个 sheet 创建成功，重复准备未重复创建 |
| 解析 DXF | 通过 | 7/7 成功，空几何样本返回 `DXF_EMPTY_CONTENT` warning |
| 查看 CAD 摘要 | 通过 | 7/7 可查看 TEXT / MTEXT / ATTRIB / layer 摘要 |
| 生成候选值 | 通过 | 生成 `cad_block_attr` / `cad_text` / `cad_mtext` / `cad_layer` / `cad_filename` |
| 字段融合 | 通过 | 融合无报错，块属性样本优先采用 `cad_block_attr` |
| 图纸台账展示 | 通过 | 7 个 DXF sheet 进入台账，均无预览路径 |
| 人工校核 | 通过 | 人工修改图号后重新生成候选与融合未被覆盖 |
| Excel 导出 | 通过 | 导出 7 行台账、24 行问题清单，导出不改变状态 |

## 四、识别质量统计

| 指标 | 数量 | 说明 |
|---|---:|---|
| DXF 文件数量 | 7 | `samples/manual_dxf_smoke_v0_2/` |
| DXF sheet 数量 | 7 | 一个 DXF 默认一张图纸页 |
| parse-dxf 成功数量 | 7 | 成功率 100% |
| parse-dxf 失败数量 | 0 | 无 P0/P1 |
| TEXT 提取总数 | 16 | 含标题栏文字和说明文字 |
| MTEXT 提取总数 | 1 | 普通文字标题栏样本 |
| ATTRIB 提取总数 | 12 | 3 个块属性样本，每个 4 个属性 |
| 图层数量 | 9 | 含 `ARCH` / `STR` / `STRUCT` / `ELEC` / `PLUMBING` 等 |
| cad_block_attr 候选数量 | 12 | 图号、图名、日期、版本 |
| cad_text 候选数量 | 9 | TEXT 来源候选 |
| cad_mtext 候选数量 | 1 | MTEXT 来源候选 |
| cad_layer 候选数量 | 35 | 均为专业候选，未生成其他字段 |
| 图号候选成功数量 | 5 | 5/7 样本生成图号候选 |
| 图名候选成功数量 | 5 | 5/7 样本生成图名候选 |
| 专业候选成功数量 | 7 | 7/7 样本生成专业候选 |
| 字段融合 A/B/C/D 分布 | C=5，D=2 | DXF Alpha 下仍需人工校核 |
| 需要人工校核数量 | 7 | 全部样本进入 `need_review` |

## 五、发现问题

| 编号 | 问题类型 | 严重程度 | 现象 | 复现步骤 | 建议处理 |
|---|---|---|---|---|---|
| REAL-DXF-001 | 识别质量 | P2 | 多图层样本容易出现 `DISCIPLINE_CONFLICT`，部分样本专业来自多来源或仅来自图层 | 上传含 `ARCH` / `STRUCT` / `ELEC` / `PLUMBING` 的 DXF 后融合 | v0.2.1 使用真实样本优化图层专业规则 |
| REAL-DXF-002 | 识别质量 | P2 | 无块属性样本中，图号/图名成功率低于块属性样本 | 使用普通 TEXT / MTEXT 标题栏或文件名样本生成候选 | v0.2.1 优化 TEXT / MTEXT 标题栏规则 |
| REAL-DXF-003 | 体验/质量 | P3 | 所有样本均需要人工校核，C/D 等级较多 | 执行字段融合后查看台账 | 内测阶段接受，后续通过真实样本调优 |

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
- 不拆分 Layout
- 不做算量
- 不做 BIM
- 不做 AI 图纸问答

## 七、结论

- 是否通过真实 DXF 小样本冒烟测试：通过
- 是否存在 P0：不存在
- 是否存在 P1：不存在
- P2 问题是否已记录：已记录 REAL-DXF-001、REAL-DXF-002
- 是否可以进入 v0.2-dxf-alpha 内测：可以
- 必须修复问题：无 P0/P1
- 可延后问题：DXF 真实样本识别质量优化、图层专业冲突规则优化、TEXT / MTEXT 标题栏规则优化
- 下一步建议：进入 v0.2.1 识别质量优化，不进入 DWG 自动转换开发
