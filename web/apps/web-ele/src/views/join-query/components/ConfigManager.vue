<script lang="ts" setup>
/**
 * 配置管理组件
 */
import { ref } from 'vue';

import { FolderOpen, Plus, Trash2 } from '@vben/icons';

import {
    ElButton,
    ElDialog,
    ElDropdown,
    ElDropdownItem,
    ElDropdownMenu,
    ElEmpty,
    ElInput,
    ElMessage,
    ElPopconfirm,
} from 'element-plus';

import type { JoinQueryConfig } from '../data';

import { deleteConfig, generateId, loadConfigs, saveConfig } from '../data';

const props = defineProps<{
    primaryTable: string;
    selectedTables: string[];
    maxDepth: number;
    visibleColumns: string[];
}>();

const emit = defineEmits<{
    load: [config: {
        primaryTable: string;
        includeTables: string[];
        maxDepth: number;
        visibleColumns?: string[];
    }];
}>();

// 保存配置对话框
const saveDialogVisible = ref(false);
const configName = ref('');

// 加载配置对话框
const loadDialogVisible = ref(false);
const savedConfigs = ref<JoinQueryConfig[]>([]);

// 打开保存对话框
function openSaveDialog() {
    if (!props.primaryTable) {
        ElMessage.warning('请先选择主表');
        return;
    }
    configName.value = '';
    saveDialogVisible.value = true;
}

// 保存配置
function handleSave() {
    if (!configName.value.trim()) {
        ElMessage.warning('请输入配置名称');
        return;
    }

    const config: JoinQueryConfig = {
        id: generateId(),
        name: configName.value.trim(),
        primaryTable: props.primaryTable,
        includeTables: props.selectedTables,
        maxDepth: props.maxDepth,
        visibleColumns: props.visibleColumns.length > 0 ? props.visibleColumns : undefined,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
    };

    saveConfig(config);
    ElMessage.success('配置保存成功');
    saveDialogVisible.value = false;
}

// 打开加载对话框
function openLoadDialog() {
    savedConfigs.value = loadConfigs();
    loadDialogVisible.value = true;
}

// 加载配置
function handleLoad(config: JoinQueryConfig) {
    emit('load', {
        primaryTable: config.primaryTable,
        includeTables: config.includeTables,
        maxDepth: config.maxDepth,
        visibleColumns: config.visibleColumns,
    });
    loadDialogVisible.value = false;
    ElMessage.success(`已加载配置：${config.name}`);
}

// 删除配置
function handleDelete(config: JoinQueryConfig) {
    deleteConfig(config.id);
    savedConfigs.value = loadConfigs();
    ElMessage.success('配置已删除');
}

// 格式化日期
function formatDate(dateStr: string): string {
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
    });
}
</script>

<template>
    <div class="config-manager">
        <ElDropdown>
            <ElButton>
                <FolderOpen class="mr-1 h-4 w-4" />
                配置
            </ElButton>
            <template #dropdown>
                <ElDropdownMenu>
                    <ElDropdownItem @click="openSaveDialog">
                        <Plus class="mr-2 h-4 w-4" />
                        保存当前配置
                    </ElDropdownItem>
                    <ElDropdownItem @click="openLoadDialog">
                        <FolderOpen class="mr-2 h-4 w-4" />
                        加载配置
                    </ElDropdownItem>
                </ElDropdownMenu>
            </template>
        </ElDropdown>

        <!-- 保存配置对话框 -->
        <ElDialog v-model="saveDialogVisible" title="保存配置" width="400px">
            <div class="space-y-4">
                <div>
                    <label class="mb-2 block text-sm text-gray-600">配置名称</label>
                    <ElInput v-model="configName" placeholder="请输入配置名称" maxlength="50" show-word-limit />
                </div>
                <div class="rounded-lg bg-gray-50 p-3 text-sm dark:bg-gray-800">
                    <p><span class="text-gray-500">主表：</span>{{ primaryTable || '未选择' }}</p>
                    <p><span class="text-gray-500">关联表：</span>{{ selectedTables.length }} 个</p>
                    <p><span class="text-gray-500">关联深度：</span>{{ maxDepth }} 级</p>
                </div>
            </div>
            <template #footer>
                <ElButton @click="saveDialogVisible = false">取消</ElButton>
                <ElButton type="primary" @click="handleSave">保存</ElButton>
            </template>
        </ElDialog>

        <!-- 加载配置对话框 -->
        <ElDialog v-model="loadDialogVisible" title="加载配置" width="500px">
            <div v-if="savedConfigs.length > 0" class="config-list space-y-3">
                <div v-for="config in savedConfigs" :key="config.id"
                    class="flex items-center justify-between rounded-lg border p-3 hover:bg-gray-50 dark:hover:bg-gray-800">
                    <div class="flex-1 cursor-pointer" @click="handleLoad(config)">
                        <p class="font-medium">{{ config.name }}</p>
                        <p class="text-sm text-gray-500">
                            {{ config.primaryTable }} · {{ config.includeTables.length }} 个关联表 · {{ config.maxDepth }}
                            级深度
                        </p>
                        <p class="text-xs text-gray-400">
                            {{ formatDate(config.updatedAt) }}
                        </p>
                    </div>
                    <ElPopconfirm title="确定要删除这个配置吗？" confirm-button-text="删除" cancel-button-text="取消"
                        @confirm="handleDelete(config)">
                        <template #reference>
                            <ElButton type="danger" :icon="Trash2" circle size="small" />
                        </template>
                    </ElPopconfirm>
                </div>
            </div>
            <ElEmpty v-else description="暂无保存的配置" :image-size="80" />
        </ElDialog>
    </div>
</template>

<style scoped>
.config-list {
    max-height: 400px;
    overflow-y: auto;
}
</style>
