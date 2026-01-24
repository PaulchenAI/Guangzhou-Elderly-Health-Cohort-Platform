<script lang="ts" setup>
/**
 * 图表视图组件
 * 用于在联合查询中展示数据图表
 */
import type { EchartsUIType } from '@vben/plugins/echarts';

import type { FieldInfo } from '#/api/core/table-query';

import { computed, nextTick, ref, watch } from 'vue';

import { EchartsUI, useEcharts } from '@vben/plugins/echarts';

import {
    ElButton,
    ElCard,
    ElCheckbox,
    ElCheckboxGroup,
    ElCol,
    ElCollapse,
    ElCollapseItem,
    ElEmpty,
    ElForm,
    ElFormItem,
    ElInput,
    ElMessage,
    ElOption,
    ElRow,
    ElSelect,
    ElSlider,
    ElTooltip,
} from 'element-plus';

import {
    type AggregationType,
    type ChartConfig,
    type ChartType,
    type FieldDataType,
    generateChartConfigId,
    getFieldDisplayName,
    getFieldTypes,
    isDataOverLimit,
    MAX_DATA_POINTS,
    recommendChartType,
    transformToChartData,
} from '../utils/chart-data-transformer';

import ChartConfigManager from './ChartConfigManager.vue';

// Props 定义
const props = defineProps<{
    /** 查询结果数据 */
    items: any[];
    /** 字段元信息 */
    fieldInfo: FieldInfo[];
    /** 主表名称 */
    primaryTable: string;
}>();

// Emits 定义
const emit = defineEmits<{
    /** 关闭图表视图 */
    (e: 'close'): void;
}>();

// 图表实例引用
const chartRef = ref<EchartsUIType>();
const { renderEcharts, getChartInstance, resize } = useEcharts(chartRef);

// 配置面板折叠状态
const configPanelActive = ref<string[]>(['config']);

// 字段类型映射
const fieldTypeMap = computed(() => {
    return getFieldTypes(props.fieldInfo, props.items);
});

// 分类可用的字段（推荐用于X轴）
const categoryFields = computed(() => {
    return props.fieldInfo.filter(f => {
        const type = fieldTypeMap.value.get(f.alias);
        return type === 'category' || type === 'datetime';
    });
});

// 数值可用的字段（Y轴）
const numericFields = computed(() => {
    return props.fieldInfo.filter(f => {
        const type = fieldTypeMap.value.get(f.alias);
        return type === 'numeric';
    });
});

// 图表配置状态
const chartType = ref<ChartType>('bar');
const xAxisFields = ref<string[]>([]);  // 改为多选
const yAxisFields = ref<string[]>([]);
const aggregation = ref<AggregationType>('sum');
const chartOptions = ref<ChartConfig['chartOptions']>({
    title: '',
    showLegend: true,
    xAxisLabel: '',
    yAxisLabel: '',
    labelRotate: 0,
});

// 推荐的图表类型
const recommendedTypes = computed(() => {
    const xField = xAxisFields.value.length > 0
        ? props.fieldInfo.find(f => f.alias === xAxisFields.value[0])
        : undefined;
    const yFields = props.fieldInfo.filter(f => yAxisFields.value.includes(f.alias));
    return recommendChartType(xField, yFields, fieldTypeMap.value);
});

// 可用的图表类型
const availableChartTypes: { value: ChartType; label: string }[] = [
    { value: 'bar', label: '柱状图' },
    { value: 'line', label: '折线图' },
    { value: 'pie', label: '饼图' },
    { value: 'scatter', label: '散点图' },
    { value: 'horizontalBar', label: '条形图' },
];

// 聚合方式选项
const aggregationOptions: { value: AggregationType; label: string }[] = [
    { value: 'none', label: '不聚合' },
    { value: 'sum', label: '求和' },
    { value: 'avg', label: '平均值' },
    { value: 'count', label: '计数' },
    { value: 'max', label: '最大值' },
    { value: 'min', label: '最小值' },
];

// 数据是否超过限制
const dataOverLimit = computed(() => isDataOverLimit(props.items));

// 是否可以生成图表
const canGenerateChart = computed(() => {
    return xAxisFields.value.length > 0 && yAxisFields.value.length > 0;
});

