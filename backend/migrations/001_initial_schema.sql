-- =============================================================================
-- ShopOps Agent — Initial PostgreSQL Database Schema Migration
-- Migration ID: 20261124000001_initial_shopops_schema
-- Description: Creates persistent application tables for ShopOps Agent:
--              1. inventory_products
--              2. approval_requests
--              3. reorder_tasks
--              Includes constraints, triggers, indexes, and fail-closed RLS.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 0. Extensions
-- -----------------------------------------------------------------------------
-- Enable pgcrypto for gen_random_uuid() support (standard in Supabase)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- -----------------------------------------------------------------------------
-- 1. Helper Functions & Triggers
-- -----------------------------------------------------------------------------
-- Automatically maintain updated_at timestamps on row modifications
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = timezone('utc'::text, now());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- -----------------------------------------------------------------------------
-- 2. Table: inventory_products
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.inventory_products (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    name VARCHAR(200) NOT NULL,
    sku VARCHAR(100) NOT NULL,
    category VARCHAR(100) NOT NULL DEFAULT 'General',
    quantity INTEGER NOT NULL DEFAULT 0,
    reorder_point INTEGER NOT NULL DEFAULT 10,
    unit VARCHAR(50) NOT NULL DEFAULT 'pcs',
    unit_cost NUMERIC(10, 2) NULL,
    supplier_name VARCHAR(200) NULL,
    description TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),

    -- Constraints
    CONSTRAINT chk_inventory_name_nonempty CHECK (length(trim(name)) > 0),
    CONSTRAINT chk_inventory_sku_nonempty CHECK (length(trim(sku)) > 0),
    CONSTRAINT uq_inventory_sku UNIQUE (sku),
    CONSTRAINT chk_inventory_quantity_nonnegative CHECK (quantity >= 0),
    CONSTRAINT chk_inventory_reorder_point_nonnegative CHECK (reorder_point >= 0),
    CONSTRAINT chk_inventory_unit_nonempty CHECK (length(trim(unit)) > 0),
    CONSTRAINT chk_inventory_unit_cost_nonnegative CHECK (unit_cost IS NULL OR unit_cost >= 0.00)
);

-- Trigger for inventory_products.updated_at
DROP TRIGGER IF EXISTS trg_inventory_products_updated_at ON public.inventory_products;
CREATE TRIGGER trg_inventory_products_updated_at
    BEFORE UPDATE ON public.inventory_products
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();

-- Indexes for inventory_products
CREATE INDEX IF NOT EXISTS idx_inventory_products_category ON public.inventory_products(category);
CREATE INDEX IF NOT EXISTS idx_inventory_products_low_stock ON public.inventory_products(quantity, reorder_point);
CREATE INDEX IF NOT EXISTS idx_inventory_products_created_at_desc ON public.inventory_products(created_at DESC);

-- -----------------------------------------------------------------------------
-- 3. Table: approval_requests
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.approval_requests (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    action_type VARCHAR(50) NOT NULL DEFAULT 'reorder',
    product_id TEXT NOT NULL,
    sku VARCHAR(100) NOT NULL,
    product_name VARCHAR(200) NOT NULL,
    current_quantity INTEGER NOT NULL,
    proposed_reorder_quantity INTEGER NOT NULL,
    reason TEXT NOT NULL,
    estimated_cost NUMERIC(10, 2) NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    owner_notes TEXT NULL,
    decided_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),

    -- Foreign Keys
    CONSTRAINT fk_approval_product FOREIGN KEY (product_id)
        REFERENCES public.inventory_products(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    -- Constraints
    CONSTRAINT chk_approval_action_type CHECK (action_type IN ('reorder')),
    CONSTRAINT chk_approval_current_quantity CHECK (current_quantity >= 0),
    CONSTRAINT chk_approval_proposed_reorder_qty CHECK (proposed_reorder_quantity >= 0),
    CONSTRAINT chk_approval_estimated_cost CHECK (estimated_cost IS NULL OR estimated_cost >= 0.00),
    CONSTRAINT chk_approval_status CHECK (status IN ('pending', 'approved', 'rejected', 'executed'))
);

