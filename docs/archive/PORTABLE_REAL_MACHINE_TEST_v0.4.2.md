# v0.4.2 Windows 便携包真实换机测试记录

## 一、测试目标

验证 `工程图纸智能台账识别系统-v0.4.1-portable` 复制到 Windows 电脑后的启动、路径兼容性、前端静态托管和核心业务可用性，并将本阶段修复后的包整理为 `工程图纸智能台账识别系统-v0.4.2-portable`。

本阶段不新增识别功能，不做 exe，不引入 Electron / Tauri。

## 二、测试电脑配置

### 测试机 A

| 项目 | 结果 |
| --- | --- |
| 类型 | 开发机本机模拟换机路径 |
| 系统 | Windows |
| Python | 3.14.3 |
| Node | 已安装，仅用于开发机构建；portable 运行不需要 Node |
| DWG 转换工具 | 未在本次自动化烟测中配置 |

### 测试机 B

| 项目 | 结果 |
| --- | --- |
| 类型 | 待真实干净 Windows 机器验证 |
| 系统 | 建议 Windows 10 / 11 |
| Python | 建议仅安装 Python 3.11+ |
| Node | 可不安装 |
| DWG 转换工具 | 可选，未安装时应提示需要配置转换工具 |

## 三、测试路径

| 路径类型 | 测试路径 | 结果 |
| --- | --- | --- |
| release 原始路径 | `release/工程图纸智能台账识别系统-v0.4.2-portable/` | 通过 |
| 空格路径 | `app_data/temp/CAD Test Package/工程图纸智能台账识别系统-v0.4.2-portable/` | 通过 |
| 中文路径 | `app_data/temp/项目软件测试/图纸识别系统/` | 通过 |
| 独立测试机路径 | `D:\工程图纸系统测试\工程图纸智能台账识别系统-v0.4.1-portable\` | 待真实测试 |

## 四、目录完整性检查

portable 包应包含：

```text
backend/
recognizer/
frontend/dist/
scripts/
app_data/
requirements.txt
start.bat
stop.bat
check_env.bat
README_本地使用说明.md
package_info.txt
RELEASE_NOTES.md
```

本机检查结果：通过。

## 五、环境检查结果

在 portable 目录执行：

```bat
python scripts\local_launcher.py --check
```

结果：

```text
[OK] Python: 3.14.3
[OK] pip: available
[OK] requirements.txt: found
[OK] backend/main.py: found
[OK] frontend/dist/index.html: found
[OK] app_data: writable
[OK] port 8000: free
```

结论：通过。

## 六、依赖安装结果

本机已有依赖，未在干净测试机执行完整联网安装。

待真实换机重点观察：

```text
scripts\install_backend_deps.bat
```

是否能正确读取根目录 `requirements.txt`，并安装 FastAPI、SQLAlchemy、PyMuPDF、openpyxl、ezdxf 等依赖。失败时窗口会保留错误并暂停。

## 七、启动结果

验证方式：

```text
在 portable 目录启动后端，访问 /api/health、/、/projects、/api/projects
```

本机烟测结果：

```text
/api/health: 200
/: 200
/projects: 200
/api/projects: 200
```

`/api/health` 返回：

```json
{"status":"ok","version":"v0.4.2","database":"ok","storage":"ok"}
```

结论：通过。

## 八、浏览器访问结果

`scripts/local_launcher.py` 在 `/api/health` 可访问后调用 `webbrowser.open("http://127.0.0.1:8000")`。

本机以 HTTP 烟测替代真实双击浏览器观察：通过。真实换机时需人工确认浏览器是否自动打开。

## 九、核心流程测试结果

自动化回归：

```text
python -m pytest
```

结果：

```text
228 passed
```

覆盖 PDF、DXF、DWG 转换、CAD pipeline、Excel 导出等旧流程测试。

真实换机仍需人工冒烟：

```text
新建项目
上传 PDF
PDF 拆页
导出 Excel
上传 DXF
准备 DXF 图纸页
解析 DXF
生成候选值
字段融合
上传 DWG
未配置转换工具时提示清楚
已配置转换工具时执行 DWG 转 DXF
CAD pipeline 批量处理
Excel 导出
```

## 十、重点问题排查

| 问题 | 本机结论 | 说明 |
| --- | --- | --- |
| start.bat 双击闪退 | 待真实双击验证 | 脚本失败时会 pause |
| Python 不在 PATH | 待真实验证 | start.bat/check_env.bat 均有提示 |
| pip install 失败 | 待干净机验证 | install_backend_deps.bat 会 pause |
| 中文路径启动失败 | 通过 | 本机中文路径模拟通过 |
| 空格路径启动失败 | 通过 | 本机空格路径模拟通过 |
| frontend/dist 找不到 | 通过 | check_env 可识别 |
| 静态页面能打开但 API 404 | 通过 | `/api/projects` 返回 200 |
| /api 被前端 fallback 抢占 | 通过 | 自动化测试覆盖 |
| app_data 写入失败 | 通过 | check_env 可写 |
| SQLite 数据库路径错误 | 通过 | `/api/health` database ok |
| 8000 端口占用提示不清楚 | 通过 | launcher 和 start_local 均提示 |
| 关闭窗口后进程残留 | 待真实双击验证 | 本机烟测可手动停止进程 |
| portable 包误带真实数据 | 通过 | app_data 仅保留 .gitkeep |
| portable 包缺少必要文件 | 通过 | 自动化测试覆盖 |
| Excel 导出路径错误 | 自动化回归通过 | 真实换机仍需手动导出 |
| CAD converted / cad/parsed 路径错误 | 自动化回归通过 | 真实换机仍需手动样本验证 |

## 十一、修复情况

* 更新本地启动提示版本文案。
* 增加本换机测试记录文档。
* 复查 portable 包重新构建后为干净状态。

## 十二、最终结论

本机模拟中文路径、空格路径和 release 原始路径均通过。  
自动化回归通过。  
portable 包结构完整，未携带开发机真实项目数据。

仍建议在独立 Windows 10 / 11 机器执行一次完整人工换机冒烟，尤其验证首次依赖安装、真实双击 start.bat、浏览器自动打开和 DWG 外部转换工具配置。
