/**
 * 联合查询工具函数
 */
import type { VxeTableGridOptions } from '@vben/plugins/vxe-table';

import type { FieldInfo, JoinPreviewResponse, JoinTableInfo, ManualJoin } from '#/api/core/table-query';

/**
 * 关联关系树节点
 */
export interface RelationTreeNode {
    id: string;
    label: string;
    tableName: string;
    depth: number;
    joinInfo: {
        sourceTable: string;
        sourceColumns: string[];
        targetColumns: string[];
    };
    children?: RelationTreeNode[];
}

/**
 * 保存的联合查询配置
 */
export interface JoinQueryConfig {
    id: string;
    name: string;
    primaryTable: string;
    includeTables: string[];
    maxDepth: number;
    visibleColumns?: string[];
    manualJoins?: ManualJoin[];
    createdAt: string;
    updatedAt: string;
}

// localStorage key
const CONFIG_STORAGE_KEY = 'join_query_configs';
const COLUMN_PREF_KEY = 'join_query_column_prefs';

/**
 * 将 API 响应的关联信息转换为树形结构
 * @param preview - API 返回的关联关系预览
 * @param tableDisplayNames - 表名到中文名称的映射（可选）
 */
export function buildRelationTree(
    preview: JoinPreviewResponse,
    tableDisplayNames?: Map<string, string>,
): RelationTreeNode[] {
    if (!preview.join_tree || preview.join_tree.length === 0) {
        return [];
    }

    // 按深度分组
    const byDepth = new Map<number, JoinTableInfo[]>();
    for (const item of preview.join_tree) {
        const depth = item.join_depth;
        if (!byDepth.has(depth)) {
            byDepth.set(depth, []);
        }
        byDepth.get(depth)!.push(item);
    }

    // 生成显示标签：优先显示中文名称
    const getDisplayLabel = (tableName: string): string => {
        const displayName = tableDisplayNames?.get(tableName);
        if (displayName && displayName !== tableName) {
            return `${displayName} (${tableName})`;
        }
        return tableName;
    };

    // 构建树形结构
    const buildNodes = (
        items: JoinTableInfo[],
        parentTable: string,
    ): RelationTreeNode[] => {
        return items
            .filter((item) => item.source_table === parentTable)
            .map((item) => {
                const nextDepth = item.join_depth + 1;
                const nextItems = byDepth.get(nextDepth) || [];

                return {
                    id: item.table_name,
                    label: getDisplayLabel(item.table_name),
                    tableName: item.table_name,
                    depth: item.join_depth,
                    joinInfo: {
                        sourceTable: item.source_table,
                        sourceColumns: item.source_columns,
                        targetColumns: item.target_columns,
                    },
                    children: buildNodes(nextItems, item.table_name),
                };
            });
    };

    // 从第一级开始构建
    const firstLevel = byDepth.get(1) || [];
    return buildNodes(firstLevel, preview.primary_table);
}

/**
 * 检查字段是否为 JSON 类型字段
 */
export function isJsonField(fieldName: string, fieldType?: string): boolean {
    // 常见的 JSON 字段名
    const jsonFieldNames = [
        'survey_data',
        'patient_info',
        'scores',
        'recorder_info',
        'raw_data',
        'data',
        'info',
    ];

    // 检查字段名是否包含 JSON 相关关键字
    if (jsonFieldNames.some(name => fieldName.toLowerCase().includes(name))) {
        return true;
    }

    // 检查字段类型
    if (fieldType === 'json' || fieldType === 'object') {
        return true;
    }

    return false;
}

/**
 * 格式化字段名（camelCase 转为可读格式，参考问卷页面）
 */
