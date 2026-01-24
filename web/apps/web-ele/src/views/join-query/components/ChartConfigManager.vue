<script lang="ts" setup>
/**
 * 图表配置管理器组件
 * 用于保存和加载图表配置
 */
import { ref } from 'vue';

import { Folder, Plus } from '@vben/icons';

import {
    ElButton,
    ElDialog,
    ElEmpty,
    ElInput,
    ElMessage,
    ElMessageBox,
    ElPopover,
    ElScrollbar,
} from 'element-plus';

import {
    type ChartConfig,
    deleteChartConfig,
    generateChartConfigId,
    getAggregationLabel,
    getChartTypeLabel,
    loadChartConfigs,
    saveChartConfig,
} from '../utils/chart-data-transformer';

// Props 定义
const props = defineProps<{
    /** 当前图表配置 */
    currentConfig: ChartConfig;
}>();

// Emits 定义
const emit = defineEmits<{
    /** 加载配置 */
    (e: 'load', config: ChartConfig): void;
}>();

// 对话框状态
const saveDialogVisible = ref(false);
const loadPopoverVisible = ref(false);

// 配置名称
const configName = ref('');

// 配置列表
const configs = ref<ChartConfig[]>([]);

/**
 * 打开保存对话框
 */
function openSaveDialog() {
    configName.value = '';
    saveDialogVisible.value = true;
}

/**
 * 保存配置
 */
function handleSave() {
    if (!configName.value.trim()) {
        ElMessage.warning('请输入配置名称');
        return;
    }

    const config: ChartConfig = {
        ...props.currentConfig,
        id: generateChartConfigId(),
        name: configName.value.trim(),
        createdAt: new Date().toISOString(),
    };

    saveChartConfig(config);
    ElMessage.success('配置保存成功');
    saveDialogVisible.value = false;
    configName.value = '';
}

/**
 * 加载配置列表
 */
function refreshConfigs() {
    configs.value = loadChartConfigs();
}

/**
 * 显示加载弹出框
 */
function showLoadPopover() {
    refreshConfigs();
    loadPopoverVisible.value = true;
}

/**
 * 加载配置
 */
function handleLoad(config: ChartConfig) {
    emit('load', config);
    loadPopoverVisible.value = false;
    ElMessage.success(`已加载配置：${config.name}`);
}

/**
 * 删除配置
 */
async function handleDelete(config: ChartConfig) {
    try {
        await ElMessageBox.confirm(
            `确定要删除配置"${config.name}"吗？`,
            '确认删除',
            {
                confirmButtonText: '删除',
                cancelButtonText: '取消',
                type: 'warning',
            },
        );

        deleteChartConfig(config.id);
        refreshConfigs();
        ElMessage.success('配置已删除');
    } catch {
        // 用户取消
    }
}

/**
 * 格式化日期
 */
function formatDate(dateStr: string): string {
    try {
        const date = new Date(dateStr);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
        });
    } catch {
        return dateStr;
    }
}
</script>

<template>
    <div class="chart-config-manager">
        <!-- 保存按钮 -->
        <ElButton :icon="Plus" @click="openSaveDialog">
            保存配置
        </ElButton>

        <!-- 加载按钮 -->
        <ElPopover
            v-model:visible="loadPopoverVisible"
            placement="bottom"
            :width="360"
            trigger="click"
            @show="refreshConfigs"
        >
            <template #reference>
                <ElButton :icon="Folder" @click="showLoadPopover">
                    加载配置
                </ElButton>
            </template>

            <div class="config-list">
                <div class="mb-2 text-sm font-medium text-gray-600">
                    已保存的配置
                </div>

                <ElScrollbar max-height="300px">
                    <ElEmpty
                        v-if="configs.length === 0"
                        description="暂无保存的配置"
                        :image-size="60"
                    />

                    <div v-else class="space-y-2">
                        <div
                            v-for="config in configs"
                            :key="config.id"
                            class="config-item"
                        >
                            <div class="config-info" @click="handleLoad(config)">
                                <div class="config-name">{{ config.name }}</div>
                                <div class="config-meta">
                                    <span>{{ getChartTypeLabel(config.chartType) }}</span>
                                    <span>·</span>
                                    <span>{{ getAggregationLabel(config.aggregation) }}</span>
                                    <span>·</span>
                                    <span>{{ config.yAxisFields.length }} 个 Y 轴字段</span>
                                </div>
                                <div class="config-date">
                                    {{ formatDate(config.createdAt) }}
                                </div>
                            </div>
                            <ElButton
                                type="danger"
                                size="small"
                                text
                                @click.stop="handleDelete(config)"
                            >
                                删除
                            </ElButton>
                        </div>
                    </div>
                </ElScrollbar>
            </div>
        </ElPopover>

        <!-- 保存对话框 -->
        <ElDialog
            v-model="saveDialogVisible"
            title="保存图表配置"
            width="400px"
            :close-on-click-modal="false"
        >
            <ElInput
                v-model="configName"
                placeholder="请输入配置名称"
                maxlength="50"
                show-word-limit
                @keyup.enter="handleSave"
            />

            <div class="mt-3 text-sm text-gray-500">
                <p>将保存以下配置：</p>
                <ul class="mt-1 list-disc pl-4">
                    <li>图表类型：{{ getChartTypeLabel(currentConfig.chartType) }}</li>
                    <li>X 轴字段：{{ currentConfig.xAxisField || '未选择' }}</li>
                    <li>Y 轴字段：{{ currentConfig.yAxisFields.length }} 个</li>
                    <li>聚合方式：{{ getAggregationLabel(currentConfig.aggregation) }}</li>
                </ul>
            </div>

            <template #footer>
                <ElButton @click="saveDialogVisible = false">取消</ElButton>
                <ElButton type="primary" @click="handleSave">保存</ElButton>
            </template>
        </ElDialog>
    </div>
</template>

<style scoped>
.chart-config-manager {
    display: inline-flex;
    gap: 8px;
}

.config-list {
    padding: 4px;
}

.config-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    border-radius: 6px;
    cursor: pointer;
    transition: background-color 0.2s;
}

.config-item:hover {
    background-color: var(--el-fill-color-light);
}

.config-info {
    flex: 1;
    min-width: 0;
}

.config-name {
    font-weight: 500;
    color: var(--el-text-color-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.config-meta {
    display: flex;
    gap: 4px;
    margin-top: 2px;
    font-size: 12px;
    color: var(--el-text-color-secondary);
}

.config-date {
    margin-top: 2px;
    font-size: 11px;
    color: var(--el-text-color-placeholder);
}
</style>
