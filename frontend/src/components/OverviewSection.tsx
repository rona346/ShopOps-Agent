import React from 'react';
import { InventoryAnalysisSummary, ApprovalListResponse, ReorderTaskListResponse } from '../types';

export interface OverviewSectionProps {
  analysis: InventoryAnalysisSummary | null;
  pendingApprovals: ApprovalListResponse | null;
  tasks: ReorderTaskListResponse | null;
  loading: boolean;
  error: string | null;
  onNavigateTab: (tab: string) => void;
  onRefresh: () => void;
}

export const OverviewSection: React.FC<OverviewSectionProps> = ({
  analysis,
  pendingApprovals,
  tasks,
  loading,
  error,
  onNavigateTab,
  onRefresh,
}) => {
  const totalProducts = analysis?.total_products ?? 0;
  const outOfStockCount = analysis?.out_of_stock_count ?? 0;
  const lowStockCount = analysis?.low_stock_count ?? 0;
  const overstockCount = analysis?.overstock_count ?? 0;
  const pendingApprovalsCount = pendingApprovals?.total ?? 0;
  const createdTasksCount = tasks?.items?.filter((t) => t.status === 'created').length ?? 0;
  const totalTasksCount = tasks?.total ?? 0;

  return (
    <div className="section-container">
      <div className="section-header">
        <div>
          <h2>Store Operational Overview</h2>
          <p className="section-subtitle">
            Real-time inventory metrics, deterministic replenishment triggers, and pending operational decisions.
          </p>
        </div>
        <div className="section-header-actions">
          <button className="btn btn-secondary" onClick={onRefresh} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh Metrics'}
          </button>
        </div>
      </div>

      {error && (
        <div className="alert-box alert-warning">
          <strong>Backend Notice:</strong> {error}
        </div>
      )}

      {/* 6 Core Metric Cards */}
      <div className="metric-grid">
        <div
          className="metric-card clickable"
          onClick={() => onNavigateTab('inventory')}
          title="View all products in inventory"
        >
          <div className="metric-header">
            <span className="metric-title">Total Products</span>
            <span className="metric-icon">📦</span>
          </div>
          <div className="metric-value">{loading && !analysis ? '...' : totalProducts}</div>
          <div className="metric-subtext">Active catalog SKUs</div>
        </div>

        <div
          className="metric-card metric-card-danger clickable"
          onClick={() => onNavigateTab('analysis')}
          title="Inspect out-of-stock products in Analysis"
        >
          <div className="metric-header">
            <span className="metric-title">Out of Stock</span>
            <span className="metric-icon">🚫</span>
          </div>
          <div className="metric-value text-danger">
            {loading && !analysis ? '...' : outOfStockCount}
          </div>
          <div className="metric-subtext">0 units on shelf</div>
        </div>

        <div
          className="metric-card metric-card-warning clickable"
          onClick={() => onNavigateTab('analysis')}
          title="Inspect low-stock products in Analysis"
        >
          <div className="metric-header">
            <span className="metric-title">Low Stock</span>
            <span className="metric-icon">⚠️</span>
          </div>
          <div className="metric-value text-warning">
            {loading && !analysis ? '...' : lowStockCount}
          </div>
          <div className="metric-subtext">Stock &le; Reorder point</div>
        </div>

        <div
          className="metric-card metric-card-info clickable"
          onClick={() => onNavigateTab('analysis')}
          title="Inspect overstock products in Analysis"
        >
          <div className="metric-header">
            <span className="metric-title">Overstock</span>
            <span className="metric-icon">📈</span>
          </div>
          <div className="metric-value text-info">
            {loading && !analysis ? '...' : overstockCount}
          </div>
          <div className="metric-subtext">Stock &gt; 3&times; reorder point</div>
        </div>

        <div
          className="metric-card metric-card-primary clickable"
          onClick={() => onNavigateTab('approvals')}
          title="Review pending replenishment approvals"
        >
          <div className="metric-header">
            <span className="metric-title">Pending Approvals</span>
            <span className="metric-icon">⏳</span>
          </div>
          <div className="metric-value text-primary">
            {loading && !pendingApprovals ? '...' : pendingApprovalsCount}
          </div>
          <div className="metric-subtext">Awaiting owner decision</div>
        </div>

        <div
          className="metric-card metric-card-success clickable"
          onClick={() => onNavigateTab('tasks')}
          title="View internal reorder execution tasks"
        >
          <div className="metric-header">
            <span className="metric-title">Created Reorder Tasks</span>
            <span className="metric-icon">📋</span>
          </div>
          <div className="metric-value text-success">
            {loading && !tasks ? '...' : `${createdTasksCount} / ${totalTasksCount}`}
          </div>
          <div className="metric-subtext">Internal execution backlog</div>
        </div>
      </div>

      {/* Quick Action & Financial Summary Banner */}
      <div className="dashboard-summary-row">
        <div className="card summary-highlight-card">
          <div className="card-body">
            <h3>Replenishment Financial Summary</h3>
            <div className="financial-stats-row">
              <div className="fstat">
                <span className="fstat-label">Total Units on Hand</span>
                <span className="fstat-val">
                  {analysis?.total_inventory_units?.toLocaleString() ?? 0}
                </span>
              </div>
              <div className="fstat">
                <span className="fstat-label">Recommended Reorder Units</span>
                <span className="fstat-val text-primary font-bold">
                  {analysis?.total_recommended_reorder_units?.toLocaleString() ?? 0}
                </span>
              </div>
              <div className="fstat">
                <span className="fstat-label">Estimated Reorder Capital</span>
                <span className="fstat-val text-success font-bold">
                  ${(analysis?.estimated_total_reorder_cost ?? 0).toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="card quick-actions-card">
          <div className="card-body">
            <h3>Quick Actions</h3>
            <div className="action-buttons-list">
              <button
                className="btn btn-outline full-width"
                onClick={() => onNavigateTab('analysis')}
              >
                📊 View Reorder Recommendations
              </button>
              <button
                className="btn btn-outline full-width"
                onClick={() => onNavigateTab('approvals')}
              >
                ⚖️ Review Pending Reorder Decisions
              </button>
              <button
                className="btn btn-outline full-width"
                onClick={() => onNavigateTab('agent')}
              >
                🤖 Ask AI Inventory Assistant
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
