<script lang="ts" setup>
import type {
    DocEndpoint,
    DocEndpointSearchParams,
    DocSummary,
} from '#/api/core/doc-api';

import { onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { Search } from '@vben/icons';

import {
    ElButton,
    ElCard,
    ElEmpty,
    ElForm,
    ElFormItem,
    ElInput,
    ElMessage,
    ElOption,
    ElSelect,
    ElStatistic,
    ElTag,
} from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
    getDocEndpointsApi,
    getDocSummaryApi,
    searchDocEndpointsApi,
} from '#/api/core/doc-api';

import EndpointDetail from './components/EndpointDetail.vue';

defineOptions({ name: 'DocApi' });

// 文档摘要
const summary = ref<DocSummary | null>(null);
const loadingSummary = ref(false);

// 搜索表单
const searchForm = ref<DocEndpointSearchParams>({
    name: '',
    path: '',
    method: '',
    keyword: '',
    page: 1,
    page_size: 20,
});

// HTTP 方法选项
const httpMethods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'];

// 详情抽屉
const detailVisible = ref(false);
const selectedOperationId = ref('');

// HTTP 方法颜色映射
function getMethodTagType(method: string): '' | 'success' | 'warning' | 'danger' | 'info' {
    const methodMap: Record<string, '' | 'success' | 'warning' | 'danger' | 'info'> = {
        GET: 'success',
        POST: '',
        PUT: 'warning',
        DELETE: 'danger',
        PATCH: 'info',
    };
    return methodMap[method.toUpperCase()] || 'info';
}

// 表格列配置
const columns = [
    {
        field: 'operation_id',
        title: '操作 ID',
        width: 160,
        fixed: 'left' as const,
    },
    {
        field: 'name',
        title: '接口名称',
        minWidth: 200,
    },
    {
        field: 'method',
        title: '方法',
        width: 100,
        align: 'center' as const,
        slots: { default: 'method' },
    },
    {
        field: 'path',
        title: '路径',
        minWidth: 400,
    },
    {
        field: 'summary',
        title: '摘要',
        minWidth: 200,
    },
];

// 使用 VxeGrid
const [Grid, gridApi] = useVbenVxeGrid({
    gridOptions: {
        columns,
        height: 'auto',
        keepSource: true,
        rowConfig: {
            keyField: 'operation_id',
        },
        proxyConfig: {
            autoLoad: true,
            ajax: {
                query: async ({ page }: { page: { currentPage: number; pageSize: number } }) => {
                    const hasSearchCondition =
                        searchForm.value.name ||
                        searchForm.value.path ||
                        searchForm.value.method ||
                        searchForm.value.keyword;

                    let result;
                    if (hasSearchCondition) {
                        result = await searchDocEndpointsApi({
                            ...searchForm.value,
                            page: page.currentPage,
                            page_size: page.pageSize,
                        });
                    } else {
                        result = await getDocEndpointsApi(page.currentPage, page.pageSize);
                    }

                    return {
                        items: result.items,
                        total: result.total,
                    };
                },
            },
        },
        pagerConfig: {
            enabled: true,
            pageSize: 20,
            pageSizes: [10, 20, 50, 100],
        },
        toolbarConfig: {
            refresh: { code: 'query' },
        },
    },
    gridEvents: {
        cellClick: ({ row }: { row: DocEndpoint }) => {
            handleRowClick(row);
        },
    },
});

/**
 * 加载文档摘要
 */
async function loadSummary() {
    try {
        loadingSummary.value = true;
        summary.value = await getDocSummaryApi();
    } catch (error) {
        console.error('加载文档摘要失败:', error);
        ElMessage.error('加载文档摘要失败');
    } finally {
        loadingSummary.value = false;
    }
}

/**
 * 执行搜索
 */
async function handleSearch() {
    await gridApi.query();
}

/**
 * 重置搜索
 */
function handleReset() {
    searchForm.value = {
        name: '',
        path: '',
        method: '',
        keyword: '',
        page: 1,
        page_size: 20,
    };
    handleSearch();
}

/**
 * 处理行点击
 */
function handleRowClick(row: DocEndpoint) {
    selectedOperationId.value = row.operation_id;
    detailVisible.value = true;
}

onMounted(() => {
    loadSummary();
});
</script>

<template>
    <Page auto-content-height>
        <div class="flex h-full flex-col gap-4">
            <!-- 文档摘要卡片 -->
            <ElCard v-if="summary" shadow="never" class="flex-shrink-0">
                <div class="flex flex-wrap items-center justify-between gap-4">
                    <div>
                        <h2 class="text-xl font-bold">{{ summary.title }}</h2>
                        <p class="mt-1 text-sm text-gray-500">
                            版本: {{ summary.version }}
                        </p>
                    </div>
                    <div class="flex flex-wrap gap-6">
                        <ElStatistic title="接口总数" :value="summary.endpoint_count" />
                        <template v-if="summary.methods_summary">
                            <ElStatistic v-for="(count, method) in summary.methods_summary" :key="method"
                                :title="method" :value="count" />
                        </template>
                    </div>
                </div>
            </ElCard>

            <!-- 主内容区 -->
            <ElCard shadow="never" class="flex min-h-0 flex-1 flex-col" :body-style="{
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                height: '100%',
                overflow: 'hidden',
            }">
                <!-- 搜索表单 -->
                <ElForm :model="searchForm" inline class="mb-4 flex-shrink-0">
                    <ElFormItem label="接口名称">
                        <ElInput v-model="searchForm.name" placeholder="请输入接口名称" clearable style="width: 160px"
                            @keyup.enter="handleSearch" />
                    </ElFormItem>
                    <ElFormItem label="接口路径">
                        <ElInput v-model="searchForm.path" placeholder="请输入接口路径" clearable style="width: 200px"
                            @keyup.enter="handleSearch" />
                    </ElFormItem>
                    <ElFormItem label="HTTP 方法">
                        <ElSelect v-model="searchForm.method" placeholder="请选择" clearable style="width: 120px">
                            <ElOption v-for="method in httpMethods" :key="method" :label="method" :value="method" />
                        </ElSelect>
                    </ElFormItem>
                    <ElFormItem label="关键词">
                        <ElInput v-model="searchForm.keyword" placeholder="搜索名称/路径/摘要" clearable style="width: 180px"
                            @keyup.enter="handleSearch" />
                    </ElFormItem>
                    <ElFormItem>
                        <ElButton type="primary" :icon="Search" @click="handleSearch">
                            搜索
                        </ElButton>
                        <ElButton @click="handleReset">重置</ElButton>
                    </ElFormItem>
                </ElForm>

                <!-- 数据表格 -->
                <div class="min-h-0 flex-1">
                    <Grid>
                        <template #method="{ row }">
                            <ElTag :type="getMethodTagType(row.method)" size="small">
                                {{ row.method }}
                            </ElTag>
                        </template>
                        <template #empty>
                            <ElEmpty description="暂无数据" :image-size="80" />
                        </template>
                    </Grid>
                </div>
            </ElCard>
        </div>

        <!-- 接口详情抽屉 -->
        <EndpointDetail v-model:visible="detailVisible" :operation-id="selectedOperationId" />
    </Page>
</template>

<style scoped>
/* 确保表格容器正确计算高度 */
:deep(.vxe-grid) {
    height: 100%;
}

/* 行可点击样式 */
:deep(.vxe-body--row) {
    cursor: pointer;
}

:deep(.vxe-body--row:hover) {
    background-color: var(--el-fill-color-light);
}
</style>
