# ZQ-Platform 前端页面开发规范

## 目录

- [1. 项目概述](#1-项目概述)
- [2. 技术栈](#2-技术栈)
- [3. 项目结构](#3-项目结构)
- [4. 开发规范](#4-开发规范)
- [5. 页面开发](#5-页面开发)
- [6. 组件开发](#6-组件开发)
- [7. API 调用](#7-api-调用)
- [8. 表单开发](#8-表单开发)
- [9. 表格开发](#9-表格开发)
- [10. 国际化](#10-国际化)
- [11. 路由配置](#11-路由配置)
- [12. 状态管理](#12-状态管理)
- [13. 样式规范](#13-样式规范)
- [14. 代码质量](#14-代码质量)

---

## 1. 项目概述

ZQ-Platform 前端项目基于 [Vben Admin](https://vben.pro) 框架开发，采用 Monorepo 架构，使用 pnpm workspace 进行包管理。

### 1.1 环境要求

- **Node.js**: >= 20.10.0
- **pnpm**: >= 9.12.0
- **包管理器**: 仅使用 pnpm（项目配置了 `preinstall` 钩子限制）

### 1.2 常用命令

```bash
# 安装依赖
pnpm install

# 开发模式
pnpm dev

# 构建生产版本
pnpm build

# 代码格式化
pnpm format

# 代码检查
pnpm lint

# 类型检查
pnpm check:type

# 单元测试
pnpm test:unit
```

---

## 2. 技术栈

| 技术 | 版本 | 说明 |
|------|------|------|
| Vue | 3.x | 响应式框架 |
| TypeScript | 5.x | 类型系统 |
| Element Plus | - | UI 组件库 |
| Vite | - | 构建工具 |
| Pinia | - | 状态管理 |
| Vue Router | - | 路由管理 |
| VxeTable | - | 高性能表格 |
| TailwindCSS | - | 原子化 CSS |
| Zod | - | 表单验证 |

---

## 3. 项目结构

### 3.1 整体结构

```
web/
├── apps/                    # 应用程序目录
│   └── web-ele/            # Element Plus 版本应用
├── packages/               # 共享包目录
│   ├── @core/             # 核心功能包
│   ├── constants/         # 常量定义
│   ├── effects/           # 副作用处理
│   ├── icons/             # 图标库
│   ├── locales/           # 国际化
│   ├── preferences/       # 偏好设置
│   ├── stores/            # 状态存储
│   ├── styles/            # 样式文件
│   ├── types/             # 类型定义
│   └── utils/             # 工具函数
├── internal/              # 内部配置
│   ├── lint-configs/      # 代码检查配置
│   ├── tailwind-config/   # TailwindCSS 配置
│   ├── tsconfig/          # TypeScript 配置
│   └── vite-config/       # Vite 配置
└── scripts/               # 脚本文件
```

### 3.2 应用目录结构 (apps/web-ele/src)

```
src/
├── adapter/               # 适配器层
│   ├── component/        # 组件适配器
│   ├── form.ts          # 表单适配器
│   └── vxe-table.ts     # 表格适配器
├── api/                  # API 接口
│   ├── core/            # 核心业务 API
│   ├── index.ts         # API 导出
│   └── request.ts       # 请求客户端配置
├── components/           # 业务组件
│   ├── zq-form/         # 表单组件
│   └── user-avatar/     # 用户头像组件
├── layouts/             # 布局组件
├── locales/             # 国际化资源
│   └── langs/           # 语言包
├── router/              # 路由配置
│   ├── routes/          # 路由模块
│   ├── guard.ts         # 路由守卫
│   └── index.ts         # 路由入口
├── store/               # 状态管理
├── utils/               # 工具函数
├── views/               # 页面视图
│   ├── _core/           # 核心系统页面
│   ├── dashboard/       # 仪表盘页面
│   └── demos/           # 演示页面
├── app.vue              # 根组件
├── bootstrap.ts         # 应用启动
├── main.ts             # 入口文件
└── preferences.ts       # 偏好设置覆盖
```

---

## 4. 开发规范

### 4.1 文件命名规范

| 类型 | 命名规则 | 示例 |
|------|----------|------|
| Vue 组件文件 | kebab-case | `user-avatar.vue` |
| TypeScript 文件 | kebab-case | `request.ts` |
| 目录名 | kebab-case | `user-avatar/` |
| 组件目录入口 | `index.vue` 或 `index.ts` | - |
| 类型定义 | PascalCase | `UserInfo` |
| 常量 | UPPER_SNAKE_CASE | `LOGIN_PATH` |
| 函数/变量 | camelCase | `getUserInfo` |

### 4.2 Vue 组件规范

```vue
<script lang="ts" setup>
// 1. 类型导入
import type { User } from '#/api/core';

// 2. 依赖导入（按顺序：Vue -> Vben -> 第三方 -> 项目内部）
import { computed, ref } from 'vue';

import { Page, useVbenDrawer } from '@vben/common-ui';
import { $t } from '@vben/locales';

import { ElButton, ElMessage } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { getUserListApi } from '#/api/core';

// 3. 组件选项定义
defineOptions({ name: 'SystemUser' });

// 4. Props 定义
const props = withDefaults(defineProps<Props>(), {
  size: 56,
});

// 5. Emits 定义
const emit = defineEmits<{
  success: [];
}>();

// 6. 响应式数据
const loading = ref(false);

// 7. 计算属性
const computedValue = computed(() => {
  // ...
});

// 8. 方法定义
function handleClick() {
  // ...
}
</script>

<template>
  <!-- 模板内容 -->
</template>

<style lang="scss" scoped>
/* 样式内容 */
</style>
```

### 4.3 TypeScript 规范

- **始终使用类型注解**：明确函数参数和返回值类型
- **优先使用 `interface`**：定义对象类型时优先使用 `interface`
- **使用 `type` 导入**：类型导入使用 `import type`
- **避免使用 `any`**：尽量使用具体类型或 `unknown`

```typescript
// 类型定义示例
export interface User {
  id: string;
  username: string;
  email?: string;
  name?: string;
  gender?: number;
  user_status?: number;
}

// 函数类型注解
export async function getUserListApi(params?: UserListParams): Promise<PaginatedResponse<User>> {
  return requestClient.get<PaginatedResponse<User>>('/api/core/user', { params });
}
```

---

## 5. 页面开发

### 5.1 标准页面结构

页面通常由以下部分组成：

```
views/
└── module-name/           # 模块目录
    ├── index.vue         # 主页面
    ├── data.ts           # 数据配置（表单/表格schema）
    └── modules/          # 子模块
        └── form.vue      # 表单弹窗/抽屉
```

### 5.2 页面模板示例

```vue
<script lang="ts" setup>
import type { OnActionClickParams, VxeTableGridOptions } from '#/adapter/vxe-table';
import type { User } from '#/api/core';

import { ref } from 'vue';

import { Page, useVbenDrawer } from '@vben/common-ui';
import { Plus } from '@vben/icons';
import { $t } from '@vben/locales';

import { ElButton, ElMessage, ElMessageBox } from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import { deleteUserApi, getUserListApi } from '#/api/core';

import { useColumns, useSearchFormSchema } from './data';
import Form from './modules/form.vue';

// 组件名称定义
defineOptions({ name: 'SystemUser' });

// 抽屉组件
const [FormDrawer, formDrawerApi] = useVbenDrawer({
  connectedComponent: Form,
  destroyOnClose: true,
});

// 创建操作
function onCreate() {
  formDrawerApi.setData({}).open();
}

// 编辑操作
function onEdit(row: User) {
  formDrawerApi.setData(row).open();
}

// 删除操作
function onDelete(row: User) {
  ElMessageBox.confirm(
    $t('ui.actionMessage.deleteConfirm', [row.name]),
    $t('common.delete'),
    {
      confirmButtonText: $t('common.confirm'),
      cancelButtonText: $t('common.cancel'),
      type: 'warning',
    },
  ).then(async () => {
    await deleteUserApi(row.id);
    ElMessage.success($t('ui.actionMessage.deleteSuccess', [row.name]));
    refreshGrid();
  });
}

// 操作按钮回调
function onActionClick({ code, row }: OnActionClickParams<User>) {
  switch (code) {
    case 'delete': {
      onDelete(row);
      break;
    }
    case 'edit': {
      onEdit(row);
      break;
    }
  }
}

// 表格配置
const [Grid, gridApi] = useVbenVxeGrid({
  formOptions: {
    schema: useSearchFormSchema(),
    submitOnChange: true,
  },
  gridOptions: {
    columns: useColumns(onActionClick),
    height: 'auto',
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          const params = {
            page: page.currentPage,
            pageSize: page.pageSize,
            ...formValues,
          };
          return await getUserListApi(params);
        },
      },
    },
    toolbarConfig: {
      custom: true,
      refresh: { code: 'query' },
      search: true,
      zoom: true,
    },
  } as VxeTableGridOptions<User>,
});

// 刷新表格
function refreshGrid() {
  gridApi.query();
}
</script>

<template>
  <Page auto-content-height>
    <FormDrawer @success="refreshGrid" />

    <Grid>
      <template #table-title>
        <ElButton type="primary" @click="onCreate">
          <Plus class="size-5" />
          {{ $t('ui.actionTitle.create', [$t('user.name')]) }}
        </ElButton>
      </template>
    </Grid>
  </Page>
</template>
```

---

## 6. 组件开发

### 6.1 组件分类

| 类型 | 位置 | 说明 |
|------|------|------|
| 通用组件 | `packages/@core/` | 跨应用共享的基础组件 |
| 业务组件 | `apps/web-ele/src/components/` | 特定业务的可复用组件 |
| 页面组件 | `views/*/modules/` | 页面专用的子组件 |

### 6.2 组件开发规范

```vue
<script lang="ts" setup>
// 1. 定义组件名称
defineOptions({
  name: 'UserAvatar',
});

// 2. 定义 Props 接口
interface Props {
  /**
   * 用户对象
   */
  user?: User;
  /**
   * 头像尺寸（像素）
   * @default 56
   */
  size?: number;
  /**
   * 是否显示阴影
   * @default true
   */
  shadow?: boolean;
}

// 3. 使用 withDefaults 设置默认值
const props = withDefaults(defineProps<Props>(), {
  size: 56,
  shadow: true,
});

// 4. 定义 Emits
const emit = defineEmits<{
  click: [user: User];
}>();

// 5. 计算属性和方法
const avatarUrl = computed(() => {
  return props.user?.avatar
    ? getFileStreamUrl(props.user.avatar)
    : undefined;
});
</script>

<template>
  <div class="user-avatar">
    <!-- 组件内容 -->
  </div>
</template>

<style lang="scss" scoped>
.user-avatar {
  // 样式
}
</style>
```

### 6.3 组件导出

在组件目录下创建 `index.ts` 导出组件：

```typescript
// components/user-avatar/index.ts
export { default as UserAvatar } from './index.vue';
```

---

## 7. API 调用

### 7.1 API 文件结构

```
api/
├── core/               # 业务 API 目录
│   ├── auth.ts        # 认证相关
│   ├── user.ts        # 用户管理
│   ├── role.ts        # 角色管理
│   └── index.ts       # 统一导出
├── request.ts         # 请求客户端配置
└── index.ts           # 总导出
```

### 7.2 API 定义规范

```typescript
// api/core/user.ts
import type { UserInfo } from '@vben/types';
import { requestClient } from '#/api/request';

/**
 * 用户相关类型定义
 */
export interface User {
  id: string;
  username: string;
  email?: string;
  name?: string;
}

export interface UserCreateInput {
  username: string;
  email?: string;
  name?: string;
}

export interface UserListParams {
  page?: number;
  pageSize?: number;
  name?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

/**
 * 获取用户信息
 */
export async function getUserInfoApi() {
  return requestClient.get<UserInfo>('/api/core/userinfo');
}

/**
 * 创建用户
 */
export async function createUserApi(data: UserCreateInput) {
  return requestClient.post<User>('/api/core/user', data);
}

/**
 * 获取用户列表（分页）
 */
export async function getUserListApi(params?: UserListParams) {
  return requestClient.get<PaginatedResponse<User>>('/api/core/user', {
    params,
  });
}

/**
 * 获取用户详情
 */
export async function getUserDetailApi(userId: string) {
  return requestClient.get<User>(`/api/core/user/${userId}`);
}

/**
 * 更新用户
 */
export async function updateUserApi(userId: string, data: Partial<User>) {
  return requestClient.put<User>(`/api/core/user/${userId}`, data);
}

/**
 * 删除用户
 */
export async function deleteUserApi(userId: string) {
  return requestClient.delete<User>(`/api/core/user/${userId}`);
}
```

### 7.3 API 命名规范

| 操作 | 前缀 | 示例 |
|------|------|------|
| 获取单个 | `get` | `getUserDetailApi` |
| 获取列表 | `get...List` | `getUserListApi` |
| 创建 | `create` | `createUserApi` |
| 更新 | `update` | `updateUserApi` |
| 删除 | `delete` | `deleteUserApi` |
| 批量删除 | `batchDelete` | `batchDeleteUserApi` |

### 7.4 请求客户端配置

项目使用封装好的 `RequestClient`，已配置：
- Token 自动注入
- Token 刷新机制
- 统一错误处理
- 响应数据格式化

```typescript
// api/request.ts
import { RequestClient } from '@vben/request';

const client = new RequestClient({
  baseURL: apiURL,
});

// 请求拦截器
client.addRequestInterceptor({
  fulfilled: async (config) => {
    const accessStore = useAccessStore();
    config.headers.Authorization = formatToken(accessStore.accessToken);
    config.headers['Accept-Language'] = preferences.app.locale;
    return config;
  },
});

// 响应拦截器
client.addResponseInterceptor(
  defaultResponseInterceptor({
    codeField: 'code',
    dataField: 'data',
    successCode: 0,
  }),
);
```

---

## 8. 表单开发

### 8.1 表单 Schema 定义

使用 `VbenFormSchema` 定义表单字段：

```typescript
// data.ts
import type { VbenFormSchema } from '#/adapter/form';
import { z } from '#/adapter/form';
import { $t } from '@vben/locales';

/**
 * 获取表单字段配置
 */
export function getFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'username',
      label: $t('user.account'),
      rules: z
        .string()
        .min(3, $t('ui.formRules.minLength', [$t('user.account'), 3]))
        .max(150, $t('ui.formRules.maxLength', [$t('user.account'), 150])),
    },
    {
      component: 'Input',
      fieldName: 'email',
      label: $t('user.email'),
      rules: z
        .string()
        .email($t('user.emailFormatError'))
        .optional()
        .or(z.literal('')),
    },
    {
      component: 'RadioGroup',
      componentProps: {
        buttonStyle: 'solid',
        options: [
          { label: $t('user.unknown'), value: 0 },
          { label: $t('user.male'), value: 1 },
          { label: $t('user.female'), value: 2 },
        ],
        isButton: true,
      },
      defaultValue: 0,
      fieldName: 'gender',
      label: $t('user.gender'),
    },
    {
      component: 'Select',
      componentProps: {
        placeholder: $t('user.selectStatus'),
        options: getStatusOptions(),
        clearable: true,
      },
      fieldName: 'user_status',
      label: $t('user.status'),
    },
    {
      component: 'DatePicker',
      componentProps: {
        placeholder: $t('user.selectBirthday'),
        valueFormat: 'YYYY-MM-DD',
      },
      fieldName: 'birthday',
      label: $t('user.birthday'),
    },
  ];
}
```

### 8.2 可用表单组件

| 组件名 | 说明 | 示例 Props |
|--------|------|------------|
| `Input` | 输入框 | `placeholder` |
| `InputNumber` | 数字输入框 | `min`, `max` |
| `Select` | 选择器 | `options`, `multiple` |
| `RadioGroup` | 单选组 | `options`, `isButton` |
| `CheckboxGroup` | 复选组 | `options` |
| `DatePicker` | 日期选择 | `valueFormat`, `type` |
| `TimePicker` | 时间选择 | `isRange` |
| `Switch` | 开关 | - |
| `Textarea` | 文本域 | `rows` |
| `TreeSelect` | 树形选择 | `data` |
| `ApiSelect` | 远程选择器 | `api`, `params` |
| `ApiTreeSelect` | 远程树形选择 | `api` |
| `DeptSelector` | 部门选择器 | `placeholder` |
| `UserSelector` | 用户选择器 | `multiple` |
| `RoleSelector` | 角色选择器 | `multiple` |
| `PostSelector` | 岗位选择器 | `multiple` |
| `ImageSelector` | 图片选择器 | `enableCrop`, `maxSize` |
| `FileSelector` | 文件选择器 | - |
| `JsonEditor` | JSON编辑器 | - |
| `IconPicker` | 图标选择器 | - |

### 8.3 表单使用

```vue
<script lang="ts" setup>
import { useVbenForm } from '#/adapter/form';
import { getFormSchema } from './data';

const [Form, formApi] = useVbenForm({
  commonConfig: {
    colon: true,
    componentProps: {
      class: 'w-full',
    },
  },
  schema: getFormSchema(),
  showDefaultActions: false,
  wrapperClass: 'grid-cols-1 gap-x-4',
});

// 表单操作
async function onSubmit() {
  const { valid } = await formApi.validate();
  if (valid) {
    const data = await formApi.getValues();
    // 提交数据
  }
}

// 设置表单值
formApi.setValues({ username: 'test' });

// 重置表单
formApi.resetForm();
</script>

<template>
  <Form class="mx-4" />
</template>
```

### 8.4 验证规则 (Zod)

```typescript
import { z } from '#/adapter/form';

// 必填字符串
z.string().min(1, '此字段必填')

// 长度限制
z.string()
  .min(3, '最少3个字符')
  .max(150, '最多150个字符')

// 邮箱验证
z.string().email('请输入有效的邮箱')

// 可选字段
z.string().optional().or(z.literal(''))

// 正则验证
z.string().regex(/^1[3-9]\d{9}$/, '请输入有效的手机号')

// 数字范围
z.number().min(0).max(100)
```

---

## 9. 表格开发

### 9.1 表格列配置

```typescript
// data.ts
import type { OnActionClickFn, VxeTableGridOptions } from '#/adapter/vxe-table';
import { $t } from '@vben/locales';

export function useColumns(
  onActionClick?: OnActionClickFn<User>,
): VxeTableGridOptions<User>['columns'] {
  return [
    // 复选框列
    {
      type: 'checkbox',
      minWidth: 60,
      align: 'center',
      fixed: 'left',
    },
    // 普通列
    {
      field: 'username',
      title: $t('user.account'),
      minWidth: 120,
    },
    // 带插槽的列
    {
      field: 'avatar',
      title: $t('user.avatar'),
      minWidth: 80,
      align: 'center',
      slots: {
        default: 'avatar',
      },
    },
    // 标签列（使用渲染器）
    {
      field: 'user_status',
      title: $t('user.status'),
      minWidth: 100,
      cellRender: {
        name: 'CellTag',
        options: [
          { type: 'danger', label: '禁用', value: 0 },
          { type: 'success', label: '启用', value: 1 },
        ],
      },
    },
    // 操作列
    {
      align: 'right',
      cellRender: {
        attrs: {
          nameField: 'name',
          nameTitle: $t('user.userName'),
          onClick: onActionClick,
        },
        name: 'CellOperation',
        options: [
          'edit',  // 预设编辑按钮
          {
            code: 'reset-password',
            text: $t('user.resetPassword'),
            icon: 'ep:refresh',
          },
          {
            code: 'delete',
            disabled: (row: User) => row.id === 'admin-id',
          },
        ],
      },
      field: 'operation',
      fixed: 'right',
      title: $t('user.operation'),
      minWidth: 200,
    },
  ];
}
```

### 9.2 搜索表单配置

```typescript
export function useSearchFormSchema(): VbenFormSchema[] {
  return [
    {
      component: 'Input',
      fieldName: 'name',
      label: $t('user.userName'),
    },
    {
      component: 'Select',
      fieldName: 'user_status',
      label: $t('user.status'),
      componentProps: {
        options: getStatusOptions(),
        clearable: true,
      },
    },
  ];
}
```

### 9.3 表格使用

```vue
<script lang="ts" setup>
import { useVbenVxeGrid } from '#/adapter/vxe-table';

const [Grid, gridApi] = useVbenVxeGrid({
  // 搜索表单
  formOptions: {
    schema: useSearchFormSchema(),
    submitOnChange: true,  // 表单变化自动提交
  },
  // 表格事件
  gridEvents: {
    checkboxChange: ({ records }) => {
      selectedRows.value = records;
    },
  },
  // 表格配置
  gridOptions: {
    columns: useColumns(onActionClick),
    height: 'auto',
    keepSource: true,
    // 代理配置
    proxyConfig: {
      ajax: {
        query: async ({ page }, formValues) => {
          return await getUserListApi({
            page: page.currentPage,
            pageSize: page.pageSize,
            ...formValues,
          });
        },
      },
    },
    // 复选框配置
    checkboxConfig: {
      reserve: true,
      trigger: 'default',
    },
    // 工具栏配置
    toolbarConfig: {
      custom: true,
      refresh: { code: 'query' },
      search: true,
      zoom: true,
    },
  },
});

// 刷新表格
gridApi.query();
</script>

<template>
  <Grid>
    <!-- 自定义工具栏按钮 -->
    <template #table-title>
      <ElButton type="primary" @click="onCreate">
        <Plus class="size-5" />
        新增
      </ElButton>
    </template>

    <!-- 自定义单元格 -->
    <template #avatar="{ row }">
      <UserAvatar :user="row" :size="34" />
    </template>
  </Grid>
</template>
```

### 9.4 单元格渲染器

| 渲染器 | 说明 | 配置示例 |
|--------|------|----------|
| `CellTag` | 标签渲染 | `options: [{ type: 'success', label: '启用', value: 1 }]` |
| `CellImage` | 图片渲染 | 自动预览 |
| `CellLink` | 链接渲染 | `props: { text: '查看' }` |
| `CellOperation` | 操作按钮 | `options: ['edit', 'delete']` |

---

## 10. 国际化

### 10.1 语言文件结构

```
locales/
└── langs/
    ├── zh-CN/          # 中文
    │   ├── common.json
    │   ├── user.json
    │   └── ...
    ├── en-US/          # 英文
    └── zh-TW/          # 繁体中文
```

### 10.2 语言文件格式

```json
// locales/langs/zh-CN/user.json
{
  "name": "用户",
  "title": "用户管理",
  "userName": "用户名称",
  "account": "登录账号",
  "email": "邮箱",
  "emailFormatError": "请输入有效的邮箱地址",
  "status": "状态",
  "selectUsersToDelete": "请选择要删除的用户",
  "deleteSuccess": "成功删除 {0} 个用户",
  "resetPasswordConfirm": "确定要重置用户{0}的密码吗？"
}
```

### 10.3 使用国际化

```typescript
import { $t } from '@vben/locales';

// 基本使用
$t('user.title')  // 用户管理

// 带参数
$t('user.deleteSuccess', [5])  // 成功删除 5 个用户
$t('ui.formRules.minLength', ['用户名', 3])  // 用户名最少3个字符

// 带命名参数
$t('user.resetPasswordConfirm', ['张三'])  // 确定要重置用户张三的密码吗？
```

### 10.4 公共语言键

```typescript
// 常用公共键
$t('common.confirm')     // 确认
$t('common.cancel')      // 取消
$t('common.delete')      // 删除
$t('common.edit')        // 编辑
$t('common.enabled')     // 启用
$t('common.disabled')    // 禁用

// UI 操作标题
$t('ui.actionTitle.create', ['用户'])  // 新增用户
$t('ui.actionTitle.edit', ['用户'])    // 编辑用户
$t('ui.actionTitle.delete', ['用户'])  // 删除用户

// 操作消息
$t('ui.actionMessage.deleteConfirm', ['张三'])  // 确定删除张三吗？
$t('ui.actionMessage.deleteSuccess', ['张三'])  // 张三删除成功

// 表单规则
$t('ui.formRules.required', ['用户名'])  // 用户名不能为空
$t('ui.formRules.minLength', ['用户名', 3])  // 用户名最少3个字符
```

---

## 11. 路由配置

### 11.1 路由文件结构

```
router/
├── routes/
│   ├── modules/         # 动态路由模块
│   │   ├── dashboard.ts
│   │   └── system.ts
│   ├── core.ts         # 核心路由
│   └── index.ts        # 路由聚合
├── guard.ts            # 路由守卫
└── index.ts            # 路由入口
```

### 11.2 动态路由定义

```typescript
// router/routes/modules/system.ts
import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    meta: {
      icon: 'ep:setting',
      order: 1,
      title: '系统管理',
    },
    name: 'System',
    path: '/system',
    children: [
      {
        meta: {
          affixTab: false,
          icon: 'ep:user',
          title: '用户管理',
        },
        name: 'SystemUser',
        path: '/system/user',
        component: () => import('#/views/_core/user/index.vue'),
      },
      {
        meta: {
          icon: 'ep:lock',
          title: '角色管理',
        },
        name: 'SystemRole',
        path: '/system/role',
        component: () => import('#/views/_core/role/index.vue'),
      },
    ],
  },
];

export default routes;
```

### 11.3 路由 Meta 配置

```typescript
interface RouteMeta {
  // 标题
  title: string;
  // 图标
  icon?: string;
  // 排序
  order?: number;
  // 是否固定标签页
  affixTab?: boolean;
  // 是否隐藏菜单
  hideInMenu?: boolean;
  // 是否隐藏标签页
  hideInTab?: boolean;
  // 是否隐藏面包屑
  hideInBreadcrumb?: boolean;
  // 权限码
  authority?: string[];
  // 徽标数量
  badge?: number;
  // 徽标类型
  badgeType?: 'dot' | 'normal';
}
```

---

## 12. 状态管理

### 12.1 创建 Store

```typescript
// store/auth.ts
import { ref } from 'vue';
import { useRouter } from 'vue-router';

import { defineStore } from 'pinia';

import { loginApi, logoutApi } from '#/api';

export const useAuthStore = defineStore('auth', () => {
  const router = useRouter();
  const loginLoading = ref(false);

  /**
   * 登录
   */
  async function authLogin(params: LoginParams) {
    try {
      loginLoading.value = true;
      const response = await loginApi(params);
      // 处理登录逻辑
    } finally {
      loginLoading.value = false;
    }
  }

  /**
   * 登出
   */
  async function logout() {
    await logoutApi();
    // 处理登出逻辑
  }

  // 重置函数
  function $reset() {
    loginLoading.value = false;
  }

  return {
    $reset,
    authLogin,
    loginLoading,
    logout,
  };
});
```

### 12.2 使用 Store

```typescript
import { useAuthStore } from '#/store';

const authStore = useAuthStore();

// 访问状态
console.log(authStore.loginLoading);

// 调用方法
await authStore.authLogin({ username: 'admin', password: '123456' });
```

---

## 13. 样式规范

### 13.1 TailwindCSS 使用

项目使用 TailwindCSS 进行样式开发，推荐优先使用 Tailwind 类名：

```vue
<template>
  <div class="flex items-center justify-between p-4">
    <span class="text-lg font-bold text-gray-800">标题</span>
    <button class="rounded bg-blue-500 px-4 py-2 text-white hover:bg-blue-600">
      按钮
    </button>
  </div>
</template>
```

### 13.2 SCSS 使用

对于复杂样式，使用 scoped SCSS：

```vue
<style lang="scss" scoped>
.component-name {
  // 使用 CSS 变量
  color: hsl(var(--foreground));
  background: hsl(var(--background));
  border: 1px solid hsl(var(--border));

  // 嵌套样式
  .title {
    font-size: 16px;
    font-weight: 600;
  }

  // 深度选择器（修改子组件样式）
  :deep(.el-button) {
    margin-left: 8px;
  }
}
</style>
```

### 13.3 CSS 变量

项目定义了统一的 CSS 变量，应优先使用：

```scss
// 颜色
hsl(var(--foreground))      // 前景色
hsl(var(--background))      // 背景色
hsl(var(--muted-foreground)) // 次要文字色
hsl(var(--border))          // 边框色
hsl(var(--primary))         // 主题色

// 使用示例
.my-element {
  color: hsl(var(--foreground));
  background: hsl(var(--background));
  border: 1px solid hsl(var(--border));
}
```

---

## 14. 代码质量

### 14.1 ESLint 规则

项目使用 `@vben/eslint-config` 统一代码风格，主要规则包括：

- 使用 TypeScript 严格模式
- Vue 3 Composition API 规范
- 导入语句排序
- 禁止未使用变量
- 强制使用分号

### 14.2 Stylelint 规则

使用 `@vben/stylelint-config` 进行样式检查：

- CSS 属性排序
- 禁止未知属性
- 颜色格式规范

### 14.3 Prettier 格式化

项目使用 Prettier 进行代码格式化，配置：

- 单引号
- 尾随逗号
- 2 空格缩进

### 14.4 Git 提交规范

使用 Commitlint 规范提交信息格式：

```bash
# 格式
<type>(<scope>): <subject>

# 类型
feat:     新功能
fix:      Bug 修复
docs:     文档更新
style:    代码格式（不影响代码运行）
refactor: 重构
perf:     性能优化
test:     测试
chore:    构建/工具变动

# 示例
feat(user): 添加用户批量删除功能
fix(form): 修复表单验证错误
docs: 更新 README
```

### 14.5 Pre-commit 检查

项目配置了 Lefthook 进行提交前检查：

- Vue 文件：Prettier + ESLint + Stylelint
- JS/TS 文件：Prettier + ESLint
- 样式文件：Prettier + Stylelint
- JSON 文件：Prettier
- Markdown 文件：Prettier

---

## 附录

### A. 常用图标

项目使用 Iconify 图标库，Element Plus 图标前缀为 `ep:`：

```vue
<template>
  <!-- 使用图标组件 -->
  <IconifyIcon icon="ep:user" />
  <IconifyIcon icon="ep:edit" />
  <IconifyIcon icon="ep:delete" />
  <IconifyIcon icon="ep:setting" />
</template>
```

### B. 常用工具函数

```typescript
// 从 @vben/utils 导入
import { openWindow, resetStaticRoutes, traverseTreeValues } from '@vben/utils';

// 打开新窗口
openWindow('https://example.com');

// 遍历树形数据
traverseTreeValues(routes, (route) => route.name);
```

### C. 相关文档

- [Vue 3 官方文档](https://vuejs.org/)
- [Element Plus 文档](https://element-plus.org/)
- [VxeTable 文档](https://vxetable.cn/)
- [TailwindCSS 文档](https://tailwindcss.com/)
- [Pinia 文档](https://pinia.vuejs.org/)
- [Vben Admin 文档](https://doc.vben.pro/)

