# Backend - ShopOps Agent

FastAPI application providing core API services, operational endpoints, inventory data management, deterministic inventory analysis, Google Gemini AI Agent Engine, Owner Approval Workflow, and Approved Action Execution.

---

## Architecture Overview

```text
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── __init__.py
│   │       │   ├── inventory.py     # Inventory CRUD, analysis, and reorder planning endpoints
│   │       │   ├── agent.py         # AI Agent insights and grounded natural language Q&A
│   │       │   ├── approvals.py     # Owner approval workflow endpoints & execution trigger
│   │       │   └── tasks.py         # Internal reorder tasks endpoints
│   │       ├── __init__.py
│   │       └── router.py            # Central API v1 router
│   ├── core/
│   │   ├── config.py                # Pydantic Settings & environment variable parsing
│   │   ├── firebase.py              # Lazy Firebase Admin & Firestore client provider
│   │   └── gemini.py                # Lazy Google Gemini client provider
│   ├── models/
│   │   ├── __init__.py
│   │   ├── inventory.py             # Product schemas (Base, Create, Update, Response)
│   │   ├── analysis.py              # Analysis schemas (StockStatus, AnalysisItem, Summary, Recommendations)
│   │   ├── agent.py                 # AI Agent schemas (InsightsResponse, QueryRequest, QueryResponse)
│   │   ├── approval.py              # Approval schemas (Request, Create, Update, Decision, Response)
│   │   └── task.py                  # Reorder task schemas (TaskStatus, TaskCreate, TaskResponse)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── inventory.py             # FirestoreInventoryService and repository interface
│   │   ├── inventory_analysis.py    # Deterministic InventoryAnalysisService engine
│   │   ├── agent.py                 # Gemini InventoryAgentService
│   │   ├── approval.py              # FirestoreApprovalService and repository interface
│   │   └── execution.py             # ActionExecutionService & FirestoreTaskService
│   ├── __init__.py
│   └── main.py                      # FastAPI entrypoint, error handlers, and core routes
├── tests/
│   ├── __init__.py
│   ├── fake_inventory_repo.py       # Isolated in-memory inventory repository
│   ├── fake_approval_repo.py        # Isolated in-memory approval repository
│   ├── fake_task_repo.py            # Isolated in-memory reorder task repository
│   ├── mock_gemini_client.py        # Mocked Gemini client for zero-cost, offline AI testing
│   ├── test_models.py               # Product model validation & low-stock logic tests
│   ├── test_inventory_api.py        # REST API endpoint tests (CRUD, filters, pagination)
│   ├── test_firestore_unconfigured.py # Real FirestoreService unconfigured error handling tests
│   ├── test_analysis_service.py     # Unit tests for deterministic analysis & reorder rules
│   ├── test_analysis_api.py         # API tests for /analysis and /reorder-recommendations
│   ├── test_agent_service.py        # Unit tests for Gemini agent prompt logic, grounding & errors
│   ├── test_agent_api.py            # API tests for /agent/insights and /agent/query
│   ├── test_approval_service.py     # Unit tests for approval lifecycle, edits, and state transitions
│   ├── test_approval_api.py         # API integration tests for /approvals endpoints
│   ├── test_execution_service.py    # Unit tests for action execution, idempotency & verification
│   ├── test_execution_api.py        # API tests for execution trigger and /tasks endpoints
│   └── run_tests.py                 # Automated test runner
├── .env.example                     # Environment template (no secrets)
├── requirements.txt                 # Backend dependencies
└── README.md                        # Documentation
```

---

## Status & Capabilities

### Implemented Functionality
- **Phase 1: Backend Foundation**:
  - Validated configuration via `pydantic-settings` reading from `.env`.
  - CORS middleware supporting configured frontend origins.
  - Decoupled `GET /` (metadata) and `GET /health` (standalone probe).
  - Lazy initialization for Firebase Admin and Google Gemini clients.
- **Phase 2: Inventory Data Layer & CRUD API**:
  - Strongly typed Pydantic models with input sanitization, non-negative numbers, UTC timestamps, and normalized SKUs.
  - Firestore inventory repository (`FirestoreInventoryService`) with unique SKU enforcement.
  - Complete RESTful endpoints mounted under `/api/v1/inventory`.
  - Deterministic low-stock calculation (`quantity <= reorder_point`).
  - Strict error handling mapping domain exceptions to HTTP 400 (Bad Request), 404 (Not Found), and 503 (Service Unavailable).
