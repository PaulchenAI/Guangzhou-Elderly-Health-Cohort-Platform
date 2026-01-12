import type { VxeTableGridOptions } from '#/adapter/vxe-table';
import type { FieldDefinition, SurveySchemaConfig } from '#/api/core/survey';

/**
 * 子问卷数据结构
 */
export interface SubQuestionnaire {
  name: string;
  key: string;
  data: Record<string, any>;
}

/**
 * 创建字段选项映射表
 * 将选项值映射到显示标签
 */
function createOptionsMap(options: FieldDefinition['options']): Map<any, string> | null {
  if (!options || options.length === 0) {
    return null;
  }
  return new Map(options.map((opt) => [opt.value, opt.label]));
}

/**
 * 格式化单元格值
 */
function formatCellValue(
  value: any,
  optionsMap: Map<any, string> | null,
  fieldType?: string,
): string {
  if (value === null || value === undefined) {
    return '-';
  }

  // 如果有选项映射，优先使用
  if (optionsMap) {
    // 先尝试直接匹配
    let label = optionsMap.get(value);
    // 如果没有匹配，尝试类型转换后匹配（处理数字/字符串类型不一致问题）
    if (!label && typeof value === 'number') {
      label = optionsMap.get(String(value));
    }
    if (!label && typeof value === 'string' && !isNaN(Number(value))) {
      label = optionsMap.get(Number(value));
    }
    if (label) return label;
    // 数组类型（如多选）
    if (Array.isArray(value)) {
      return value.map((v) => {
        let l = optionsMap.get(v);
        if (!l && typeof v === 'number') l = optionsMap.get(String(v));
        if (!l && typeof v === 'string' && !isNaN(Number(v))) l = optionsMap.get(Number(v));
        return l || v;
      }).join('、');
    }
  }

  // 布尔类型
  if (fieldType === 'boolean') {
    return value ? '是' : '否';
  }

  // 日期时间类型
  if ((fieldType === 'datetime' || fieldType === 'date') && typeof value === 'string') {
    return value.replace('T', ' ').substring(0, 19);
  }

  // 数组类型
  if (Array.isArray(value)) {
    return value.join('、');
  }

  return String(value);
}

// 有子问卷数据的问卷类型（包含嵌套数据结构）
const SURVEY_TYPES_WITH_SUB_QUESTIONNAIRES = new Set([
  'personality', // 性格特征记录表（含 mentalStateScores, personalityScores）
  'outdoor_activity', // 户外活动记录表（含 activities, summary, statistics）
]);

/**
 * 检查问卷类型是否有子问卷数据
 */
export function hasSubQuestionnaires(surveyType: string): boolean {
  return SURVEY_TYPES_WITH_SUB_QUESTIONNAIRES.has(surveyType?.toLowerCase());
}

/**
 * 根据 Schema 配置构建表格列
 * 完全基于 Schema 的 fields 定义动态生成
 * @param schema - Schema 配置
 * @param showExpand - 是否显示展开列（默认根据问卷类型自动判断）
 */
