/**
 * 图表数据转换工具
 * 将联合查询结果数据转换为 ECharts 格式
 */

import type { FieldInfo } from '#/api/core/table-query';

// ECharts 配置类型（简化版，避免依赖 echarts 类型）
export type EChartsOption = Record<string, any>;

/**
 * 图表类型枚举
 */
export type ChartType = 'bar' | 'line' | 'pie' | 'scatter' | 'horizontalBar';

/**
 * 字段类型枚举
 */
export type FieldDataType = 'numeric' | 'category' | 'datetime' | 'unknown';

/**
 * 聚合方式枚举
 */
export type AggregationType = 'sum' | 'avg' | 'count' | 'max' | 'min' | 'none';

/**
 * 图表配置接口
 */
export interface ChartConfig {
    id: string;
    name: string;
    chartType: ChartType;
    xAxisFields?: string[];  // 改为数组，支持多字段组合
    yAxisFields: string[];
    categoryField?: string;
    aggregation: AggregationType;
    chartOptions: {
        title?: string;
        showLegend?: boolean;
        xAxisLabel?: string;
        yAxisLabel?: string;
        labelRotate?: number;
    };
    createdAt: string;
}

/**
 * 数据限制常量
 */
// 图表侧采样上限（查询侧也会限制 page_size<=1000，避免一次拿太多数据）
export const MAX_DATA_POINTS = 1000;

/**
 * 图表配置存储键
 */
const CHART_CONFIG_STORAGE_KEY = 'join-query-chart-configs';

/**
 * 数值类型关键字
 */
const NUMERIC_TYPES = ['int', 'integer', 'float', 'double', 'decimal', 'numeric', 'number', 'bigint', 'smallint', 'tinyint'];

/**
 * 时间类型关键字
 */
const DATETIME_TYPES = ['datetime', 'date', 'timestamp', 'time'];

/**
 * 识别字段数据类型
 * @param field - 字段信息
 * @param sampleValues - 样本值（用于推断类型）
 */
export function identifyFieldType(field: FieldInfo, sampleValues?: any[]): FieldDataType {
    const fieldType = field.field_type?.toLowerCase() || '';

    // 检查数值类型
    if (NUMERIC_TYPES.some(t => fieldType.includes(t))) {
        return 'numeric';
    }

    // 检查时间类型
    if (DATETIME_TYPES.some(t => fieldType.includes(t))) {
        return 'datetime';
    }

    // 基于样本值推断
    if (sampleValues && sampleValues.length > 0) {
        const nonNullValues = sampleValues.filter(v => v !== null && v !== undefined && v !== '');
        if (nonNullValues.length > 0) {
            // 检查是否全为数字
            const allNumeric = nonNullValues.every(v => {
                if (typeof v === 'number') return true;
                if (typeof v === 'string') {
                    const num = Number(v);
                    return !isNaN(num) && isFinite(num);
                }
                return false;
            });
            if (allNumeric) return 'numeric';

            // 检查是否为时间格式
            const allDatetime = nonNullValues.every(v => {
                if (typeof v === 'string') {
                    // 常见日期格式检查
                    return /^\d{4}-\d{2}-\d{2}/.test(v) || /^\d{2}\/\d{2}\/\d{4}/.test(v);
                }
                return false;
            });
            if (allDatetime) return 'datetime';

            // 检查唯一值数量判断是否为分类
            const uniqueValues = new Set(nonNullValues.map(v => String(v)));
            if (uniqueValues.size <= 20) {
                return 'category';
            }
        }
    }

    // 默认为分类类型
    return 'category';
}

/**
 * 获取字段的数据类型映射
 */
export function getFieldTypes(
    fieldInfo: FieldInfo[],
    items: any[],
): Map<string, FieldDataType> {
    const typeMap = new Map<string, FieldDataType>();
    const sampleSize = Math.min(items.length, 100);
    const sampleItems = items.slice(0, sampleSize);

    for (const field of fieldInfo) {
        const sampleValues = sampleItems.map(item => item[field.alias]);
        typeMap.set(field.alias, identifyFieldType(field, sampleValues));
    }

    return typeMap;
}

