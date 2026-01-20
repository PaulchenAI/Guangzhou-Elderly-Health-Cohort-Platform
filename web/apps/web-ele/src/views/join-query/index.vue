<script lang="ts" setup>
import type {
    FieldInfo,
    FilterCondition,
    JoinPreviewResponse,
    JoinQueryResult,
    ManualJoin,
    TableQueryConfig,
} from '#/api/core/table-query';

import { computed, onMounted, ref, watch } from 'vue';

import { Page } from '@vben/common-ui';
import { Download, Search, Settings } from '@vben/icons';

import {
    ElButton,
    ElCard,
    ElCollapse,
    ElCollapseItem,
    ElDropdown,
    ElDropdownItem,
    ElDropdownMenu,
    ElEmpty,
    ElInput,
    ElOption,
    ElSelect,
    ElLoading,
    ElMessage,
    ElMessageBox,
} from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
    executeJoinQueryApi,
    exportJoinDataApi,
    getAllTableQueryConfigsApi,
    getJoinPreviewApi,
} from '#/api/core/table-query';

import ColumnSelector from './components/ColumnSelector.vue';
import ConfigManager from './components/ConfigManager.vue';
import RelationTree from './components/RelationTree.vue';
import TableSelector from './components/TableSelector.vue';
import {
    buildJoinColumns,
    expandJsonFields,
    isJsonField,
    loadColumnPreferences,
    saveColumnPreferences,
} from './data';

defineOptions({ name: 'JoinQuery' });

// 表配置列表
const configs = ref<TableQueryConfig[]>([]);
const loading = ref(false);

// 表名到中文名称的映射
const tableDisplayNames = computed(() => {
    const map = new Map<string, string>();
    for (const config of configs.value) {
        map.set(config.table_name, config.display_name);
    }
    return map;
});

// 主表选择
const primaryTable = ref<string>('');
const primaryTableConfig = computed(() =>
    configs.value.find((c) => c.table_name === primaryTable.value),
);

// 关联关系
const relations = ref<JoinPreviewResponse | null>(null);
const loadingRelations = ref(false);

// 关联表选择
const selectedTables = ref<string[]>([]);
const maxDepth = ref(2);

// 查询结果
const queryResult = ref<JoinQueryResult | null>(null);
const loadingData = ref(false);
const fieldInfo = ref<FieldInfo[]>([]);
const expandedFieldInfo = ref<FieldInfo[]>([]);
const expandedItems = ref<any[]>([]);

// 手动关联
type ManualJoinDraft = ManualJoin & { id: string };
const manualJoins = ref<ManualJoinDraft[]>([]);
const manualJoinTargets = ref<Record<string, FieldInfo[]>>({});
const loadingManualTargets = ref<Record<string, boolean>>({});

// 列选择器
const columnSelectorVisible = ref(false);
const visibleColumns = ref<string[]>([]);

// 关联配置折叠状态
const relationCollapseActive = ref<string[]>(['relation']);

// 搜索表单
const searchForm = ref<Record<string, any>>({});

// 动态列配置（使用展开后的字段信息）
const columns = computed(() => {
    // 使用展开后的字段信息，如果没有则使用原始字段信息
    const fieldsToUse = expandedFieldInfo.value.length > 0 ? expandedFieldInfo.value : fieldInfo.value;
    const result = buildJoinColumns(
        fieldsToUse,
        visibleColumns.value.length > 0 ? visibleColumns.value : undefined,
    );
    return result;
});

const resolvedPrimaryTable = computed(
    () => relations.value?.primary_table || primaryTable.value,
);

const primaryTableFields = computed(() => {
    if (!relations.value?.all_fields) {
        return [];
    }
    const fields = relations.value.all_fields.filter(
        (field) => field.original_table === resolvedPrimaryTable.value,
    );
    // 如果字段没有 field_comment，尝试从表配置中获取
    const tableConfig = configs.value.find(c => c.table_name === resolvedPrimaryTable.value);
    if (tableConfig?.config_json?.fields) {
        const fieldConfigMap = new Map(
            tableConfig.config_json.fields.map((f: { name: string; displayName: string }) => [
                f.name,
                f.displayName,
            ]),
        );
        return fields.map(field => ({
            ...field,
            field_comment: field.field_comment || fieldConfigMap.get(field.original_field) || '',
        }));
    }

    return fields;
});

