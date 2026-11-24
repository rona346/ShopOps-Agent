/**
 * TypeScript Data Models for ShopOps Agent Frontend
 * Strictly aligned with FastAPI backend Pydantic models.
 */

export interface Product {
  id: string;
  name: string;
  sku: string;
  category: string;
  quantity: number;
  reorder_point: number;
  unit: string;
  unit_cost?: number | null;
  supplier_name?: string | null;
  description?: string | null;
  is_low_stock?: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductCreate {
  name: string;
  sku: string;
  category: string;
  quantity: number;
  reorder_point: number;
  unit?: string;
  unit_cost?: number | null;
  supplier_name?: string | null;
  description?: string | null;
}

export interface ProductUpdate {
  name?: string;
  sku?: string;
  category?: string;
  quantity?: number;
  reorder_point?: number;
  unit?: string;
  unit_cost?: number | null;
  supplier_name?: string | null;
  description?: string | null;
}

export interface ProductListResponse {
  items: Product[];
  total: number;
  limit: number;
  offset: number;
}

export type StockStatus = 'out_of_stock' | 'low_stock' | 'normal' | 'overstock';

export interface ProductAnalysisItem {
  product_id: string;
  sku: string;
  name: string;
  category: string;
  current_quantity: number;
  reorder_point: number;
  unit: string;
  unit_cost?: number | null;
  status: StockStatus;
  recommended_reorder_quantity: number;
  estimated_reorder_cost?: number | null;
  reason: string;
}

export interface InventoryAnalysisSummary {
  total_products: number;
  total_inventory_units: number;
  out_of_stock_count: number;
  low_stock_count: number;
  normal_stock_count: number;
  overstock_count: number;
  total_recommended_reorder_units: number;
  estimated_total_reorder_cost: number;
  items: ProductAnalysisItem[];
}

export interface ReorderRecommendationsResponse {
  total_items_to_reorder: number;
  total_recommended_units: number;
  estimated_total_cost: number;
  items: ProductAnalysisItem[];
}

export interface InventoryInsightsResponse {
  summary: string;
  critical_alerts: string[];
  reorder_advice: string;
  overstock_advice?: string | null;
  action_items: string[];
}

export interface AgentQueryRequest {
  query: string;
  category?: string | null;
}

export interface AgentQueryResponse {
  answer: string;
  relevant_skus: string[];
  referenced_metrics: Record<string, any>;
  suggested_followups: string[];
}

export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'executed';
export type ApprovalActionType = 'reorder';

export interface ApprovalRequest {
  id: string;
  action_type: ApprovalActionType;
  product_id: string;
  sku: string;
  product_name: string;
  current_quantity: number;
  proposed_reorder_quantity: number;
  reason: string;
  estimated_cost?: number | null;
  status: ApprovalStatus;
  owner_notes?: string | null;
  decided_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApprovalRequestCreate {
  action_type?: ApprovalActionType;
  product_id: string;
  sku: string;
  product_name: string;
  current_quantity: number;
  proposed_reorder_quantity: number;
  reason: string;
  estimated_cost?: number | null;
}

export interface ApprovalListResponse {
  items: ApprovalRequest[];
  total: number;
  limit: number;
  offset: number;
}

export type TaskStatus = 'created' | 'in_progress' | 'completed' | 'cancelled';

export interface ReorderTask {
  id: string;
  approval_id: string;
  product_id: string;
  sku: string;
  product_name: string;
  approved_reorder_quantity: number;
  estimated_cost?: number | null;
  status: TaskStatus;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReorderTaskListResponse {
  items: ReorderTask[];
  total: number;
  limit: number;
  offset: number;
}

export interface HealthResponse {
  status: string;
  service: string;
  environment: string;
}

export interface AuthenticatedUser {
  uid: string;
  email?: string | null;
  role: string;
}

export interface AuthStatusResponse {
  supabase_configured?: boolean;
  firebase_configured: boolean;
  auth_provider: string;
  owner_email_configured: boolean;
  environment: string;
}