function formatFieldName(name: string): string {
    // 常用字段名映射（参考问卷页面）
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
        // 患者信息相关
        patientName: '患者姓名',
        patient_name: '患者姓名',
        age: '年龄',
        gender: '性别',
        phone: '电话',
        height: '身高',
        weight: '体重',
        idCard: '身份证',
        email: '邮箱',
        address: '地址',
        remarks: '备注',
        // 问卷相关
        surveyId: '问卷ID',
        survey_id: '问卷ID',
        recordTime: '记录时间',
        record_time: '记录时间',
        createdAt: '创建时间',
        created_at: '创建时间',
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

// 活动类别映射（参考问卷页面）
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
 * 格式化字段值（处理 JSON 数据，参考问卷页面的格式化方式）
 */
export function formatFieldValue(value: any, fieldName: string, fieldType?: string): string {
    if (value === null || value === undefined || value === '') {
        return '-';
    }

    // 布尔类型
    if (typeof value === 'boolean') {
        return value ? '是' : '否';
    }

    // 如果是字符串，尝试解析为 JSON（处理数据库中存储为字符串的 JSON 字段）
    if (typeof value === 'string') {
        // 先检查是否是日期时间格式
        if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(value)) {
            return value.replace('T', ' ').substring(0, 19);
        }

        // 尝试解析为 JSON（检查是否以 { 或 [ 开头，且长度合理）
        const trimmed = value.trim();
        if ((trimmed.startsWith('{') || trimmed.startsWith('[')) && trimmed.length > 2) {
            try {
                const parsed = JSON.parse(value);
                // 递归处理解析后的对象
                return formatFieldValue(parsed, fieldName, fieldType);
            } catch {
                // 解析失败，继续按字符串处理
            }
        }
    }

    // 数组类型
    if (Array.isArray(value)) {
        if (value.length === 0) return '-';
        // 如果数组元素是对象，尝试格式化
        if (value.length > 0 && typeof value[0] === 'object' && value[0] !== null) {
            // 对于对象数组，显示简化信息
            return `${value.length} 项`;
        }
        return value.join('、');
    }

    // JSON 对象处理（参考问卷页面的格式化方式）
    if (typeof value === 'object' && value !== null) {
        // 如果是评估等级对象（包含 level 和 description）
        if ('level' in value && typeof value.level === 'string') {
            return value.level + (value.description ? `（${value.description}）` : '');
        }

        // 如果是简单的键值对象，尝试格式化显示（参考问卷页面）
        const keys = Object.keys(value);
        if (keys.length <= 5) {
            const parts = Object.entries(value)
                .filter(([k]) => k !== 'color') // 排除颜色字段
                .map(([k, v]) => {
                    const formattedKey = formatFieldName(k);
                    // 格式化值
                    let formattedValue = v;
                    if (v === null || v === undefined || v === '') {
                        formattedValue = '-';
                    } else if (typeof v === 'boolean') {
                        formattedValue = v ? '是' : '否';
                    } else if (typeof v === 'object') {
                        if (Array.isArray(v)) {
                            formattedValue = v.length > 0 ? `${v.length}项` : '[]';
                        } else {
                            formattedValue = `{${Object.keys(v).length}个字段}`;
                        }
                    } else {
                        formattedValue = String(v);
                    }
                    return `${formattedKey}: ${formattedValue}`;
                })
                .join(', ');
            if (parts.length < 100) return parts;
        }

        // 复杂对象，显示为 JSON 字符串（但格式化）
        try {
            return JSON.stringify(value, null, 2);
        } catch {
            return String(value);
        }
    }

    // 活动类别特殊处理（参考问卷页面）
    if (fieldName === 'category' || fieldName === 'activityCode' || fieldName === 'mostCommonCategory') {
        const categoryLabel = ACTIVITY_CATEGORY_MAP[value];
        if (categoryLabel) return categoryLabel;
    }

    return String(value);
}

/**
 * 展开 JSON 字段，将 JSON 对象中的字段拆分为独立列
 */
