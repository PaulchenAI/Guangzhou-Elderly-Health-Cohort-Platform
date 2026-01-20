<script lang="ts" setup>
/**
 * 主表选择器组件
 */
import type { TableQueryConfig } from '#/api/core/table-query';

import { computed, ref } from 'vue';

import { Search } from '@vben/icons';

import {
    ElCard,
    ElEmpty,
    ElInput,
    ElMenu,
    ElMenuItem,
    ElSkeleton,
    ElSkeletonItem,
} from 'element-plus';

interface TableOption {
    table_name: string;
    display_name: string;
}

const props = defineProps<{
    configs: TableQueryConfig[];
    loading: boolean;
    selected: string;
}>();

const emit = defineEmits<{
    select: [tableName: string];
}>();

// 搜索关键词
const searchKeyword = ref('');

// 数据表列表
const allTables = computed<TableOption[]>(() => {
    const tables: TableOption[] = [];

    // 添加数据表
    for (const config of props.configs) {
        tables.push({
            table_name: config.table_name,
            display_name: config.display_name,
        });
    }

    return tables;
});

// 过滤后的配置列表
const filteredConfigs = computed(() => {
    if (!searchKeyword.value.trim()) {
        return allTables.value;
    }

    const keyword = searchKeyword.value.toLowerCase();
    return allTables.value.filter(
        (table) =>
            table.display_name.toLowerCase().includes(keyword) ||
            table.table_name.toLowerCase().includes(keyword),
    );
});

// 处理选择
function handleSelect(tableName: string) {
    emit('select', tableName);
}
</script>

<template>
    <ElCard shadow="never" class="h-full" :body-style="{ padding: '12px' }">
        <template #header>
            <div class="flex items-center justify-between">
                <span class="font-medium">选择主表</span>
                <span class="text-xs text-gray-400">
                    {{ allTables.length }} 个
                </span>
            </div>
        </template>

        <!-- 搜索框 -->
        <div class="mb-3">
            <ElInput v-model="searchKeyword" placeholder="搜索表名..." clearable :prefix-icon="Search" size="small" />
        </div>

        <!-- 配置列表 -->
        <div class="config-list max-h-[calc(100vh-280px)] overflow-auto">
            <ElSkeleton :loading="loading" animated :count="6">
                <template #template>
                    <div class="space-y-2">
                        <div v-for="i in 6" :key="i">
                            <ElSkeletonItem variant="text" style="width: 100%; height: 40px" />
                        </div>
                    </div>
                </template>
                <template #default>
                    <ElMenu v-if="filteredConfigs.length > 0" :default-active="selected" @select="handleSelect">
                        <ElMenuItem v-for="table in filteredConfigs" :key="table.table_name" :index="table.table_name"
                            class="!h-auto !py-2">
                            <div class="flex flex-col">
                                <span class="text-sm font-medium">
                                    {{ table.display_name }}
                                </span>
                                <span class="text-xs text-gray-400">
                                    {{ table.table_name }}
                                </span>
                            </div>
                        </ElMenuItem>
                    </ElMenu>
                    <ElEmpty v-else :description="searchKeyword ? '未找到匹配的表' : '暂无数据表'" :image-size="60" />
                </template>
            </ElSkeleton>
        </div>
    </ElCard>
</template>

<style scoped>
.config-list :deep(.el-menu) {
    border-right: none;
}

.config-list :deep(.el-menu-item) {
    border-radius: 6px;
    margin-bottom: 4px;
}

.config-list :deep(.el-menu-item.is-active) {
    background-color: var(--el-color-primary-light-9);
}
</style>
