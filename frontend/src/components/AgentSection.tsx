import React, { useState, useEffect } from 'react';
import {
  InventoryInsightsResponse,
  AgentQueryResponse,
} from '../types';
import { getAgentInsights, queryAgent } from '../services/api';

export interface AgentSectionProps {
  onNotify: (type: 'success' | 'error' | 'warning' | 'info', message: string) => void;
}

export const AgentSection: React.FC<AgentSectionProps> = ({ onNotify }) => {
  // Insights state
  const [insights, setInsights] = useState<InventoryInsightsResponse | null>(null);
  const [loadingInsights, setLoadingInsights] = useState(false);
  const [insightsError, setInsightsError] = useState<string | null>(null);

  // Q&A state
  const [userQuery, setUserQuery] = useState('');
  const [queryCategory, setQueryCategory] = useState('');
  const [queryLoading, setQueryLoading] = useState(false);
  const [queryResult, setQueryResult] = useState<AgentQueryResponse | null>(null);
  const [queryError, setQueryError] = useState<string | null>(null);

  const fetchInsights = async () => {
    try {
      setLoadingInsights(true);
      setInsightsError(null);
      const res = await getAgentInsights();
      setInsights(res);
      onNotify('success', 'Executive inventory briefing updated.');
    } catch (err: any) {
      setInsightsError(err.message || 'Failed to generate inventory insights');
    } finally {
      setLoadingInsights(false);
    }
  };

  useEffect(() => {
    fetchInsights();
  }, []);

  const handleAskQuestion = async (e?: React.FormEvent, customQuery?: string) => {
    if (e) e.preventDefault();
    const queryToAsk = customQuery || userQuery;
    if (!queryToAsk.trim() || queryToAsk.trim().length < 2) {
      setQueryError('Please enter a query with at least 2 characters.');
      return;
    }

    try {
      setQueryLoading(true);
      setQueryError(null);
      const res = await queryAgent(queryToAsk.trim(), queryCategory.trim() || null);
      setQueryResult(res);
      setUserQuery(queryToAsk);
    } catch (err: any) {
      setQueryError(err.message || 'Failed to query inventory assistant');
    } finally {
      setQueryLoading(false);
    }
  };

  const sampleQuestions = [
    'Which items are critically low or out of stock?',
    'What is our total recommended reorder cost?',
    'Do we have any overstocked items tying up cash?',
    'Which products should I order first today?',
  ];

  return (
    <div className="section-container">
      <div className="section-header">
        <div>
          <h2>AI Inventory Agent</h2>
          <p className="section-subtitle">
            Gemini-powered operational briefings and interactive natural language inventory inquiry.
          </p>
        </div>
        <div className="section-header-actions">
          <button
            className="btn btn-secondary"
            onClick={fetchInsights}
            disabled={loadingInsights}
          >
            {loadingInsights ? 'Analyzing...' : 'Refresh Executive Briefing'}
          </button>
        </div>
      </div>

      {/* Ground Truth Safety Banner */}
      <div className="alert-box alert-info" style={{ marginBottom: '1.5rem' }}>
        <strong>Source of Truth Distinction:</strong>
        <p style={{ marginTop: '0.25rem', fontSize: '0.875rem' }}>
          Deterministic calculations (quantities, reorder thresholds, and unit costs) are computed by the deterministic analysis engine.
          The AI Agent synthesizes these numbers into business explanations and prioritized operational guidance without altering stock counts or placing automated orders.
        </p>
      </div>

      <div className="agent-layout-grid">
        {/* Left Column: Executive AI Briefing */}
        <div className="agent-column">
          <div className="card agent-card">
            <div className="card-header">
              <h3>📋 Executive Store Briefing</h3>
              <span className="badge badge-primary">Gemini 3.8 Flash</span>
            </div>

            <div className="card-body">
              {loadingInsights ? (
                <div className="loading-state">
                  <span className="spin">🤖</span>
                  <p>Synthesizing current inventory health with Gemini...</p>
                </div>
              ) : insightsError ? (
                <div className="alert-box alert-warning">
                  <strong>Service Notice:</strong> {insightsError}
                  {insightsError.includes('GEMINI_API_KEY') && (
                    <p style={{ marginTop: '0.5rem', fontSize: '0.85rem' }}>
                      Set your <code>GEMINI_API_KEY</code> in <code>backend/.env</code> to enable live Gemini AI synthesis.
                    </p>
                  )}
                </div>
              ) : !insights ? (
                <div className="empty-state">
                  <p>No briefing available. Click "Refresh Executive Briefing" above.</p>
                </div>
              ) : (
                <div className="insights-content">
                  {/* Summary */}
                  <div className="insight-block">
                    <h4 className="insight-heading">Operational Summary</h4>
                    <p className="insight-text">{insights.summary}</p>
                  </div>

                  {/* Critical Alerts */}
                  {insights.critical_alerts && insights.critical_alerts.length > 0 && (
                    <div className="insight-block">
                      <h4 className="insight-heading text-danger">⚠️ Critical Stock Alerts</h4>
                      <ul className="insight-list alert-list">
                        {insights.critical_alerts.map((alert, idx) => (
                          <li key={idx} className="alert-item-danger">
                            {alert}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Reorder Advice */}
                  <div className="insight-block">
                    <h4 className="insight-heading text-primary">🔄 Replenishment Guidance</h4>
                    <p className="insight-text">{insights.reorder_advice}</p>
                  </div>

                  {/* Overstock Advice */}
                  {insights.overstock_advice && (
                    <div className="insight-block">
                      <h4 className="insight-heading text-info">📈 Capital Release & Overstock</h4>
                      <p className="insight-text">{insights.overstock_advice}</p>
                    </div>
                  )}

                  {/* Action Items */}
                  {insights.action_items && insights.action_items.length > 0 && (
                    <div className="insight-block">
                      <h4 className="insight-heading text-success">✅ Recommended Actions Today</h4>
                      <ul className="insight-list">
                        {insights.action_items.map((item, idx) => (
                          <li key={idx} className="action-item">
                            {item}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Interactive Q&A Assistant */}
        <div className="agent-column">
          <div className="card agent-card">
            <div className="card-header">
              <h3>💬 Ask ShopOps Assistant</h3>
              <span className="badge badge-success">Interactive Q&amp;A</span>
            </div>

            <div className="card-body">
              <form onSubmit={handleAskQuestion} className="agent-query-form">
                <div className="form-group">
                  <label htmlFor="user-q">Ask anything about your store's inventory:</label>
                  <div className="input-group">
                    <input
                      id="user-q"
                      type="text"
                      className="form-control"
                      placeholder="e.g. How much will it cost to replenish dairy items?"
                      value={userQuery}
                      onChange={(e) => setUserQuery(e.target.value)}
                      disabled={queryLoading}
                    />
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={queryLoading || !userQuery.trim()}
                    >
                      {queryLoading ? 'Asking...' : 'Ask'}
                    </button>
                  </div>
                </div>

                <div className="form-group" style={{ marginBottom: '1rem' }}>
                  <input
                    type="text"
                    className="form-control form-control-sm"
                    placeholder="Optional category filter (e.g. Beverages)"
                    value={queryCategory}
                    onChange={(e) => setQueryCategory(e.target.value)}
                    disabled={queryLoading}
                  />
                </div>
              </form>

              {/* Sample Questions Pills */}
              <div className="suggested-queries">
                <span className="suggested-label">Try asking:</span>
                <div className="query-pills">
                  {sampleQuestions.map((q, idx) => (
                    <button
                      key={idx}
                      className="query-pill"
                      onClick={() => handleAskQuestion(undefined, q)}
                      disabled={queryLoading}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>

              {/* Query Error */}
              {queryError && (
                <div className="alert-box alert-warning" style={{ marginTop: '1rem' }}>
                  <strong>Notice:</strong> {queryError}
                </div>
              )}

              {/* Query Result Display */}
              {queryLoading ? (
                <div className="loading-state" style={{ marginTop: '1.5rem' }}>
                  <span className="spin">🤖</span>
                  <p>Consulting inventory database...</p>
                </div>
              ) : queryResult ? (
                <div className="query-response-card" style={{ marginTop: '1.5rem' }}>
                  <div className="response-header">
                    <span className="response-badge">Agent Answer</span>
                  </div>
                  <div className="response-text">{queryResult.answer}</div>

                  {/* Relevant SKUs */}
                  {queryResult.relevant_skus && queryResult.relevant_skus.length > 0 && (
                    <div className="referenced-section">
                      <span className="sub-label">Referenced SKUs:</span>
                      <div className="sku-tag-list">
                        {queryResult.relevant_skus.map((sku, idx) => (
                          <span key={idx} className="sku-tag">
                            {sku}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Referenced Metrics */}
                  {queryResult.referenced_metrics &&
                    Object.keys(queryResult.referenced_metrics).length > 0 && (
                      <div className="referenced-section">
                        <span className="sub-label">Ground Truth Metrics:</span>
                        <div className="metric-tags">
                          {Object.entries(queryResult.referenced_metrics).map(([k, v]) => (
                            <span key={k} className="metric-tag">
                              {k.replace(/_/g, ' ')}: <strong>{String(v)}</strong>
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                  {/* Follow-up suggestions */}
                  {queryResult.suggested_followups &&
                    queryResult.suggested_followups.length > 0 && (
                      <div className="followup-section">
                        <span className="sub-label">Suggested follow-ups:</span>
                        <div className="followup-list">
                          {queryResult.suggested_followups.map((f, idx) => (
                            <button
                              key={idx}
                              className="followup-btn"
                              onClick={() => handleAskQuestion(undefined, f)}
                            >
                              👉 {f}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