-- Trigger for approval_requests.updated_at
DROP TRIGGER IF EXISTS trg_approval_requests_updated_at ON public.approval_requests;
CREATE TRIGGER trg_approval_requests_updated_at
    BEFORE UPDATE ON public.approval_requests
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();

-- Indexes for approval_requests
CREATE INDEX IF NOT EXISTS idx_approval_requests_status ON public.approval_requests(status);
CREATE INDEX IF NOT EXISTS idx_approval_requests_product_id ON public.approval_requests(product_id);
CREATE INDEX IF NOT EXISTS idx_approval_requests_created_at_desc ON public.approval_requests(created_at DESC);

-- -----------------------------------------------------------------------------
-- 4. Table: reorder_tasks
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.reorder_tasks (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    approval_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    sku VARCHAR(100) NOT NULL,
    product_name VARCHAR(200) NOT NULL,
    approved_reorder_quantity INTEGER NOT NULL,
    estimated_cost NUMERIC(10, 2) NULL,
    notes VARCHAR(500) NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'created',
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),

    -- Foreign Keys & Idempotency Constraints
    CONSTRAINT uq_reorder_tasks_approval_id UNIQUE (approval_id),
    CONSTRAINT fk_reorder_task_approval FOREIGN KEY (approval_id)
        REFERENCES public.approval_requests(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    CONSTRAINT fk_reorder_task_product FOREIGN KEY (product_id)
        REFERENCES public.inventory_products(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    -- Constraints
    CONSTRAINT chk_reorder_task_quantity CHECK (approved_reorder_quantity >= 0),
    CONSTRAINT chk_reorder_task_cost CHECK (estimated_cost IS NULL OR estimated_cost >= 0.00),
    CONSTRAINT chk_reorder_task_status CHECK (status IN ('created', 'in_progress', 'completed', 'cancelled'))
);

-- Trigger for reorder_tasks.updated_at
DROP TRIGGER IF EXISTS trg_reorder_tasks_updated_at ON public.reorder_tasks;
CREATE TRIGGER trg_reorder_tasks_updated_at
    BEFORE UPDATE ON public.reorder_tasks
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();

-- Indexes for reorder_tasks
CREATE INDEX IF NOT EXISTS idx_reorder_tasks_status ON public.reorder_tasks(status);
CREATE INDEX IF NOT EXISTS idx_reorder_tasks_product_id ON public.reorder_tasks(product_id);
CREATE INDEX IF NOT EXISTS idx_reorder_tasks_approval_id ON public.reorder_tasks(approval_id);
CREATE INDEX IF NOT EXISTS idx_reorder_tasks_created_at_desc ON public.reorder_tasks(created_at DESC);

-- -----------------------------------------------------------------------------
-- 5. Row Level Security (RLS) & Access Policies (Strict Fail-Closed)
-- -----------------------------------------------------------------------------
-- Enable RLS on all persistent tables.
ALTER TABLE public.inventory_products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.approval_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reorder_tasks ENABLE ROW LEVEL SECURITY;

-- Clean up any previously created permissive policies to ensure clean, idempotent reruns
DROP POLICY IF EXISTS "Allow authenticated read on inventory_products" ON public.inventory_products;
DROP POLICY IF EXISTS "Allow authenticated read on approval_requests" ON public.approval_requests;
DROP POLICY IF EXISTS "Allow authenticated read on reorder_tasks" ON public.reorder_tasks;

-- STRICT FAIL-CLOSED SECURITY INVARIANT:
-- No client-facing policies (SELECT, INSERT, UPDATE, DELETE) are granted to 'anon' or 'authenticated'.
-- Direct PostgREST/client SDK access from browsers or untrusted parties is 100% blocked.
-- All database interactions MUST be mediated exclusively by the FastAPI backend using its
-- privileged connection (service_role key or direct PostgreSQL DATABASE_URL), which bypasses RLS.

-- End of Migration