- **Phase 3: Inventory Analysis & Reorder Planning Engine**:
  - Deterministic stock classification (`out_of_stock`, `low_stock`, `normal`, `overstock`).
  - Replenishment targets calculated without altering stored quantities: `target_stock = max(2 * reorder_point, 10)`.
  - Overstock detection: flags products with `quantity > (reorder_point * 3)` (or `quantity > 50` when `reorder_point == 0`).
  - Read-only, non-destructive execution.
- **Phase 4: Gemini AI Agent Engine**:
  - Dedicated `InventoryAgentService` consuming deterministic inventory analysis.
  - Structured executive inventory briefings for small retail business owners (`GET /api/v1/agent/insights`).
  - Grounded natural language Q&A endpoint (`POST /api/v1/agent/query`).
  - Safety constraints: zero database write permissions, zero side-effects, hallucination guards, and clean error handling (503 when unconfigured, 502 on model failure).
- **Phase 5: Owner Approval Workflow**:
  - Structured human-in-the-loop approval requests persisted in collection `approval_requests`.
  - Generates approval requests directly from deterministic reorder recommendations.
  - Lifecycle state machine: `pending` -> `approved` or `rejected`.
  - Prevents illegal state transitions (cannot approve already decided requests).
  - Allows owners to adjust the proposed reorder quantity before finalizing a decision.
- **Phase 6: Approved Action Execution & Verification**:
  - Dedicated `ActionExecutionService` converting approved proposals into internal reorder tasks in collection `reorder_tasks`.
  - **Pre-execution Gate**: Only requests with status `approved` can be executed.
  - **Idempotency**: Prevents duplicate task creation if an approved request is executed more than once.
  - **Verification Gate**: Verifies task persistence in Firestore before transitioning the source approval to `executed`.
  - **Failure Handling**: If task creation fails, the approval request remains in `approved` state.
  - **Inventory Immutability**: Inventory quantity is **not** increased upon task creation. Stock updates will occur only upon verified physical delivery receipt in subsequent operational workflows.

> **Security & Authentication Note**:
> Authentication is **not implemented yet**. The API is currently intended for **local development and hackathon demonstration use only**. Firebase Authentication token validation will be added in a future phase.

### Future Functionality (Subsequent Phases)
- **Supplier Order Dispatch & Delivery Receipt**: Real external supplier email/API communication, delivery tracking, and receiving workflow to increment inventory.
- **Firebase Authentication**: User token verification and shop-level multitenancy security.

---

## API Endpoints Overview

### Core & Health
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Application metadata and documentation links |
| `GET` | `/health` | Standalone health status probe (independent of credentials) |

### Inventory (`/api/v1/inventory`)
| Method | Endpoint | Description | Query Parameters |
|---|---|---|---|
| `GET` | `/api/v1/inventory` | List products with pagination & filters | `limit` (default 50), `offset` (default 0), `search` (name/SKU), `low_stock` (true/false) |
| `POST` | `/api/v1/inventory` | Create a new product (enforces unique SKU) | None |
| `GET` | `/api/v1/inventory/analysis` | Full deterministic catalog analysis and stock breakdown | `category` (optional) |
| `GET` | `/api/v1/inventory/reorder-recommendations` | List items requiring replenishment | `category` (optional) |
| `GET` | `/api/v1/inventory/low-stock` | List low-stock products (`quantity <= reorder_point`) | `limit` (default 50), `offset` (default 0) |
| `GET` | `/api/v1/inventory/{product_id}` | Retrieve a single product by ID | None |
| `PATCH` | `/api/v1/inventory/{product_id}` | Update specific fields of an existing product | None |
| `DELETE` | `/api/v1/inventory/{product_id}` | Permanently delete a product | None |

### AI Agent (`/api/v1/agent`)
| Method | Endpoint | Description | Query / Body |
|---|---|---|---|
| `GET` | `/api/v1/agent/insights` | Executive inventory analysis and recommendations | Query: `category` (optional) |
| `POST` | `/api/v1/agent/query` | Natural language question answering grounded in inventory data | Body: `{"query": "...", "category": "..."}` |

