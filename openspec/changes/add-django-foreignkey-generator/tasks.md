## 1. 实施

- [ ] 1.1 创建 `generate_django_foreignkey_metadata.py` management command
- [ ] 1.2 实现 Django 模型扫描逻辑（遍历所有已注册模型）
- [ ] 1.3 实现 ForeignKey 关系提取（包括自引用外键）
- [ ] 1.4 实现 ManyToManyField 关系提取（包括中间表）
- [ ] 1.5 实现数据导入逻辑（插入到 `table_foreignkey_metadata` 表）
- [ ] 1.6 实现命令行参数（--dry-run, --truncate, --app-labels, --exclude-apps, --verbose）
- [ ] 1.7 添加导入报告输出（统计信息、错误列表）

## 2. 验证

- [ ] 2.1 测试 --dry-run 模式
- [ ] 2.2 测试实际导入功能
- [ ] 2.3 验证通过 foreignkey API 可以查询到 Django 模型的外键关系
