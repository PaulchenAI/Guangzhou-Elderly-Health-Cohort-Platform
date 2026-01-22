## 1. 规范与接口

- [x] 1.1 定义 `oracle-db-export` 的需求与场景（全量/增量、输出结构、checkpoint、错误处理）
- [x] 1.2 明确 CLI 入口与参数清单（最小集合：连接信息、schema、表选择、模式、输出目录、checkpoint）

## 2. 实现（apply 阶段）

- [x] 2.1 在 `tools/oracle_db_exporter.py` 实现 `OracleDBExporter` 工具类（连接、查询、导出编排）
- [x] 2.1.1 实现配置加载：从项目根目录 `.env` 读取 Oracle 连接参数（支持命令行覆盖）
- [x] 2.1.2 实现增量列 JSON 配置解析：支持 `default_incremental_column` 与按表配置
- [x] 2.2 实现 DDL 导出（按表输出 `CREATE TABLE`，并支持导出注释）
- [x] 2.3 实现 DML 导出（按表输出 `INSERT`，支持批量写入与大表分页）
- [x] 2.4 实现全量导出模式（覆盖/跳过策略、manifest 统计）
- [x] 2.5 实现增量导出模式（读取/写入 checkpoint、按增量列过滤、更新水位线）
- [x] 2.6 增加最小验证脚本/示例（dry-run 或仅导出 1 张小表），并在 README/使用指南中给出命令示例

## 3. 验证

- [x] 3.1 增加基本自检：输出目录结构、manifest.json 格式、checkpoint 更新行为（通过 `--dry-run` 支持）
- [ ] 3.2 以一张示例表验证：全量导出后增量导出不重复导出旧数据（基于增量列）—— 需用户在有 Oracle 环境时验证

## 依赖关系

```
1.1/1.2 -> 2.*
2.* -> 3.*
```

