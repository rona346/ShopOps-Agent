# Frontend - ShopOps Agent Dashboard

A modern, responsive, and accessible React + Vite + TypeScript dashboard for retail store owners, integrating real-time inventory management, deterministic replenishment analysis, Gemini AI operational insights, and an owner-governed approval and execution workflow.

---

## Features

1. **Store Operational Overview (`/`)**:
   - 6 real-time metric cards: Total Products, Out of Stock, Low Stock, Overstock, Pending Approvals, Created Tasks.
   - Replenishment financial summary (units on hand, recommended reorder units, estimated capital).
   - Live backend health indicator and quick navigation shortcuts.

2. **Inventory Catalog (`/inventory`)**:
   - Full product table with SKU, name, category, quantity, reorder point, unit cost, and health status badges.
   - Search by SKU or product name with category filtering and client pagination.
   - Create new products, edit existing items, and delete with modal confirmations.

3. **Inventory Analysis & Reorder Planning (`/analysis`)**:
   - Purely deterministic stock health classification (`out_of_stock`, `low_stock`, `normal`, `overstock`).
   - Rule-based replenishment calculation: `recommended_units = (reorder_point * 2) - quantity`.
   - Estimated total reorder costs based on recorded unit costs.
   - One-click **"Request Reorder"** action to generate a pending approval directly from a recommendation.

4. **AI Inventory Agent (`/agent`)**:
   - **Executive Briefing**: High-level store operational summary, critical stock alerts, replenishment guidance, and capital-release suggestions powered by Gemini.
   - **Interactive Q&A Assistant**: Ask natural-language inventory questions with grounded answers, referenced SKU tags, ground-truth metric tags, and clickable follow-up queries.
   - Clear architectural distinction between deterministic calculations (source of truth) and AI explanations.
   - Graceful 503 notification if `GEMINI_API_KEY` is unconfigured.

5. **Owner Approval Workflow (`/approvals`)**:
   - Small business owner authorization control.
   - Pending review filter, inline proposed quantity modification modal with validation.
   - Approve and reject actions with optional owner rationale notes.
   - Execution trigger for approved requests.

6. **Reorder Tasks Audit Log (`/tasks`)**:
   - Tracks internal replenishment tasks generated from approved recommendations.
   - Displays task ID, product name, SKU, approved units, estimated cost, status (`created`, `in_progress`, etc.), and source approval ID.
   - Non-destructive execution policy: strictly creates internal tasks; does not contact suppliers or charge payments.

---

## Setup & Running

### Prerequisites
- Node.js (v18+)
- npm (v9+)

### Installation

```bash
cd frontend
npm install
```

### Environment Configuration

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Default backend base URL is `http://localhost:8000`. If running on a different port or domain, adjust `VITE_API_BASE_URL` in `.env`.

### Supabase Authentication Configuration
To enable live store owner sign-in:
1. Go to your [Supabase Dashboard](https://supabase.com/dashboard) -> **Project Settings** -> **API**.
2. Copy the **Project URL** and set it as `VITE_SUPABASE_URL`.
3. Copy the **anon public key** and set it as `VITE_SUPABASE_ANON_KEY`.
4. *Important:* Never expose `SUPABASE_SERVICE_ROLE_KEY` or `SUPABASE_JWT_SECRET` in frontend `.env` or Vercel variables.

### Running Development Server

```bash
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

### Production Build & Type Checking

```bash
npm run build
```
Runs `tsc -b && vite build` ensuring zero TypeScript compilation or linting errors.
