<script lang="ts" setup>
import type { DocInvokeResponse } from '#/api/core/doc-api';

import { ref, watch } from 'vue';

import {
    ElAlert,
    ElButton,
    ElInput,
    ElMessage,
    ElRadioButton,
    ElRadioGroup,
    ElSkeleton,
    ElTable,
    ElTableColumn,
    ElTag,
} from 'element-plus';

import {
    getDocDefaultParamsApi,
    invokeDocEndpointApi,
} from '#/api/core/doc-api';

const props = defineProps<{
    operationId: string;
}>();

// 请求参数（JSON 字符串）
const paramsText = ref('{}');
const paramsError = ref('');

// 调用状态
const loading = ref(false);
const response = ref<DocInvokeResponse | null>(null);

// 响应展示模式
const displayMode = ref<'table' | 'json'>('json');

// 加载默认参数
const loadingDefault = ref(false);

/**
 * 加载默认参数
 */
async function loadDefaultParams() {
    if (!props.operationId) return;

    try {
        loadingDefault.value = true;
        const result = await getDocDefaultParamsApi(props.operationId);
        paramsText.value = JSON.stringify(result.params, null, 2);
        paramsError.value = '';
    } catch (error: any) {
        console.error('加载默认参数失败:', error);
        ElMessage.error('加载默认参数失败');
    } finally {
        loadingDefault.value = false;
    }
}

/**
 * 验证 JSON
 */
function validateJson(): boolean {
    try {
        JSON.parse(paramsText.value);
        paramsError.value = '';
        return true;
    } catch (e: any) {
        paramsError.value = `JSON 格式错误: ${e.message}`;
        return false;
    }
}

/**
 * 发送请求
 */
async function handleInvoke() {
    if (!validateJson()) {
        return;
    }

    try {
        loading.value = true;
        response.value = null;

        const params = JSON.parse(paramsText.value);
        response.value = await invokeDocEndpointApi(props.operationId, params);

        if (response.value.success) {
            ElMessage.success('调用成功');
        } else {
            ElMessage.warning(`调用返回非成功状态: ${response.value.status_code}`);
        }
    } catch (error: any) {
        console.error('调用失败:', error);
        ElMessage.error(error?.message || '调用失败');
    } finally {
        loading.value = false;
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

/**
 * 获取响应数据数组（用于表格展示）
 */
function getResponseArray(): any[] {
    if (!response.value?.data) return [];

    const data = response.value.data;

    // 如果是数组，直接返回
    if (Array.isArray(data)) {
        return data;
    }

    // 如果有 data 字段且是数组
    if (data.data && Array.isArray(data.data)) {
        return data.data;
    }

    // 如果有 items 字段且是数组
    if (data.items && Array.isArray(data.items)) {
        return data.items;
    }

    // 否则包装成单元素数组
    return [data];
}

/**
 * 获取表格列
 */
function getTableColumns(): string[] {
    const arr = getResponseArray();
    if (arr.length === 0) return [];

    const firstItem = arr[0];
    if (typeof firstItem !== 'object' || firstItem === null) {
        return ['value'];
    }

    return Object.keys(firstItem);
}

// 监听 operationId 变化，重置状态
watch(
    () => props.operationId,
    () => {
        paramsText.value = '{}';
        paramsError.value = '';
        response.value = null;
    },
);
</script>

<template>
    <div class="invoke-panel">
        <!-- 请求参数区域 -->
        <div class="mb-4">
            <div class="mb-2 flex items-center justify-between">
                <span class="font-medium">请求参数</span>
                <ElButton size="small" :loading="loadingDefault" @click="loadDefaultParams">
                    加载默认参数
                </ElButton>
            </div>
            <ElInput v-model="paramsText" type="textarea" :rows="8" placeholder='请输入 JSON 格式的请求参数，如 {"key": "value"}'
                :class="{ 'is-error': paramsError }" @blur="validateJson" />
            <p v-if="paramsError" class="mt-1 text-sm text-red-500">
                {{ paramsError }}
            </p>
        </div>

        <!-- 发送按钮 -->
        <div class="mb-4">
            <ElButton type="primary" :loading="loading" :disabled="!!paramsError" @click="handleInvoke">
                {{ loading ? '调用中...' : '发送请求' }}
            </ElButton>
        </div>

        <!-- 响应结果区域 -->
        <div v-if="response">
            <!-- 状态信息 -->
            <div class="mb-3 flex items-center gap-4">
                <span class="font-medium">响应结果</span>
                <ElTag :type="response.success ? 'success' : 'danger'" size="small">
                    {{ response.success ? '成功' : '失败' }}
                </ElTag>
                <span class="text-sm text-gray-500">
                    状态码: {{ response.status_code }}
                </span>
                <span class="text-sm text-gray-500">
                    耗时: {{ response.duration_ms }}ms
                </span>
            </div>

            <!-- 错误信息 -->
            <ElAlert v-if="response.error" :title="response.error" type="error" show-icon :closable="false"
                class="mb-3" />

            <!-- 展示模式切换 -->
            <div v-if="response.data" class="mb-3">
                <ElRadioGroup v-model="displayMode" size="small">
                    <ElRadioButton value="json">JSON</ElRadioButton>
                    <ElRadioButton value="table">表格</ElRadioButton>
                </ElRadioGroup>
            </div>

            <!-- JSON 展示 -->
            <div v-if="displayMode === 'json' && response.data">
                <pre
                    class="max-h-96 overflow-auto rounded-lg bg-gray-50 p-4 text-sm dark:bg-gray-900">{{ formatJson(response.data) }}</pre>
            </div>

            <!-- 表格展示 -->
            <div v-if="displayMode === 'table' && response.data" class="max-h-96 overflow-auto">
                <ElTable :data="getResponseArray()" border stripe size="small" max-height="350">
                    <ElTableColumn v-for="col in getTableColumns()" :key="col" :prop="col" :label="col" min-width="120"
                        show-overflow-tooltip />
                </ElTable>
            </div>
        </div>

        <!-- 空状态 -->
        <div v-else-if="!loading" class="text-center text-gray-400">
            点击"发送请求"调用接口
        </div>

        <!-- 加载中 -->
        <ElSkeleton v-if="loading" :rows="5" animated />
    </div>
</template>

<style scoped>
.invoke-panel {
    padding: 8px 0;
}

:deep(.el-textarea__inner) {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 13px;
}

:deep(.is-error .el-textarea__inner) {
    border-color: var(--el-color-danger);
}

pre {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    white-space: pre-wrap;
    word-break: break-all;
}
</style>
