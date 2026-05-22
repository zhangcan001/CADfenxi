# v0.2-dxf-alpha 真实 DXF 小样本冒烟测试目录

本目录用于放置真实或接近真实的 DXF 冒烟测试样本。

注意：

- 不要放入涉密图纸。
- 如果使用真实项目图纸，请仅保留在本地。
- `.gitignore` 已排除本目录下的 `*.dxf`，只保留本说明文件。
- 当前本地样本可由脚本或 `ezdxf` 生成，用于模拟真实 DXF 的常见结构。

建议覆盖：

| 类型 | 说明 |
|---|---|
| 普通 CAD 导出的 DXF | 基础 TEXT / MTEXT / LINE / LAYER |
| DWG 转换得到的 DXF | 文件名或备注标注来源，系统仍按 DXF 导入 |
| 标题栏块属性 DXF | 含 `DRAWING_NO` / `DRAWING_NAME` / `DATE` / `REV` |
| 标题栏普通文字 DXF | 图签内容由 TEXT / MTEXT 表达 |
| 多图层 DXF | 含 `ARCH` / `STR` / `ELEC` / `给排水` / `建筑` / `结构` |
| 文件名规范 DXF | 文件名含图号、图名、版本、日期 |
| 文件名不规范 DXF | 文件名无法直接提取字段 |
| 无文字或少文字 DXF | 用于验证 `DXF_EMPTY_CONTENT` |
| 大量说明文字 DXF | 用于观察普通说明文字误识别情况 |