export function expandJsonFields(
    fieldInfo: FieldInfo[],
    items: any[],
): { expandedFieldInfo: FieldInfo[]; expandedItems: any[] } {
    const jsonFields = fieldInfo.filter(f => isJsonField(f.original_field, f.field_type));
    if (jsonFields.length === 0 || items.length === 0) {
        return { expandedFieldInfo: fieldInfo, expandedItems: items };
    }

    // 收集所有 JSON 字段的结构
    const jsonFieldStructures = new Map<string, Set<string>>();
    for (const item of items) {
        for (const jsonField of jsonFields) {
            const value = item[jsonField.alias];
            if (value !== null && value !== undefined && value !== '') {
                let parsedValue = value;
                // 尝试解析字符串形式的 JSON
                if (typeof value === 'string') {
                    const trimmed = value.trim();
                    if ((trimmed.startsWith('{') || trimmed.startsWith('[')) && trimmed.length > 2) {
                        try {
                            parsedValue = JSON.parse(value);
                        } catch {
                            continue;
                        }
                    } else {
                        continue;
                    }
                }

                // 如果是对象，收集其键
                if (typeof parsedValue === 'object' && !Array.isArray(parsedValue) && parsedValue !== null) {
                    if (!jsonFieldStructures.has(jsonField.alias)) {
                        jsonFieldStructures.set(jsonField.alias, new Set());
                    }
                    const keys = Object.keys(parsedValue);
                    for (const key of keys) {
                        jsonFieldStructures.get(jsonField.alias)!.add(key);
                    }
                }
            }
        }
    }

    // 创建展开后的字段信息
    const expandedFieldInfo: FieldInfo[] = [...fieldInfo];
    const jsonFieldMap = new Map<string, FieldInfo>();

    // 为每个 JSON 字段的每个键创建新字段
    for (const [jsonFieldAlias, keys] of jsonFieldStructures.entries()) {
        const jsonField = fieldInfo.find(f => f.alias === jsonFieldAlias);
        if (!jsonField) continue;

        for (const key of keys) {
            const expandedAlias = `${jsonFieldAlias}_${key}`;

            // 使用默认格式化（驼峰转空格）
            const fieldComment = key.replace(/([a-z])([A-Z])/g, '$1 $2');

            const expandedField: FieldInfo = {
                alias: expandedAlias,
                original_table: jsonField.original_table,
                original_field: `${jsonField.original_field}.${key}`,
                field_type: 'string', // 默认类型，可以根据实际值推断
                field_comment: fieldComment,
            };
            expandedFieldInfo.push(expandedField);
            jsonFieldMap.set(expandedAlias, expandedField);
        }
    }

    // 展开数据项
    const expandedItems = items.map(item => {
        const expandedItem = { ...item };
        for (const [jsonFieldAlias, keys] of jsonFieldStructures.entries()) {
            const value = item[jsonFieldAlias];
            if (value !== null && value !== undefined && value !== '') {
                let parsedValue = value;
                if (typeof value === 'string') {
                    const trimmed = value.trim();
                    if ((trimmed.startsWith('{') || trimmed.startsWith('[')) && trimmed.length > 2) {
                        try {
                            parsedValue = JSON.parse(value);
                        } catch {
                            continue;
                        }
                    } else {
                        continue;
                    }
                }

                if (typeof parsedValue === 'object' && !Array.isArray(parsedValue) && parsedValue !== null) {
                    for (const key of keys) {
                        const expandedAlias = `${jsonFieldAlias}_${key}`;
                        expandedItem[expandedAlias] = parsedValue[key] ?? null;
                    }
                }
            }
        }
        return expandedItem;
    });

    return { expandedFieldInfo, expandedItems };
}

/**
 * 根据字段信息构建表格列配置
 */
