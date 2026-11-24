# Supabase Database Migrations for ShopOps Agent

This directory contains the versioned PostgreSQL database migrations for ShopOps Agent.

## Migration Files

- `migrations/20261124000001_initial_shopops_schema.sql`:
  Initial database schema creating:
  - `public.inventory_products`
  - `public.approval_requests`
  - `public.reorder_tasks`
  - Automatic `updated_at` triggers
  - Indexes for performance, low-stock querying, and newest-first sorting
  - Strict fail-closed Row Level Security (RLS) policies

## How to Apply Migrations

### Option A: Via Supabase Dashboard (Recommended for fast setup)

1. Log in to your [Supabase Dashboard](https://supabase.com/dashboard).
2. Select your ShopOps Agent project.
3. In the left navigation menu, click **SQL Editor**.
4. Click **New query** (or the **+** button).
5. Copy the entire contents of `supabase/migrations/20261124000001_initial_shopops_schema.sql` and paste it into the query editor.
6. Click **Run** (or press `Ctrl+Enter` / `Cmd+Enter`).
7. Confirm that the query reports **"Success. No rows returned"** (or execution success).
8. Go to **Table Editor** in the left sidebar to verify that all three tables are visible:
   - `inventory_products`
   - `approval_requests`
   - `reorder_tasks`

### Option B: Via Supabase CLI (For automated local or CI workflows)

If you have the Supabase CLI installed:

```bash
# Link to your Supabase project (requires project ref and database password)
supabase link --project-ref <your-project-ref>

# Push the migrations to the remote database
supabase db push
```

## Security & Access Model (Strict Fail-Closed Architecture)

- **Row Level Security (RLS):** Enabled on all three tables (`inventory_products`, `approval_requests`, `reorder_tasks`).
- **Direct Client Access (`anon` & `authenticated`):** **Intentionally disabled.** Zero client policies are granted. Any direct query from browser clients, frontend apps, or arbitrary authenticated users via the Supabase PostgREST API is completely denied (fail-closed).
- **Backend Orchestrator Access:** The FastAPI backend accesses PostgreSQL directly using either:
  1. The direct PostgreSQL connection string (`DATABASE_URL`), or
  2. The Supabase `service_role` key.

  Both methods have `BYPASSRLS` privileges, allowing the backend to act as the sole, authoritative orchestrator of all business logic, owner authentication verification, AI reasoning, and approval safeguards.
