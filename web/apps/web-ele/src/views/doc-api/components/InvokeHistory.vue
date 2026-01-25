<script lang="ts" setup>
import type { DocInvokeLog } from '#/api/core/doc-api';

import { onMounted, ref, watch } from 'vue';

import {
    ElButton,
    ElDialog,
    ElEmpty,
    ElMessage,
    ElPagination,
    ElSkeleton,
    ElTable,
    ElTableColumn,
    ElTag,
} from 'element-plus';

import { getDocInvokeLogsApi } from '#/api/core/doc-api';

const props = defineProps<{
    operationId?: string;
}>();

// 分页
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);

// 数据
const loading = ref(false);
const logs = ref<DocInvokeLog[]>([]);

// 详情对话框
const detailVisible = ref(false);
const selectedLog = ref<DocInvokeLog | null>(null);

/**
 * 加载调用历史
 */
async function loadLogs() {
    try {
        loading.value = true;
        const result = await getDocInvokeLogsApi(
            page.value,
            pageSize.value,
            props.operationId,
        );
        logs.value = result.items;
        total.value = result.total;
    } catch (error: any) {
        console.error('加载调用历史失败:', error);
        ElMessage.error('加载调用历史失败');
    } finally {
        loading.value = false;
    }
}

/**
 * 分页变化
 */
function handlePageChange(newPage: number) {
    page.value = newPage;
    loadLogs();
}

/**
 * 查看详情
 */
function viewDetail(log: DocInvokeLog) {
    selectedLog.value = log;
    detailVisible.value = true;
}

/**
 * 格式化时间
 */
function formatTime(dateStr?: string): string {
    if (!dateStr) return '-';
    try {
        const date = new Date(dateStr);
        return date.toLocaleString('zh-CN');
    } catch {
        return dateStr;
    }
}

/**
 * 格式化 JSON
 */
function formatJson(data: any): string {
    if (!data) return '';
    try {
        return JSON.stringify(data, null, 2);
    } catch {
        return String(data);
    }
}

// 监听 operationId 变化
watch(
    () => props.operationId,
    () => {
        page.value = 1;
        loadLogs();
    },
);

onMounted(() => {
    loadLogs();
});
</script>

<template>
    <div class="invoke-history">
        <ElSkeleton v-if="loading && logs.length === 0" :rows="5" animated />

        <template v-else-if="logs.length > 0">
            <ElTable :data="logs" border stripe size="small" v-loading="loading">
                <ElTableColumn prop="endpoint_name" label="接口名称" min-width="150" show-overflow-tooltip />
                <ElTableColumn prop="method" label="方法" width="80" align="center">
                    <template #default="{ row }">
                        <ElTag size="small">{{ row.method }}</ElTag>
                    </template>
                </ElTableColumn>
                <ElTableColumn prop="response_status" label="状态码" width="90" align="center">
                    <template #default="{ row }">
                        <ElTag :type="row.success ? 'success' : 'danger'" size="small">
                            {{ row.response_status || '-' }}
                        </ElTag>
                    </template>
                </ElTableColumn>
                <ElTableColumn prop="duration_ms" label="耗时" width="90" align="right">
                    <template #default="{ row }">
                        {{ row.duration_ms }}ms
                    </template>
                </ElTableColumn>
                <ElTableColumn prop="sys_create_datetime" label="调用时间" width="170">
                    <template #default="{ row }">
                        {{ formatTime(row.sys_create_datetime) }}
                    </template>
                </ElTableColumn>
                <ElTableColumn label="操作" width="80" align="center" fixed="right">
                    <template #default="{ row }">
                        <ElButton type="primary" link size="small" @click="viewDetail(row)">
                            详情
                        </ElButton>
                    </template>
                </ElTableColumn>
            </ElTable>

            <!-- 分页 -->
            <div class="mt-4 flex justify-end">
                <ElPagination v-model:current-page="page" :page-size="pageSize" :total="total"
                    layout="total, prev, pager, next" small @current-change="handlePageChange" />
            </div>
        </template>

        <ElEmpty v-else description="暂无调用记录" :image-size="60" />

        <!-- 详情对话框 -->
        <ElDialog v-model="detailVisible" title="调用详情" width="700px" destroy-on-close>
            <template v-if="selectedLog">
                <div class="space-y-4">
                    <!-- 基本信息 -->
                    <div class="flex flex-wrap gap-4 text-sm">
                        <div>
                            <span class="text-gray-500">接口:</span>
                            <span class="ml-2 font-medium">{{ selectedLog.endpoint_name }}</span>
                        </div>
                        <div>
                            <span class="text-gray-500">方法:</span>
                            <ElTag size="small" class="ml-2">{{ selectedLog.method }}</ElTag>
                        </div>
                        <div>
                            <span class="text-gray-500">状态:</span>
                            <ElTag :type="selectedLog.success ? 'success' : 'danger'" size="small" class="ml-2">
                                {{ selectedLog.response_status || '-' }}
                            </ElTag>
                        </div>
                        <div>
                            <span class="text-gray-500">耗时:</span>
                            <span class="ml-2">{{ selectedLog.duration_ms }}ms</span>
                        </div>
                    </div>

                    <!-- 路径 -->
                    <div class="text-sm">
                        <span class="text-gray-500">路径:</span>
                        <code class="ml-2 rounded bg-gray-100 px-2 py-1 dark:bg-gray-800">
                            {{ selectedLog.path }}
                        </code>
                    </div>

                    <!-- 错误信息 -->
                    <div v-if="selectedLog.error_message" class="text-sm text-red-500">
                        <span class="text-gray-500">错误:</span>
                        <span class="ml-2">{{ selectedLog.error_message }}</span>
                    </div>

                    <!-- 请求参数 -->
                    <div>
                        <h4 class="mb-2 font-medium">请求参数</h4>
                        <pre
                            class="max-h-48 overflow-auto rounded-lg bg-gray-50 p-3 text-sm dark:bg-gray-900">{{ formatJson(selectedLog.request_params) }}</pre>
                    </div>

                    <!-- 响应数据 -->
                    <div>
                        <h4 class="mb-2 font-medium">响应数据</h4>
                        <pre
                            class="max-h-64 overflow-auto rounded-lg bg-gray-50 p-3 text-sm dark:bg-gray-900">{{ formatJson(selectedLog.response_data) }}</pre>
                    </div>
                </div>
            </template>
        </ElDialog>
    </div>
</template>

<style scoped>
pre {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    white-space: pre-wrap;
    word-break: break-all;
}
</style>
