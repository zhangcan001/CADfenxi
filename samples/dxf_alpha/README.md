# v0.2-dxf-alpha DXF 样本说明

本目录包含用于 DXF Alpha 冒烟测试的轻量样本，均由 `ezdxf` 生成，不包含真实工程图纸或涉密数据。

| 样本名称 | 内容 | 预期 |
|---|---|---|
| `simple_text.dxf` | 包含 `TEXT`：`建施-03` | 可解析 `TEXT`，生成 `cad_text` 图号候选 |
| `simple_mtext.dxf` | 包含 `MTEXT`：`二层平面图` | 可解析 `MTEXT`，生成 `cad_mtext` 图名候选 |
| `title_block_attrib.dxf` | 包含块属性 `DRAWING_NO` / `DRAWING_NAME` / `DATE` / `REV` | 可解析 `INSERT` / `ATTRIB`，生成 `cad_block_attr` 候选 |
| `layers_discipline.dxf` | 包含 `ARCH` / `STRUCT` / `ELEC` 图层 | `cad_layer` 仅生成专业候选 |
| `empty_geometry_only.dxf` | 只有线，没有文字或属性 | 解析成功并返回 `DXF_EMPTY_CONTENT` warning |
