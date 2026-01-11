# 表查询配置示例

本文件提供了为已导入的医院数据表创建查询配置的示例。

## 配置文件格式

每个表的配置使用 JSON 格式，包含以下字段：

```json
{
  "table_name": "数据库表名",
  "display_name": "显示名称",
  "description": "表描述",
  "fields": [
    {
      "name": "字段名",
      "display_name": "显示名称",
      "type": "数据类型",
      "searchable": true/false,
      "sortable": true/false,
      "visible": true/false,
      "width": 可选列宽度
    }
  ],
  "default_page_size": 20,
  "max_page_size": 100,
  "default_order_by": "字段名 DESC/ASC",
  "allowed_operations": ["query", "export"]
}
```

## 字段类型说明

- `string`: 字符串类型
- `integer`: 整数类型
- `decimal`: 小数类型
- `date`: 日期类型
- `datetime`: 日期时间类型
- `boolean`: 布尔类型

## 示例 1：工作流请求表

```json
{
  "table_name": "WORKFLOW_REQUESTBASE",
  "display_name": "工作流请求",
  "description": "工作流系统请求基础数据表",
  "fields": [
    {
      "name": "REQUESTID",
      "display_name": "请求ID",
      "type": "integer",
      "searchable": true,
      "sortable": true,
      "visible": true,
      "width": 100
    },
    {
      "name": "REQUESTNAME",
      "display_name": "请求名称",
      "type": "string",
      "searchable": true,
      "sortable": true,
      "visible": true,
      "width": 200
    },
    {
      "name": "CREATER",
      "display_name": "创建人",
      "type": "string",
      "searchable": true,
      "sortable": false,
      "visible": true,
      "width": 100
    },
    {
      "name": "CREATEDATE",
      "display_name": "创建日期",
      "type": "datetime",
      "searchable": true,
      "sortable": true,
      "visible": true,
      "width": 150
    },
    {
      "name": "CURRENTNODEID",
      "display_name": "当前节点ID",
      "type": "integer",
      "searchable": true,
      "sortable": false,
      "visible": true,
      "width": 100
    },
    {
      "name": "STATUS",
      "display_name": "状态",
      "type": "string",
      "searchable": true,
      "sortable": true,
      "visible": true,
      "width": 100
    }
  ],
  "default_page_size": 20,
  "max_page_size": 100,
  "default_order_by": "REQUESTID DESC",
  "allowed_operations": ["query", "export"]
}
```

## 示例 2：部门表

```json
{
  "table_name": "BS_DEPARTMENT",
  "display_name": "部门信息",
  "description": "医院部门基础信息表",
  "fields": [
    {
      "name": "ID",
      "display_name": "部门ID",
      "type": "integer",
      "searchable": true,
      "sortable": true,
      "visible": true,
      "width": 100
    },
    {
      "name": "DEPARTMENTNAME",
      "display_name": "部门名称",
      "type": "string",
      "searchable": true,
      "sortable": true,
      "visible": true,
      "width": 200
    },
    {
      "name": "SUBCOMPANYID1",
      "display_name": "分部ID",
      "type": "integer",
      "searchable": true,
      "sortable": false,
      "visible": true,
      "width": 100
    },
    {
      "name": "DEPARTMENTMARK",
      "display_name": "部门编码",
      "type": "string",
      "searchable": true,
      "sortable": false,
      "visible": true,
      "width": 120
    },
    {
      "name": "CANCELED",
      "display_name": "是否停用",
      "type": "boolean",
      "searchable": true,
      "sortable": true,
      "visible": true,
      "width": 80
    }
  ],
  "default_page_size": 50,
  "max_page_size": 200,
  "default_order_by": "ID ASC",
  "allowed_operations": ["query", "export"]
}
```

## 示例 3：物资表

```json
{
  "table_name": "WM_MATERIAL",
  "display_name": "物资信息",
  "description": "仓库物资管理表",
  "fields": [
    {
      "name": "ID",
      "display_name": "物资ID",
      "type": "integer",
      "searchable": true,
      "sortable": true,
      "visible": true,
      "width": 100
    },
    {
      "name": "MATERIAL_NAME",
      "display_name": "物资名称",
      "type": "string",
      "searchable": true,
      "sortable": true,
      "visible": true,
      "width": 200
    },
    {
      "name": "SPECIFICATION",
      "display_name": "规格",
      "type": "string",
      "searchable": true,
      "sortable": false,
      "visible": true,
      "width": 150
    },
    {
      "name": "UNIT",
      "display_name": "单位",
      "type": "string",
      "searchable": false,
      "sortable": false,
      "visible": true,
      "width": 80
    },
    {
      "name": "PRICE",
      "display_name": "价格",
      "type": "decimal",
      "searchable": false,
      "sortable": true,
      "visible": true,
      "width": 100
    },
    {
      "name": "CATEGORY",
      "display_name": "分类",
      "type": "string",
      "searchable": true,
      "sortable": true,
      "visible": true,
      "width": 120
    }
  ],
  "default_page_size": 30,
  "max_page_size": 100,
  "default_order_by": "ID DESC",
  "allowed_operations": ["query", "export"]
}
```

