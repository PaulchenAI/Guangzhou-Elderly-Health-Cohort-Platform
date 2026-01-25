<script lang="ts" setup>
import type { DocEndpointDetail } from '#/api/core/doc-api';

import { ref, watch } from 'vue';

import {
    ElCollapse,
    ElCollapseItem,
    ElDescriptions,
    ElDescriptionsItem,
    ElDrawer,
    ElEmpty,
    ElMessage,
    ElSkeleton,
    ElTag,
} from 'element-plus';

import { getDocEndpointDetailApi } from '#/api/core/doc-api';

const props = defineProps<{
    operationId: string;
    visible: boolean;
}>();

const emit = defineEmits<{
    'update:visible': [value: boolean];
}>();

// 接口详情数据
const detail = ref<DocEndpointDetail | null>(null);
const loading = ref(false);
const error = ref('');

// 折叠面板状态
const activeNames = ref(['basic', 'parameters', 'request', 'response', 'examples']);

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

// JSON 格式化
function formatJson(data: any): string {
    if (!data) return '';
    try {
        return JSON.stringify(data, null, 2);
    } catch {
        return String(data);
    }
}

// 加载接口详情
async function loadDetail() {
    if (!props.operationId) return;

    try {
        loading.value = true;
        error.value = '';
        detail.value = await getDocEndpointDetailApi(props.operationId);
    } catch (err: any) {
        console.error('加载接口详情失败:', err);
        error.value = err?.message || '加载失败';
        ElMessage.error('加载接口详情失败');
    } finally {
        loading.value = false;
    }
}

// 关闭抽屉
function handleClose() {
    emit('update:visible', false);
}

// 监听 operationId 变化
watch(
    () => props.operationId,
    (newVal) => {
        if (newVal && props.visible) {
            loadDetail();
        }
    },
);

// 监听 visible 变化
watch(
    () => props.visible,
    (newVal) => {
        if (newVal && props.operationId) {
            loadDetail();
        } else if (!newVal) {
            detail.value = null;
            error.value = '';
        }
    },
);
</script>

