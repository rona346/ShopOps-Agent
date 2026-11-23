import React, { useState, useEffect } from 'react';
import { Product, ProductCreate, ProductUpdate, ProductListResponse } from '../types';
import { listProducts, createProduct, updateProduct, deleteProduct } from '../services/api';
import { ProductModal } from './ProductModal';
import { Modal } from './Modal';

export interface InventorySectionProps {
  onNotify: (type: 'success' | 'error' | 'warning' | 'info', message: string) => void;
}

export const InventorySection: React.FC<InventorySectionProps> = ({ onNotify }) => {
  const [products, setProducts] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [limit] = useState(10);
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Modals state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);

  // Delete confirmation
  const [productToDelete, setProductToDelete] = useState<Product | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetchProducts = async () => {
    try {
      setLoading(true);
      setError(null);
      const res: ProductListResponse = await listProducts({
        search: search.trim() || undefined,
        category: categoryFilter.trim() || undefined,
        limit,
        offset,
      });
      setProducts(res.items);
      setTotal(res.total);
    } catch (err: any) {
      const msg = err.message || 'Failed to fetch inventory products';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, [offset, categoryFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setOffset(0);
    fetchProducts();
  };

  const handleOpenCreate = () => {
    setSelectedProduct(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (p: Product) => {
    setSelectedProduct(p);
    setIsModalOpen(true);
  };

  const handleSaveProduct = async (data: ProductCreate | ProductUpdate, isEdit: boolean) => {
    if (isEdit && selectedProduct) {
      await updateProduct(selectedProduct.id, data as ProductUpdate);
      onNotify('success', `Product "${selectedProduct.name}" updated successfully.`);
    } else {
      await createProduct(data as ProductCreate);
      onNotify('success', 'New product created successfully.');
    }
    fetchProducts();
  };

  const handleConfirmDelete = async () => {
    if (!productToDelete) return;
    try {
      setDeleting(true);
      await deleteProduct(productToDelete.id);
      onNotify('success', `Product "${productToDelete.name}" removed from inventory.`);
      setProductToDelete(null);
      fetchProducts();
    } catch (err: any) {
      onNotify('error', err.message || 'Failed to delete product.');
    } finally {
      setDeleting(false);
    }
  };

  const totalPages = Math.ceil(total / limit) || 1;
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <div className="section-container">
      <div className="section-header">
        <div>
          <h2>Inventory Catalog</h2>
          <p className="section-subtitle">
            Manage your store's stock levels, reorder thresholds, and unit costs.
          </p>
        </div>
        <div className="section-header-actions">
          <button className="btn btn-primary" onClick={handleOpenCreate}>
            + Add Product
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="filter-bar">
        <form onSubmit={handleSearchSubmit} className="search-form">
          <input
            type="text"
            className="form-control"
            placeholder="Search by SKU or Product Name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button type="submit" className="btn btn-secondary">
            Search
          </button>
          {search && (
            <button
              type="button"
              className="btn btn-outline"
              onClick={() => {
                setSearch('');
                setOffset(0);
                setTimeout(fetchProducts, 0);
              }}
            >
              Clear
            </button>
          )}
        </form>

        <div className="category-filter">
          <input
            type="text"
            className="form-control"
            placeholder="Filter by category..."
            value={categoryFilter}
            onChange={(e) => {
              setCategoryFilter(e.target.value);
              setOffset(0);
            }}
          />
        </div>
      </div>

      {error && (
        <div className="alert-box alert-warning">
          <strong>Notice:</strong> {error}
        </div>
      )}

      {/* Products Table */}
      <div className="card table-card">
        {loading ? (
          <div className="loading-state">
            <span className="spin">🔄</span>
            <p>Loading inventory items...</p>
          </div>
        ) : products.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📦</div>
            <h3>No Products Found</h3>
            <p>
              {search || categoryFilter
                ? 'Try adjusting your search query or category filter.'
                : 'Your inventory catalog is currently empty. Add your first product to get started.'}
            </p>
            {!search && !categoryFilter && (
              <button className="btn btn-primary" onClick={handleOpenCreate}>
                + Add First Product
              </button>
            )}
          </div>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>SKU</th>
                  <th>Product Name</th>
                  <th>Category</th>
                  <th>Stock Qty</th>
                  <th>Reorder Point</th>
                  <th>Unit Cost</th>
                  <th>Status</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {products.map((p) => {
                  const isLow = p.quantity <= p.reorder_point;
                  const isOut = p.quantity === 0;

                  return (
                    <tr key={p.id}>
                      <td className="code-cell">{p.sku}</td>
                      <td>
                        <div className="product-name font-semibold">{p.name}</div>
                        {p.supplier_name && (
                          <div className="product-supplier text-muted">
                            {p.supplier_name}
                          </div>
                        )}
                      </td>
                      <td>
                        <span className="category-pill">{p.category}</span>
                      </td>
                      <td>
                        <span className={`font-bold ${isOut ? 'text-danger' : isLow ? 'text-warning' : ''}`}>
                          {p.quantity} {p.unit || 'pcs'}
                        </span>
                      </td>
                      <td>{p.reorder_point}</td>
                      <td>
                        {p.unit_cost !== null && p.unit_cost !== undefined
                          ? `$${p.unit_cost.toFixed(2)}`
                          : '—'}
                      </td>
                      <td>
                        {isOut ? (
                          <span className="badge badge-danger">Out of Stock</span>
                        ) : isLow ? (
                          <span className="badge badge-warning">Low Stock</span>
                        ) : (
                          <span className="badge badge-success">Healthy</span>
                        )}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div className="table-actions">
                          <button
                            className="btn btn-sm btn-outline"
                            onClick={() => handleOpenEdit(p)}
                            title="Edit product details"
                          >
                            Edit
                          </button>
                          <button
                            className="btn btn-sm btn-danger-outline"
                            onClick={() => setProductToDelete(p)}
                            title="Delete product"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {total > limit && (
          <div className="pagination-bar">
            <span className="pagination-info">
              Showing {offset + 1} to {Math.min(offset + limit, total)} of {total} products
            </span>
            <div className="pagination-buttons">
              <button
                className="btn btn-sm btn-secondary"
                disabled={offset === 0 || loading}
                onClick={() => setOffset(Math.max(0, offset - limit))}
              >
                &larr; Previous
              </button>
              <span className="page-indicator">
                Page {currentPage} of {totalPages}
              </span>
              <button
                className="btn btn-sm btn-secondary"
                disabled={offset + limit >= total || loading}
                onClick={() => setOffset(offset + limit)}
              >
                Next &rarr;
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Product Create/Edit Modal */}
      <ProductModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        product={selectedProduct}
        onSave={handleSaveProduct}
      />

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={!!productToDelete}
        onClose={() => setProductToDelete(null)}
        title="Confirm Delete Product"
        footer={
          <div className="modal-footer-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setProductToDelete(null)}
              disabled={deleting}
            >
              Cancel
            </button>
            <button
              type="button"
              className="btn btn-danger"
              onClick={handleConfirmDelete}
              disabled={deleting}
            >
              {deleting ? 'Deleting...' : 'Delete Product'}
            </button>
          </div>
        }
      >
        <p>
          Are you sure you want to delete <strong>{productToDelete?.name}</strong> (SKU:{' '}
          {productToDelete?.sku})?
        </p>
        <p style={{ marginTop: '0.5rem', color: '#64748b', fontSize: '0.875rem' }}>
          This will permanently remove the item from your store inventory catalog.
        </p>
      </Modal>
    </div>
  );
};
