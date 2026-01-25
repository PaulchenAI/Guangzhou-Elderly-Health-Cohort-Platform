import { requestClient } from '#/api/request';

/**
 * 文档 API 相关类型定义
 */

// 文档接口基本信息
export interface DocEndpoint {
    operation_id: string;
    name: string;
    method: string;
    path: string;
    summary?: string;
}

// 带访问状态的文档接口信息
export interface DocEndpointWithAccess extends DocEndpoint {
    accessible: boolean;
}

// 带访问状态的列表响应
export interface DocEndpointWithAccessListResponse {
    total: number;
    page: number;
    page_size: number;
    items: DocEndpointWithAccess[];
}

// 文档接口详情
export interface DocEndpointDetail extends DocEndpoint {
    description?: string;
    parameters: Array<Record<string, any>>;
    request_body?: Record<string, any>;
    responses: Record<string, any>;
    request_example?: any;
    response_example?: any;
    // 来自 report.json 的额外信息
    request_fields?: number;
    response_fields?: number;
    location?: Record<string, any>;
}

// 搜索参数
export interface DocEndpointSearchParams {
    name?: string;
    path?: string;
    method?: string;
    operation_id?: string;
    keyword?: string;
    page?: number;
    page_size?: number;
}

// 列表响应
export interface DocEndpointListResponse {
    total: number;
    page: number;
    page_size: number;
    items: DocEndpoint[];
}

// 文档摘要信息
export interface DocSummary {
    title: string;
    version: string;
    endpoint_count: number;
    issue_count: number;
    openapi_error_count: number;
    methods_summary?: Record<string, number>;
}

// ============ 文档 API ============

/**
 * 获取文档接口列表（分页）
 */
export async function getDocEndpointsApi(page = 1, pageSize = 20) {
    return requestClient.get<DocEndpointListResponse>(
        '/api/core/doc-api/endpoints',
        {
            params: { page, page_size: pageSize },
        },
    );
}

/**
 * 搜索文档接口
 */
export async function searchDocEndpointsApi(params: DocEndpointSearchParams) {
    return requestClient.post<DocEndpointListResponse>(
        '/api/core/doc-api/endpoints/search',
        {
            name: params.name,
            path: params.path,
            method: params.method,
            operation_id: params.operation_id,
            keyword: params.keyword,
            page: params.page || 1,
            page_size: params.page_size || 20,
        },
    );
}

/**
 * 获取文档接口详情
 */
export async function getDocEndpointDetailApi(operationId: string) {
    return requestClient.get<DocEndpointDetail>(
        `/api/core/doc-api/endpoints/${encodeURIComponent(operationId)}`,
    );
}

/**
 * 获取文档摘要信息
 */
export async function getDocSummaryApi() {
    return requestClient.get<DocSummary>('/api/core/doc-api/summary');
}

// ============ 带访问状态的接口 API ============

/**
 * 获取带访问状态的接口列表（分页）
 */
export async function getDocEndpointsWithAccessApi(
    page = 1,
    pageSize = 20,
    includeInaccessible = true
) {
    return requestClient.get<DocEndpointWithAccessListResponse>(
        '/api/core/doc-api/endpoints-with-access',
        {
            params: {
                page,
                page_size: pageSize,
                include_inaccessible: includeInaccessible,
            },
        },
    );
}

/**
 * 搜索带访问状态的接口
 */
export async function searchDocEndpointsWithAccessApi(params: DocEndpointSearchParams) {
    return requestClient.post<DocEndpointWithAccessListResponse>(
        '/api/core/doc-api/endpoints-with-access/search',
        {
            name: params.name,
            path: params.path,
            method: params.method,
            operation_id: params.operation_id,
            keyword: params.keyword,
            page: params.page || 1,
            page_size: params.page_size || 20,
        },
    );
}

// ============ HIS 接口调用 API ============

// 调用请求参数
export interface DocInvokeRequest {
    params: Record<string, any>;
}

// 调用响应
export interface DocInvokeResponse {
    success: boolean;
    status_code: number;
    duration_ms: number;
    data?: any;
    error?: string;
    log_id?: string;
}

// 默认参数响应
export interface DocDefaultParamsResponse {
    params: Record<string, any>;
}

/**
 * 调用 HIS 接口
 */
export async function invokeDocEndpointApi(operationId: string, params: Record<string, any>) {
    return requestClient.post<DocInvokeResponse>(
        `/api/core/doc-api/invoke/${encodeURIComponent(operationId)}`,
        { params },
        {
            // 调用 HIS 接口可能需要较长时间
            timeout: 60_000,
        },
    );
}

/**
 * 获取接口默认测试参数
 */
export async function getDocDefaultParamsApi(operationId: string) {
    return requestClient.get<DocDefaultParamsResponse>(
        `/api/core/doc-api/endpoints/${encodeURIComponent(operationId)}/default-params`,
    );
}

// ============ 调用历史 API ============

// 调用历史记录
export interface DocInvokeLog {
    id: string;
    operation_id: string;
    endpoint_name: string;
    method: string;
    path: string;
    request_params: Record<string, any>;
    response_data: Record<string, any>;
    response_status: number;
    duration_ms: number;
    success: boolean;
    error_message: string;
    user_id: string;
    sys_create_datetime?: string;
}

// 调用历史列表响应
export interface DocInvokeLogListResponse {
    total: number;
    page: number;
    page_size: number;
    items: DocInvokeLog[];
}

/**
 * 获取调用历史列表
 */
export async function getDocInvokeLogsApi(
    page = 1,
    pageSize = 20,
    operationId?: string
) {
    return requestClient.get<DocInvokeLogListResponse>(
        '/api/core/doc-api/invoke-logs',
        {
            params: {
                page,
                page_size: pageSize,
                operation_id: operationId,
            },
        },
    );
}
