import React, { useState, useEffect } from 'react';
import { Modal } from './Modal';
import { Product, ProductCreate, ProductUpdate } from '../types';

export interface ProductModalProps {
  isOpen: boolean;
  onClose: () => void;
  product: Product | null; // null for Create mode, Product for Edit mode
  onSave: (data: ProductCreate | ProductUpdate, isEdit: boolean) => Promise<void>;
}

export const ProductModal: React.FC<ProductModalProps> = ({
  isOpen,
  onClose,
  product,
  onSave,
}) => {
  const [formData, setFormData] = useState({
    name: '',
    sku: '',
    category: '',
    quantity: 0,
    reorder_point: 10,
    unit: 'pcs',
    unit_cost: '' as string | number,
    supplier_name: '',
    description: '',
  });

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isEdit = !!product;

  useEffect(() => {
    if (product) {
      setFormData({
        name: product.name,
        sku: product.sku,
        category: product.category,
        quantity: product.quantity,
        reorder_point: product.reorder_point,
        unit: product.unit || 'pcs',
        unit_cost: product.unit_cost !== null && product.unit_cost !== undefined ? product.unit_cost : '',
        supplier_name: product.supplier_name || '',
        description: product.description || '',
      });
      setError(null);
    } else {
      setFormData({
        name: '',
        sku: '',
        category: '',
        quantity: 0,
        reorder_point: 10,
        unit: 'pcs',
        unit_cost: '',
        supplier_name: '',
        description: '',
      });
      setError(null);
    }
  }, [product, isOpen]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: name === 'quantity' || name === 'reorder_point'
        ? Math.max(0, parseInt(value, 10) || 0)
        : value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      setError('Product name is required.');
      return;
    }
    if (!formData.sku.trim()) {
      setError('Product SKU is required.');
      return;
    }
    if (!formData.category.trim()) {
      setError('Category is required.');
      return;
    }

    const payload: ProductCreate = {
      name: formData.name.trim(),
      sku: formData.sku.trim().toUpperCase(),
      category: formData.category.trim(),
      quantity: Number(formData.quantity),
      reorder_point: Number(formData.reorder_point),
      unit: formData.unit.trim() || 'pcs',
      unit_cost: formData.unit_cost !== '' ? parseFloat(formData.unit_cost as string) : null,
      supplier_name: formData.supplier_name.trim() || null,
      description: formData.description.trim() || null,
    };

    try {
      setSubmitting(true);
      setError(null);
      await onSave(payload, isEdit);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to save product');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isEdit ? `Edit Product: ${product?.name}` : 'Add New Inventory Product'}
      footer={
        <div className="modal-footer-actions">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onClose}
            disabled={submitting}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={submitting}
          >
            {submitting ? 'Saving...' : isEdit ? 'Update Product' : 'Create Product'}
          </button>
        </div>
      }
    >
      <form onSubmit={handleSubmit} className="product-form">
        <div className="form-row">
          <div className="form-group flex-2">
            <label htmlFor="p-name">
              Product Name <span className="required">*</span>
            </label>
            <input
              id="p-name"
              name="name"
              type="text"
              className="form-control"
              value={formData.name}
              onChange={handleChange}
              placeholder="e.g. Organic Almond Milk 1L"
              required
              disabled={submitting}
            />
          </div>
          <div className="form-group flex-1">
            <label htmlFor="p-sku">
              SKU <span className="required">*</span>
            </label>
            <input
              id="p-sku"
              name="sku"
              type="text"
              className="form-control uppercase"
              value={formData.sku}
              onChange={handleChange}
              placeholder="e.g. ALM-001"
              required
              disabled={submitting}
            />
          </div>
        </div>

        <div className="form-row">
          <div className="form-group flex-1">
            <label htmlFor="p-category">
              Category <span className="required">*</span>
            </label>
            <input
              id="p-category"
              name="category"
              type="text"
              className="form-control"
              value={formData.category}
              onChange={handleChange}
              placeholder="e.g. Dairy Alternatives"
              required
              disabled={submitting}
            />
          </div>
          <div className="form-group flex-1">
            <label htmlFor="p-unit">Unit</label>
            <input
              id="p-unit"
              name="unit"
              type="text"
              className="form-control"
              value={formData.unit}
              onChange={handleChange}
              placeholder="pcs, kg, box"
              disabled={submitting}
            />
          </div>
          <div className="form-group flex-1">
            <label htmlFor="p-cost">Unit Cost ($)</label>
            <input
              id="p-cost"
              name="unit_cost"
              type="number"
              step="0.01"
              min="0"
              className="form-control"
              value={formData.unit_cost}
              onChange={handleChange}
              placeholder="0.00"
              disabled={submitting}
            />
          </div>
        </div>

        <div className="form-row">
          <div className="form-group flex-1">
            <label htmlFor="p-qty">
              Current Stock Quantity <span className="required">*</span>
            </label>
            <input
              id="p-qty"
              name="quantity"
              type="number"
              min="0"
              className="form-control"
              value={formData.quantity}
              onChange={handleChange}
              required
              disabled={submitting}
            />
          </div>
          <div className="form-group flex-1">
            <label htmlFor="p-reorder">
              Reorder Point (Threshold) <span className="required">*</span>
            </label>
            <input
              id="p-reorder"
              name="reorder_point"
              type="number"
              min="0"
              className="form-control"
              value={formData.reorder_point}
              onChange={handleChange}
              required
              disabled={submitting}
            />
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="p-supplier">Supplier / Vendor Name</label>
          <input
            id="p-supplier"
            name="supplier_name"
            type="text"
            className="form-control"
            value={formData.supplier_name}
            onChange={handleChange}
            placeholder="e.g. Organic Foods Distributor"
            disabled={submitting}
          />
        </div>

        <div className="form-group">
          <label htmlFor="p-desc">Description</label>
          <textarea
            id="p-desc"
            name="description"
            rows={2}
            className="form-control"
            value={formData.description}
            onChange={handleChange}
            placeholder="Optional product details..."
            disabled={submitting}
          />
        </div>

        {error && <div className="alert-box alert-error">{error}</div>}
      </form>
    </Modal>
  );
};
