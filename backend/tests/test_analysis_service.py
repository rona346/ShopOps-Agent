"""
Unit tests for InventoryAnalysisService.
Tests deterministic categorization, reorder quantity calculations, and overstock detection.
"""

import unittest
from app.models.analysis import StockStatus
from app.models.inventory import ProductCreate
from app.services.inventory_analysis import InventoryAnalysisService
from tests.fake_inventory_repo import InMemoryInventoryRepository


class TestInventoryAnalysisService(unittest.TestCase):
    """Test suite for deterministic inventory analysis engine."""

    def setUp(self):
        self.repo = InMemoryInventoryRepository()
        self.service = InventoryAnalysisService(inventory_service=self.repo)

    def test_out_of_stock_detection_and_calculation(self):
        prod = self.repo.create_product(
            ProductCreate(
                name="Coffee Beans",
                sku="COF-01",
                category="Beverages",
                quantity=0,
                reorder_point=10,
                unit_cost=12.0,
            )
        )
        item = self.service.analyze_product(prod)
        self.assertEqual(item.status, StockStatus.OUT_OF_STOCK)
        # Target stock is max(10 * 2, 10) = 20. Recommended = 20.
        self.assertEqual(item.recommended_reorder_quantity, 20)
        self.assertEqual(item.estimated_reorder_cost, 240.0)
        self.assertIn("out of stock", item.reason.lower())

    def test_low_stock_detection_and_calculation(self):
        prod = self.repo.create_product(
            ProductCreate(
                name="Green Tea",
                sku="TEA-01",
                category="Beverages",
                quantity=4,
                reorder_point=10,
                unit_cost=5.0,
            )
        )
        item = self.service.analyze_product(prod)
        self.assertEqual(item.status, StockStatus.LOW_STOCK)
        # Target stock = 20. Needed = 20 - 4 = 16.
        self.assertEqual(item.recommended_reorder_quantity, 16)
        self.assertEqual(item.estimated_reorder_cost, 80.0)
        self.assertIn("reorder threshold", item.reason.lower())

    def test_low_stock_exact_threshold(self):
        prod = self.repo.create_product(
            ProductCreate(
                name="Black Tea",
                sku="TEA-02",
                category="Beverages",
                quantity=10,
                reorder_point=10,
            )
        )
        item = self.service.analyze_product(prod)
        self.assertEqual(item.status, StockStatus.LOW_STOCK)
        self.assertEqual(item.recommended_reorder_quantity, 10)

    def test_normal_stock_detection(self):
        prod = self.repo.create_product(
            ProductCreate(
                name="Sugar",
                sku="SGR-01",
                category="Pantry",
                quantity=15,
                reorder_point=10,
                unit_cost=2.0,
            )
        )
        item = self.service.analyze_product(prod)
        self.assertEqual(item.status, StockStatus.NORMAL)
        self.assertEqual(item.recommended_reorder_quantity, 0)
        self.assertIsNone(item.estimated_reorder_cost)
        self.assertIn("healthy", item.reason.lower())

    def test_overstock_detection(self):
        # Overstock threshold = 10 * 3 = 30. Quantity = 35 > 30.
        prod = self.repo.create_product(
            ProductCreate(
                name="Paper Towels",
                sku="TOWEL-01",
                category="Supplies",
                quantity=35,
                reorder_point=10,
            )
        )
        item = self.service.analyze_product(prod)
        self.assertEqual(item.status, StockStatus.OVERSTOCK)
        self.assertEqual(item.recommended_reorder_quantity, 0)
        self.assertIn("overstock", item.reason.lower())

    def test_zero_reorder_point_behavior(self):
        # Case A: Out of stock with reorder_point 0 -> target minimum is 10
        prod_zero_oos = self.repo.create_product(
            ProductCreate(
                name="Specialty Item",
                sku="SPEC-01",
                category="Specialty",
                quantity=0,
                reorder_point=0,
            )
        )
        item_oos = self.service.analyze_product(prod_zero_oos)
        self.assertEqual(item_oos.status, StockStatus.OUT_OF_STOCK)
        self.assertEqual(item_oos.recommended_reorder_quantity, 10)

        # Case B: Overstock with reorder_point 0 -> threshold is default 50
        prod_zero_over = self.repo.create_product(
            ProductCreate(
                name="Surplus Item",
                sku="SURP-01",
                category="Specialty",
                quantity=55,
                reorder_point=0,
            )
        )
        item_over = self.service.analyze_product(prod_zero_over)
        self.assertEqual(item_over.status, StockStatus.OVERSTOCK)

    def test_inventory_analysis_summary_aggregation(self):
        # 1 Out of stock (0 / 10, unit_cost $10) -> reorder 20 ($200)
        self.repo.create_product(
            ProductCreate(name="Item 1", sku="SKU-1", category="CatA", quantity=0, reorder_point=10, unit_cost=10.0)
        )
        # 1 Low stock (5 / 10, unit_cost $5) -> reorder 15 ($75)
        self.repo.create_product(
            ProductCreate(name="Item 2", sku="SKU-2", category="CatA", quantity=5, reorder_point=10, unit_cost=5.0)
        )
        # 1 Normal (15 / 10) -> reorder 0
        self.repo.create_product(
            ProductCreate(name="Item 3", sku="SKU-3", category="CatB", quantity=15, reorder_point=10, unit_cost=8.0)
        )
        # 1 Overstock (40 / 10) -> reorder 0
        self.repo.create_product(
            ProductCreate(name="Item 4", sku="SKU-4", category="CatB", quantity=40, reorder_point=10, unit_cost=1.0)
        )

        summary = self.service.analyze_inventory()
        self.assertEqual(summary.total_products, 4)
        self.assertEqual(summary.total_inventory_units, 60)  # 0 + 5 + 15 + 40
        self.assertEqual(summary.out_of_stock_count, 1)
        self.assertEqual(summary.low_stock_count, 2)  # Item 1 (0) + Item 2 (5)
        self.assertEqual(summary.normal_stock_count, 1)
        self.assertEqual(summary.overstock_count, 1)
        self.assertEqual(summary.total_recommended_reorder_units, 35)  # 20 + 15
        self.assertEqual(summary.estimated_total_reorder_cost, 275.0)  # 200 + 75

    def test_reorder_recommendations_filters_healthy_items(self):
        self.repo.create_product(
            ProductCreate(name="Low Item", sku="LOW-1", category="CatA", quantity=2, reorder_point=10, unit_cost=5.0)
        )
        self.repo.create_product(
            ProductCreate(name="Healthy Item", sku="HLT-1", category="CatA", quantity=20, reorder_point=10)
        )

        reorder_resp = self.service.get_reorder_recommendations()
        self.assertEqual(reorder_resp.total_items_to_reorder, 1)
        self.assertEqual(len(reorder_resp.items), 1)
        self.assertEqual(reorder_resp.items[0].sku, "LOW-1")
        self.assertEqual(reorder_resp.total_recommended_units, 18)  # 20 - 2
        self.assertEqual(reorder_resp.estimated_total_cost, 90.0)


if __name__ == "__main__":
    unittest.main()