// X轴字段选项（带类型标识和推荐标记）
const xAxisFieldOptions = computed(() => {
    return props.fieldInfo.map(f => {
        const type = fieldTypeMap.value.get(f.alias);
        const typeLabel = getTypeLabel(type);
        // 推荐分类和时间类型作为X轴
        const isRecommended = type === 'category' || type === 'datetime';
        return {
            value: f.alias,
            label: `${getFieldDisplayName(f)} (${f.original_table})`,
            type,
            typeLabel,
            isRecommended,
        };
    });
});

/**
 * 获取字段类型标签
 */
function getTypeLabel(type?: FieldDataType): string {
    const labels: Record<FieldDataType, string> = {
        numeric: '数值',
        category: '分类',
        datetime: '时间',
        unknown: '未知',
    };
    return type ? labels[type] : '未知';
}

/**
 * 处理生成图表按钮点击
 */
function handleGenerateChartClick() {
    generateChart();
}

/**
 * 生成图表
 */
async function generateChart() {
    if (!canGenerateChart.value) {
        ElMessage.warning('请至少选择一个 X 轴字段和一个 Y 轴字段');
        return;
    }

    const option = transformToChartData(
        props.items,
        props.fieldInfo,
        chartType.value,
        xAxisFields.value,  // 现在是数组
        yAxisFields.value,
        aggregation.value,
        chartOptions.value,
    );

    // 等待 DOM 更新，确保图表容器已经渲染
    await nextTick();

    // 如果图表容器仍然不存在，再等待一次
    if (!chartRef.value) {
        await new Promise(resolve => setTimeout(resolve, 100));
    }

    try {
        // 在渲染之前先确保容器尺寸正确
        await nextTick();

        const instance = await renderEcharts(option);

        // 在渲染完成后，使用 requestAnimationFrame 确保 DOM 更新完成后再调用 resize
        await nextTick();
        await new Promise<void>(resolve => {
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    const currentInstance = instance || getChartInstance();
                    const currentEl = chartRef.value?.$el || (chartRef.value as any);
                    const elWidth = currentEl?.offsetWidth || 0;
                    const elHeight = currentEl?.offsetHeight || 0;
                    if (currentInstance && elWidth > 0 && elHeight > 0) {
                        // 显式传递宽度和高度参数，确保 resize 生效
                        currentInstance.resize({
                            width: elWidth,
                            height: elHeight,
                        });
                    } else if (currentInstance) {
                        currentInstance.resize();
                    } else {
                        resize();
                    }
                    resolve();
                });
            });
        });
    } catch (error) {
        console.error('生成图表失败:', error);
        ElMessage.error('生成图表失败');
    }
}

/**
 * 导出图表为 PNG
 */