<template>
    <ElDrawer :model-value="visible" title="接口详情" size="50%" direction="rtl" @close="handleClose">
        <!-- 加载状态 -->
        <ElSkeleton v-if="loading" :rows="10" animated />

        <!-- 错误状态 -->
        <ElEmpty v-else-if="error" :description="error" />

        <!-- 详情内容 -->
        <template v-else-if="detail">
            <ElCollapse v-model="activeNames">
                <!-- 基本信息 -->
                <ElCollapseItem title="基本信息" name="basic">
                    <ElDescriptions :column="1" border>
                        <ElDescriptionsItem label="操作 ID">
                            <code class="rounded bg-gray-100 px-2 py-1 text-sm dark:bg-gray-800">
                                {{ detail.operation_id }}
                            </code>
                        </ElDescriptionsItem>
                        <ElDescriptionsItem label="接口名称">
                            {{ detail.name }}
                        </ElDescriptionsItem>
                        <ElDescriptionsItem label="HTTP 方法">
                            <ElTag :type="getMethodTagType(detail.method)" size="small">
                                {{ detail.method }}
                            </ElTag>
                        </ElDescriptionsItem>
                        <ElDescriptionsItem label="接口路径">
                            <code class="break-all rounded bg-gray-100 px-2 py-1 text-sm dark:bg-gray-800">
                                {{ detail.path }}
                            </code>
                        </ElDescriptionsItem>
                        <ElDescriptionsItem v-if="detail.summary" label="摘要">
                            {{ detail.summary }}
                        </ElDescriptionsItem>
                        <ElDescriptionsItem v-if="detail.description" label="描述">
                            {{ detail.description }}
                        </ElDescriptionsItem>
                    </ElDescriptions>
                </ElCollapseItem>

                <!-- 请求参数 -->
                <ElCollapseItem v-if="detail.parameters && detail.parameters.length > 0" title="请求参数" name="parameters">
                    <div class="overflow-x-auto">
                        <table class="min-w-full border-collapse border border-gray-200 text-sm dark:border-gray-700">
                            <thead>
                                <tr class="bg-gray-50 dark:bg-gray-800">
                                    <th class="border border-gray-200 px-3 py-2 text-left dark:border-gray-700">名称</th>
                                    <th class="border border-gray-200 px-3 py-2 text-left dark:border-gray-700">位置</th>
                                    <th class="border border-gray-200 px-3 py-2 text-left dark:border-gray-700">必填</th>
                                    <th class="border border-gray-200 px-3 py-2 text-left dark:border-gray-700">类型</th>
                                    <th class="border border-gray-200 px-3 py-2 text-left dark:border-gray-700">描述</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="(param, index) in detail.parameters" :key="index">
                                    <td class="border border-gray-200 px-3 py-2 dark:border-gray-700">
                                        <code>{{ param.name }}</code>
                                    </td>
                                    <td class="border border-gray-200 px-3 py-2 dark:border-gray-700">
                                        {{ param.in }}
                                    </td>
                                    <td class="border border-gray-200 px-3 py-2 dark:border-gray-700">
                                        <ElTag v-if="param.required" type="danger" size="small">是</ElTag>
                                        <span v-else class="text-gray-400">否</span>
                                    </td>
                                    <td class="border border-gray-200 px-3 py-2 dark:border-gray-700">
                                        {{ param.schema?.type || '-' }}
                                    </td>
                                    <td class="border border-gray-200 px-3 py-2 dark:border-gray-700">
                                        {{ param.description || '-' }}
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </ElCollapseItem>

                <!-- 请求体 -->
                <ElCollapseItem v-if="detail.request_body" title="请求体" name="request">
                    <pre
                        class="overflow-x-auto rounded-lg bg-gray-50 p-4 text-sm dark:bg-gray-900">{{ formatJson(detail.request_body) }}</pre>
                </ElCollapseItem>

                <!-- 响应定义 -->
                <ElCollapseItem v-if="detail.responses && Object.keys(detail.responses).length > 0" title="响应定义"
                    name="response">
                    <div v-for="(response, statusCode) in detail.responses" :key="statusCode" class="mb-4">
                        <h4 class="mb-2 font-medium">
                            <ElTag :type="String(statusCode).startsWith('2') ? 'success' : 'warning'" size="small">
                                {{ statusCode }}
                            </ElTag>
                            <span class="ml-2">{{ response.description || '' }}</span>
                        </h4>
                        <pre v-if="response.content"
                            class="overflow-x-auto rounded-lg bg-gray-50 p-4 text-sm dark:bg-gray-900">{{ formatJson(response.content) }}</pre>
                    </div>
                </ElCollapseItem>

                <!-- 示例数据 -->
                <ElCollapseItem v-if="detail.request_example || detail.response_example" title="示例数据" name="examples">
                    <div v-if="detail.request_example" class="mb-4">
                        <h4 class="mb-2 font-medium">请求示例</h4>
                        <pre
                            class="overflow-x-auto rounded-lg bg-gray-50 p-4 text-sm dark:bg-gray-900">{{ formatJson(detail.request_example) }}</pre>
                    </div>
                    <div v-if="detail.response_example">
                        <h4 class="mb-2 font-medium">响应示例</h4>
                        <pre
                            class="overflow-x-auto rounded-lg bg-gray-50 p-4 text-sm dark:bg-gray-900">{{ formatJson(detail.response_example) }}</pre>
                    </div>
                </ElCollapseItem>

                <!-- 额外信息 -->
                <ElCollapseItem v-if="detail.request_fields || detail.response_fields || detail.location" title="额外信息"
                    name="extra">
                    <ElDescriptions :column="2" border>
                        <ElDescriptionsItem v-if="detail.request_fields" label="请求字段数">
                            {{ detail.request_fields }}
                        </ElDescriptionsItem>
                        <ElDescriptionsItem v-if="detail.response_fields" label="响应字段数">
                            {{ detail.response_fields }}
                        </ElDescriptionsItem>
                    </ElDescriptions>
                    <div v-if="detail.location" class="mt-4">
                        <h4 class="mb-2 font-medium">文档位置</h4>
                        <pre
                            class="overflow-x-auto rounded-lg bg-gray-50 p-4 text-sm dark:bg-gray-900">{{ formatJson(detail.location) }}</pre>
                    </div>
                </ElCollapseItem>
            </ElCollapse>
        </template>

        <!-- 空状态 -->
        <ElEmpty v-else description="请选择一个接口" />
    </ElDrawer>
</template>

<style scoped>
/* 折叠面板样式 */
:deep(.el-collapse) {
    border: none;
}

:deep(.el-collapse-item__header) {
    font-weight: 600;
    font-size: 14px;
}

:deep(.el-collapse-item__content) {
    padding-top: 8px;
}

/* 代码块样式 */
pre {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    white-space: pre-wrap;
    word-break: break-all;
}

code {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

/* 表格响应式 */
table {
    table-layout: auto;
}
</style>
