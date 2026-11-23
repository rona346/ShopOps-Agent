"""
Unit tests for Inventory Pydantic Models and Validation.
"""

import unittest
from pydantic import ValidationError
from app.models.inventory import Product, ProductCreate, ProductUpdate


class TestProductModels(unittest.TestCase):
    """Test suite for product schemas, validations, and low-stock property."""

    def test_valid_product_create(self):
        data = {
            "name": "Wireless Mouse",
            "sku": "wm-100",
            "category": "Electronics",
            "quantity": 25,
            "reorder_point": 10,
            "unit": "pcs",
            "unit_cost": 15.50,
            "supplier_name": "Tech Supplies Inc",
            "description": "Ergonomic 2.4GHz wireless mouse",
        }
        product_in = ProductCreate(**data)
        self.assertEqual(product_in.name, "Wireless Mouse")
        # SKU must be normalized to uppercase and stripped
        self.assertEqual(product_in.sku, "WM-100")
        self.assertEqual(product_in.quantity, 25)
        self.assertEqual(product_in.reorder_point, 10)
        self.assertEqual(product_in.unit_cost, 15.50)

    def test_sku_normalization_and_trimming(self):
        product_in = ProductCreate(
            name="Keyboard",
            sku="  kb- mechanical - 01  ",
            category="Electronics",
            quantity=5,
        )
        self.assertEqual(product_in.sku, "KB- MECHANICAL - 01")

    def test_empty_name_rejected(self):
        with self.assertRaises(ValidationError):
            ProductCreate(
                name="   ",
                sku="SKU123",
                category="General",
            )

    def test_negative_quantity_rejected(self):
        with self.assertRaises(ValidationError):
            ProductCreate(
                name="Cable",
                sku="CBL-01",
                category="Accessories",
                quantity=-1,
            )

    def test_negative_reorder_point_rejected(self):
        with self.assertRaises(ValidationError):
            ProductCreate(
                name="Cable",
                sku="CBL-01",
                category="Accessories",
                reorder_point=-5,
            )

    def test_negative_unit_cost_rejected(self):
        with self.assertRaises(ValidationError):
            ProductCreate(
                name="Cable",
                sku="CBL-01",
                category="Accessories",
                unit_cost=-10.0,
            )

    def test_low_stock_property(self):
        # Case 1: quantity <= reorder_point -> low stock
        low_prod = Product(
            id="p1",
            name="Widget",
            sku="WDG-01",
            category="Hardware",
            quantity=5,
            reorder_point=10,
        )
        self.assertTrue(low_prod.is_low_stock)

        # Case 2: quantity == reorder_point -> low stock
        exact_prod = Product(
            id="p2",
            name="Widget",
            sku="WDG-02",
            category="Hardware",
            quantity=10,
            reorder_point=10,
        )
        self.assertTrue(exact_prod.is_low_stock)

        # Case 3: quantity > reorder_point -> not low stock
        healthy_prod = Product(
            id="p3",
            name="Widget",
            sku="WDG-03",
            category="Hardware",
            quantity=25,
            reorder_point=10,
        )
        self.assertFalse(healthy_prod.is_low_stock)

    def test_product_update_validation(self):
        # Empty values allowed in optional update
        update = ProductUpdate(quantity=15)
        self.assertEqual(update.quantity, 15)
        self.assertIsNone(update.name)

        # Negative values still rejected
        with self.assertRaises(ValidationError):
            ProductUpdate(quantity=-5)


if __name__ == "__main__":
    unittest.main()
