<script lang="ts" setup>
import type { VxeTableGridOptions } from '#/adapter/vxe-table';

import type { FilterCondition, SurveySchemaConfig } from '#/api/core/survey';

import { computed, onMounted, ref, watch } from 'vue';

import { Page } from '@vben/common-ui';
import { Download, ReloadOutlined, Search } from '@vben/icons';

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
  ElTag,
} from 'element-plus';

import { useVbenVxeGrid } from '#/adapter/vxe-table';
import {
  exportSurveyDataApi,
  getAllSurveySchemasApi,
  querySurveyDataApi,
  triggerSurveySyncApi,
} from '#/api/core/survey';

import { buildColumns, hasSubQuestionnaires, useSearchFormSchema } from './data';

defineOptions({ name: 'SurveyQuery' });

// Schema 配置列表
const schemas = ref<SurveySchemaConfig[]>([]);
const loading = ref(false);
const selectedSchemaId = ref<string>('');
const searchKeyword = ref<string>('');
const syncing = ref(false);

// 搜索表单数据
const searchForm = ref<Record<string, any>>({});

// 计算当前选中的配置
const selectedSchema = computed(() =>
  schemas.value.find((s) => s.id === selectedSchemaId.value),
);

// 判断当前问卷是否有子问卷数据
const showExpandColumn = computed(() =>
  selectedSchema.value ? hasSubQuestionnaires(selectedSchema.value.survey_type) : false,
);

// 动态生成列配置
const columns = computed(() => buildColumns(selectedSchema.value));

// 动态生成搜索表单 Schema
const searchFormSchema = computed(() =>
  useSearchFormSchema(selectedSchema.value),
);

// 计算过滤后的配置列表
const filteredSchemas = computed(() => {
  if (!searchKeyword.value.trim()) {
    return schemas.value;
  }

  const keyword = searchKeyword.value.toLowerCase();
  return schemas.value.filter(
    (schema) =>
      schema.survey_name.toLowerCase().includes(keyword) ||
      schema.survey_type.toLowerCase().includes(keyword),
  );
});