## 示例 4：护理检查表

```json
{
  "table_name": "BSE_NURSE_INSPECTION",
  "display_name": "护理检查记录",
  "description": "护理质量检查记录表",
  "fields": [
    {
      "name": "ID",
      "display_name": "记录ID",
      "type": "integer",
      "searchable": true,
      "sortable": true,
      "visible": true,
      "width": 100
    },
    {
      "name": "INSPECTION_DATE",
      "display_name": "检查日期",
      "type": "date",
      "searchable": true,
      "sortable": true,
      "visible": true,
      "width": 120
    },
    {
      "name": "INSPECTOR",
      "display_name": "检查人",
      "type": "string",
      "searchable": true,
      "sortable": false,
      "visible": true,
      "width": 100
    },
    {
      "name": "DEPT_NAME",
      "display_name": "检查科室",
      "type": "string",
      "searchable": true,
      "sortable": true,
      "visible": true,
      "width": 150
    },
    {
      "name": "SCORE",
      "display_name": "检查分数",
      "type": "decimal",
      "searchable": false,
      "sortable": true,
      "visible": true,
      "width": 100
    },
    {
      "name": "RESULT",
      "display_name": "检查结果",
      "type": "string",
      "searchable": true,
      "sortable": false,
      "visible": true,
      "width": 200
    }
  ],
  "default_page_size": 20,
  "max_page_size": 100,
  "default_order_by": "INSPECTION_DATE DESC",
  "allowed_operations": ["query", "export"]
}
```

## 示例 5：用户表

```json
{
  "table_name": "YZJ_USER",
  "display_name": "用户信息",
  "description": "系统用户基础信息表",
  "fields": [
    {
      "name": "ID",
      "display_name": "用户ID",
      "type": "integer",
      "searchable": true,
      "sortable": true,
      "visible": true,
      "width": 100
    },
    {
      "name": "USERNAME",
      "display_name": "用户名",
      "type": "string",
      "searchable": true,
      "sortable": true,
      "visible": true,
      "width": 150
    },
    {
      "name": "REALNAME",
      "display_name": "真实姓名",
      "type": "string",
      "searchable": true,
      "sortable": true,
      "visible": true,
      "width": 120
    },
    {
      "name": "MOBILE",
      "display_name": "手机号",
      "type": "string",
      "searchable": true,
      "sortable": false,
      "visible": true,
      "width": 130
    },
    {
      "name": "EMAIL",
      "display_name": "邮箱",
      "type": "string",
      "searchable": true,
      "sortable": false,
      "visible": true,
      "width": 180
    },
    {
      "name": "DEPT_NAME",
      "display_name": "部门",
      "type": "string",
      "searchable": true,
      "sortable": true,
      "visible": true,
      "width": 150
    },
    {
      "name": "STATUS",
      "display_name": "状态",
      "type": "integer",
      "searchable": true,
      "sortable": true,
      "visible": true,
      "width": 80
    }
  ],
  "default_page_size": 20,
  "max_page_size": 100,
  "default_order_by": "ID ASC",
  "allowed_operations": ["query"]
}
```

## 批量配置导入格式

如果需要批量导入多个表配置，可以使用数组格式：

```json
{
  "configs": [
    {
      "table_name": "BS_DEPARTMENT",
      "display_name": "部门信息",
      ...
    },
    {
      "table_name": "WM_MATERIAL",
      "display_name": "物资信息",
      ...
    }
  ]
}
```

## 使用说明

1. **创建配置**：复制上述示例，根据实际表结构修改字段定义
2. **导入配置**：通过管理 API 或导入命令将配置导入系统
3. **初始化菜单**：执行 `python manage.py init_table_query_menus` 生成菜单
4. **验证功能**：在前端页面测试查询和导出功能

## 注意事项

- 字段名必须与数据库表中的实际字段名完全匹配（区分大小写）
- `searchable` 设置为 `true` 的字段将出现在查询表单中
- `sortable` 设置为 `true` 的字段支持排序功能
- `visible` 设置为 `false` 的字段不会在结果中显示
- `default_page_size` 建议根据表数据量设置，大表建议设置较小值
- `max_page_size` 用于限制单次查询的最大记录数，防止性能问题
- 敏感字段（如密码）不应添加到配置中，或设置 `visible: false`

