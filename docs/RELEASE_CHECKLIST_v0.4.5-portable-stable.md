# v0.4.5-portable-stable 发布检查清单

## 一、版本检查

| 检查项 | 结果 | 备注 |
|---|---|---|
| /api/health version 正确 | 通过 | v0.4.5-portable-stable |
| 前端版本展示正确 | 通过 | 首页标题显示 stable 版本 |
| package_info.txt 版本正确 | 通过 | |
| README 版本正确 | 通过 | |
| README_本地使用说明版本正确 | 通过 | |
| RELEASE_NOTES 版本正确 | 通过 | |

## 二、包结构检查

| 检查项 | 结果 | 备注 |
|---|---|---|
| backend 存在 | 通过 | |
| recognizer 存在 | 通过 | |
| frontend/dist/index.html 存在 | 通过 | |
| scripts/local_launcher.py 存在 | 通过 | |
| app_data 基础目录存在 | 通过 | projects/database/logs/temp |
| requirements.txt 存在 | 通过 | |
| start.bat 存在 | 通过 | |
| stop.bat 存在 | 通过 | |
| check_env.bat 存在 | 通过 | |
| README_本地使用说明.md 存在 | 通过 | |
| package_info.txt 存在 | 通过 | |

## 三、清理检查

| 检查项 | 结果 | 备注 |
|---|---|---|
| 不包含 .git | 通过 | |
| 不包含 node_modules | 通过 | |
| 不包含 __pycache__ | 通过 | |
| 不包含 .env | 通过 | |
| 不包含真实项目数据 | 通过 | app_data 仅含 .gitkeep |
| 不包含真实图纸样本 | 通过 | samples 不进入包 |
| 不包含历史日志 | 通过 | |
| 不包含临时测试文件 | 通过 | |

## 四、启动检查

| 检查项 | 结果 | 备注 |
|---|---|---|
| check_env.bat 可运行 | 通过 | Python 检查等价命令已验证 |
| scripts/install_backend_deps.bat 可运行 | 待真实干净机验证 | 本机已有依赖 |
| start.bat 可启动 | 通过 | 服务烟测验证 |
| 浏览器自动打开 | 待真实双击验证 | launcher 调用 webbrowser.open |
| /api/health 正常 | 通过 | |
| GET / 返回前端页面 | 通过 | |
| /api/* 不被前端 fallback 抢占 | 通过 | 自动化测试覆盖 |
| app_data/logs/local_launcher.log 正常生成 | 通过 | 自动化测试覆盖 |

## 五、业务冒烟检查

| 流程 | 结果 | 备注 |
|---|---|---|
| 新建项目 | 通过 | 自动化覆盖 |
| PDF 上传 | 通过 | 自动化覆盖 |
| PDF 拆页 | 通过 | 自动化覆盖 |
| DXF 上传 | 通过 | 自动化覆盖 |
| DXF 解析 | 通过 | 自动化覆盖 |
| DXF 候选值 | 通过 | 自动化覆盖 |
| DXF 字段融合 | 通过 | 自动化覆盖 |
| DWG 上传 | 通过 | 自动化覆盖 |
| DWG 转 DXF，若配置工具 | 通过 | mock/集成测试覆盖；真实工具需现场验证 |
| CAD pipeline | 通过 | 自动化覆盖 |
| 校核工作台 | 通过 | 自动化覆盖 |
| Excel 导出 | 通过 | 自动化覆盖 |

## 六、结论

- 是否可作为 v0.4.5 portable stable 发布：是。
- 必须修复问题：暂无。
- 可延后问题：真实干净机首次依赖安装、真实 DWG 外部转换工具兼容性样本继续收集。
