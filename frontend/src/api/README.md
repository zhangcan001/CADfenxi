# API 客户端

## 文件说明

- `client.ts` — 统一的 `fetch` 包装,所有请求都带 60 秒默认超时(可在调用方覆盖),错误统一返回 `ApiError`
- `errors.ts` — `ApiError` 类 + `readApiError` 解析 FastAPI 错误响应
- `*.ts`(projects、imports、cad、cadConverter、cadPipeline、candidates、fusion、issues、recognition、review、sheets、titleCrops) — 业务接口
- `openapi.gen.ts` — **自动生成**,不要手动编辑

## 同步后端 schema

后端 Pydantic 模型改了之后,跑:

```sh
npm run openapi:dump   # 把 FastAPI 的 /openapi.json 写到 src/api/openapi-schema.json(不提交)
npm run openapi:types  # 生成 openapi.gen.ts(提交)
```

新业务接口可以直接 `import type { components } from "./openapi.gen"` 取 `components["schemas"]["XxxRead"]` 代替手写 `type`。

## 超时约定

`client.ts` 默认 60 秒;以下场景已显式覆盖:

- 上传、Excel 导出、长批处理:5 分钟
- DWG/DXF 转换、解析、候选值、融合、OCR、文本抽取:5 分钟
- `runCadPipeline`(整批走完所有步骤):30 分钟

需要更长时间的接口在调用处加 `{ timeoutMs: ... }` 即可。