const manualJoinOptions = computed(() => {
    const options: Array<{ value: string; label: string }> = [];

    // 添加数据表
    for (const config of configs.value) {
        options.push({
            value: config.table_name,
            label: config.display_name
                ? `${config.display_name} (${config.table_name})`
                : config.table_name,
        });
    }


    return options;
});

// 使用 VxeGrid
const [Grid, gridApi] = useVbenVxeGrid({
    gridOptions: {
        columns: columns.value,
        height: 'auto',
        keepSource: true,
        proxyConfig: {
            autoLoad: false,
            ajax: {
                query: async ({ page }: { page: { currentPage: number; pageSize: number } }) => {
                    if (!primaryTable.value) {
                        return { items: [], total: 0 };
                    }

                    // 构建过滤条件
                    const filters: FilterCondition[] = [];
                    for (const [field, value] of Object.entries(searchForm.value)) {
                        if (value !== undefined && value !== null && value !== '') {
                            filters.push({
                                field,
                                operator: 'like',
                                value,
                            });
                        }
                    }

                    const result = await executeJoinQueryApi({
                        primary_table: primaryTable.value,
                        max_depth: maxDepth.value,
                        include_tables:
                            selectedTables.value.length > 0
                                ? selectedTables.value
                                : undefined,
                        manual_joins: buildManualJoinParams(),
                        page: page.currentPage,
                        page_size: page.pageSize,
                        filters: filters.length > 0 ? filters : undefined,
                    });

                    // 更新字段信息和结果
                    queryResult.value = result;
                    fieldInfo.value = result.field_info || [];

                    // 展开 JSON 字段
                    let finalResult = result;
                    if (result.items && result.items.length > 0) {
                        const { expandedFieldInfo: expanded, expandedItems: expandedData } = expandJsonFields(
                            fieldInfo.value,
                            result.items,
                        );
                        expandedFieldInfo.value = expanded;
                        expandedItems.value = expandedData;

                        // 处理可见列：如果有展开的新字段
                        if (expanded.length > fieldInfo.value.length) {
                            const newFields = expanded.slice(fieldInfo.value.length);
                            const jsonFields = fieldInfo.value.filter(f => isJsonField(f.original_field, f.field_type));

                            // 如果 visibleColumns 为空，显示所有字段（包括展开的）
                            if (visibleColumns.value.length === 0) {
                                // 不设置 visibleColumns，让所有字段都显示
                            } else {
                                // 如果 visibleColumns 包含原始 JSON 字段，自动包含其展开字段
                                const jsonFieldAliases = new Set(jsonFields.map(f => f.alias));
                                const shouldAutoInclude = Array.from(jsonFieldAliases).some(alias =>
                                    visibleColumns.value.includes(alias)
                                );

                                if (shouldAutoInclude) {
                                    // 找到所有被选中的 JSON 字段，添加它们的展开字段
                                    for (const jsonField of jsonFields) {
                                        if (visibleColumns.value.includes(jsonField.alias)) {
                                            // 添加这个 JSON 字段的所有展开字段
                                            const expandedFieldsForThisJson = newFields.filter(f =>
                                                f.alias.startsWith(`${jsonField.alias}_`)
                                            );
                                            for (const expandedField of expandedFieldsForThisJson) {
                                                if (!visibleColumns.value.includes(expandedField.alias)) {
                                                    visibleColumns.value.push(expandedField.alias);
                                                }
                                            }
                                        }
                                    }
                                    // 保存更新后的列偏好
                                    saveColumnPreferences(primaryTable.value, visibleColumns.value);
                                } else {
                                    // 如果没有选中 JSON 字段，但用户可能想看到展开字段
                                    // 可以选择自动添加所有展开字段，或者保持原样
                                    // 这里我们选择自动添加所有展开字段
                                    const newFieldAliases = newFields.map(f => f.alias);
                                    for (const alias of newFieldAliases) {
                                        if (!visibleColumns.value.includes(alias)) {
                                            visibleColumns.value.push(alias);
                                        }
                                    }
                                    saveColumnPreferences(primaryTable.value, visibleColumns.value);
                                }
                            }
                        }

                        // 更新返回的数据，使用展开后的数据
                        finalResult = {
                            ...result,
                            items: expandedData,
                        };
                    } else {
                        expandedFieldInfo.value = fieldInfo.value;
                        expandedItems.value = result.items || [];
                    }

                    return finalResult;
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
            zoom: true,
        },
    },
});

/**
 * 加载表配置列表
 */
async function fetchConfigs() {
    try {
        loading.value = true;
        const tableConfigs = await getAllTableQueryConfigsApi(true);
        configs.value = tableConfigs;
    } catch (error) {
        console.error('加载配置列表失败:', error);
        ElMessage.error('加载配置列表失败');
    } finally {
        loading.value = false;
    }
}

/**
 * 加载关联关系
 */
async function fetchRelations() {
    if (!primaryTable.value) {
        relations.value = null;
        return;
    }

    try {
        loadingRelations.value = true;
        relations.value = await getJoinPreviewApi(primaryTable.value, maxDepth.value);

        // 加载列偏好
        const savedColumns = loadColumnPreferences(primaryTable.value);
        if (savedColumns) {
            visibleColumns.value = savedColumns;
        } else {
            visibleColumns.value = [];
        }
    } catch (error) {
        console.error('加载关联关系失败:', error);
        ElMessage.error('加载关联关系失败');
        relations.value = null;
    } finally {
        loadingRelations.value = false;
    }
}

async function loadManualTargetFields(tableName: string) {
    if (!tableName || manualJoinTargets.value[tableName]) {
        return;
    }

    try {
        loadingManualTargets.value = {
            ...loadingManualTargets.value,
            [tableName]: true,
        };
        const preview = await getJoinPreviewApi(tableName, 1);
        let fields = preview.all_fields.filter(
            (field) => field.original_table === preview.primary_table,
        );

        // 如果字段没有 field_comment，尝试从表配置中获取
        const tableConfig = configs.value.find(c => c.table_name === tableName);
        if (tableConfig?.config_json?.fields) {
            const fieldConfigMap = new Map(
                tableConfig.config_json.fields.map((f: { name: string; displayName: string }) => [
                    f.name,
                    f.displayName,
                ]),
            );
            fields = fields.map(field => ({
                ...field,
                field_comment: field.field_comment || fieldConfigMap.get(field.original_field) || '',
            }));
        }

        manualJoinTargets.value = {
            ...manualJoinTargets.value,
            [tableName]: fields,
        };
    } catch (error) {
        console.error('加载手动关联字段失败:', error);
        ElMessage.error('加载手动关联字段失败');
    } finally {
        loadingManualTargets.value = {
            ...loadingManualTargets.value,
            [tableName]: false,
        };
    }
}

function addManualJoin() {
    if (!primaryTable.value) {
        ElMessage.warning('请先选择主表');
        return;
    }
    manualJoins.value.push({
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
        source_field: '',
        target_table: '',
        target_field: '',
        match_type: 'exact',
    });
}

function removeManualJoin(index: number) {
    manualJoins.value.splice(index, 1);
}

function formatFieldLabel(field: FieldInfo) {
    return field.field_comment
        ? `${field.field_comment}/${field.original_field}`
        : field.original_field;
}

function buildManualJoinParams() {
    const params = manualJoins.value
        .filter((item) => item.source_field && item.target_table && item.target_field)
        .map((item) => ({
            source_field: item.source_field,
            target_table: item.target_table,
            target_field: item.target_field,
            match_type: item.match_type || 'exact',
        }));
    return params.length > 0 ? params : undefined;
}

/**
 * 处理主表变化
 */
function handlePrimaryTableChange(tableName: string) {
    primaryTable.value = tableName;
    selectedTables.value = [];
    searchForm.value = {};
    queryResult.value = null;
    fieldInfo.value = [];
    manualJoins.value = [];
    manualJoinTargets.value = {};
}

/**
 * 执行查询
 */
async function handleQuery() {
    if (!primaryTable.value) {
        ElMessage.warning('请先选择主表');
        return;
    }

    try {
        loadingData.value = true;
        await gridApi.query();
    } catch (error: any) {
        console.error('查询失败:', error);
        // 检测是否是超时错误
        const isTimeout = error?.message?.includes?.('timeout') ||
            error?.message?.includes?.('超时') ||
            error?.code === 'ECONNABORTED';

        if (isTimeout) {
            // 超时错误显示弹窗提示
            await ElMessageBox.alert(
                '查询请求超时，可能是数据量过大导致处理时间较长。建议：\n1. 添加更多过滤条件缩小查询范围\n2. 减少关联表的数量\n3. 降低查询深度',
                '请求超时',
                {
                    type: 'warning',
                    confirmButtonText: '我知道了',
                },
            );
        } else {
            ElMessage.error('查询失败');
        }
    } finally {
        loadingData.value = false;
    }
}

/**
 * 重置搜索
 */
function handleReset() {
    searchForm.value = {};
    handleQuery();
}

// 导出数据量上限
const EXPORT_MAX_ROWS = 100000;

/**
 * 导出数据
 */
async function handleExport(format: 'csv' | 'excel') {
    if (!primaryTable.value) {
        ElMessage.warning('请先选择主表并执行查询');
        return;
    }

    // 检查数据量是否超过上限
    if (queryResult.value && queryResult.value.total > EXPORT_MAX_ROWS) {
        ElMessage.warning(
            `数据量过大（${queryResult.value.total} 条），超过导出上限 ${EXPORT_MAX_ROWS} 条。请添加过滤条件缩小范围后再导出。`,
        );
        return;
    }


    // 显示加载弹窗
    const loadingInstance = ElLoading.service({
        lock: true,
        text: '正在导出数据，请稍候...',
        background: 'rgba(0, 0, 0, 0.7)',
    });

    try {
        // 构建过滤条件
        const filters: FilterCondition[] = [];
        for (const [field, value] of Object.entries(searchForm.value)) {
            if (value !== undefined && value !== null && value !== '') {
                filters.push({
                    field,
                    operator: 'like',
                    value,
                });
            }
        }

        const response = await exportJoinDataApi({
            primary_table: primaryTable.value,
            max_depth: maxDepth.value,
            include_tables:
                selectedTables.value.length > 0 ? selectedTables.value : undefined,
            format,
            filters: filters.length > 0 ? filters : undefined,
        });

        // 创建下载链接
        const blob = new Blob([response as any], {
            type:
                format === 'excel'
                    ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    : 'text/csv',
        });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        const timestamp = new Date().toISOString().slice(0, 10);
        link.download = `${primaryTable.value}_联合查询_${timestamp}.${format === 'excel' ? 'xlsx' : 'csv'}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);


        ElMessage.success('导出成功');
    } catch (error: any) {
        console.error('导出失败:', error);

        // 检测是否是超时错误
        const isTimeout = error?.message?.includes?.('timeout') ||
            error?.message?.includes?.('超时') ||
            error?.code === 'ECONNABORTED';

        if (isTimeout) {
            // 超时错误显示弹窗提示
            await ElMessageBox.alert(
                '导出请求超时，可能是数据量过大导致处理时间较长。建议：\n1. 添加更多过滤条件缩小导出范围\n2. 减少关联表的数量\n3. 降低查询深度\n4. 分批导出数据',
                '导出超时',
                {
                    type: 'warning',
                    confirmButtonText: '我知道了',
                },
            );
        } else {
            ElMessage.error('导出失败');
        }
    } finally {
        // 关闭加载弹窗
        loadingInstance.close();
    }
}

/**
 * 处理列选择变化
 */
function handleColumnChange(columns: string[]) {
    visibleColumns.value = columns;
    saveColumnPreferences(primaryTable.value, columns);

    // 更新表格列
    const newColumns = buildJoinColumns(fieldInfo.value, columns.length > 0 ? columns : undefined);
    gridApi.setGridOptions({ columns: newColumns });
}

/**
 * 处理关联深度变化
 */
function handleDepthChange(depth: number) {
    maxDepth.value = depth;
    fetchRelations();
}

/**
 * 处理加载配置
 */
function handleLoadConfig(config: {
    primaryTable: string;
    includeTables: string[];
    maxDepth: number;
    visibleColumns?: string[];
    manualJoins?: ManualJoin[];
}) {
    primaryTable.value = config.primaryTable;
    selectedTables.value = config.includeTables;
    maxDepth.value = config.maxDepth;
    manualJoins.value = (config.manualJoins || []).map((item) => ({
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
        source_field: item.source_field,
        target_table: item.target_table,
        target_field: item.target_field,
        match_type: item.match_type || 'exact',
    }));
    manualJoins.value.forEach((item) => {
        if (item.target_table) {
            loadManualTargetFields(item.target_table);
        }
    });

    if (config.visibleColumns) {
        visibleColumns.value = config.visibleColumns;
    }

    // 加载关联关系并执行查询
    fetchRelations().then(() => {
        handleQuery();
    });
}

// 监听主表变化
watch(primaryTable, () => {
    fetchRelations();
    manualJoins.value = [];
    manualJoinTargets.value = {};
});

// 监听列配置变化，更新表格
watch(columns, (newColumns) => {
    gridApi.setGridOptions({ columns: newColumns });
});

onMounted(() => {
    fetchConfigs();
});
</script>

<template>
    <Page auto-content-height>
        <div class="flex h-full gap-4">
            <!-- 左侧：主表选择 -->
            <div class="w-64 flex-shrink-0">
                <TableSelector :configs="configs" :loading="loading" :selected="primaryTable"
                    @select="handlePrimaryTableChange" />
            </div>

            <!-- 右侧：数据展示区域 -->
            <div class="flex flex-1 flex-col overflow-hidden">
                <ElCard shadow="never" class="flex h-full flex-col" :body-style="{
                    padding: '12px',
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    overflow: 'hidden',
                }">
                    <!-- 工具栏 -->
                    <div class="mb-3 flex items-center justify-between">
                        <div>
                            <h3 class="text-lg font-medium">
                                {{ primaryTableConfig?.display_name || '联合查询' }}
                            </h3>
                            <p v-if="queryResult" class="text-sm text-gray-500">
                                关联了 {{ queryResult.join_info?.joined_tables?.length || 0 }} 个表，
                                共 {{ queryResult.total }} 条数据
                            </p>
                        </div>
                        <div class="flex gap-2">
                            <!-- 配置管理 -->
                            <ConfigManager :max-depth="maxDepth" :primary-table="primaryTable"
                                :selected-tables="selectedTables" :visible-columns="visibleColumns"
                                :manual-joins="manualJoins" @load="handleLoadConfig" />

                            <!-- 列设置 -->
                            <ElButton :icon="Settings" :disabled="fieldInfo.length === 0"
                                @click="columnSelectorVisible = true">
                                列设置
                            </ElButton>

                            <!-- 导出 -->
                            <ElDropdown :disabled="!queryResult" @command="handleExport">
                                <ElButton type="primary" :icon="Download" :disabled="!queryResult">
                                    导出数据
                                </ElButton>
                                <template #dropdown>
                                    <ElDropdownMenu>
                                        <ElDropdownItem command="excel">导出 Excel</ElDropdownItem>
                                        <ElDropdownItem command="csv">导出 CSV</ElDropdownItem>
                                    </ElDropdownMenu>
                                </template>
                            </ElDropdown>
                        </div>
                    </div>

                    <!-- 关联配置（可折叠） -->
                    <ElCollapse v-if="primaryTable" v-model="relationCollapseActive" class="mb-3">
                        <ElCollapseItem name="relation">
                            <template #title>
                                <span class="font-medium">关联配置</span>
                                <span v-if="selectedTables.length > 0" class="ml-2 text-sm text-gray-500">
                                    (已选 {{ selectedTables.length }} 个关联表)
                                </span>
                            </template>
                            <div class="relation-config-content">
                                <RelationTree :loading="loadingRelations" :max-depth="maxDepth" :relations="relations"
                                    :selected-tables="selectedTables" :table-display-names="tableDisplayNames"
                                    @depth-change="handleDepthChange" @update:selected-tables="selectedTables = $event"
                                    :embedded="true" />
                            </div>
                            <div class="mt-4 rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
                                <div class="mb-2 flex items-center justify-between">
                                    <span class="text-sm font-medium">手动关联</span>
                                    <ElButton size="small" @click="addManualJoin">添加关联</ElButton>
                                </div>
                                <div v-if="manualJoins.length === 0" class="text-xs text-gray-500">
                                    暂无手动关联，支持选择主表字段与目标表字段进行匹配关联。
                                </div>
                                <div v-else class="space-y-2">
                                    <div v-for="(item, index) in manualJoins" :key="item.id"
                                        class="flex flex-wrap items-center gap-2 rounded-md bg-white p-2 dark:bg-gray-900">
                                        <ElSelect v-model="item.source_field" filterable placeholder="主表字段"
                                            style="width: 180px">
                                            <ElOption v-for="field in primaryTableFields" :key="field.alias"
                                                :label="formatFieldLabel(field)" :value="field.original_field" />
                                        </ElSelect>
                                        <ElSelect v-model="item.target_table" filterable allow-create placeholder="目标表"
                                            style="width: 200px"
                                            @change="(value: string) => { item.target_field = ''; loadManualTargetFields(value); }">
                                            <ElOption v-for="option in manualJoinOptions" :key="option.value"
                                                :label="option.label" :value="option.value" />
                                        </ElSelect>
                                        <ElSelect v-model="item.target_field" filterable allow-create placeholder="目标字段"
                                            style="width: 180px" :loading="loadingManualTargets[item.target_table]">
                                            <ElOption v-for="field in (manualJoinTargets[item.target_table] || [])"
                                                :key="field.alias" :label="formatFieldLabel(field)"
                                                :value="field.original_field" />
                                        </ElSelect>
                                        <ElSelect v-model="item.match_type" placeholder="匹配方式" style="width: 120px">
                                            <ElOption label="精确" value="exact" />
                                            <ElOption label="模糊" value="fuzzy" />
                                        </ElSelect>
                                        <ElButton type="danger" size="small" @click="removeManualJoin(index)">
                                            删除
                                        </ElButton>
                                    </div>
                                </div>
                            </div>
                        </ElCollapseItem>
                    </ElCollapse>

                    <!-- 搜索表单（仅在有字段时显示） -->
                    <div v-if="fieldInfo.length > 0"
                        class="mb-3 flex flex-wrap items-center gap-3 rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
                        <template v-for="field in fieldInfo.slice(0, 5)" :key="field.alias">
                            <div class="flex items-center gap-2">
                                <span class="text-sm text-gray-600 dark:text-gray-300">
                                    {{ field.field_comment || field.original_field }}:
                                </span>
                                <ElInput v-model="searchForm[field.alias]"
                                    :placeholder="`请输入${field.field_comment || field.original_field}`" clearable
                                    size="small" style="width: 150px" />
                            </div>
                        </template>
                        <div class="flex gap-2">
                            <ElButton type="primary" size="small" :icon="Search" @click="handleQuery">
                                查询
                            </ElButton>
                            <ElButton size="small" @click="handleReset">重置</ElButton>
                        </div>
                    </div>

                    <!-- 执行查询按钮（未查询时显示） -->
                    <div v-if="primaryTable && !queryResult" class="mb-3 flex justify-center">
                        <ElButton type="primary" size="large" :loading="loadingData" @click="handleQuery">
                            执行联合查询
                        </ElButton>
                    </div>

                    <!-- 数据表格 -->
                    <div class="flex-1 overflow-hidden">
                        <Grid v-if="primaryTable" />
                        <ElEmpty v-else description="请从左侧选择主表" :image-size="100" />
                    </div>
                </ElCard>
            </div>
        </div>

        <!-- 列选择器抽屉 -->
        <ColumnSelector v-model:visible="columnSelectorVisible" :field-info="fieldInfo"
            :visible-columns="visibleColumns" @update:visible-columns="handleColumnChange" />
    </Page>
</template>

<style scoped>
:deep(.vxe-grid) {
    height: 100% !important;
}

/* 关联配置折叠面板样式 */
:deep(.el-collapse) {
    border: none;
}

:deep(.el-collapse-item__header) {
    background-color: #f5f7fa;
    border-radius: 4px;
    padding: 0 12px;
}

:deep(.el-collapse-item__wrap) {
    border: none;
}

:deep(.el-collapse-item__content) {
    padding: 12px 0 0 0;
}

.relation-config-content {
    max-height: 200px;
    overflow-y: auto;
}

/* 暗色模式 */
.dark :deep(.el-collapse-item__header) {
    background-color: #374151;
}
</style>