/**
 * 获取数值类型字段
 */
export function getNumericFields(fieldInfo: FieldInfo[], items: any[]): FieldInfo[] {
    const typeMap = getFieldTypes(fieldInfo, items);
    return fieldInfo.filter(f => typeMap.get(f.alias) === 'numeric');
}

/**
 * 获取分类类型字段
 */
export function getCategoryFields(fieldInfo: FieldInfo[], items: any[]): FieldInfo[] {
    const typeMap = getFieldTypes(fieldInfo, items);
    return fieldInfo.filter(f => typeMap.get(f.alias) === 'category' || typeMap.get(f.alias) === 'datetime');
}

/**
 * 智能推荐图表类型
 */
export function recommendChartType(
    xAxisField: FieldInfo | undefined,
    yAxisFields: FieldInfo[],
    fieldTypeMap: Map<string, FieldDataType>,
): ChartType[] {
    const recommendations: ChartType[] = [];

    if (!xAxisField || yAxisFields.length === 0) {
        return ['bar'];
    }

    const xType = fieldTypeMap.get(xAxisField.alias);

    // 时间 + 数值 => 折线图优先
    if (xType === 'datetime') {
        recommendations.push('line', 'bar');
    }
    // 分类 + 数值 => 柱状图/饼图优先
    else if (xType === 'category') {
        recommendations.push('bar', 'pie', 'line', 'horizontalBar');
    }
    // 数值 + 数值 => 散点图
    else if (xType === 'numeric' && yAxisFields.length === 1) {
        recommendations.push('scatter', 'line');
    }

    // 如果没有推荐，默认柱状图
    if (recommendations.length === 0) {
        recommendations.push('bar', 'line', 'pie');
    }

    return recommendations;
}

/**
 * 生成组合分组键
 * @param item - 数据项
 * @param categoryFields - 分组字段数组
 * @param separator - 分隔符
 */
function getCombinedCategoryKey(item: any, categoryFields: string[], separator = ' - '): string {
    return categoryFields
        .map(field => String(item[field] ?? '(空)'))
        .join(separator);
}

/**
 * 聚合数据（支持多字段组合分组）
 */
function aggregateData(
    items: any[],
    categoryFields: string[],  // 改为数组，支持多字段组合
    valueField: string,
    aggregation: AggregationType,
): Map<string, number> {
    const groupedData = new Map<string, number[]>();

    for (const item of items) {
        const category = getCombinedCategoryKey(item, categoryFields);
        const value = Number(item[valueField]) || 0;

        if (!groupedData.has(category)) {
            groupedData.set(category, []);
        }
        groupedData.get(category)!.push(value);
    }

    const result = new Map<string, number>();

    for (const [category, values] of groupedData) {
        let aggregatedValue = 0;
        switch (aggregation) {
            case 'sum':
                aggregatedValue = values.reduce((a, b) => a + b, 0);
                break;
            case 'avg':
                aggregatedValue = values.reduce((a, b) => a + b, 0) / values.length;
                break;
            case 'count':
                aggregatedValue = values.length;
                break;
            case 'max':
                aggregatedValue = Math.max(...values);
                break;
            case 'min':
                aggregatedValue = Math.min(...values);
                break;
            case 'none':
            default:
                aggregatedValue = values[0] || 0;
                break;
        }
        result.set(category, aggregatedValue);
    }

    return result;
}

/**
 * 获取字段显示名称
 */
export function getFieldDisplayName(field: FieldInfo): string {
    return field.field_comment || field.original_field;
}

/**
 * 获取 X 轴标签（多字段组合）
 */
