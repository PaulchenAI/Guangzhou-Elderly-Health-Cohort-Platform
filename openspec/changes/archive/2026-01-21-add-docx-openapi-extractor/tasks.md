## 1. 提案（本 PR）

- [x] 1.1 创建 `proposal.md`，明确范围：输入 `.docx` → 输出 OpenAPI 3.x JSON（覆盖 A+B+C）
- [x] 1.2 创建 `specs/api-doc-extractor/spec.md` 规范增量（新增需求 + 场景齐全）
- [x] 1.3 需要时创建 `design.md`，记录解析策略与关键权衡（确定性解析 vs LLM 辅助、表格解析、示例映射）
- [x] 1.4 运行 `openspec-cn validate add-docx-openapi-extractor --strict` 并修复所有校验问题

## 2. 实施（批准后）

- [x] 2.1 在 `AIagent` 内新增 DOCX 文本/表格抽取模块（优先本地解析；不依赖外部服务）
- [x] 2.2 新增结构化中间模型（Endpoint/Schema/Example），并实现到 OpenAPI 3.x 的映射
- [x] 2.3 增加 LLM 辅助解析（可选、可配置、默认尽量少用）：用于处理非标准段落/表格或字段缺失补全建议
- [x] 2.4 增加 OpenAPI 输出校验与错误报告（定位到接口、字段、来源片段）
- [x] 2.5 提供 CLI：从 docx 生成 `openapi.json`，支持输出目录、覆盖/增量、只解析某接口等参数
- [x] 2.6 为示例文档添加可复现演示（固定输入路径 + 固定输出路径），并写清楚使用步骤
- [x] 2.7 添加单元测试与最小集成测试（至少覆盖：接口识别、入参/出参表解析、示例解析、OpenAPI 校验失败路径）

