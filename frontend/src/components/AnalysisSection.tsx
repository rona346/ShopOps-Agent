import React, { useState, useEffect } from 'react';
import {
  InventoryAnalysisSummary,
  ProductAnalysisItem,
} from '../types';
import {
  getInventoryAnalysis,
  createApprovalFromRecommendation,
} from '../services/api';

export interface AnalysisSectionProps {
  onNotify: (type: 'success' | 'error' | 'warning' | 'info', message: string) => void;
  onNavigateToApprovals: () => void;
}

export const AnalysisSection: React.FC<AnalysisSectionProps> = ({
  onNotify,
  onNavigateToApprovals,
}) => {
  const [analysis, setAnalysis] = useState<InventoryAnalysisSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [creatingApprovalForId, setCreatingApprovalForId] = useState<string | null>(null);

  const fetchAnalysis = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await getInventoryAnalysis();
      setAnalysis(res);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch inventory analysis');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalysis();
  }, []);

  const handleCreateApproval = async (item: ProductAnalysisItem) => {
    try {
      setCreatingApprovalForId(item.product_id);
      await createApprovalFromRecommendation(item.product_id);
      onNotify(
        'success',
        `Reorder approval request created for "${item.name}" (${item.recommended_reorder_quantity} units).`
      );
    } catch (err: any) {
      onNotify('error', err.message || 'Failed to create approval request');
    } finally {
      setCreatingApprovalForId(null);
    }
  };

  const filteredItems = (analysis?.items || []).filter((item) => {
    if (statusFilter === 'all') return true;
    if (statusFilter === 'needs_reorder') {
      return item.recommended_reorder_quantity > 0;
    }
    return item.status === statusFilter;
  });

  return (
    <div className="section-container">
      <div className="section-header">
        <div>
          <h2>Inventory Analysis & Reorder Planning</h2>
          <p className="section-subtitle">
            Deterministic stock analysis and rule-based replenishment calculations (reorder point + safety buffer).
          </p>
        </div>
        <div className="section-header-actions">
          <button className="btn btn-outline" onClick={onNavigateToApprovals}>
            Go to Approvals &rarr;
          </button>
          <button className="btn btn-secondary" onClick={fetchAnalysis} disabled={loading}>
            {loading ? 'Analyzing...' : 'Re-run Analysis'}
          </button>
        </div>
      </div>

      {error && (
        <div className="alert-box alert-warning">
          <strong>Notice:</strong> {error}
        </div>
      )}

      {/* Analysis Metrics Summary */}
      <div className="metric-grid">
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">Units on Hand</span>
            <span className="metric-icon">📦</span>
          </div>
          <div className="metric-value">
            {analysis?.total_inventory_units?.toLocaleString() ?? 0}
          </div>
          <div className="metric-subtext">Across {analysis?.total_products ?? 0} SKUs</div>
        </div>

        <div className="metric-card metric-card-danger">
          <div className="metric-header">
            <span className="metric-title">Out of Stock</span>
            <span className="metric-icon">🚫</span>
          </div>
          <div className="metric-value text-danger">
            {analysis?.out_of_stock_count ?? 0}
          </div>
          <div className="metric-subtext">Stock = 0 units</div>
        </div>

        <div className="metric-card metric-card-warning">
          <div className="metric-header">
            <span className="metric-title">Low Stock</span>
            <span className="metric-icon">⚠️</span>
          </div>
          <div className="metric-value text-warning">
            {analysis?.low_stock_count ?? 0}
          </div>
          <div className="metric-subtext">Stock &le; Reorder point</div>
        </div>

        <div className="metric-card metric-card-info">
          <div className="metric-header">
            <span className="metric-title">Overstock</span>
            <span className="metric-icon">📈</span>
          </div>
          <div className="metric-value text-info">
            {analysis?.overstock_count ?? 0}
          </div>
          <div className="metric-subtext">Stock &gt; 3&times; reorder point</div>
        </div>

        <div className="metric-card metric-card-primary">
          <div className="metric-header">
            <span className="metric-title">Reorder Units Needed</span>
            <span className="metric-icon">🔄</span>
          </div>
          <div className="metric-value text-primary">
            {analysis?.total_recommended_reorder_units?.toLocaleString() ?? 0}
          </div>
          <div className="metric-subtext">Calculated replenishment sum</div>
        </div>

        <div className="metric-card metric-card-success">
          <div className="metric-header">
            <span className="metric-title">Estimated Reorder Cost</span>
            <span className="metric-icon">💰</span>
          </div>
          <div className="metric-value text-success">
            ${(analysis?.estimated_total_reorder_cost ?? 0).toLocaleString(undefined, {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </div>
          <div className="metric-subtext">Based on recorded unit costs</div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="filter-tabs">
        <button
          className={`filter-tab ${statusFilter === 'all' ? 'active' : ''}`}
          onClick={() => setStatusFilter('all')}
        >
          All Items ({analysis?.items.length ?? 0})
        </button>
        <button
          className={`filter-tab ${statusFilter === 'needs_reorder' ? 'active' : ''}`}
          onClick={() => setStatusFilter('needs_reorder')}
        >
          Needs Reorder (
          {(analysis?.items || []).filter((i) => i.recommended_reorder_quantity > 0).length}
          )
        </button>
        <button
          className={`filter-tab ${statusFilter === 'out_of_stock' ? 'active' : ''}`}
          onClick={() => setStatusFilter('out_of_stock')}
        >
          Out of Stock ({analysis?.out_of_stock_count ?? 0})
        </button>
        <button
          className={`filter-tab ${statusFilter === 'low_stock' ? 'active' : ''}`}
          onClick={() => setStatusFilter('low_stock')}
        >
          Low Stock ({analysis?.low_stock_count ?? 0})
        </button>
        <button
          className={`filter-tab ${statusFilter === 'overstock' ? 'active' : ''}`}
          onClick={() => setStatusFilter('overstock')}
        >
          Overstock ({analysis?.overstock_count ?? 0})
        </button>
        <button
          className={`filter-tab ${statusFilter === 'normal' ? 'active' : ''}`}
          onClick={() => setStatusFilter('normal')}
        >
          Normal Stock ({analysis?.normal_stock_count ?? 0})
        </button>
      </div>

      {/* Items Table */}
      <div className="card table-card">
        {loading ? (
          <div className="loading-state">
            <span className="spin">🔄</span>
            <p>Evaluating inventory metrics...</p>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">✨</div>
            <h3>No Products in this Category</h3>
            <p>No products currently match the selected status filter.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Product</th>
                  <th>SKU</th>
                  <th>Current Qty</th>
                  <th>Reorder Point</th>
                  <th>Status</th>
                  <th>Recommended Reorder</th>
                  <th>Estimated Cost</th>
                  <th>Deterministic Reason</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((item) => {
                  const needsReorder = item.recommended_reorder_quantity > 0;

                  return (
                    <tr key={item.product_id}>
                      <td>
                        <div className="font-semibold">{item.name}</div>
                        <div className="text-muted" style={{ fontSize: '0.8rem' }}>
                          {item.category}
                        </div>
                      </td>
                      <td className="code-cell">{item.sku}</td>
                      <td>
                        <span className="font-bold">
                          {item.current_quantity} {item.unit}
                        </span>
                      </td>
                      <td>{item.reorder_point}</td>
                      <td>
                        {item.status === 'out_of_stock' && (
                          <span className="badge badge-danger">Out of Stock</span>
                        )}
                        {item.status === 'low_stock' && (
                          <span className="badge badge-warning">Low Stock</span>
                        )}
                        {item.status === 'overstock' && (
                          <span className="badge badge-info">Overstock</span>
                        )}
                        {item.status === 'normal' && (
                          <span className="badge badge-success">Healthy</span>
                        )}
                      </td>
                      <td>
                        {needsReorder ? (
                          <span className="font-bold text-primary">
                            +{item.recommended_reorder_quantity} {item.unit}
                          </span>
                        ) : (
                          <span className="text-muted">0</span>
                        )}
                      </td>
                      <td>
                        {item.estimated_reorder_cost != null && needsReorder
                          ? `$${item.estimated_reorder_cost.toFixed(2)}`
                          : '—'}
                      </td>
                      <td style={{ maxWidth: '300px', fontSize: '0.85rem' }}>
                        {item.reason}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        {needsReorder ? (
                          <button
                            className="btn btn-sm btn-primary"
                            disabled={creatingApprovalForId === item.product_id}
                            onClick={() => handleCreateApproval(item)}
                            title="Propose reorder approval request to owner"
                          >
                            {creatingApprovalForId === item.product_id
                              ? 'Proposing...'
                              : 'Request Reorder'}
                          </button>
                        ) : (
                          <span className="text-muted" style={{ fontSize: '0.8rem' }}>
                            Adequate
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