function getXAxisLabel(xAxisFields: string[], fieldInfo: FieldInfo[], options: ChartConfig['chartOptions']): string {
    if (options.xAxisLabel) return options.xAxisLabel;
    const fieldMap = new Map(fieldInfo.map(f => [f.alias, f]));
    return xAxisFields
        .map(f => {
            const field = fieldMap.get(f);
            return field ? getFieldDisplayName(field) : f;
        })
        .join(' + ');
}

/**
 * 转换数据为柱状图格式
 */
function transformToBarChart(
    items: any[],
    xAxisFields: string[],  // 改为数组
    yAxisFields: string[],
    fieldInfo: FieldInfo[],
    aggregation: AggregationType,
    options: ChartConfig['chartOptions'],
): EChartsOption {
    const fieldMap = new Map(fieldInfo.map(f => [f.alias, f]));

    // 如果需要聚合
    if (aggregation !== 'none') {
        const categories: string[] = [];
        const seriesData: Map<string, number[]> = new Map();

        for (const yField of yAxisFields) {
            const aggregated = aggregateData(items, xAxisFields, yField, aggregation);
            seriesData.set(yField, []);

            for (const [category] of aggregated) {
                if (!categories.includes(category)) {
                    categories.push(category);
                }
            }

            for (const category of categories) {
                seriesData.get(yField)!.push(aggregated.get(category) || 0);
            }
        }

        const series = yAxisFields.map(yField => {
            const field = fieldMap.get(yField);
            return {
                name: field ? getFieldDisplayName(field) : yField,
                type: 'bar' as const,
                data: seriesData.get(yField) || [],
            };
        });

        return {
            title: options.title ? { text: options.title, left: 'center' } : undefined,
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' },
            },
            legend: options.showLegend !== false ? { top: 30 } : undefined,
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                containLabel: true,
            },
            xAxis: {
                type: 'category',
                data: categories,
                name: getXAxisLabel(xAxisFields, fieldInfo, options),
                axisLabel: {
                    rotate: options.labelRotate || 0,
                },
            },
            yAxis: {
                type: 'value',
                name: options.yAxisLabel || '',
            },
            series,
        };
    }

    // 不聚合，直接使用原始数据（多字段组合）
    const categories = items.map(item => getCombinedCategoryKey(item, xAxisFields));
    const series = yAxisFields.map(yField => {
        const field = fieldMap.get(yField);
        return {
            name: field ? getFieldDisplayName(field) : yField,
            type: 'bar' as const,
            data: items.map(item => Number(item[yField]) || 0),
        };
    });

    return {
        title: options.title ? { text: options.title, left: 'center' } : undefined,
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
        },
        legend: options.showLegend !== false ? { top: 30 } : undefined,
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true,
        },
        xAxis: {
            type: 'category',
            data: categories,
            name: getXAxisLabel(xAxisFields, fieldInfo, options),
            axisLabel: {
                rotate: options.labelRotate || 0,
            },
        },
        yAxis: {
            type: 'value',
            name: options.yAxisLabel || '',
        },
        series,
    };
}

/**
 * 转换数据为折线图格式
 */
function transformToLineChart(
    items: any[],
    xAxisFields: string[],  // 改为数组
    yAxisFields: string[],
    fieldInfo: FieldInfo[],
    aggregation: AggregationType,
    options: ChartConfig['chartOptions'],
): EChartsOption {
    const barOption = transformToBarChart(items, xAxisFields, yAxisFields, fieldInfo, aggregation, options);

    // 修改 series 类型为 line
    if (barOption.series && Array.isArray(barOption.series)) {
        barOption.series = barOption.series.map((s: any) => ({
            ...s,
            type: 'line',
            smooth: true,
        }));
    }

    return barOption;
}

/**
 * 转换数据为条形图格式（横向柱状图）
 */
