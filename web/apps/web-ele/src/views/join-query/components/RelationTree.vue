<script lang="ts" setup>
/**
 * 关联关系树组件
 */
import type { JoinPreviewResponse } from '#/api/core/table-query';

import { computed, ref, watch } from 'vue';

import { CircleHelp } from '@vben/icons';

import {
    ElCard,
    ElEmpty,
    ElSkeleton,
    ElSkeletonItem,
    ElSlider,
    ElTag,
    ElTooltip,
    ElTree,
} from 'element-plus';

import type { RelationTreeNode } from '../data';

import { buildRelationTree, getDefaultExpandedKeys } from '../data';

const props = withDefaults(
    defineProps<{
        relations: JoinPreviewResponse | null;
        loading: boolean;
        selectedTables: string[];
        maxDepth: number;
        tableDisplayNames?: Map<string, string>; // 表名到中文名称的映射
        embedded?: boolean; // 嵌入式模式（不显示外层卡片）
    }>(),
    {
        embedded: false,
    },
);

const emit = defineEmits<{
    'update:selectedTables': [tables: string[]];
    'depthChange': [depth: number];
}>();

// 树形组件引用
const treeRef = ref<InstanceType<typeof ElTree> | null>(null);

// 当前深度
const currentDepth = ref(props.maxDepth);

// 树形数据
const treeData = computed(() => {
    if (!props.relations) {
        return [];
    }
    return buildRelationTree(props.relations, props.tableDisplayNames);
});

// 默认展开的节点
const defaultExpandedKeys = computed(() => {
    return getDefaultExpandedKeys(treeData.value);
});

// 树形属性
const treeProps = {
    children: 'children',
    label: 'label',
};

// 处理勾选变化
function handleCheck(
    _data: RelationTreeNode,
    { checkedKeys }: { checkedKeys: string[] },
) {
    emit('update:selectedTables', checkedKeys);
}

// 处理深度变化
function handleDepthChange(value: number) {
    emit('depthChange', value);
}

// 生成关联信息提示
function getJoinTooltip(node: RelationTreeNode): string {
    const { joinInfo } = node;
    const sourceFields = joinInfo.sourceColumns.join(', ');
    const targetFields = joinInfo.targetColumns.join(', ');
    return `${joinInfo.sourceTable}.${sourceFields} → ${node.tableName}.${targetFields}`;
}

// 监听外部深度变化
watch(
    () => props.maxDepth,
    (newDepth) => {
        currentDepth.value = newDepth;
    },
);

// 监听外部选中表变化，同步到树组件
watch(
    () => props.selectedTables,
    (tables) => {
        if (treeRef.value) {
            treeRef.value.setCheckedKeys(tables);
        }
    },
    { immediate: true },
);
</script>