// 使用 useVbenVxeGrid 创建表格
const [Grid, gridApi] = useVbenVxeGrid({
  gridOptions: {
    columns: columns.value,
    height: 'auto',
    keepSource: true,
    rowConfig: {
      keyField: 'id',
    },
    // 展开行配置
    expandConfig: {
      accordion: true, // 手风琴模式，一次只展开一行
      trigger: 'row', // 点击行展开
      lazy: false, // 不使用懒加载
      expandRowKeys: [], // 默认不展开
    },
    proxyConfig: {
      autoLoad: false, // 不自动加载，等选中配置后手动触发
      ajax: {
        query: async ({ page }) => {
          if (!selectedSchemaId.value) {
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

          const result = await querySurveyDataApi({
            schemaId: selectedSchemaId.value,
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
 * 加载 Schema 配置列表
 */
async function fetchSchemas() {
  try {
    loading.value = true;
    const result = await getAllSurveySchemasApi(true);
    schemas.value = result;

    // 自动选中第一个配置
    if (result.length > 0 && !selectedSchemaId.value) {
      selectedSchemaId.value = result[0]!.id;
    }
  } catch (error) {
    console.error('加载问卷配置列表失败:', error);
    ElMessage.error('加载问卷配置列表失败');
  } finally {
    loading.value = false;
  }
}

/**
 * 执行查询
 */
function executeQuery() {
  if (!selectedSchemaId.value) {
    return;
  }
  gridApi.query();
}

/**
 * 切换 Schema 配置
 */
function handleSchemaChange(schemaId: string) {
  selectedSchemaId.value = schemaId;
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
 * 判断是否为复杂值（对象或数组）
 */
function isComplexValue(value: any): boolean {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/**
 * 格式化字段名（camelCase 转为可读格式）
 */
function formatFieldName(name: string): string {
  // 常用字段名映射
  const fieldMap: Record<string, string> = {
    // 评分相关
    totalScore: '总分',
    total_score: '总分',
    averageScore: '平均分',
    average_score: '平均分',
    answeredCount: '已答题数',
    totalQuestions: '总题数',
    completeness: '完成度',
    percentage: '百分比',
    scores: '各项得分',
    level: '等级',
    description: '描述',
    color: '颜色',
    total: '总计',
    filled: '已填',
    count: '数量',
    average: '平均值',
    anxietyScore: '焦虑评分',
    depressionScore: '抑郁评分',
    // 性格特征/心理状态相关
    required: '必填项',
    personality: '性格特征',
    mentalState: '心理状态',
    // 户外活动相关
    mainVenue: '主要场所',
    weekendRatio: '周末活动比例',
    totalDuration: '总时长(分钟)',
    averageDuration: '平均时长(分钟)',
    totalActivities: '活动总数',
    mainActivityType: '主要活动类型',
    activityFrequency: '活动频率',
    route: '路线',
    venue: '场所',
    category: '活动类别',
    duration: '时长(分钟)',
    isWeekend: '是否周末',
    itemsUsed: '使用物品',
    startTime: '开始时间',
    activityCode: '活动代码',
    mostCommonVenue: '最常去场所',
    mostCommonCategory: '最常见类别',
    weekdayActivities: '工作日活动数',
    weekendActivities: '周末活动数',
    venueDistribution: '场所分布',
    categoryDistribution: '类别分布',
  };

  if (fieldMap[name]) {
    return fieldMap[name];
  }

  // 如果是全大写+数字的格式（如 MS01, PT01），直接返回原名
  if (/^[A-Z]+\d+$/.test(name)) {
    return name;
  }

  // 转换 camelCase 为空格分隔（只在小写字母后跟大写字母时插入空格）
  return name.replace(/([a-z])([A-Z])/g, '$1 $2').replace(/^./, (s) => s.toUpperCase()).trim();
}

// 活动类别映射
const ACTIVITY_CATEGORY_MAP: Record<number | string, string> = {
  1: '快步走',
  2: '慢跑',
  3: '骑行',
  4: '健身操/舞蹈',
  5: '球类运动',
  6: '休闲步行',
  7: '园艺活动',
  8: '其他',
};

/**
 * 格式化显示值
 */
function formatValue(value: any, fieldName?: string): string {
  if (value === null || value === undefined || value === '') {
    return '-';
  }
  if (typeof value === 'boolean') {
    return value ? '是' : '否';
  }
  // 活动类别特殊处理
  if (fieldName === 'category' || fieldName === 'activityCode' || fieldName === 'mostCommonCategory') {
    const categoryLabel = ACTIVITY_CATEGORY_MAP[value];
    if (categoryLabel) return categoryLabel;
  }
  // 日期时间格式化
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(value)) {
    return value.replace('T', ' ').substring(0, 16);
  }
  // 嵌套对象特殊处理：提取 level 或 description
  if (typeof value === 'object' && value !== null) {
    // 如果是评估等级对象（包含 level 和 description）
    if ('level' in value && typeof value.level === 'string') {
      return value.level + (value.description ? `（${value.description}）` : '');
    }
    // 如果是简单的键值对象，尝试格式化显示
    if (Object.keys(value).length <= 5) {
      const parts = Object.entries(value)
        .filter(([k]) => k !== 'color') // 排除颜色字段
        .map(([k, v]) => `${formatFieldName(k)}: ${v}`)
        .join(', ');
      if (parts.length < 100) return parts;
    }
    return JSON.stringify(value);
  }
  return String(value);
}

/**
 * 获取数组项的所有键（用于表格表头）
 * 排除不需要显示的内部字段
 */
function getArrayItemKeys(data: any[]): string[] {
  if (!data || data.length === 0) return [];

  // 从第一个元素获取所有键
  const firstItem = data[0];
  const keys = Object.keys(firstItem);

  // 排除内部字段和索引字段
  const excludeKeys = new Set(['index', 'id', '_id']);

  return keys.filter(k => !excludeKeys.has(k));
}

/**
 * 导出数据
 * @param command 格式为 "format:mode"，如 "excel:label" 或 "csv:value"
 */
async function handleExport(command: string) {
  if (!selectedSchemaId.value) {
    ElMessage.warning('请先选择问卷类型');
    return;
  }

  // 解析命令：格式为 "format:mode"
  const [format, valueMode] = command.split(':') as ['csv' | 'excel', 'label' | 'value'];

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

    const response = await exportSurveyDataApi({
      schemaId: selectedSchemaId.value,
      format,
      valueMode, // 新增：导出模式（label=文案, value=数值）
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
    const modeSuffix = valueMode === 'label' ? '文案' : '数值';
    link.download = `${selectedSchema.value?.survey_name || 'data'}_${modeSuffix}.${format === 'excel' ? 'xlsx' : 'csv'}`;
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

/**
 * 手动同步数据
 */
async function handleSync() {
  if (syncing.value) {
    return;
  }

  try {
    syncing.value = true;
    ElMessage.info('正在同步数据，请稍候...');

    const result = await triggerSurveySyncApi({
      incremental: true,
      surveyType: selectedSchema.value?.survey_type,
    });

    ElMessage.success(result.message);

    // 同步完成后刷新数据
    if (result.success > 0) {
      executeQuery();
    }
  } catch (error: any) {
    console.error('同步失败:', error);
    ElMessage.error(error?.message || '同步失败，请稍后重试');
  } finally {
    syncing.value = false;
  }
}

// 监听配置变化，更新列配置并重新查询
watch(selectedSchema, (newSchema) => {
  if (newSchema) {
    // 更新表格列配置
    const newColumns = buildColumns(newSchema);
    gridApi.setGridOptions({ columns: newColumns });
    // 重新查询数据
    executeQuery();
  }
});

onMounted(() => {
  fetchSchemas();
});
</script>

<template>
  <Page auto-content-height>
    <div class="flex h-full gap-4">
      <!-- 问卷类型选择器侧边栏 -->
      <div class="w-64 flex-shrink-0">
        <ElCard shadow="never" class="h-full" :body-style="{ padding: '12px' }">
          <template #header>
            <div class="flex items-center justify-between">
              <span class="font-medium">问卷类型</span>
              <span class="text-xs text-gray-400">
                {{ schemas.length }} 个
              </span>
            </div>
          </template>

          <!-- 搜索框 -->
          <div class="mb-3">
            <ElInput v-model="searchKeyword" placeholder="搜索问卷类型..." clearable :prefix-icon="Search" size="small" />
          </div>

          <!-- 配置列表 -->
          <div class="config-list max-h-[calc(100vh-280px)] overflow-auto">
            <ElSkeleton :loading="loading" animated :count="6">
              <template #template>
                <div class="space-y-2">
                  <div v-for="i in 6" :key="i">
                    <ElSkeletonItem variant="text" style="width: 100%; height: 50px" />
                  </div>
                </div>
              </template>
              <template #default>
                <ElMenu v-if="filteredSchemas.length > 0" :default-active="selectedSchemaId"
                  @select="handleSchemaChange">
                  <ElMenuItem v-for="schema in filteredSchemas" :key="schema.id" :index="schema.id"
                    class="!h-auto !py-2">
                    <div class="flex flex-col">
                      <span class="text-sm font-medium">
                        {{ schema.survey_name }}
                      </span>
                      <span class="text-xs text-gray-400">
                        {{ schema.survey_type }}
                      </span>
                    </div>
                  </ElMenuItem>
                </ElMenu>
                <ElEmpty v-else description="暂无问卷类型" :image-size="60">
                  <template #description>
                    <div class="text-center">
                      <p class="text-sm text-gray-500">暂无问卷类型</p>
                      <p class="text-xs text-gray-400 mt-1">
                        请先运行同步命令
                      </p>
                    </div>
                  </template>
                </ElEmpty>
              </template>
            </ElSkeleton>
          </div>
        </ElCard>
      </div>

      <!-- 数据表格区域 -->
      <div class="flex flex-1 flex-col overflow-hidden">
        <ElCard v-if="selectedSchema" shadow="never" class="flex h-full flex-col"
          :body-style="{ padding: '12px', flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }">
          <!-- 表头信息 -->
          <div class="mb-3 flex items-center justify-between">
            <div>
              <div class="flex items-center gap-2">
                <h3 class="text-lg font-medium">
                  {{ selectedSchema.survey_name }}
                </h3>
                <ElTag size="small" type="info">
                  {{ selectedSchema.survey_type }}
                </ElTag>
              </div>
              <p v-if="selectedSchema.description" class="text-sm text-gray-500 mt-1">
                {{ selectedSchema.description }}
              </p>
            </div>
            <div class="flex gap-2">
              <ElButton :icon="ReloadOutlined" :loading="syncing" :disabled="syncing" @click="handleSync">
                同步数据
              </ElButton>
              <ElDropdown @command="handleExport">
                <ElButton type="primary" :icon="Download">
                  导出数据
                </ElButton>
                <template #dropdown>
                  <ElDropdownMenu>
                    <ElDropdownItem command="excel:label">导出 Excel（文案）</ElDropdownItem>
                    <ElDropdownItem command="excel:value">导出 Excel（数值）</ElDropdownItem>
                    <ElDropdownItem divided disabled class="!text-gray-400 !text-xs">CSV 格式</ElDropdownItem>
                    <ElDropdownItem command="csv:label">导出 CSV（文案）</ElDropdownItem>
                    <ElDropdownItem command="csv:value">导出 CSV（数值）</ElDropdownItem>
                  </ElDropdownMenu>
                </template>
              </ElDropdown>
            </div>
          </div>

          <!-- 搜索表单 -->
          <div v-if="searchFormSchema.length > 0"
            class="mb-3 flex flex-wrap items-center gap-3 rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
            <template v-for="field in searchFormSchema" :key="field.fieldName">
              <div class="flex items-center gap-2">
                <span class="text-sm text-gray-600 dark:text-gray-300">
                  {{ field.label }}:
                </span>
                <ElInput v-model="searchForm[field.fieldName]" :placeholder="`请输入${field.label}`" clearable size="small"
                  style="width: 150px" />
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
            <Grid>
              <!-- 展开行内容插槽 -->
              <template #expand_content="{ row }">
                <div v-if="row._sub_questionnaires && row._sub_questionnaires.length > 0" class="expand-content p-4">
                  <div v-for="(sq, index) in row._sub_questionnaires" :key="index" class="sub-questionnaire mb-4">
                    <h4 class="text-sm font-semibold text-gray-700 mb-2 pb-1 border-b border-gray-200">
                      {{ sq.name }}
                      <span v-if="sq.type === 'array'" class="text-xs text-gray-400 ml-2">
                        (共 {{ sq.data.length }} 条记录)
                      </span>
                    </h4>

                    <!-- 数组类型：显示为表格 -->
                    <template v-if="sq.type === 'array' && Array.isArray(sq.data)">
                      <div class="overflow-x-auto">
                        <table class="min-w-full text-sm border-collapse">
                          <thead>
                            <tr class="bg-gray-100">
                              <th class="px-3 py-2 text-left text-xs font-medium text-gray-600 border">#</th>
                              <th v-for="key in getArrayItemKeys(sq.data)" :key="key"
                                class="px-3 py-2 text-left text-xs font-medium text-gray-600 border">
                                {{ formatFieldName(key) }}
                              </th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr v-for="(item, itemIndex) in sq.data" :key="itemIndex" class="hover:bg-gray-50">
                              <td class="px-3 py-2 border text-gray-500">{{ itemIndex + 1 }}</td>
                              <td v-for="key in getArrayItemKeys(sq.data)" :key="key" class="px-3 py-2 border">
                                {{ formatValue(item[key], key) }}
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </template>

                    <!-- 对象类型：原有逻辑 -->
                    <template v-else>
                      <div class="grid grid-cols-4 gap-2 text-sm">
                        <template v-for="(value, key) in sq.data" :key="key">
                          <div v-if="!isComplexValue(value)" class="flex">
                            <span class="text-gray-500 mr-2">{{ formatFieldName(String(key)) }}:</span>
                            <span class="text-gray-800 font-medium">{{ formatValue(value, String(key)) }}</span>
                          </div>
                        </template>
                      </div>
                      <!-- 嵌套的复杂数据 -->
                      <template v-for="(value, key) in sq.data" :key="key + '_nested'">
                        <div v-if="isComplexValue(value)" class="mt-3">
                          <h5 class="text-xs font-medium text-gray-600 mb-1">{{ formatFieldName(String(key)) }}</h5>
                          <div class="bg-gray-50 rounded p-2 text-xs">
                            <template v-if="typeof value === 'object'">
                              <div v-for="(v, k) in value" :key="k" class="flex gap-2">
                                <span class="text-gray-500">{{ formatFieldName(String(k)) }}:</span>
                                <span class="text-gray-700">{{ formatValue(v, String(k)) }}</span>
                              </div>
                            </template>
                            <span v-else>{{ formatValue(value) }}</span>
                          </div>
                        </div>
                      </template>
                    </template>
                  </div>
                </div>
                <div v-else class="p-4 text-sm text-gray-400">
                  暂无子问卷数据
                </div>
              </template>
            </Grid>
          </div>
        </ElCard>

        <!-- 未选择配置时的提示 -->
        <ElCard v-else shadow="never" class="flex h-full items-center justify-center">
          <ElEmpty description="请从左侧选择要查询的问卷类型">
            <template v-if="schemas.length === 0 && !loading" #description>
              <div class="text-center">
                <p class="text-sm text-gray-500">暂无问卷类型</p>
                <p class="text-xs text-gray-400 mt-2">
                  请先运行以下命令同步问卷 Schema：
                </p>
                <code class="text-xs bg-gray-100 px-2 py-1 rounded mt-2 inline-block">
                  python manage.py sync_survey_schemas
                </code>
              </div>
            </template>
          </ElEmpty>
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

/* 展开行样式 */
.expand-content {
  background-color: #fafafa;
  border-radius: 4px;
}

.dark .expand-content {
  background-color: #1f2937;
}

.sub-questionnaire:last-child {
  margin-bottom: 0;
}

.sub-questionnaire h4 {
  color: #374151;
}

.dark .sub-questionnaire h4 {
  color: #d1d5db;
}
</style>