### Approval Workflow (`/api/v1/approvals`)
| Method | Endpoint | Description | Query / Body |
|---|---|---|---|
| `GET` | `/api/v1/approvals` | List approval requests with pagination & status filter | Query: `status` (pending/approved/rejected/executed), `limit`, `offset` |
| `POST` | `/api/v1/approvals` | Create approval request manually | Body: `ApprovalRequestCreate` |
| `POST` | `/api/v1/approvals/from-recommendation` | Create approval request from product's reorder recommendation | Body: `{"product_id": "..."}` |
| `GET` | `/api/v1/approvals/{request_id}` | Retrieve approval request details | None |
| `PATCH` | `/api/v1/approvals/{request_id}` | Edit proposed reorder quantity before decision | Body: `{"proposed_reorder_quantity": 25, "notes": "..."}` |
| `POST` | `/api/v1/approvals/{request_id}/approve` | Approve a pending proposal | Body: `{"notes": "..."}` (optional) |
| `POST` | `/api/v1/approvals/{request_id}/reject` | Reject a pending proposal | Body: `{"notes": "..."}` (optional) |
| `POST` | `/api/v1/approvals/{request_id}/execute` | Execute an approved proposal into an internal reorder task | Query: `execution_notes` (optional) |

### Reorder Tasks (`/api/v1/tasks`)
| Method | Endpoint | Description | Query Parameters |
|---|---|---|---|
| `GET` | `/api/v1/tasks` | List internal reorder tasks with pagination & status filter | Query: `status` (created/in_progress/completed/cancelled), `limit`, `offset` |
| `GET` | `/api/v1/tasks/{task_id}` | Retrieve reorder task by document ID | None |
| `GET` | `/api/v1/tasks/by-approval/{approval_id}` | Retrieve reorder task linked to an approval request | None |

---

## Example Execution Request & Response Payloads

### Execute Approved Request (`POST /api/v1/approvals/appr_9a1b2c3d/execute?execution_notes=PO-2026-101`)

**Response (`201 Created`)**:
```json
{
  "id": "task_4f7e2a1b",
  "approval_id": "appr_9a1b2c3d",
  "product_id": "7xF2qK1vAbCdE9z",
  "sku": "HONEY-500G",
  "product_name": "Organic Honey",
  "approved_reorder_quantity": 20,
  "estimated_cost": 170.0,
  "status": "created",
  "notes": "PO-2026-101",
  "created_at": "2026-11-22T13:25:00.000000+00:00",
  "updated_at": "2026-11-22T13:25:00.000000+00:00"
}
```

---

## Running the Automated Test Suite

All tests use Python's built-in `unittest` framework:

```powershell
cd backend
.\venv\Scripts\Activate.ps1   # Windows
# source venv/bin/activate    # macOS/Linux

python tests/run_tests.py
```

### Test Suite Structure (80 Tests Total):
- `tests/test_models.py`: 8 tests (product schema validation, SKU normalization, low-stock logic).
- `tests/test_inventory_api.py`: 11 tests (inventory CRUD, pagination, search, low-stock filters).
- `tests/test_firestore_unconfigured.py`: 3 tests (unconfigured Firebase handling).
- `tests/test_analysis_service.py`: 8 tests (deterministic stock classification, reorder targets, overstock rules).
- `tests/test_analysis_api.py`: 4 tests (`/analysis` and `/reorder-recommendations` endpoints).
- `tests/test_agent_service.py`: 5 tests (Gemini prompt grounding, insights parsing, missing keys, API errors).
- `tests/test_agent_api.py`: 5 tests (`/agent/insights` and `/agent/query` integration).
- `tests/test_approval_service.py`: 11 tests (approval lifecycle, quantity edits, cost recalculation, invalid state transitions, non-destruction).
- `tests/test_approval_api.py`: 11 tests (`/approvals` REST endpoints, status filters, transitions, 422 validations, unconfigured Firestore 503).
- `tests/test_execution_service.py`: 6 tests (executing approved requests, rejecting pending/rejected, duplicate execution prevention, task verification, failure safety, inventory immutability).
- `tests/test_execution_api.py`: 8 tests (`/approvals/{id}/execute` endpoint, duplicate 400s, `/tasks` list/pagination, `/tasks/{id}`, `/tasks/by-approval/{id}`, unconfigured Firestore 503).
