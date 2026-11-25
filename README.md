# ShopOps Agent

> **Autonomous Inventory Intelligence & Safe Human-in-the-Loop Operations for Small Retailers**  
> *Homingo Hack Days — Agents Track Submission*

[![Backend Tests](https://img.shields.io/badge/backend%20tests-113%20passed-brightgreen)](#verification--testing)
[![E2E Smoke Tests](https://img.shields.io/badge/e2e%20smoke%20tests-12%20passed-brightgreen)](#verification--testing)
[![Frontend Tests](https://img.shields.io/badge/frontend%20tests-9%20passed-brightgreen)](#verification--testing)
[![Frontend](https://img.shields.io/badge/frontend-React%2018%20%2B%20Vite%20%28Vercel%29-blue)](#tech-stack)
[![Backend](https://img.shields.io/badge/backend-FastAPI%20%2B%20Python%20%28Render%29-009688)](#tech-stack)
[![Database](https://img.shields.io/badge/database-Supabase%20PostgreSQL%20%28RLS%29-3ECF8E)](#supabase-database-schema--migration)
[![Auth](https://img.shields.io/badge/auth-Supabase%20Auth%20%28JWT%29-green)](#authentication--security-architecture)
[![Gemini](https://img.shields.io/badge/AI-Google%20Gemini%202.5%20Flash-orange)](#deterministic-math--gemini-ai-why-the-hybrid-model-matters)

---

## Table of Contents
1. [The Real Problem ShopOps Agent Solves](#the-real-problem-shopops-agent-solves)
2. [Target User: The Independent Small Retailer](#target-user-the-independent-small-retailer)
3. [The Autonomous Agent Workflow (7 Stages)](#the-autonomous-agent-workflow-7-stages)
4. [Deterministic Math + Gemini AI: Why the Hybrid Model Matters](#deterministic-math--gemini-ai-why-the-hybrid-model-matters)
5. [Owner Approval & Execution Safety Guarantees](#owner-approval--execution-safety-guarantees)
6. [System Architecture](#system-architecture)
7. [Authentication & Security Architecture](#authentication--security-architecture)
8. [Supabase Database Schema & Migration](#supabase-database-schema--migration)
9. [Tech Stack](#tech-stack)
10. [Environment Variables & Configuration](#environment-variables--configuration)
11. [Local Quickstart & Setup](#local-quickstart--setup)
12. [Verification & Testing](#verification--testing)
13. [Deployment & Live Cloud Verification Guide](#deployment--live-cloud-verification-guide)
14. [Demo Video & Walkthrough Script](#demo-video--walkthrough-script)

---

## The Real Problem ShopOps Agent Solves

Small, independent retail businesses operate on razor-thin margins and face two opposing, costly operational traps every day:

1. **The Stockout Trap (Lost Revenue & Churned Customers):** When high-velocity products (e.g., fresh dairy, coffee beans, specialty staples) run out, customers walk out the door and shop at big-box competitors.
2. **The Overstock Trap (Trapped Working Capital):** Over-ordering slow-moving goods ties up scarce cash, clutters valuable stockroom space, and leads to inventory spoilage or markdowns.

### Why Existing Solutions Fail Small Retailers
- **Enterprise ERPs (SAP, NetSuite, Oracle):** Too expensive ($10k–$100k+/year), require months of configuration, and demand dedicated IT teams.
- **Manual Spreadsheets & Gut Feeling:** Error-prone, time-consuming, purely reactive, and forgotten during busy shifts.
- **Generic LLM Chatbots:** Prone to mathematical hallucinations, cannot calculate accurate replenishment quantities or costs reliably, and lack safe transactional execution controls.

**ShopOps Agent solves this dilemma** by providing an autonomous, deterministic inventory intelligence engine coupled with Google Gemini for contextual executive insights—protected by a non-negotiable **human-in-the-loop owner approval gate**.

---

## Target User: The Independent Small Retailer

ShopOps Agent is specifically designed for:
- **Independent Grocers & Bodegas:** Tracking perishables, dairy, staples, and daily turnover.
- **Specialty Boutiques & Coffee Roasters:** Balancing high-margin specialty items and packaging supplies.
- **Neighborhood Pharmacies & Hardware Stores:** Managing thousands of SKUs without an enterprise IT department.

These business owners wear every hat: store manager, cashier, buyer, and bookkeeper. They need a trusted co-pilot that flags risks early, does the math accurately, and asks for approval before taking operational action.

---

## The Autonomous Agent Workflow (7 Stages)

ShopOps Agent preserves a rigorous, cyclical 7-stage autonomous operational loop:

```
    ┌──────────┐      ┌──────────┐      ┌──────────┐      ┌───────────────┐
    │ 1.OBSERVE│ ───► │ 2.ANALYZE│ ───► │  3.PLAN  │ ───► │4.ASK APPROVAL │
    └──────────┘      └──────────┘      └──────────┘      └───────┬───────┘
                                                                  │
                                                          [ Owner Decision ]
                                                          (Approve / Reject)
                                                                  │
    ┌──────────┐      ┌──────────┐      ┌──────────┐              ▼
    │ 7.REPORT │ ◄─── │ 6.VERIFY │ ◄─── │5.EXECUTE │ ◄────────────┘
    └──────────┘      └──────────┘      └──────────┘
```

1. **Observe:** Continuously monitors catalog stock levels, on-hand counts, unit costs, and defined reorder thresholds across all product categories.
2. **Analyze:** Purely deterministic classification of inventory health into four distinct states: `out_of_stock`, `low_stock`, `normal`, and `overstock`.
3. **Plan:** Computes exact replenishment quantities and projected cash outlay using mathematical formulas (e.g., `recommended_quantity = max(reorder_point * 2 - current_quantity, reorder_point)`).
4. **Ask Approval:** Transforms actionable plans into structured, transparent approval requests (`pending` status) with full unit economics and reasoning for the business owner.
5. **Execute:** Upon explicit owner approval, executes an **internal reorder task** (`created` status). Strictly forbids automated external ordering or unsupervised credit card charges.
6. **Verify:** Asserts execution invariants—locks the approval request against duplicate execution (idempotency), confirms task logging in the operational backlog, and verifies on-hand inventory counts remain unchanged.
7. **Report:** Gemini AI synthesizes deterministic metrics into natural-language executive briefings, highlights urgency, and responds to owner questions.

---

## Deterministic Math + Gemini AI: Why the Hybrid Model Matters

Many AI projects delegate mathematical calculations directly to large language models. In retail operations, this is dangerous: LLMs can hallucinate quantities, miscalculate multiplication, or invent inconsistent numbers between turns.

ShopOps Agent enforces a **strict architectural separation of concerns**:

| Capability | Deterministic Python Engine (Source of Truth) | Google Gemini AI (Contextual Intelligence) |
|:---|:---|:---|
| **Stock Level Evaluation** | Evaluates exact inequality: `quantity <= reorder_point` | Explains retail consequences of the stockout |
| **Reorder Quantity Calculation** | Deterministic formula: `reorder_point * 2 - quantity` | Contextualizes whether to order early for holidays |
| **Supplier Cost Estimation** | Arithmetic: `recommended_quantity * unit_cost` | Summarizes working capital and cash outlay risks |
| **Execution Eligibility** | Strict state machine gate (`status == 'approved'`) | Cannot trigger or bypass approval or execution |
| **Conversational Inquiries** | Supplies verified structured context payload | Answers natural language questions grounded in verified data |

> **Key Invariant:** Gemini never calculates quantities or costs. It consumes the structured JSON payload produced by the deterministic engine and translates it into actionable business intelligence.

---

## Owner Approval & Execution Safety Guarantees

1. **Human-in-the-Loop (HITL) Governance:**
   - The agent proposes actions; only the verified store owner can approve them.
   - Owners can adjust proposed reorder quantities before approving.
   - Status transitions follow an atomic state machine: `pending` &rarr; `approved` / `rejected` &rarr; `executed`.
2. **Non-Destructive Invariant:**
   - Executing an approval **never modifies on-hand inventory counts**. In-store physical quantities only change when goods are physically received and scanned into the shop.
3. **Internal Task Creation (No External Mock Orders):**
   - Execution creates an internal, traceable `ReorderTask` with unique identifiers, timestamps, and audit metadata. It does not contact external suppliers or charge credit cards.
4. **Strict Idempotency Protection:**
   - Each approval request can only be executed once. Enforced at both the service layer and the database layer via PostgreSQL `UNIQUE (approval_id)`.
5. **Fail-Closed Security Architecture:**
   - In production (`ENVIRONMENT=production`), all protected routes require verified authentication. Missing, expired, or invalid tokens strictly fail closed (`HTTP 401 Unauthorized`).
   - If `OWNER_EMAIL` is configured, accounts with non-matching emails receive `HTTP 403 Forbidden`.

---

## System Architecture

```text
React 18 / Vite Frontend (Vercel)
          │
          ├──► Supabase Auth (Store Owner Sign-In)
          │         │
          │    (Bearer JWT)
          ▼         ▼
  FastAPI Backend (Render)
          │
          ├──► OWNER_EMAIL Verification (Dependency Injection)
          ├──► Deterministic Analysis Engine (Pure Python Math)
          ├──► Google Gemini AI Engine (Insights & Grounded Q&A)
          │
          ▼ (Privileged service_role PostgREST)
  Supabase PostgreSQL Database
          ├── inventory_products (SKU uniqueness, stock levels)
          ├── approval_requests  (HITL approval state machine)
          └── reorder_tasks      (1:1 unique approval_id idempotency)
          (Strict Fail-Closed RLS blocks all direct client queries)
```

### Repository Layout

```text
ShopOps_Agent/
├── backend/                       # Python + FastAPI Backend
│   ├── app/
│   │   ├── api/v1/                # Versioned REST API endpoints
│   │   │   ├── endpoints/
│   │   │   │   ├── inventory.py   # Product CRUD, pagination, search, low-stock filter
│   │   │   │   ├── analysis.py    # Deterministic inventory health & reorder engine
│   │   │   │   ├── agent.py       # Gemini AI executive briefings & grounded Q&A
│   │   │   │   ├── approvals.py   # Owner approval workflow & quantity customization
│   │   │   │   ├── tasks.py       # Internal reorder task tracking & status
│   │   │   │   └── auth.py        # Public health/status & token introspection
│   │   │   └── router.py          # Unified API Router (/api/v1)
│   │   ├── core/                  # App config, security guards, Supabase client, Gemini SDK
│   │   │   ├── config.py          # Pydantic Settings & environment variable parsing
│   │   │   ├── auth.py            # Centralized JWT verification & owner authorization
│   │   │   ├── supabase.py        # Supabase JWT verification & PostgREST client
│   │   │   ├── firebase.py        # Legacy Firebase client provider (fallback)
│   │   │   └── gemini.py          # Google Gemini client provider
│   │   ├── models/                # Pydantic schemas (Inventory, Analysis, Agent, Approvals, Tasks)
│   │   ├── services/              # Pure business logic & database services
│   │   │   ├── supabase_inventory.py # Supabase PostgreSQL inventory service
│   │   │   ├── supabase_approval.py  # Supabase PostgreSQL approval service
│   │   │   ├── supabase_task.py      # Supabase PostgreSQL task service
│   │   │   ├── inventory_analysis.py # Deterministic calculation engine
│   │   │   ├── agent.py              # Gemini AI agent service
│   │   │   └── execution.py          # Action execution & idempotency coordinator
│   │   └── main.py                # FastAPI entrypoint, exception handlers, and CORS
│   ├── migrations/                # Backend migration mirror (001_initial_schema.sql)
│   ├── tests/                     # 113 comprehensive automated tests
│   │   ├── run_tests.py           # Automated regression runner (113 passing tests)
│   │   ├── smoke_test_e2e.py      # 12-step end-to-end operational lifecycle test
│   │   ├── test_auth_api.py       # Supabase JWT & owner authorization tests
│   │   ├── test_supabase_repositories.py # Supabase PostgreSQL repository tests
│   │   └── test_live_cloud.py     # Live cloud integration test runner
│   ├── requirements.txt           # Minimal backend dependencies
│   └── README.md
│
├── frontend/                      # React + Vite + TypeScript Dashboard
│   ├── src/
│   │   ├── components/            # UI: Overview, Inventory, Analysis, Agent, Approvals, Tasks, AuthModal
│   │   ├── services/
│   │   │   ├── api.ts             # Type-safe API client with auto token refresh
│   │   │   ├── supabaseAuth.ts    # Zero-dependency Supabase GoTrue Auth client
│   │   │   └── firebase.ts        # Legacy Firebase client (fallback)
│   │   ├── types/                 # Shared TypeScript interfaces
│   │   ├── App.tsx                # Master dashboard shell, navigation & auth status
│   │   └── index.css              # Responsive modern styling for retail operations
│   ├── package.json               # Frontend scripts (dev, build, preview, test)
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── README.md
│
├── supabase/                      # Database Foundation
│   ├── migrations/
│   │   └── 20261124000001_initial_shopops_schema.sql # Core PostgreSQL schema migration
│   └── README.md                  # Supabase SQL execution guide
│
├── DEMO_SCRIPT.md                 # 3-5 minute demo video script for hackathon recording
├── .gitignore                     # Strict secret & credential isolation rules
└── README.md                      # Consolidated master documentation
```

---

## Authentication & Security Architecture

1. **Frontend Authentication:** The React dashboard uses a zero-external-dependency Supabase Auth client ([frontend/src/services/supabaseAuth.ts](file:///c:/Users/gupta/Desktop/ShopOps_Agent/frontend/src/services/supabaseAuth.ts)) talking directly to the Supabase GoTrue Auth API.
2. **Token Management & Refresh:**
   - Tokens are persisted in `localStorage`.
   - **Proactive Refresh:** Before making protected API calls, if the token is within 60 seconds of expiry, it is silently renewed in the background.
   - **Reactive Retry:** If an endpoint returns HTTP 401, the API client automatically attempts token refresh and retries the request once before redirecting to sign-in.
3. **Backend JWT Verification:** In [backend/app/core/supabase.py](file:///c:/Users/gupta/Desktop/ShopOps_Agent/backend/app/core/supabase.py), tokens are cryptographically verified using `SUPABASE_JWT_SECRET` (HS256) or verified via the Supabase Auth API endpoint `{SUPABASE_URL}/auth/v1/user`.
4. **Owner Authorization (`OWNER_EMAIL`):** The verified email claim is compared against `OWNER_EMAIL`. If a non-owner logs in, they are blocked with `HTTP 403 Forbidden`.
5. **Secrets Hygiene:**
   - `SUPABASE_SERVICE_ROLE_KEY` and `SUPABASE_JWT_SECRET` are **never** bundled into the frontend or exposed in `VITE_` variables.
   - The frontend only receives the public `VITE_SUPABASE_ANON_KEY`.

---

## Supabase Database Schema & Migration

The persistent data model consists of three PostgreSQL tables in the `public` schema:

1. **`inventory_products`**:
   - `id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text`
   - `sku VARCHAR(100) NOT NULL UNIQUE` (enforces catalog uniqueness)
   - `name`, `category`, `quantity`, `reorder_point`, `unit`, `unit_cost`, `supplier_name`, `description`
   - Automated `updated_at` triggers and performance indexes on `category`, `(quantity, reorder_point)`, and `created_at DESC`.
2. **`approval_requests`**:
   - `id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text`
   - `product_id TEXT NOT NULL REFERENCES inventory_products(id) ON DELETE RESTRICT`
   - `sku`, `product_name`, `current_quantity`, `proposed_reorder_quantity`, `reason`, `estimated_cost`
   - `status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'executed'))`
3. **`reorder_tasks`**:
   - `id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text`
   - `approval_id TEXT NOT NULL UNIQUE REFERENCES approval_requests(id) ON DELETE RESTRICT` (strictly prevents duplicate task creation)
   - `product_id TEXT NOT NULL REFERENCES inventory_products(id)`
   - `approved_reorder_quantity`, `estimated_cost`, `status`, timestamps.

### Row Level Security (RLS) Policy
All three tables have Row Level Security enabled (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY;`) with **zero public/client policies**. Direct PostgREST queries from browser clients are completely denied (fail-closed). All database operations are mediated exclusively by the FastAPI backend using `SUPABASE_SERVICE_ROLE_KEY` (which has `BYPASSRLS` privileges).

### Migration Instructions
To apply the database schema to your Supabase project:
1. Open the [Supabase Dashboard](https://supabase.com/dashboard) and select your project.
2. Navigate to **SQL Editor** in the left sidebar and click **New query**.
3. Copy the entire contents of [supabase/migrations/20261124000001_initial_shopops_schema.sql](file:///c:/Users/gupta/Desktop/ShopOps_Agent/supabase/migrations/20261124000001_initial_shopops_schema.sql).
4. Click **Run** (`Ctrl+Enter`).
5. Verify in **Table Editor** that `inventory_products`, `approval_requests`, and `reorder_tasks` appear.

---

## Tech Stack

| Tier | Technologies | Purpose |
|:---|:---|:---|
| **Backend Framework** | **FastAPI** (Python 3.10+) | High-performance asynchronous REST API, OpenAPI docs |
| **Data Validation** | **Pydantic v2** & **Pydantic Settings** | Strict schemas, field validation, settings management |
| **Generative AI** | **Google Gemini API** (`gemini-3.8-flash`) | Executive briefing synthesis, grounded conversational inquiry |
| **Database** | **Supabase PostgreSQL** | Relational storage, triggers, indexes, fail-closed RLS |
| **Backend Auth** | **Supabase JWT** + PyJWT | Cryptographic token verification & `OWNER_EMAIL` authorization |
| **Frontend Framework** | **React 18**, **TypeScript**, **Vite** | Responsive, accessible retail owner dashboard |
| **Frontend Auth** | **Supabase GoTrue REST** | Lightweight, zero-dependency token storage & refresh |
| **Testing Harness** | `unittest`, `node:test`, `httpx` | 113 backend unit tests, 12-step smoke test, frontend auth tests |

---

## Environment Variables & Configuration

### Backend Variables (Render Dashboard / `backend/.env`)

| Variable Name | Description | Required | Example |
| :--- | :--- | :---: | :--- |
| `ENVIRONMENT` | Runtime environment (`production` or `development`) | Yes | `production` |
| `OWNER_EMAIL` | Authorized store owner email | Yes | `owner@yourstore.com` |
| `SUPABASE_URL` | Supabase project URL | Yes | `https://<ref>.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Privileged secret key for database operations | Yes | *Confidential secret* |
| `SUPABASE_JWT_SECRET` | Secret used to verify Supabase JWT signatures | Yes | *Confidential secret* |
| `GEMINI_API_KEY` | Google AI Studio API key | Yes | *Confidential secret* |
| `CORS_ORIGINS` | Permitted frontend origins | Yes | `https://shop-ops-agent.vercel.app` |
| `CORS_ORIGIN_REGEX` | Permitted origin regex for preview branches | No | `^https:\/\/.*\.vercel\.app$` |

> [!CAUTION]
> **Security Guardrail:** `SUPABASE_SERVICE_ROLE_KEY` and `SUPABASE_JWT_SECRET` must **ONLY** be set on the backend. Never commit them to Git or expose them in frontend environments.

### Frontend Variables (Vercel Dashboard / `frontend/.env`)

| Variable Name | Description | Required | Example |
| :--- | :--- | :---: | :--- |
| `VITE_API_BASE_URL` | Render backend base URL | Yes | `https://shopops-agent.onrender.com` |
| `VITE_SUPABASE_URL` | Supabase project URL | Yes | `https://<ref>.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | Public client key (safe for browser exposure) | Yes | `<public-anon-key>` |

---

## Local Quickstart & Setup

### Prerequisites
- Python 3.10+
- Node.js 18+ & npm
- Git

### 1. Configure & Start Backend
```bash
cd backend
python -m venv venv

# Windows:
.\venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

# Start FastAPI dev server
uvicorn app.main:app --reload --port 8000
```
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)
- OpenAPI Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Configure & Start Frontend
In a separate terminal:
```bash
cd frontend
npm install
cp .env.example .env

# Start Vite dev server
npm run dev
```
- Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Verification & Testing

The project maintains a multi-tiered test suite covering backend logic, E2E smoke steps, and frontend token management:

### 1. Backend Regression Suite (113 Tests)
Runs all unit and integration tests across inventory CRUD, deterministic analysis, Gemini AI prompts, approval state machine, execution idempotency, Supabase repositories, and JWT auth:
```bash
cd backend
.\venv\Scripts\python.exe tests/run_tests.py
```
```text
Ran 113 tests in 0.520s
OK
============================================================
TEST EXECUTION SUMMARY:
Total Tests Run: 113 | Passed: 113 | Failures: 0 | Errors: 0
============================================================
```

### 2. End-to-End Operational Lifecycle Smoke Test (12 Steps)
Validates the complete 7-stage loop with mock repositories:
```bash
cd backend
.\venv\Scripts\python.exe tests/smoke_test_e2e.py
```
```text
  [STEP 1 PASS] Backend /health reports healthy status.
  [STEP 2 PASS] Created test product ID (SKU: SMOKE-MILK-001, Qty: 50).
  [STEP 3 PASS] Product confirmed present in inventory catalog query.
  [STEP 4 PASS] Patched qty to 8 (<20). Deterministic analysis: status='low_stock', recommended=32.
  [STEP 5 PASS] Approval request created as 'pending'. Quantity edited to 30 units.
  [STEP 6 PASS] Request successfully transitioned to 'approved'.
  [STEP 7 PASS] Executed approval. Created internal reorder task.
  [STEP 8 PASS] Reorder task confirmed in task backlog with status 'created'.
  [STEP 9 PASS] Approval confirmed in status 'executed'.
  [STEP 10 PASS] Invariant verified: Inventory quantity remains at 8 (non-destructive).
  [STEP 11 PASS] Idempotency verified: Duplicate execution was blocked with HTTP 400.
  [STEP 12 PASS] Authentication verified (401 on unauthenticated) & unconfigured handling verified.
```

### 3. Frontend Authentication Unit Tests (3 Tests)
Verifies configuration detection, token session persistence, and expiration buffer math:
```bash
cd frontend
npm test
```
```text
✔ isSupabaseConfigured detects valid vs placeholder configurations
✔ storeAuthSession and clearAuthSession manage token lifecycle
✔ isTokenExpired returns true when token is expired or within 60s buffer
ℹ tests 3 | pass 3 | fail 0 | duration_ms 70ms
```

### 4. Frontend Production Build & Typecheck
```bash
cd frontend
npm run build
```
```text
> tsc -b && vite build
✓ 62 modules transformed.
dist/assets/index-PkxdVGGt.js   449.20 kB │ gzip: 119.00 kB
✓ built in 1.08s
```

---

## Deployment & Live Cloud Verification Guide

### Completed Local / Mock Verification
- [x] 113 backend unit tests passed.
- [x] 12 E2E workflow smoke test steps passed.
- [x] 9 frontend auth and reactive retry unit tests passed.
- [x] Frontend TypeScript compilation and Vite build succeeded with 0 errors.

### Pending Live Cloud Verification Steps
To verify the application live in production after pushing code:

1. **Supabase Setup:**
   - Execute the migration [supabase/migrations/20261124000001_initial_shopops_schema.sql](file:///c:/Users/gupta/Desktop/ShopOps_Agent/supabase/migrations/20261124000001_initial_shopops_schema.sql) in your Supabase SQL Editor.
   - In Supabase Auth &rarr; Users, create a store owner user matching your `OWNER_EMAIL`.
2. **Render Backend Deployment:**
   - In the Render Dashboard, update the environment variables for `shopops-agent`:
     `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `OWNER_EMAIL`, `GEMINI_API_KEY`.
   - Verify health: `curl https://shopops-agent.onrender.com/health` returns `status: healthy`.
   - Verify auth provider: `curl https://shopops-agent.onrender.com/api/v1/auth/status` returns `"auth_provider": "supabase"`.
3. **Vercel Frontend Deployment:**
   - In the Vercel Dashboard, update environment variables for `shop-ops-agent`:
     `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`.
   - Trigger a redeploy.
   - Open `https://shop-ops-agent.vercel.app`, sign in with the store owner account, and verify that inventory, analysis, and approvals load live data.

---

## Demo Video & Walkthrough Script

A complete, timed 3–5 minute presentation script tailored for the Homingo Hack Days submission is available in [DEMO_SCRIPT.md](file:///c:/Users/gupta/Desktop/ShopOps_Agent/DEMO_SCRIPT.md).

It guides judges through:
1. **The Small Retail Dilemma** (0:00–0:45)
2. **The Observe & Analyze Loop** (0:45–1:30)
3. **Grounded Gemini AI Copilot** (1:30–2:25)
4. **Human-in-the-Loop Approval Gate** (2:25–3:15)
5. **Safe Execution & Invariants** (3:15–4:05)
6. **Architecture & Security Guarantees** (4:05–4:30)