export function buildColumns(
  schema: SurveySchemaConfig | undefined,
  showExpand?: boolean,
): VxeTableGridOptions['columns'] {
  if (!schema) {
    return [];
  }

  const schemaFields = schema.schema_json?.fields || [];
  const columns: VxeTableGridOptions['columns'] = [];

  // 自动判断是否显示展开列
  const shouldShowExpand = showExpand ?? hasSubQuestionnaires(schema.survey_type);

  // 只有有子问卷数据的问卷才显示展开列
  if (shouldShowExpand) {
    columns.push({
      type: 'expand',
      width: 50,
      fixed: 'left',
      slots: {
        content: 'expand_content',
      },
    });
  }

  // 添加基础固定列
  columns.push({
    field: 'survey_id',
    title: '问卷ID',
    width: 140,
    fixed: 'left',
  });

  columns.push({
    field: 'patient_name',
    title: '患者姓名',
    width: 100,
  });

  columns.push({
    field: 'record_time',
    title: '记录时间',
    width: 160,
    formatter: ({ cellValue }: { cellValue: string }) => {
      if (!cellValue) return '';
      return cellValue.replace('T', ' ').substring(0, 19);
    },
  });

  // 患者基本信息列（通用字段）
  const patientInfoColumns = [
    { field: 'age', title: '年龄', width: 70 },
    { field: 'gender', title: '性别', width: 70 },
  ];

  for (const col of patientInfoColumns) {
    columns.push({
      field: col.field,
      title: col.title,
      width: col.width,
      formatter: ({ cellValue }: { cellValue: any }) => {
        if (col.field === 'gender') {
          return cellValue === 'male' ? '男' : cellValue === 'female' ? '女' : cellValue || '-';
        }
        return cellValue ?? '-';
      },
    });
  }

  // 跳过的字段（已经作为固定列或不需要显示）
  const skipFields = new Set<string>([
    'surveyId', 'survey_id', 'patientName', 'patient_name',
    'recordTime', 'record_time', 'createdAt', 'created_at',
    'age', 'gender', 'phone', 'remarks',
    'patientId', 'recorderName', 'recorderPosition',
    'recorderInstitution', 'recorderContact',
  ]);

  // 根据 Schema 字段定义生成列
  for (const field of schemaFields) {
    const fieldName = field.name || field.fieldName;
    const fieldTitle = field.title || field.label || fieldName;
    const fieldType = field.type || field.fieldType;

    if (!fieldName) continue;

    // 跳过已添加的固定字段
    if (skipFields.has(fieldName)) continue;

    // 创建选项映射表
    const optionsMap = createOptionsMap(field.options);

    // 确定列宽
    let width = 120;
    if (fieldType === 'integer' || fieldType === 'float' || fieldType === 'number') {
      width = 100;
    }
    if (optionsMap && optionsMap.size > 3) {
      width = 150; // 选项多的字段需要更宽
    }

    const column: Record<string, any> = {
      field: fieldName,
      title: fieldTitle,
      minWidth: width,
    };

    // 数值类型右对齐
    if (fieldType === 'integer' || fieldType === 'float' || fieldType === 'number') {
      column.align = 'right';
    }

    // 添加格式化器
    column.formatter = ({ cellValue }: { cellValue: any }) => {
      return formatCellValue(cellValue, optionsMap, fieldType);
    };

    columns.push(column);
  }

  // 户外活动特殊处理：添加汇总字段列（因为 Schema 定义的是子活动字段）
  if (schema.survey_type === 'outdoor_activity') {
    const summaryColumns = [
      { field: 'totalActivities', title: '活动总数', width: 90 },
      { field: 'totalDuration', title: '总时长(分钟)', width: 110 },
      { field: 'averageDuration', title: '平均时长', width: 90 },
      { field: 'activityFrequency', title: '活动频率', width: 90 },
      { field: 'mainActivityType', title: '主要活动类型', width: 120 },
      { field: 'mainVenue', title: '主要场所', width: 100 },
    ];
    for (const col of summaryColumns) {
      columns.push({
        field: col.field,
        title: col.title,
        width: col.width,
        formatter: ({ cellValue }: { cellValue: any }) => {
          if (cellValue === null || cellValue === undefined || cellValue === '') return '-';
          return String(cellValue);
        },
      });
    }
  }

  // 性格特征记录表特殊处理：添加评分汇总列
  if (schema.survey_type === 'personality') {
    const personalityColumns = [
      { field: 'personality_total', title: '性格总分', width: 90 },
      { field: 'mental_total', title: '心理总分', width: 90 },
      { field: 'anxiety_score', title: '焦虑分数', width: 90 },
      { field: 'anxiety_level', title: '焦虑等级', width: 100 },
      { field: 'depression_score', title: '抑郁分数', width: 90 },
      { field: 'depression_level', title: '抑郁等级', width: 100 },
    ];
    for (const col of personalityColumns) {
      columns.push({
        field: col.field,
        title: col.title,
        width: col.width,
        formatter: ({ cellValue }: { cellValue: any }) => {
          if (cellValue === null || cellValue === undefined || cellValue === '') return '-';
          return String(cellValue);
        },
      });
    }
  }

  // 添加诊断/结果列（跳过户外活动和性格特征，因为它们有专门的列）
  if (schema.survey_type !== 'outdoor_activity' && schema.survey_type !== 'personality') {
    const resultFields = [
      { field: 'diagnosis', title: '诊断结果' },
      { field: 'level', title: '评估等级' },
      { field: 'category', title: '分类' },
    ];

    for (const rf of resultFields) {
      columns.push({
        field: rf.field,
        title: rf.title,
        minWidth: 120,
      });
    }
  }

  // 添加记录者信息
  columns.push({
    field: 'recorder_name',
    title: '记录者',
    width: 100,
  });

  return columns;
}

/**
 * 根据 Schema 配置生成搜索表单字段
 */
export function useSearchFormSchema(
  schema: SurveySchemaConfig | undefined,
): Array<{ fieldName: string; label: string; type: string }> {
  if (!schema) {
    return [];
  }

  const fields = schema.schema_json?.fields || [];
  const searchFields: Array<{ fieldName: string; label: string; type: string }> = [];

  // 添加默认搜索字段
  searchFields.push({
    fieldName: 'patient_name',
    label: '患者姓名',
    type: 'string',
  });

  // 根据 Schema 中的 searchable 字段添加搜索字段
  for (const field of fields) {
    if (field.searchable === true) {
      const fieldName = field.name || field.fieldName;

      if (!fieldName) continue;

      // 跳过已经添加的字段
      if (fieldName === 'patient_name' || fieldName === 'patientName') {
        continue;
      }

      searchFields.push({
        fieldName,
        label: field.title || field.label || fieldName,
        type: field.type || field.fieldType || 'string',
      });
    }
  }

  return searchFields;
}