<template>
    <!-- 嵌入式模式：不显示外层卡片 -->
    <div v-if="embedded" class="relation-tree-embedded">
        <ElSkeleton :loading="loading" animated :count="3">
            <template #template>
                <div class="space-y-3">
                    <ElSkeletonItem variant="text" style="width: 100%; height: 32px" />
                    <ElSkeletonItem variant="text" style="width: 80%; height: 24px" />
                </div>
            </template>
            <template #default>
                <!-- 关联深度设置（水平布局） -->
                <div class="mb-3 flex items-center gap-4">
                    <span class="flex-shrink-0 text-sm text-gray-500">关联深度:</span>
                    <ElSlider v-model="currentDepth" :min="1" :max="5" :step="1" :show-stops="true" style="width: 200px"
                        @change="handleDepthChange" />
                    <span class="text-sm font-medium text-primary">{{ currentDepth }} 级</span>
                    <span class="ml-4 text-xs text-gray-400">
                        共 {{ relations?.total_related_tables || 0 }} 个关联表
                        <ElTag v-if="relations?.has_cycle" size="small" type="warning" class="ml-2">
                            存在循环引用
                        </ElTag>
                    </span>
                </div>

                <!-- 关联关系树（水平滚动） -->
                <div v-if="treeData.length > 0" class="relation-tree flex gap-2 overflow-x-auto pb-2">
                    <ElTree ref="treeRef" :data="treeData" show-checkbox node-key="id"
                        :default-expanded-keys="defaultExpandedKeys" :props="treeProps"
                        :default-checked-keys="selectedTables" @check="handleCheck" class="min-w-max">
                        <template #default="{ data }">
                            <div class="flex items-center gap-2">
                                <ElTooltip :content="getJoinTooltip(data)" placement="right">
                                    <span class="cursor-help whitespace-nowrap">{{ data.label }}</span>
                                </ElTooltip>
                                <ElTag size="small" type="info">
                                    {{ data.depth }}级
                                </ElTag>
                            </div>
                        </template>
                    </ElTree>
                </div>

                <!-- 无关联关系 -->
                <div v-else class="py-4 text-center text-sm text-gray-400">
                    该表无外键关联，请选择其他表或使用单表查询
                </div>
            </template>
        </ElSkeleton>
    </div>

    <!-- 独立模式：显示外层卡片 -->
    <ElCard v-else shadow="never" class="h-full" :body-style="{ padding: '12px' }">
        <template #header>
            <div class="flex items-center justify-between">
                <span class="font-medium">关联配置</span>
                <ElTooltip content="勾选要关联的表，设置关联深度">
                    <CircleHelp class="h-4 w-4 cursor-help text-gray-400" />
                </ElTooltip>
            </div>
        </template>

        <ElSkeleton :loading="loading" animated :count="3">
            <template #template>
                <div class="space-y-3">
                    <ElSkeletonItem variant="text" style="width: 100%; height: 32px" />
                    <ElSkeletonItem variant="text" style="width: 80%; height: 24px" />
                    <ElSkeletonItem variant="text" style="width: 60%; height: 24px" />
                    <ElSkeletonItem variant="text" style="width: 70%; height: 24px" />
                </div>
            </template>
            <template #default>
                <!-- 关联深度设置 -->
                <div class="mb-4">
                    <div class="mb-2 flex items-center justify-between">
                        <span class="text-sm text-gray-500">关联深度</span>
                        <span class="text-sm font-medium text-primary">{{ currentDepth }} 级</span>
                    </div>
                    <ElSlider v-model="currentDepth" :min="1" :max="5" :step="1" :marks="{
                        1: '1',
                        2: '2',
                        3: '3',
                        4: '4',
                        5: '5',
                    }" @change="handleDepthChange" />
                </div>

                <!-- 关联关系树 -->
                <div v-if="treeData.length > 0" class="relation-tree">
                    <div class="mb-2 text-xs text-gray-400">
                        共 {{ relations?.total_related_tables || 0 }} 个关联表
                        <ElTag v-if="relations?.has_cycle" size="small" type="warning" class="ml-2">
                            存在循环引用
                        </ElTag>
                    </div>

                    <ElTree ref="treeRef" :data="treeData" show-checkbox node-key="id"
                        :default-expanded-keys="defaultExpandedKeys" :props="treeProps"
                        :default-checked-keys="selectedTables" @check="handleCheck">
                        <template #default="{ data }">
                            <div class="flex items-center gap-2">
                                <ElTooltip :content="getJoinTooltip(data)" placement="right">
                                    <span class="cursor-help">{{ data.label }}</span>
                                </ElTooltip>
                                <ElTag size="small" type="info">
                                    {{ data.depth }}级
                                </ElTag>
                            </div>
                        </template>
                    </ElTree>
                </div>

                <!-- 无关联关系 -->
                <ElEmpty v-else description="该表无外键关联" :image-size="60">
                    <template #description>
                        <div class="text-center">
                            <p class="text-sm text-gray-500">该表无外键关联</p>
                            <p class="mt-1 text-xs text-gray-400">
                                请选择其他表或使用单表查询
                            </p>
                        </div>
                    </template>
                </ElEmpty>
            </template>
        </ElSkeleton>
    </ElCard>
</template>

<style scoped>
.relation-tree :deep(.el-tree-node__content) {
    height: auto;
    padding: 6px 0;
}

.relation-tree :deep(.el-tree-node__expand-icon) {
    padding: 6px;
}
</style>
