"""
Inventory REST API Endpoints.
Mounted under /api/v1/inventory.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from app.models.analysis import (
    InventoryAnalysisSummary,
    ReorderRecommendationsResponse,
)
from app.models.inventory import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)
from app.services.inventory import (
    InventoryServiceInterface,
    get_inventory_service,
)
from app.services.inventory_analysis import (
    InventoryAnalysisService,
    get_inventory_analysis_service,
)

router = APIRouter()


@router.get(
    "",
    response_model=ProductListResponse,
    summary="List inventory products",
)
def list_products(
    limit: int = Query(default=50, ge=1, le=100, description="Items per page"),
    offset: int = Query(default=0, ge=0, description="Offset items"),
    search: Optional[str] = Query(default=None, description="Search by name or SKU"),
    low_stock: Optional[bool] = Query(default=None, description="Filter low-stock products"),
    service: InventoryServiceInterface = Depends(get_inventory_service),
):
    """
    List inventory products with pagination, search, and low-stock filters.
    """
    items, total = service.list_products(
        limit=limit, offset=offset, search=search, low_stock=low_stock
    )
    return ProductListResponse(
        items=[ProductResponse.from_product(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new inventory product",
)
def create_product(
    product_in: ProductCreate,
    service: InventoryServiceInterface = Depends(get_inventory_service),
):
    """
    Create a new inventory product with validated attributes and unique SKU.
    """
    created = service.create_product(product_in)
    return ProductResponse.from_product(created)


@router.get(
    "/analysis",
    response_model=InventoryAnalysisSummary,
    summary="Inventory analysis & stock health overview",
)
def get_inventory_analysis(
    category: Optional[str] = Query(default=None, description="Filter analysis by category"),
    analysis_service: InventoryAnalysisService = Depends(get_inventory_analysis_service),
):
    """
    Deterministic inventory health analysis.
    Identifies out-of-stock, low-stock, and overstock products, and calculates
    replenishment targets without modifying database state.
    """
    return analysis_service.analyze_inventory(category=category)


@router.get(
    "/reorder-recommendations",
    response_model=ReorderRecommendationsResponse,
    summary="Deterministic reorder recommendations",
)
def get_reorder_recommendations(
    category: Optional[str] = Query(default=None, description="Filter recommendations by category"),
    analysis_service: InventoryAnalysisService = Depends(get_inventory_analysis_service),
):
    """
    Retrieve products that require reordering along with recommended quantities
    and reasons. Deterministically calculated from stock levels and reorder points.
    """
    return analysis_service.get_reorder_recommendations(category=category)


@router.get(
    "/low-stock",
    response_model=ProductListResponse,
    summary="List products with low stock",
)
def get_low_stock(
    limit: int = Query(default=50, ge=1, le=100, description="Items per page"),
    offset: int = Query(default=0, ge=0, description="Offset items"),
    service: InventoryServiceInterface = Depends(get_inventory_service),
):
    """
    Retrieve products where quantity <= reorder_point.
    Calculated deterministically from stored values.
    """
    items, total = service.get_low_stock_products(limit=limit, offset=offset)
    return ProductListResponse(
        items=[ProductResponse.from_product(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get product by ID",
)
def get_product(
    product_id: str,
    service: InventoryServiceInterface = Depends(get_inventory_service),
):
    """
    Retrieve product details by document ID. Returns 404 if not found.
    """
    product = service.get_product(product_id)
    return ProductResponse.from_product(product)


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update product fields",
)
def update_product(
    product_id: str,
    product_update: ProductUpdate,
    service: InventoryServiceInterface = Depends(get_inventory_service),
):
    """
    Update supplied product fields. Validates input, prevents duplicate SKU, and updates updated_at.
    """
    updated = service.update_product(product_id, product_update)
    return ProductResponse.from_product(updated)


@router.delete(
    "/{product_id}",
    summary="Delete product",
)
def delete_product(
    product_id: str,
    service: InventoryServiceInterface = Depends(get_inventory_service),
):
    """
    Delete a product by document ID. Returns 404 if not found.
    """
    service.delete_product(product_id)
    return {"message": f"Product '{product_id}' deleted successfully", "id": product_id}