function transformToHorizontalBarChart(
    items: any[],
    xAxisFields: string[],  // 改为数组
    yAxisFields: string[],
    fieldInfo: FieldInfo[],
    aggregation: AggregationType,
    options: ChartConfig['chartOptions'],
): EChartsOption {
    const barOption = transformToBarChart(items, xAxisFields, yAxisFields, fieldInfo, aggregation, options);

    // 交换 X 和 Y 轴
    const temp = barOption.xAxis;
    barOption.xAxis = {
        type: 'value',
        name: options.yAxisLabel || '',
    };
    barOption.yAxis = {
        ...temp,
        type: 'category',
    };

    return barOption;
}

/**
 * 转换数据为饼图格式
 */
function transformToPieChart(
    items: any[],
    xAxisFields: string[],  // 改为数组
    yAxisFields: string[],
    fieldInfo: FieldInfo[],
    aggregation: AggregationType,
    options: ChartConfig['chartOptions'],
): EChartsOption {
    const fieldMap = new Map(fieldInfo.map(f => [f.alias, f]));

    // 饼图只使用第一个 Y 轴字段
    const yField = yAxisFields[0];
    if (!yField) {
        return { series: [] };
    }

    // 聚合数据（使用多字段组合分组）
    const aggregated = aggregateData(items, xAxisFields, yField, aggregation !== 'none' ? aggregation : 'sum');

    const data = Array.from(aggregated.entries()).map(([name, value]) => ({
        name,
        value,
    }));

    const yFieldInfo = fieldMap.get(yField);

    return {
        title: options.title ? { text: options.title, left: 'center' } : undefined,
        tooltip: {
            trigger: 'item',
            formatter: '{b}: {c} ({d}%)',
        },
        legend: options.showLegend !== false ? {
            orient: 'vertical',
            left: 'left',
            top: 'middle',
        } : undefined,
        series: [
            {
                name: yFieldInfo ? getFieldDisplayName(yFieldInfo) : yField,
                type: 'pie',
                radius: ['40%', '70%'],
                avoidLabelOverlap: true,
                itemStyle: {
                    borderRadius: 10,
                    borderColor: '#fff',
                    borderWidth: 2,
                },
                label: {
                    show: true,
                    formatter: '{b}: {d}%',
                },
                data,
            },
        ],
    };
}

/**
 * 转换数据为散点图格式
 */
function transformToScatterChart(
    items: any[],
    xAxisFields: string[],  // 改为数组
    yAxisFields: string[],
    fieldInfo: FieldInfo[],
    options: ChartConfig['chartOptions'],
): EChartsOption {
    const fieldMap = new Map(fieldInfo.map(f => [f.alias, f]));

    // 散点图：使用第一个 X 轴字段作为数值坐标
    const xAxisField = xAxisFields[0] || '';

    // 散点图使用 X 轴和 Y 轴字段作为坐标
    const series = yAxisFields.map(yField => {
        const field = fieldMap.get(yField);
        return {
            name: field ? getFieldDisplayName(field) : yField,
            type: 'scatter' as const,
            data: items.map(item => [
                Number(item[xAxisField]) || 0,
                Number(item[yField]) || 0,
            ]),
        };
    });

    return {
        title: options.title ? { text: options.title, left: 'center' } : undefined,
        tooltip: {
            trigger: 'item',
            formatter: (params: any) => {
                return `${params.seriesName}<br/>X: ${params.value[0]}<br/>Y: ${params.value[1]}`;
            },
        },
        legend: options.showLegend !== false ? { top: 30 } : undefined,
        grid: {
            left: '3%',
            right: '4%',
            bottom: '3%',
            containLabel: true,
        },
        xAxis: {
            type: 'value',
            name: getXAxisLabel(xAxisFields, fieldInfo, options),
        },
        yAxis: {
            type: 'value',
            name: options.yAxisLabel || '',
        },
        series,
    };
}

/**
 * 采样数据（当数据量超过限制时）
 */
