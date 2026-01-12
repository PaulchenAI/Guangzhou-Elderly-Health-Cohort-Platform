import { requestClient } from '#/api/request';

/**
 * 问卷数据相关类型定义
 */

// 字段定义（兼容外部 API 格式）
export interface FieldDefinition {
    // 标准字段名（外部 API 使用）
    name?: string;
    title?: string;
    type?: string;
    // 兼容字段名
    fieldName?: string;
    label?: string;
    fieldType?: string;
    // 其他属性
    required?: boolean;
    searchable?: boolean;
    visible?: boolean;
    range?: [number, number] | null;
    description?: string | null;
    options?: Array<{ value: any; label: string; description?: string | null }> | null;
}

// Schema 配置
export interface SurveySchemaConfig {
    id: string;
    survey_type: string;
    survey_name: string;
    description?: string;
    schema_json: {
        fields?: FieldDefinition[];
        scoring?: any;
        interpretation?: any[];
        guideUrl?: string;
    };
    guide_url?: string;
    last_synced_at?: string;
    is_active: boolean;
    sort: number;
    sys_create_datetime?: string;
    sys_update_datetime?: string;
}

// 问卷记录
export interface SurveyRecord {
    id: string;
    survey_type: string;
    survey_id: string;
    patient_name: string;
    patient_info: Record<string, any>;
    survey_data: Record<string, any>;
    scores: Record<string, any>;
    record_time: string;
    recorder_info: Record<string, any>;
    external_created_at?: string;
    sys_create_datetime?: string;
    sys_update_datetime?: string;
}

// 导入日志
export interface SurveyImportLog {
    id: string;
    batch_id: string;
    survey_type?: string;
    status: 'running' | 'success' | 'failed' | 'partial';
    trigger_type: 'manual' | 'scheduled';
    total_count: number;
    success_count: number;
    skip_count: number;
    fail_count: number;
    error_details: Array<Record<string, any>>;
    start_time: string;
    end_time?: string;
    duration_seconds?: number;
    sys_create_datetime?: string;
}

// 过滤条件
export interface FilterCondition {
    field: string;
    operator: 'eq' | 'ne' | 'gt' | 'gte' | 'lt' | 'lte' | 'like' | 'in' | 'between';
    value: any;
}

// 查询参数
export interface SurveyQueryParams {
    schemaId: string;
    page: number;
    pageSize: number;
    filters?: FilterCondition[];
    orderBy?: string;
}

// 查询结果
export interface SurveyQueryResult {
    items: Record<string, any>[];
    total: number;
    page: number;
    page_size: number;
}

// 导出参数
export interface SurveyExportParams {
    schemaId: string;
    format: 'excel' | 'csv';
    valueMode?: 'label' | 'value'; // 导出模式：label=文案, value=数值
    filters?: FilterCondition[];
    maxRows?: number;
}

// 分页响应
export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    pageSize: number;
}

// ============ Schema 配置 API ============

/**
 * 获取所有问卷 Schema 配置（不分页）
 */
export async function getAllSurveySchemasApi(isActive?: boolean) {
    return requestClient.get<SurveySchemaConfig[]>(
        '/api/core/survey/schemas/all',
        {
            params: { is_active: isActive },
        },
    );
}

/**
 * 获取问卷 Schema 配置列表（分页）
 */
export async function getSurveySchemaListApi(params?: {
    page?: number;
    pageSize?: number;
    survey_type?: string;
    survey_name?: string;
    is_active?: boolean;
}) {
    return requestClient.get<PaginatedResponse<SurveySchemaConfig>>(
        '/api/core/survey/schemas',
        { params },
    );
}

/**
 * 获取问卷 Schema 配置详情
 */
export async function getSurveySchemaApi(schemaId: string) {
    return requestClient.get<SurveySchemaConfig>(
        `/api/core/survey/schemas/${schemaId}`,
    );
}

/**
 * 根据问卷类型获取 Schema 配置
 */
export async function getSurveySchemaByTypeApi(surveyType: string) {
    return requestClient.get<SurveySchemaConfig>(
        `/api/core/survey/schemas/by-type/${surveyType}`,
    );
}

// ============ 问卷数据 API ============

/**
 * 获取问卷数据列表（分页）
 */
export async function getSurveyRecordListApi(params?: {
    page?: number;
    pageSize?: number;
    survey_type?: string;
    survey_id?: string;
    patient_name?: string;
    start_date?: string;
    end_date?: string;
}) {
    return requestClient.get<PaginatedResponse<SurveyRecord>>(
        '/api/core/survey/records',
        { params },
    );
}

/**
 * 获取问卷数据详情
 */
export async function getSurveyRecordApi(recordId: string) {
    return requestClient.get<SurveyRecord>(
        `/api/core/survey/records/${recordId}`,
    );
}

/**
 * 执行动态问卷查询
 */
export async function querySurveyDataApi(params: SurveyQueryParams) {
    return requestClient.post<SurveyQueryResult>('/api/core/survey/query', {
        schema_id: params.schemaId,
        page: params.page,
        page_size: params.pageSize,
        filters: params.filters,
        order_by: params.orderBy,
    });
}

/**
 * 导出问卷数据
 */
export async function exportSurveyDataApi(params: SurveyExportParams) {
    return requestClient.post('/api/core/survey/export', {
        schema_id: params.schemaId,
        format: params.format,
        value_mode: params.valueMode || 'label', // 默认导出文案
        filters: params.filters,
        max_rows: params.maxRows || 10000,
    }, {
        responseType: 'blob',
    });
}

// ============ 导入日志 API ============

/**
 * 获取导入日志列表（分页）
 */
export async function getSurveyImportLogListApi(params?: {
    page?: number;
    pageSize?: number;
    batch_id?: string;
    survey_type?: string;
    status?: string;
    trigger_type?: string;
}) {
    return requestClient.get<PaginatedResponse<SurveyImportLog>>(
        '/api/core/survey/import-logs',
        { params },
    );
}

/**
 * 获取导入日志详情
 */
export async function getSurveyImportLogApi(logId: string) {
    return requestClient.get<SurveyImportLog>(
        `/api/core/survey/import-logs/${logId}`,
    );
}