function exportChart() {
    const instance = getChartInstance();
    if (!instance) {
        ElMessage.warning('图表尚未生成');
        return;
    }

    try {
        const dataUrl = instance.getDataURL({
            type: 'png',
            pixelRatio: 2,
            backgroundColor: '#fff',
        });

        // 创建下载链接
        const link = document.createElement('a');
        link.href = dataUrl;
        const timestamp = new Date().toISOString().slice(0, 10);
        link.download = `联合查询_${props.primaryTable}_${timestamp}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        ElMessage.success('图表导出成功');
    } catch (error) {
        console.error('导出图表失败:', error);
        ElMessage.error('导出图表失败');
    }
}

/**
 * 获取当前配置
 */
function getCurrentConfig(): ChartConfig {
    return {
        id: generateChartConfigId(),
        name: '',
        chartType: chartType.value,
        xAxisFields: xAxisFields.value,  // 改为数组
        yAxisFields: yAxisFields.value,
        aggregation: aggregation.value,
        chartOptions: { ...chartOptions.value },
        createdAt: new Date().toISOString(),
    };
}

/**
 * 加载配置
 */
function handleLoadConfig(config: ChartConfig) {
    chartType.value = config.chartType;
    // 兼容旧格式（单选）和新格式（多选）
    if (config.xAxisFields) {
        xAxisFields.value = config.xAxisFields;
    } else if ((config as any).xAxisField) {
        xAxisFields.value = [(config as any).xAxisField];
    } else {
        xAxisFields.value = [];
    }
    yAxisFields.value = config.yAxisFields || [];
    aggregation.value = config.aggregation;
    chartOptions.value = { ...config.chartOptions };

    // 验证字段是否存在
    const availableAliases = new Set(props.fieldInfo.map(f => f.alias));
    xAxisFields.value = xAxisFields.value.filter(f => {
        if (!availableAliases.has(f)) {
            ElMessage.warning(`X 轴字段 "${f}" 在当前数据中不存在`);
            return false;
        }
        return true;
    });
    yAxisFields.value = yAxisFields.value.filter(f => {
        if (!availableAliases.has(f)) {
            ElMessage.warning(`Y 轴字段 "${f}" 在当前数据中不存在`);
            return false;
        }
        return true;
    });

    // 自动生成图表
    if (canGenerateChart.value) {
        generateChart();
    }
}

/**
 * 初始化默认选择
 */
function initDefaultSelection() {
    // 默认选择第一个分类字段作为 X 轴
    if (categoryFields.value.length > 0) {
        xAxisFields.value = [categoryFields.value[0]!.alias];
    } else if (props.fieldInfo.length > 0) {
        xAxisFields.value = [props.fieldInfo[0]!.alias];
    }

    // 默认选择第一个数值字段作为 Y 轴
    if (numericFields.value.length > 0) {
        yAxisFields.value = [numericFields.value[0]!.alias];
    }
}

// 监听数据变化，重新初始化
watch(
    () => props.fieldInfo,
    () => {
        if (props.fieldInfo.length > 0 && xAxisFields.value.length === 0) {
            initDefaultSelection();
        }
    },
    { immediate: true },
);

// 注意：移除了自动生成的 watch 监听器
// 原因：当配置变化时（特别是 Y 轴字段被清空时），canGenerateChart 会变为 false，
// 导致图表容器被隐藏（v-else），此时如果 watch 立即触发，chartRef 可能不存在。
// 改为仅在用户点击"生成图表"按钮时手动生成图表，避免时序问题。
</script>

<template>
    <div class="chart-viewer">
        <!-- 工具栏 -->
        <div class="mb-3 flex items-center justify-between">
            <div class="flex items-center gap-2">
                <ElButton type="primary" @click="emit('close')">
                    返回表格视图
                </ElButton>
                <span class="text-gray-500">
                    共 {{ items.length }} 条数据
                    <span v-if="dataOverLimit" class="text-orange-500">
                        （数据量较大，已采样显示 {{ MAX_DATA_POINTS }} 条）
                    </span>
                </span>
            </div>
            <div class="flex gap-2">
                <!-- 配置管理 -->
                <ChartConfigManager :current-config="getCurrentConfig()" @load="handleLoadConfig" />
                <!-- 导出 PNG -->
                <ElButton :disabled="!canGenerateChart" @click="exportChart">
                    导出 PNG
                </ElButton>
            </div>
        </div>

        <!-- 数据量警告 -->
        <div v-if="dataOverLimit"
            class="mb-3 rounded bg-orange-50 p-3 text-orange-700 dark:bg-orange-900/20 dark:text-orange-300">
            <strong>提示：</strong>数据量较大（{{ items.length }} 条），建议添加过滤条件或使用数据聚合功能以获得更好的展示效果。
        </div>

        <ElRow :gutter="16">
            <!-- 左侧：配置面板 -->
            <ElCol :span="7">
                <ElCard shadow="never" class="h-full">
                    <ElCollapse v-model="configPanelActive">
                        <ElCollapseItem name="config" title="图表配置">
                            <ElForm label-position="top" size="small">
                                <!-- 图表类型 -->
                                <ElFormItem label="图表类型">
                                    <div class="chart-type-selector">
                                        <ElTooltip v-for="type in availableChartTypes" :key="type.value"
                                            :content="recommendedTypes.includes(type.value) ? `${type.label}（推荐）` : type.label"
                                            placement="top">
                                            <ElButton :type="chartType === type.value ? 'primary' : 'default'"
                                                :class="{ 'is-recommended': recommendedTypes.includes(type.value) }"
                                                @click="chartType = type.value">
                                                {{ type.label }}
                                            </ElButton>
                                        </ElTooltip>
                                    </div>
                                </ElFormItem>

                                <!-- X 轴字段（分组字段，可多选组合） -->
                                <ElFormItem label="X 轴字段（分组依据，可多选）">
                                    <ElCheckboxGroup v-model="xAxisFields" class="x-axis-fields">
                                        <ElCheckbox v-for="option in xAxisFieldOptions" :key="option.value"
                                            :label="option.value" :value="option.value">
                                            <span :class="{ 'font-medium': option.isRecommended }">
                                                {{ option.label }}
                                            </span>
                                            <span class="ml-1 text-xs"
                                                :class="option.isRecommended ? 'text-green-500' : 'text-gray-400'">
                                                [{{ option.typeLabel }}]{{ option.isRecommended ? ' 推荐' : '' }}
                                            </span>
                                        </ElCheckbox>
                                    </ElCheckboxGroup>
                                    <div class="mt-1 text-xs text-gray-400">
                                        选择用于分组的字段，可多选组合（如"性别+婚姻状况"）
                                    </div>
                                </ElFormItem>

                                <!-- Y 轴字段（统计字段，可多选） -->
                                <ElFormItem label="Y 轴字段（统计数值）">
                                    <ElCheckboxGroup v-model="yAxisFields" class="y-axis-fields">
                                        <ElCheckbox v-for="field in numericFields" :key="field.alias"
                                            :label="field.alias" :value="field.alias">
                                            {{ getFieldDisplayName(field) }}
                                            <span class="text-xs text-gray-400">({{ field.original_table }})</span>
                                        </ElCheckbox>
                                    </ElCheckboxGroup>
                                    <div v-if="numericFields.length === 0" class="text-xs text-gray-400">
                                        暂无可用的数值字段
                                    </div>
                                    <div v-else class="mt-1 text-xs text-gray-400">
                                        选择要统计的数值字段，将按 X 轴字段分组后进行聚合计算
                                    </div>
                                </ElFormItem>

                                <!-- 聚合方式 -->
                                <ElFormItem label="聚合方式">
                                    <ElSelect v-model="aggregation" class="w-full">
                                        <ElOption v-for="option in aggregationOptions" :key="option.value"
                                            :label="option.label" :value="option.value" />
                                    </ElSelect>
                                    <div class="mt-1 text-xs text-gray-400">
                                        选择对 Y 轴数值进行的统计方式
                                    </div>
                                </ElFormItem>

                                <!-- 数据数量限制已移到查询侧（影响后端 page_size），图表侧不再单独控制 -->

                                <!-- 图表标题 -->
                                <ElFormItem label="图表标题">
                                    <ElInput v-model="chartOptions.title" placeholder="可选，输入图表标题" />
                                </ElFormItem>

                                <!-- 显示图例 -->
                                <ElFormItem label="显示图例">
                                    <ElCheckbox v-model="chartOptions.showLegend">
                                        显示图例
                                    </ElCheckbox>
                                </ElFormItem>

                                <!-- X 轴标签旋转 -->
                                <ElFormItem label="X 轴标签旋转角度">
                                    <ElSlider v-model="chartOptions.labelRotate" :min="-90" :max="90" :step="15"
                                        show-stops />
                                </ElFormItem>

                                <!-- 生成图表按钮 -->
                                <ElFormItem>
                                    <ElButton type="primary" class="w-full" :disabled="!canGenerateChart"
                                        @click="handleGenerateChartClick">
                                        生成图表
                                    </ElButton>
                                </ElFormItem>
                            </ElForm>
                        </ElCollapseItem>
                    </ElCollapse>
                </ElCard>
            </ElCol>

            <!-- 右侧：图表区域 -->
            <ElCol :span="17">
                <ElCard shadow="never" class="chart-container">
                    <!-- 使用 v-show 而不是 v-if/v-else，避免切换 Y 轴字段时组件被卸载导致图表实例丢失 -->
                    <div v-show="!canGenerateChart" class="flex h-full items-center justify-center">
                        <ElEmpty description="请在左侧配置图表参数">
                            <template #image>
                                <svg class="h-32 w-32 text-gray-300" viewBox="0 0 24 24" fill="none"
                                    stroke="currentColor" stroke-width="1.5">
                                    <path stroke-linecap="round" stroke-linejoin="round"
                                        d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
                                </svg>
                            </template>
                        </ElEmpty>
                    </div>
                    <EchartsUI v-show="canGenerateChart" ref="chartRef" class="h-full w-full" />
                </ElCard>
            </ElCol>
        </ElRow>
    </div>
</template>

<style scoped>
.chart-viewer {
    height: 100%;
    display: flex;
    flex-direction: column;
}

.chart-container {
    height: 500px;
}

.chart-container :deep(.el-card__body) {
    height: 100%;
    padding: 12px;
}

.chart-type-selector {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.chart-type-selector .is-recommended {
    border-color: var(--el-color-primary);
}

.x-axis-fields,
.y-axis-fields {
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-height: 200px;
    overflow-y: auto;
}

.x-axis-fields :deep(.el-checkbox),
.y-axis-fields :deep(.el-checkbox) {
    margin-right: 0;
}
</style>
