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
