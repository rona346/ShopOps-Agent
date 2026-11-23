/**
 * ShopOps Agent API Service
 * Centralized HTTP client consuming FastAPI backend endpoints.
 */

import {
  Product,
  ProductCreate,
  ProductUpdate,
  ProductListResponse,
  InventoryAnalysisSummary,
  ReorderRecommendationsResponse,
  InventoryInsightsResponse,
  AgentQueryResponse,
  ApprovalRequest,
  ApprovalRequestCreate,
  ApprovalListResponse,
  ReorderTask,
  ReorderTaskListResponse,
  HealthResponse,
  AuthenticatedUser,
  AuthStatusResponse,
} from '../types';

const API_BASE_URL: string =
  (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000';

const TOKEN_KEY = 'shopops_auth_token';

let currentAuthToken: string | null =
  typeof window !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null;

export function getAuthToken(): string | null {
  if (!currentAuthToken && typeof window !== 'undefined') {
    currentAuthToken = localStorage.getItem(TOKEN_KEY);
  }
  return currentAuthToken;
}

export function setAuthToken(token: string | null): void {
  currentAuthToken = token;
  if (typeof window !== 'undefined') {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  }
}

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail || `API request failed with status ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = getAuthToken();
  const authHeaders: Record<string, string> = token
    ? { Authorization: `Bearer ${token}` }
    : {};

  const headers = {
    'Content-Type': 'application/json',
    ...authHeaders,
    ...(options.headers || {}),
  };

  try {
    const response = await fetch(url, { ...options, headers });

    if (!response.ok) {
      let detail = `Error ${response.status}: ${response.statusText}`;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          detail = typeof errorData.detail === 'string'
            ? errorData.detail
            : JSON.stringify(errorData.detail);
        }
      } catch {
        // Fall back to status text if body is not JSON
      }

      if (response.status === 401 && typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('shopops-auth-unauthorized'));
      }

      throw new ApiError(response.status, detail);
    }

    // For 204 No Content
    if (response.status === 204) {
      return {} as T;
    }

    return await response.json();
  } catch (err: any) {
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(0, err.message || 'Network error connecting to backend service');
  }
}

// ==========================================
// Authentication & Profile Endpoints
// ==========================================
export async function getAuthStatus(): Promise<AuthStatusResponse> {
  return request<AuthStatusResponse>('/api/v1/auth/status');
}

export async function getAuthMe(): Promise<AuthenticatedUser> {
  return request<AuthenticatedUser>('/api/v1/auth/me');
}

// ==========================================
// Health
// ==========================================
export async function checkBackendHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health');
}

// ==========================================
// Inventory Endpoints
// ==========================================
export async function listProducts(params?: {
  category?: string;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<ProductListResponse> {
  const query = new URLSearchParams();
  if (params?.category) query.append('category', params.category);
  if (params?.search) query.append('search', params.search);
  if (params?.limit !== undefined) query.append('limit', params.limit.toString());
  if (params?.offset !== undefined) query.append('offset', params.offset.toString());

  const qs = query.toString();
  return request<ProductListResponse>(`/api/v1/inventory${qs ? `?${qs}` : ''}`);
}

export async function getProduct(id: string): Promise<Product> {
  return request<Product>(`/api/v1/inventory/${id}`);
}

export async function createProduct(payload: ProductCreate): Promise<Product> {
  return request<Product>('/api/v1/inventory', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateProduct(id: string, payload: ProductUpdate): Promise<Product> {
  return request<Product>(`/api/v1/inventory/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function deleteProduct(id: string): Promise<{ success: boolean; id: string }> {
  return request<{ success: boolean; id: string }>(`/api/v1/inventory/${id}`, {
    method: 'DELETE',
  });
}

export async function getLowStockProducts(): Promise<Product[]> {
  return request<Product[]>('/api/v1/inventory/low-stock');
}

export async function getInventoryAnalysis(category?: string): Promise<InventoryAnalysisSummary> {
  const query = category ? `?category=${encodeURIComponent(category)}` : '';
  return request<InventoryAnalysisSummary>(`/api/v1/inventory/analysis${query}`);
}

export async function getReorderRecommendations(
  category?: string
): Promise<ReorderRecommendationsResponse> {
  const query = category ? `?category=${encodeURIComponent(category)}` : '';
  return request<ReorderRecommendationsResponse>(`/api/v1/inventory/reorder-recommendations${query}`);
}

// ==========================================
// AI Agent Endpoints
// ==========================================
export async function getAgentInsights(category?: string): Promise<InventoryInsightsResponse> {
  const query = category ? `?category=${encodeURIComponent(category)}` : '';
  return request<InventoryInsightsResponse>(`/api/v1/agent/insights${query}`);
}

export async function queryAgent(
  query: string,
  category?: string | null
): Promise<AgentQueryResponse> {
  return request<AgentQueryResponse>('/api/v1/agent/query', {
    method: 'POST',
    body: JSON.stringify({ query, category: category || null }),
  });
}

// ==========================================
// Approvals Endpoints
// ==========================================
export async function listApprovals(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<ApprovalListResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.append('status', params.status);
  if (params?.limit !== undefined) query.append('limit', params.limit.toString());
  if (params?.offset !== undefined) query.append('offset', params.offset.toString());

  const qs = query.toString();
  return request<ApprovalListResponse>(`/api/v1/approvals${qs ? `?${qs}` : ''}`);
}

export async function getApproval(id: string): Promise<ApprovalRequest> {
  return request<ApprovalRequest>(`/api/v1/approvals/${id}`);
}

export async function createApproval(
  payload: ApprovalRequestCreate
): Promise<ApprovalRequest> {
  return request<ApprovalRequest>('/api/v1/approvals', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function createApprovalFromRecommendation(
  productId: string
): Promise<ApprovalRequest> {
  return request<ApprovalRequest>('/api/v1/approvals/from-recommendation', {
    method: 'POST',
    body: JSON.stringify({ product_id: productId }),
  });
}

export async function updateApprovalQuantity(
  id: string,
  proposedReorderQuantity: number,
  notes?: string
): Promise<ApprovalRequest> {
  return request<ApprovalRequest>(`/api/v1/approvals/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({
      proposed_reorder_quantity: proposedReorderQuantity,
      notes: notes || undefined,
    }),
  });
}

export async function approveRequest(id: string, notes?: string): Promise<ApprovalRequest> {
  return request<ApprovalRequest>(`/api/v1/approvals/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify({ notes: notes || null }),
  });
}

export async function rejectRequest(id: string, notes?: string): Promise<ApprovalRequest> {
  return request<ApprovalRequest>(`/api/v1/approvals/${id}/reject`, {
    method: 'POST',
    body: JSON.stringify({ notes: notes || null }),
  });
}

export async function executeApproval(
  id: string,
  notes?: string
): Promise<ReorderTask> {
  const query = notes ? `?execution_notes=${encodeURIComponent(notes)}` : '';
  return request<ReorderTask>(
    `/api/v1/approvals/${id}/execute${query}`,
    {
      method: 'POST',
    }
  );
}

// ==========================================
// Reorder Tasks Endpoints
// ==========================================
export async function listTasks(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<ReorderTaskListResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.append('status', params.status);
  if (params?.limit !== undefined) query.append('limit', params.limit.toString());
  if (params?.offset !== undefined) query.append('offset', params.offset.toString());

  const qs = query.toString();
  return request<ReorderTaskListResponse>(`/api/v1/tasks${qs ? `?${qs}` : ''}`);
}

export async function getTask(id: string): Promise<ReorderTask> {
  return request<ReorderTask>(`/api/v1/tasks/${id}`);
}

export async function getTaskByApproval(approvalId: string): Promise<ReorderTask> {
  return request<ReorderTask>(`/api/v1/tasks/by-approval/${approvalId}`);
}