export function buildJoinColumns(
    fieldInfo: FieldInfo[],
    visibleColumns?: string[],
): VxeTableGridOptions['columns'] {
    const columns: VxeTableGridOptions['columns'] = [];

    // 添加序号列
    columns.push({
        type: 'seq',
        width: 60,
        title: '#',
    });

    // 生成数据列
    for (const field of fieldInfo) {
        // 如果指定了可见列，检查是否应该显示
        if (visibleColumns && visibleColumns.length > 0) {
            if (!visibleColumns.includes(field.alias)) {
                continue;
            }
        }

        // 生成列标题：优先显示中文注释，格式为 "中文名/字段名 (表名)"
        const displayName = field.field_comment
            ? `${field.field_comment}/${field.original_field}`
            : field.original_field;
        const title = `${displayName} (${field.original_table})`;

        const column: Record<string, any> = {
            field: field.alias,
            title,
            minWidth: 150,
            sortable: true,
            showOverflow: true,
        };

        // 如果是 JSON 字段，添加格式化器
        const isJson = isJsonField(field.original_field, field.field_type);
        if (isJson) {
            // 使用 formatter 返回格式化的文本（简化版本，因为 VXE Table 不支持直接渲染 HTML）
            column.formatter = ({ cellValue }: { cellValue: any }) => {
                const result = formatFieldValue(cellValue, field.original_field, field.field_type);
                return result;
            };
            // JSON 字段可能需要更宽的列
            column.minWidth = 300;
        } else if (field.field_type === 'datetime' || field.field_type === 'date') {
            // 日期时间字段格式化
            column.formatter = ({ cellValue }: { cellValue: any }) => {
                if (!cellValue) return '-';
                if (typeof cellValue === 'string') {
                    return cellValue.replace('T', ' ').substring(0, 19);
                }
                return String(cellValue);
            };
        } else if (field.field_type === 'boolean') {
            // 布尔字段格式化
            column.formatter = ({ cellValue }: { cellValue: any }) => {
                return cellValue === true ? '是' : cellValue === false ? '否' : '-';
            };
        }

        columns.push(column);
    }

    return columns;
}

/**
 * 按表分组字段信息
 */
export function groupFieldsByTable(
    fieldInfo: FieldInfo[],
): Map<string, FieldInfo[]> {
    const grouped = new Map<string, FieldInfo[]>();

    for (const field of fieldInfo) {
        const tableName = field.original_table;
        if (!grouped.has(tableName)) {
            grouped.set(tableName, []);
        }
        grouped.get(tableName)!.push(field);
    }

    return grouped;
}

/**
 * 从 localStorage 加载配置列表
 */
export function loadConfigs(): JoinQueryConfig[] {
    try {
        const data = localStorage.getItem(CONFIG_STORAGE_KEY);
        if (data) {
            return JSON.parse(data);
        }
    } catch (e) {
        console.error('加载配置失败:', e);
    }
    return [];
}

/**
 * 保存配置到 localStorage
 */
export function saveConfig(config: JoinQueryConfig): void {
    const configs = loadConfigs();
    const existingIndex = configs.findIndex((c) => c.id === config.id);

    if (existingIndex >= 0) {
        configs[existingIndex] = config;
    } else {
        configs.push(config);
    }

    localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(configs));
}

/**
 * 删除配置
 */
export function deleteConfig(configId: string): void {
    const configs = loadConfigs().filter((c) => c.id !== configId);
    localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(configs));
}

/**
 * 生成唯一 ID
 */
export function generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

/**
 * 保存列偏好设置
 */
export function saveColumnPreferences(
    primaryTable: string,
    visibleColumns: string[],
): void {
    try {
        const prefs = loadAllColumnPreferences();
        prefs[primaryTable] = visibleColumns;
        localStorage.setItem(COLUMN_PREF_KEY, JSON.stringify(prefs));
    } catch (e) {
        console.error('保存列偏好失败:', e);
    }
}

/**
 * 加载列偏好设置
 */
export function loadColumnPreferences(primaryTable: string): string[] | null {
    try {
        const prefs = loadAllColumnPreferences();
        return prefs[primaryTable] || null;
    } catch {
        return null;
    }
}

/**
 * 加载所有列偏好
 */
function loadAllColumnPreferences(): Record<string, string[]> {
    try {
        const data = localStorage.getItem(COLUMN_PREF_KEY);
        if (data) {
            return JSON.parse(data);
        }
    } catch {
        // ignore
    }
    return {};
}

/**
 * 获取树的默认展开节点（第一级）
 */
export function getDefaultExpandedKeys(
    treeData: RelationTreeNode[],
): string[] {
    return treeData.map((node) => node.id);
}

/**
 * 展平树形结构获取所有表名
 */
export function flattenTreeToTableNames(
    treeData: RelationTreeNode[],
): string[] {
    const tables: string[] = [];

    function traverse(nodes: RelationTreeNode[]) {
        for (const node of nodes) {
            tables.push(node.tableName);
            if (node.children && node.children.length > 0) {
                traverse(node.children);
            }
        }
    }

    traverse(treeData);
    return tables;
}
