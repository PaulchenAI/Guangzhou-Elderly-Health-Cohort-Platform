<script lang="ts" setup>
/**
 * 列选择器组件（抽屉）
 */
import type { FieldInfo } from '#/api/core/table-query';

import { computed } from 'vue';

import {
    ElButton,
    ElCheckbox,
    ElCheckboxGroup,
    ElCollapse,
    ElCollapseItem,
    ElDrawer,
    ElEmpty,
} from 'element-plus';

import { groupFieldsByTable } from '../data';

const props = defineProps<{
    visible: boolean;
    fieldInfo: FieldInfo[];
    visibleColumns: string[];
}>();

const emit = defineEmits<{
    'update:visible': [visible: boolean];
    'update:visibleColumns': [columns: string[]];
}>();

// 按表分组的字段
const groupedFields = computed(() => {
    return groupFieldsByTable(props.fieldInfo);
});

// 表名列表
const tableNames = computed(() => {
    return Array.from(groupedFields.value.keys());
});

// 当前选中的列
const checkedColumns = computed({
    get: () => props.visibleColumns,
    set: (val) => emit('update:visibleColumns', val),
});

// 检查表是否全选
function isTableAllChecked(tableName: string): boolean {
    const fields = groupedFields.value.get(tableName) || [];
    return fields.every((f) => checkedColumns.value.includes(f.alias));
}

// 检查表是否部分选中
function isTableIndeterminate(tableName: string): boolean {
    const fields = groupedFields.value.get(tableName) || [];
    const checkedCount = fields.filter((f) =>
        checkedColumns.value.includes(f.alias),
    ).length;
    return checkedCount > 0 && checkedCount < fields.length;
}

// 切换表的全选状态
function toggleTableAll(tableName: string, checked: boolean) {
    const fields = groupedFields.value.get(tableName) || [];
    const fieldAliases = fields.map((f) => f.alias);

    if (checked) {
        // 添加该表所有字段
        const newColumns = [...checkedColumns.value];
        for (const alias of fieldAliases) {
            if (!newColumns.includes(alias)) {
                newColumns.push(alias);
            }
        }
        checkedColumns.value = newColumns;
    } else {
        // 移除该表所有字段
        checkedColumns.value = checkedColumns.value.filter(
            (col) => !fieldAliases.includes(col),
        );
    }
}

// 全选所有列
function selectAll() {
    checkedColumns.value = props.fieldInfo.map((f) => f.alias);
}

// 取消全选
function deselectAll() {
    checkedColumns.value = [];
}

// 关闭抽屉
function handleClose() {
    emit('update:visible', false);
}
</script>

<template>
    <ElDrawer :model-value="visible" title="列设置" direction="rtl" size="360px" @update:model-value="handleClose">
        <template #header>
            <div class="flex items-center justify-between">
                <span class="text-lg font-medium">列设置</span>
                <div class="flex gap-2">
                    <ElButton size="small" @click="selectAll">全选</ElButton>
                    <ElButton size="small" @click="deselectAll">取消全选</ElButton>
                </div>
            </div>
        </template>

        <div v-if="fieldInfo.length > 0" class="column-selector">
            <p class="mb-3 text-sm text-gray-500">
                已选择 {{ visibleColumns.length }} / {{ fieldInfo.length }} 列
            </p>

            <ElCollapse accordion>
                <ElCollapseItem v-for="tableName in tableNames" :key="tableName" :name="tableName">
                    <template #title>
                        <div class="flex items-center gap-2" @click.stop>
                            <ElCheckbox :model-value="isTableAllChecked(tableName)"
                                :indeterminate="isTableIndeterminate(tableName)"
                                @change="(val: boolean) => toggleTableAll(tableName, val)" />
                            <span class="font-medium">{{ tableName }}</span>
                            <span class="text-xs text-gray-400">
                                ({{ groupedFields.get(tableName)?.length || 0 }} 列)
                            </span>
                        </div>
                    </template>

                    <ElCheckboxGroup v-model="checkedColumns" class="flex flex-col gap-2 pl-6">
                        <ElCheckbox v-for="field in groupedFields.get(tableName)" :key="field.alias"
                            :value="field.alias" :label="field.alias">
                            <span class="text-sm">{{ field.original_field }}</span>
                            <span class="ml-1 text-xs text-gray-400">({{ field.field_type }})</span>
                        </ElCheckbox>
                    </ElCheckboxGroup>
                </ElCollapseItem>
            </ElCollapse>
        </div>

        <ElEmpty v-else description="暂无字段信息" :image-size="80">
            <template #description>
                <p class="text-sm text-gray-500">请先执行查询以获取字段信息</p>
            </template>
        </ElEmpty>
    </ElDrawer>
</template>

<style scoped>
.column-selector :deep(.el-collapse-item__header) {
    padding: 8px 0;
}

.column-selector :deep(.el-collapse-item__content) {
    padding-bottom: 12px;
}
</style>
