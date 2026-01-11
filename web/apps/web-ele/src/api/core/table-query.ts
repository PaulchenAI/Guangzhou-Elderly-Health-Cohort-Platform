import { requestClient } from '#/api/request';

/**
 * 表查询相关类型定义
 */

// 字段配置
export interface FieldConfig {
    name: string;
    displayName: string;
    type: 'string' | 'integer' | 'decimal' | 'date' | 'datetime' | 'boolean';
    searchable?: boolean;
    sortable?: boolean;
    visible?: boolean;
    width?: number;
}

// 配置 JSON
export interface ConfigJson {
    fields: FieldConfig[];
    defaultPageSize: number;
    maxPageSize: number;
    defaultOrderBy: string;
    allowedOperations: string[];
}

// 表查询配置
export interface TableQueryConfig {
    id: string;
    table_name: string;
    display_name: string;
    description?: string;
    config_json: ConfigJson;
    is_active: boolean;
    sort: number;
    sys_create_datetime?: string;
    sys_update_datetime?: string;
}

// 创建配置输入
export interface TableQueryConfigCreateInput {
    table_name: string;
    display_name: string;
    description?: string;
    config_json?: Record<string, any>;
    is_active?: boolean;
    sort?: number;
}

// 更新配置输入
export interface TableQueryConfigUpdateInput
    extends Partial<TableQueryConfigCreateInput> { }

// 配置列表参数
export interface TableQueryConfigListParams {
    page?: number;
    pageSize?: number;
    table_name?: string;
    display_name?: string;
    is_active?: boolean;
}

// 过滤条件
export interface FilterCondition {
    field: string;
    operator:
    | 'eq'
    | 'ne'
    | 'gt'
    | 'gte'
    | 'lt'
    | 'lte'
    | 'like'
    | 'in'
    | 'between';
    value: any;
}

// 查询参数
export interface TableQueryParams {
    configId: string;
    page: number;
    pageSize: number;
    fields?: string[];
    filters?: FilterCondition[];
    orderBy?: string;
}

// 查询结果
export interface TableQueryResult {
    items: Record<string, any>[];
    total: number;
    page: number;
    page_size: number;
}

// 导出参数
export interface ExportParams {
    configId: string;
    format: 'excel' | 'csv';
    fields?: string[];
    filters?: FilterCondition[];
    maxRows?: number;
}

// 查询日志
export interface TableQueryLog {
    id: string;
    user_id: string;
    table_name: string;
    operation: 'query' | 'export';
    filters: Record<string, any>;
    record_count: number;
    execution_time: number;
    sys_create_datetime?: string;
}

// 分页响应
export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    pageSize: number;
}

// ============ 配置管理 API ============

/**
 * 创建表查询配置
 */
export async function createTableQueryConfigApi(
    data: TableQueryConfigCreateInput,
) {
    return requestClient.post<TableQueryConfig>(
        '/api/core/table-query/configs',
        data,
    );
}

/**
 * 获取表查询配置列表（分页）
 */
export async function getTableQueryConfigListApi(
    params?: TableQueryConfigListParams,
) {
    return requestClient.get<PaginatedResponse<TableQueryConfig>>(
        '/api/core/table-query/configs',
        { params },
    );
}

/**
 * 获取所有表查询配置（不分页）
 */
export async function getAllTableQueryConfigsApi(isActive?: boolean) {
    return requestClient.get<TableQueryConfig[]>(
        '/api/core/table-query/configs/all',
        {
            params: { is_active: isActive },
        },
    );
}

/**
 * 获取表查询配置详情
 */
export async function getTableQueryConfigApi(configId: string) {
    return requestClient.get<TableQueryConfig>(
        `/api/core/table-query/configs/${configId}`,
    );
}

/**
 * 更新表查询配置
 */
export async function updateTableQueryConfigApi(
    configId: string,
    data: TableQueryConfigUpdateInput,
) {
    return requestClient.put<TableQueryConfig>(
        `/api/core/table-query/configs/${configId}`,
        data,
    );
}

/**
 * 删除表查询配置
 */
export async function deleteTableQueryConfigApi(configId: string) {
    return requestClient.delete<TableQueryConfig>(
        `/api/core/table-query/configs/${configId}`,
    );
}

// ============ 动态查询 API ============

/**
 * 执行动态表查询
 */
export async function executeTableQueryApi(params: TableQueryParams) {
    return requestClient.post<TableQueryResult>('/api/core/table-query/query', {
        config_id: params.configId,
        page: params.page,
        page_size: params.pageSize,
        fields: params.fields,
        filters: params.filters,
        order_by: params.orderBy,
    });
}

/**
 * 导出表数据
 */
export async function exportTableDataApi(params: ExportParams) {
    return requestClient.post('/api/core/table-query/export', {
        config_id: params.configId,
        format: params.format,
        fields: params.fields,
        filters: params.filters,
        max_rows: params.maxRows || 10000,
    }, {
        responseType: 'blob',
    });
}

// ============ 日志查询 API ============

/**
 * 获取查询日志列表（分页）
 */
export async function getTableQueryLogsApi(params?: {
    page?: number;
    pageSize?: number;
    user_id?: string;
    table_name?: string;
    operation?: string;
}) {
    return requestClient.get<PaginatedResponse<TableQueryLog>>(
        '/api/core/table-query/logs',
        { params },
    );
}

