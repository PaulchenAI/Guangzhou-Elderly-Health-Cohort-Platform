<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';

import type { FilterCondition, TableQueryConfig } from '#/api/core/table-query';

import { computed, onMounted, ref, watch } from 'vue';

import { Page } from '@vben/common-ui';
import { Download, Search } from '@vben/icons';

import {
  ElButton,
  ElCard,
  ElDropdown,
  ElDropdownItem,
  ElDropdownMenu,
  ElEmpty,
  ElInput,
  ElMenu,
  ElMenuItem,
  ElMessage,
  ElSkeleton,
  ElSkeletonItem,
} from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  executeTableQueryApi,
  exportTableDataApi,
  getAllTableQueryConfigsApi,
} from '#/api/core/table-query';

import { buildColumns, useSearchFormSchema } from './data';

defineOptions({ name: 'TableQuery' });

// 表配置列表
const configs = ref<TableQueryConfig[]>([]);
const loading = ref(false);
const selectedConfigId = ref<string>('');
const searchKeyword = ref<string>('');

// 搜索表单数据
const searchForm = ref<Record<string, any>>({});

// 计算当前选中的配置
const selectedConfig = computed(() =>
  configs.value.find((c) => c.id === selectedConfigId.value),
);

// 动态生成列配置
const columns = computed(() => buildColumns(selectedConfig.value));

// 动态生成搜索表单 Schema
const searchFormSchema = computed(() =>
  useSearchFormSchema(selectedConfig.value),
);

// 计算过滤后的配置列表
const filteredConfigs = computed(() => {
  if (!searchKeyword.value.trim()) {
    return configs.value;
  }

  const keyword = searchKeyword.value.toLowerCase();
  return configs.value.filter(
    (config) =>
      config.display_name.toLowerCase().includes(keyword) ||
      config.table_name.toLowerCase().includes(keyword),
  );
});

