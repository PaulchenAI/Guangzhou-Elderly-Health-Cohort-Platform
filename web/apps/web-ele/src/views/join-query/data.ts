/**
 * 联合查询工具函数
 */
import type { VxeTableGridOptions } from '@vben/plugins/vxe-table';

import type { FieldInfo, JoinPreviewResponse, JoinTableInfo } from '#/api/core/table-query';

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

        columns.push({
            field: field.alias,
            title,
            minWidth: 150,
            sortable: true,
            showOverflow: true,
        });
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
