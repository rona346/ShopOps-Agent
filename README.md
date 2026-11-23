# ShopOps Agent

> **Autonomous Inventory Intelligence & Safe Human-in-the-Loop Operations for Small Retailers**  
> *Homingo Hack Days — Agents Track Submission*

[![Backend Tests](https://img.shields.io/badge/backend%20tests-100%20passed-brightgreen)](#verification--testing)
[![E2E Smoke Tests](https://img.shields.io/badge/e2e%20smoke%20tests-12%20passed-brightgreen)](#verification--testing)
[![Frontend](https://img.shields.io/badge/frontend-React%2018%20%2B%20TypeScript-blue)](#tech-stack)
[![FastAPI](https://img.shields.io/badge/backend-FastAPI%20%2B%20Pydantic-009688)](#tech-stack)
[![Gemini](https://img.shields.io/badge/AI-Google%20Gemini-orange)](#deterministic-math--gemini-ai-why-the-hybrid-model-matters)
[![Firebase](https://img.shields.io/badge/auth%20%26%20storage-Firebase%20%2F%20Firestore-yellow)](#tech-stack)

---

## Table of Contents
1. [The Real Problem ShopOps Agent Solves](#the-real-problem-shopops-agent-solves)
2. [Target User: The Independent Small Retailer](#target-user-the-independent-small-retailer)
3. [The Autonomous Agent Workflow (7 Stages)](#the-autonomous-agent-workflow-7-stages)
4. [Deterministic Math + Gemini AI: Why the Hybrid Model Matters](#deterministic-math--gemini-ai-why-the-hybrid-model-matters)
5. [Owner Approval & Execution Safety Guarantees](#owner-approval--execution-safety-guarantees)
6. [System Architecture & Project Layout](#system-architecture--project-layout)
7. [Tech Stack](#tech-stack)
8. [Local Quickstart & Setup](#local-quickstart--setup)
9. [Verification & Testing](#verification--testing)
10. [Demo Video & Walkthrough Script](#demo-video--walkthrough-script)

---

## The Real Problem ShopOps Agent Solves

Small, independent retail businesses operate on razor-thin margins and face two opposing, costly operational traps every day:

1. **The Stockout Trap (Lost Revenue & Churned Customers):** When high-velocity products (e.g., fresh dairy, coffee beans, specialty baked goods) run out, customers walk out the door and shop at big-box competitors. 
2. **The Overstock Trap (Trapped Working Capital):** Over-ordering slow-moving goods ties up scarce cash, clutters valuable stockroom space, and leads to inventory spoilage or markdowns.

### Why Existing Solutions Fail Small Retailers
- **Enterprise ERPs (SAP, NetSuite, Oracle):** Too expensive ($10k–$100k+/year), require months of configuration, and demand dedicated IT teams.
- **Manual Spreadsheets & Gut Feeling:** Error-prone, time-consuming, purely reactive, and forgotten during busy weekend shifts.
- **Generic LLM Chatbots:** Prone to mathematical hallucinations, cannot calculate accurate replenishment quantities or costs reliably, and lack safe transactional execution controls.

**ShopOps Agent solves this dilemma** by providing an autonomous, deterministic inventory intelligence engine coupled with Google Gemini for contextual executive insights—protected by a non-negotiable **human-in-the-loop owner approval gate**.

---

## Target User: The Independent Small Retailer

ShopOps Agent is specifically designed for:
- **Independent Grocers & Bodegas:** Tracking perishables, dairy, staples, and daily turnover.
- **Specialty Boutiques & Coffee Roasters:** Balancing high-margin specialty items and packaging supplies.
- **Neighborhood Pharmacies & Hardware Stores:** Managing thousands of SKUs without an enterprise IT department.

These business owners wear every hat: store manager, cashier, buyer, and bookkeeper. They do not have time to audit spreadsheets or calculate economic order quantities manually. They need a trusted co-pilot that flags risks early, does the math accurately, and asks for approval before taking operational action.

---

## The Autonomous Agent Workflow (7 Stages)

ShopOps Agent follows a rigorous, cyclical 7-stage autonomous operational loop:

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

Trust is the single most critical factor when bringing AI into retail operations. ShopOps Agent incorporates enterprise-grade safety mechanisms:

1. **Human-in-the-Loop (HITL) Governance:**
   - The agent proposes actions; only the verified store owner can approve them.
   - Owners can adjust proposed reorder quantities (e.g., matching supplier case sizes) before approving.
   - Status transitions follow an atomic state machine: `pending` &rarr; `approved` / `rejected` &rarr; `executed`.
2. **Non-Destructive Invariant:**
   - Executing an approval **never modifies on-hand inventory counts**. In-store physical quantities only change when goods are physically received and scanned into the shop.
3. **Internal Task Creation (No External Mock Orders):**
   - Execution creates an internal, traceable `ReorderTask` with unique identifiers, timestamps, and audit metadata. It does not attempt to contact real suppliers or execute real financial transactions.
4. **Strict Idempotency Protection:**
   - Each approval request can only be executed once. Attempting duplicate executions via API or UI immediately fails with `HTTP 400 Bad Request`.
5. **Fail-Closed Security Architecture:**
   - In production (`ENVIRONMENT=production`), the application strictly requires valid Firebase credentials. If credentials are missing or invalid, all protected endpoints fail closed (`HTTP 401 Unauthorized`).
   - Development fallback tokens (`DEV_AUTH_TOKEN`) are strictly prohibited in production and rejected by security guards.

---

## System Architecture & Project Layout

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
│   │   ├── core/                  # App config, security guards, Firebase Admin, Gemini SDK
│   │   ├── models/                # Pydantic schemas (Inventory, Analysis, Agent, Approvals, Tasks)
│   │   ├── services/              # Pure business logic & Firestore persistence services
│   │   └── main.py                # FastAPI ASGI application entrypoint
│   ├── tests/                     # 100 comprehensive unit & integration tests
│   │   ├── run_tests.py           # Automated regression runner (100 passing tests)
│   │   ├── smoke_test_e2e.py      # 12-step end-to-end operational lifecycle test
│   │   └── test_live_cloud.py     # Live Firestore & Gemini integration test suite
│   ├── requirements.txt           # Minimal backend dependencies
│   └── README.md
│
├── frontend/                      # React + Vite + TypeScript Dashboard
│   ├── src/
│   │   ├── components/            # Clean UI: Overview, Inventory, Analysis, Agent, Approvals, Tasks
│   │   ├── services/              # Type-safe API client (api.ts) & Firebase client (firebase.ts)
│   │   ├── types/                 # Shared TypeScript interfaces matching backend models
│   │   ├── App.tsx                # Master dashboard shell, navigation & auth status
│   │   └── index.css              # Responsive modern styling for retail operations
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── DEMO_SCRIPT.md                 # 3-5 minute demo video script for hackathon recording
├── .gitignore                     # Strict secret & credential isolation rules
└── README.md                      # Project documentation
```

---

## Tech Stack

| Tier | Technologies | Purpose |
|:---|:---|:---|
| **Backend Framework** | **FastAPI** (Python 3.10+) | High-performance asynchronous REST API, OpenAPI docs |
| **Data Validation** | **Pydantic v2** & **Pydantic Settings** | Strict schemas, field validation, settings management |
| **Generative AI** | **Google Gemini API** (`google-generativeai`) | Executive briefing synthesis, grounded conversational inquiry |
| **Database & Auth** | **Firebase Admin SDK** / **Firestore** | Cloud NoSQL database, Firebase ID token verification |
| **Frontend Framework** | **React 18**, **TypeScript**, **Vite** | Fast, responsive, type-safe retail owner dashboard |
| **Styling & Icons** | Custom responsive CSS & Lucide icons | Purpose-built, clutter-free single-page operations UI |
| **Testing Harness** | `unittest`, `pytest`, `httpx` | 100 automated unit/integration tests + 12-step E2E smoke tests |

---

## Local Quickstart & Setup

### Prerequisites
- Python 3.10 or higher
- Node.js 18 or higher & npm
- Git

### 1. Configure Backend Environment
Create `backend/.env` from the provided example:
```bash
cp backend/.env.example backend/.env
```
Default local settings in `backend/.env`:
```env
PROJECT_NAME="ShopOps Agent API"
ENVIRONMENT=development
ENABLE_DEV_AUTH=true
DEV_AUTH_TOKEN=dev-owner-token
OWNER_EMAIL=owner@shopops.local
FIREBASE_PROJECT_ID=
FIREBASE_CREDENTIALS_PATH=
GEMINI_API_KEY=
```

### 2. Install & Start Backend
```bash
cd backend
python -m venv venv

# Windows:
.\venv\Scripts\activate
# macOS/Linux:
# source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
- API Health Status: [http://localhost:8000/health](http://localhost:8000/health)
- Interactive OpenAPI Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Install & Start Frontend
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
- Open your browser to: [http://localhost:5173](http://localhost:5173)

---

## Verification & Testing

ShopOps Agent includes a complete, multi-tiered test suite ensuring zero regressions, solid math, and rock-solid security.

### 1. Run Complete Backend Regression Suite (100 Tests)
```bash
cd backend
.\venv\Scripts\python.exe tests/run_tests.py
```
```text
Ran 100 tests in 0.857s
OK
============================================================
TEST EXECUTION SUMMARY:
Total Tests Run: 100 | Passed: 100 | Failures: 0 | Errors: 0
============================================================
```

### 2. Run End-to-End Smoke Test Suite (12 Lifecycle Steps)
Tests the full lifecycle from product creation, low-stock detection, approval proposal, quantity modification, approved execution, task creation, non-destructive invariant checks, and idempotency protection.
```bash
cd backend
.\venv\Scripts\python.exe tests/smoke_test_e2e.py
```
```text
  [STEP 1 PASS] Backend /health reports healthy status.
  [STEP 2 PASS] Created test product ID: test_xxx (SKU: SMOKE-MILK-001, Qty: 50).
  [STEP 3 PASS] Product confirmed present in inventory catalog query.
  [STEP 4 PASS] Patched qty to 8 (<20). Deterministic analysis: status='low_stock', recommended=32.
  [STEP 5 PASS] Approval request created as 'pending'. Quantity edited to 30 units.
  [STEP 6 PASS] Request successfully transitioned to 'approved'.
  [STEP 7 PASS] Executed approval. Created internal reorder task.
  [STEP 8 PASS] Reorder task confirmed in task backlog with status 'created'.
  [STEP 9 PASS] Approval confirmed in status 'executed'.
  [STEP 10 PASS] Invariant verified: Inventory quantity remains at 8 (non-destructive).
  [STEP 11 PASS] Idempotency verified: Duplicate execution blocked with HTTP 400.
  [STEP 12 PASS] Authentication verified & unconfigured cloud gracefully handles 503.
```

### 3. Run Live Cloud Integration Suite
```bash
cd backend
.\venv\Scripts\python.exe tests/test_live_cloud.py
```
> Gracefully detects when cloud credentials are unconfigured and reports `BLOCKED` with instructions, or tests live Firestore and Gemini if valid credentials are provided.

### 4. Build Frontend Production Bundle
```bash
cd frontend
npm run build
```
> TypeScript compilation (`tsc -b`) and Vite production bundle build cleanly with 0 errors.

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