// 使用 useVbenVxeGrid 创建表格
const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions: {
    columns: columns.value,
    height: 'auto',
    keepSource: true,
    proxyConfig: {
      autoLoad: false, // 不自动加载，等选中配置后手动触发
      ajax: {
        query: async ({ page }) => {
          if (!selectedConfigId.value) {
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

          const result = await executeTableQueryApi({
            configId: selectedConfigId.value,
            page: page.currentPage,
            pageSize: page.pageSize,
            filters: filters.length > 0 ? filters : undefined,
          });

          return result;
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
  } as VxeTableGridOptions,
});

/**
 * 加载配置列表
 */
async function fetchConfigs() {
  try {
    loading.value = true;
    const result = await getAllTableQueryConfigsApi(true);
    configs.value = result;

    // 自动选中第一个配置
    if (result.length > 0 && !selectedConfigId.value) {
      selectedConfigId.value = result[0]!.id;
    }
  } catch (error) {
    console.error('加载配置列表失败:', error);
    ElMessage.error('加载配置列表失败');
  } finally {
    loading.value = false;
  }
}

/**
 * 执行查询
 */
function executeQuery() {
  if (!selectedConfigId.value) {
    return;
  }
  gridApi.query();
}

/**
 * 切换表配置
 */
function handleConfigChange(configId: string) {
  selectedConfigId.value = configId;
  searchForm.value = {};
  // watch 会自动触发更新列和查询
}

/**
 * 搜索
 */
function handleSearch() {
  executeQuery();
}

/**
 * 重置搜索
 */
function handleReset() {
  searchForm.value = {};
  executeQuery();
}

/**
 * 导出数据
 */
async function handleExport(format: 'csv' | 'excel') {
  if (!selectedConfigId.value) {
    ElMessage.warning('请先选择数据表');
    return;
  }

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

    const response = await exportTableDataApi({
      configId: selectedConfigId.value,
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
    link.download = `${selectedConfig.value?.display_name || 'data'}.${format === 'excel' ? 'xlsx' : 'csv'}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);

    ElMessage.success('导出成功');
  } catch (error) {
    console.error('导出失败:', error);
    ElMessage.error('导出失败');
  }
}

// 监听配置变化，更新列配置并重新查询
watch(selectedConfig, (newConfig) => {
  if (newConfig) {
    // 更新表格列配置
    const newColumns = buildColumns(newConfig);
    gridApi.setGridOptions({ columns: newColumns });
    // 重新查询数据
    executeQuery();
  }
});

onMounted(() => {
  fetchConfigs();
});
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full gap-4">
      <!-- 表选择器侧边栏 -->
      <div class="w-60 flex-shrink-0">
        <ElCard shadow="never" class="h-full" :body-style="{ padding: '12px' }">
          <template #header>
            <div class="flex items-center justify-between">
              <span class="font-medium">数据表</span>
              <span class="text-xs text-gray-400">
                {{ configs.length }} 个
              </span>
            </div>
          </template>

          <!-- 搜索框 -->
          <div class="mb-3">
            <ElInput
              v-model="searchKeyword"
              placeholder="搜索表名..."
              clearable
              :prefix-icon="Search"
              size="small"
            />
          </div>

          <!-- 配置列表 -->
          <div class="config-list max-h-[calc(100vh-280px)] overflow-auto">
            <ElSkeleton :loading="loading" animated :count="6">
              <template #template>
                <div class="space-y-2">
                  <div v-for="i in 6" :key="i">
                    <ElSkeletonItem
                      variant="text"
                      style="width: 100%; height: 40px"
                    />
                  </div>
                </div>
              </template>
              <template #default>
                <ElMenu
                  v-if="filteredConfigs.length > 0"
                  :default-active="selectedConfigId"
                  @select="handleConfigChange"
                >
                  <ElMenuItem
                    v-for="config in filteredConfigs"
                    :key="config.id"
                    :index="config.id"
                    class="!h-auto !py-2"
                  >
                    <div class="flex flex-col">
                      <span class="text-sm font-medium">
                        {{ config.display_name }}
                      </span>
                      <span class="text-xs text-gray-400">
                        {{ config.table_name }}
                      </span>
                    </div>
                  </ElMenuItem>
                </ElMenu>
                <ElEmpty
                  v-else
                  description="暂无数据表"
                  :image-size="60"
                />
              </template>
            </ElSkeleton>
          </div>
        </ElCard>
      </div>

      <!-- 数据表格区域 -->
      <div class="flex flex-1 flex-col overflow-hidden">
        <ElCard
          v-if="selectedConfig"
          shadow="never"
          class="flex h-full flex-col"
          :body-style="{ padding: '12px', flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }"
        >
          <!-- 表头信息 -->
          <div class="mb-3 flex items-center justify-between">
            <div>
              <h3 class="text-lg font-medium">
                {{ selectedConfig.display_name }}
              </h3>
              <p v-if="selectedConfig.description" class="text-sm text-gray-500">
                {{ selectedConfig.description }}
              </p>
            </div>
            <div class="flex gap-2">
              <ElDropdown @command="handleExport">
                <ElButton type="primary" :icon="Download">
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

          <!-- 搜索表单 -->
          <div
            v-if="searchFormSchema.length > 0"
            class="mb-3 flex flex-wrap items-center gap-3 rounded-lg bg-gray-50 p-3 dark:bg-gray-800"
          >
            <template v-for="field in searchFormSchema" :key="field.fieldName">
              <div class="flex items-center gap-2">
                <span class="text-sm text-gray-600 dark:text-gray-300">
                  {{ field.label }}:
                </span>
                <ElInput
                  v-model="searchForm[field.fieldName]"
                  :placeholder="`请输入${field.label}`"
                  clearable
                  size="small"
                  style="width: 150px"
                />
              </div>
            </template>
            <div class="flex gap-2">
              <ElButton type="primary" size="small" @click="handleSearch">
                查询
              </ElButton>
              <ElButton size="small" @click="handleReset">重置</ElButton>
            </div>
          </div>

          <!-- 数据表格 -->
          <div class="flex-1 overflow-hidden">
            <Grid />
          </div>
        </ElCard>

        <!-- 未选择配置时的提示 -->
        <ElCard
          v-else
          shadow="never"
          class="flex h-full items-center justify-center"
        >
          <ElEmpty description="请从左侧选择要查询的数据表" />
        </ElCard>
      </div>
    </div>
  </Page>
</template>

<style scoped>
/* 配置列表样式 */
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

/* 表格容器样式 */
:deep(.vxe-grid) {
  height: 100% !important;
}
</style>

