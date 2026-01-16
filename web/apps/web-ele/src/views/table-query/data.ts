import type { VxeTableGridOptions } from '@vben/plugins/vxe-table';

import type { VbenFormSchema } from '#/adapter/form';
import type { FieldConfig, TableQueryConfig } from '#/api/core/table-query';

/**
 * 根据字段类型获取对应的表单组件
 */
function getComponentByType(
    type: string,
): 'DatePicker' | 'Input' | 'InputNumber' | 'Switch' {
    switch (type) {
        case 'integer':
        case 'decimal': {
            return 'InputNumber';
        }
        case 'date':
        case 'datetime': {
            return 'DatePicker';
        }
        case 'boolean': {
            return 'Switch';
        }
        default: {
            return 'Input';
        }
    }
}

/**
 * 根据字段类型获取日期选择器的类型
 */
function getDatePickerType(type: string): 'date' | 'datetime' | undefined {
    if (type === 'date') return 'date';
    if (type === 'datetime') return 'datetime';
    return undefined;
}

/**
 * 根据配置动态生成表格列
 */
export function buildColumns(
    config?: TableQueryConfig,
): VxeTableGridOptions['columns'] {
    if (!config?.config_json?.fields) {
        return [];
    }

    const columns: VxeTableGridOptions['columns'] = [];

    // 添加序号列
    columns.push({
        type: 'seq',
        width: 60,
        title: '#',
    });

    // 根据配置生成数据列
    for (const field of config.config_json.fields) {
        if (!field.visible) continue;

        // 生成列标题：如果 displayName 存在且与 name 不同，显示 "中文名称 (字段名)"，否则只显示字段名
        let title: string;
        if (field.displayName && field.displayName.trim() && field.displayName !== field.name) {
            title = `${field.displayName} (${field.name})`;
        } else {
            title = field.name;
        }

        columns.push({
            field: field.name,
            title,
            minWidth: field.width || 120,
            sortable: field.sortable,
            showOverflow: true,
        });
    }

    return columns;
}

/**
 * 根据配置动态生成搜索表单 Schema
 */
export function useSearchFormSchema(config?: TableQueryConfig): VbenFormSchema[] {
    if (!config?.config_json?.fields) {
        return [];
    }

    const schema: VbenFormSchema[] = [];

    for (const field of config.config_json.fields) {
        if (!field.searchable) continue;

        const component = getComponentByType(field.type);
        const formItem: VbenFormSchema = {
            component,
            fieldName: field.name,
            label: field.displayName,
        };

        // 为日期选择器添加类型
        if (component === 'DatePicker') {
            formItem.componentProps = {
                type: getDatePickerType(field.type),
                valueFormat: field.type === 'date' ? 'YYYY-MM-DD' : 'YYYY-MM-DD HH:mm:ss',
            };
        }

        schema.push(formItem);
    }

    return schema;
}

/**
 * 获取字段的显示名称映射
 */
export function getFieldDisplayNames(
    config?: TableQueryConfig,
): Record<string, string> {
    if (!config?.config_json?.fields) {
        return {};
    }

    const map: Record<string, string> = {};
    for (const field of config.config_json.fields) {
        map[field.name] = field.displayName;
    }
    return map;
}

/**
 * 获取可见字段列表
 */
export function getVisibleFields(config?: TableQueryConfig): FieldConfig[] {
    if (!config?.config_json?.fields) {
        return [];
    }
    return config.config_json.fields.filter((f) => f.visible !== false);
}

/**
 * 获取可搜索字段列表
 */
export function getSearchableFields(config?: TableQueryConfig): FieldConfig[] {
    if (!config?.config_json?.fields) {
        return [];
    }
    return config.config_json.fields.filter((f) => f.searchable);
}

/**
 * 获取可排序字段列表
 */
export function getSortableFields(config?: TableQueryConfig): FieldConfig[] {
    if (!config?.config_json?.fields) {
        return [];
    }
    return config.config_json.fields.filter((f) => f.sortable);
}