export function sampleData<T>(items: T[], maxPoints: number = MAX_DATA_POINTS): T[] {
    if (items.length <= maxPoints) {
        return items;
    }

    const step = Math.ceil(items.length / maxPoints);
    const sampled: T[] = [];

    for (let i = 0; i < items.length; i += step) {
        sampled.push(items[i]!);
    }

    return sampled;
}

/**
 * 主转换函数：将表格数据转换为 ECharts 格式
 */
export function transformToChartData(
    items: any[],
    fieldInfo: FieldInfo[],
    chartType: ChartType,
    xAxisFields: string[],  // 改为数组，支持多字段组合
    yAxisFields: string[],
    aggregation: AggregationType = 'none',
    options: ChartConfig['chartOptions'] = {},
): EChartsOption {
    if (!items || items.length === 0 || !xAxisFields || xAxisFields.length === 0 || yAxisFields.length === 0) {
        return {
            title: { text: '暂无数据', left: 'center', top: 'center' },
        };
    }

    // 采样数据
    const sampledItems = sampleData(items);

    switch (chartType) {
        case 'bar':
            return transformToBarChart(sampledItems, xAxisFields, yAxisFields, fieldInfo, aggregation, options);
        case 'line':
            return transformToLineChart(sampledItems, xAxisFields, yAxisFields, fieldInfo, aggregation, options);
        case 'horizontalBar':
            return transformToHorizontalBarChart(sampledItems, xAxisFields, yAxisFields, fieldInfo, aggregation, options);
        case 'pie':
            return transformToPieChart(sampledItems, xAxisFields, yAxisFields, fieldInfo, aggregation, options);
        case 'scatter':
            return transformToScatterChart(sampledItems, xAxisFields, yAxisFields, fieldInfo, options);
        default:
            return transformToBarChart(sampledItems, xAxisFields, yAxisFields, fieldInfo, aggregation, options);
    }
}

/**
 * 检查数据量是否超过限制
 */
export function isDataOverLimit(items: any[]): boolean {
    return items.length > MAX_DATA_POINTS;
}

/**
 * 获取图表类型显示名称
 */
export function getChartTypeLabel(type: ChartType): string {
    const labels: Record<ChartType, string> = {
        bar: '柱状图',
        line: '折线图',
        pie: '饼图',
        scatter: '散点图',
        horizontalBar: '条形图',
    };
    return labels[type] || type;
}

/**
 * 获取聚合方式显示名称
 */
export function getAggregationLabel(type: AggregationType): string {
    const labels: Record<AggregationType, string> = {
        sum: '求和',
        avg: '平均值',
        count: '计数',
        max: '最大值',
        min: '最小值',
        none: '不聚合',
    };
    return labels[type] || type;
}

// ============ 图表配置存储 ============

/**
 * 加载图表配置列表
 */
export function loadChartConfigs(): ChartConfig[] {
    try {
        const data = localStorage.getItem(CHART_CONFIG_STORAGE_KEY);
        if (data) {
            return JSON.parse(data);
        }
    } catch (e) {
        console.error('加载图表配置失败:', e);
    }
    return [];
}

/**
 * 保存图表配置
 */
export function saveChartConfig(config: ChartConfig): void {
    const configs = loadChartConfigs();
    const existingIndex = configs.findIndex(c => c.id === config.id);

    if (existingIndex >= 0) {
        configs[existingIndex] = config;
    } else {
        configs.push(config);
    }

    localStorage.setItem(CHART_CONFIG_STORAGE_KEY, JSON.stringify(configs));
}

/**
 * 删除图表配置
 */
export function deleteChartConfig(configId: string): void {
    const configs = loadChartConfigs().filter(c => c.id !== configId);
    localStorage.setItem(CHART_CONFIG_STORAGE_KEY, JSON.stringify(configs));
}

/**
 * 生成唯一 ID
 */
export function generateChartConfigId(): string {
    return `chart-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}
