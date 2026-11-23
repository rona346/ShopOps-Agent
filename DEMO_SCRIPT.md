# ShopOps Agent — 3–5 Minute Demo Video Script
**Homingo Hack Days — Agents Track Submission**

---

## Video Specifications
- **Target Duration:** 3 minutes 30 seconds – 4 minutes 30 seconds
- **Format:** Screen capture with voiceover narration + web camera overlay (bottom-right corner)
- **Resolution:** 1080p (1920x1080) at 60 fps
- **Key Persona:** Alex, owner of *Cornerstone Pantry & Goods* (an independent neighborhood specialty retailer)
- **Demo Scenario:** Identifying a critical low-stock product ("Organic Whole Milk - 1 Gallon"), analyzing reorder urgency, consulting Gemini AI, adjusting and approving a reorder proposal, and safely executing an internal reorder task.

---

## Visual & Setup Checklist Before Recording

1. **Backend Terminal:** Running `uvicorn app.main:app --port 8000` (in `backend/` with venv activated).
2. **Frontend Browser Tab:** Opened to `http://localhost:5173` at standard 100% zoom.
3. **Demo Data Ready:**
   - In-memory/mock storage or Firestore with at least 5 realistic retail products:
     - `SMOKE-MILK-001` — *Organic Whole Milk (1 Gallon)*: Quantity = 8, Reorder Point = 20, Unit Cost = $3.75 (Status: Low Stock)
     - `BEV-COF-002` — *Artisan Espresso Beans (1kg)*: Quantity = 45, Reorder Point = 15, Unit Cost = $14.50 (Status: Normal)
     - `BAK-FLR-003` — *Organic Sourdough Flour (5kg)*: Quantity = 0, Reorder Point = 10, Unit Cost = $8.00 (Status: Out of Stock)
     - `SNK-CHIP-004` — *Sea Salt Kettle Chips (24-pack)*: Quantity = 85, Reorder Point = 20, Unit Cost = $18.00 (Status: Overstock)
4. **Authentication:** Logged in as `owner@shopops.local` (Development mode or Firebase Auth).

---

## Step-by-Step Script & Timing

### Scene 1: The Problem & Vision (0:00 – 0:45)
**Screen:** Camera on speaker, transitioning to the ShopOps Agent Dashboard Overview.

> **Voiceover (Presenter):**
> *"Every single day, independent retail shop owners face an agonizing dilemma: run out of stock and lose customers to big-box chains, or over-order and choke their working capital in unsold inventory.*
>
> *Enterprise ERPs like SAP and NetSuite are built for Fortune 500 corporations with dedicated IT teams. Small shop owners are left juggling messy spreadsheets, scribbled notepads, and gut instinct.*
>
> *Meet **ShopOps Agent** — the autonomous operations partner built specifically for small retail business owners. It bridges the gap between pure mathematical inventory discipline and generative AI intelligence, wrapped in a strict human-in-the-loop safety architecture."*

---

### Scene 2: The Agentic Observe & Analyze Loop (0:45 – 1:30)
**Screen:** Navigate to **Overview** and **Inventory Analysis** tabs.

> **Voiceover (Presenter):**
> *"ShopOps Agent operates on a continuous 7-stage autonomous loop: Observe, Analyze, Plan, Ask Approval, Execute, Verify, and Report.*
>
> *Here on the Overview screen, the agent has already **Observed** our current catalog. Notice our real-time inventory health counters: 1 out-of-stock item, 1 critical low-stock item, and 1 overstocked item.*
>
> *Let's drill into the **Inventory Analysis** tab. Unlike black-box AI chatbots that make up numbers, ShopOps Agent's analysis is **100% deterministic**. The engine computes stock thresholds with strict formulas. 
>
> *Look at our 'Organic Whole Milk' — with only 8 units left against a reorder threshold of 20, the engine determines it is critically low, calculates an exact recommended replenishment of 32 units, and estimates the supplier cost at exactly \$120.00."*

---

### Scene 3: Grounded Gemini AI Insights & Inquiries (1:30 – 2:25)
**Screen:** Navigate to the **Agent Insights** tab. Click "Generate Executive Briefing", then submit a natural-language query.

> **Voiceover (Presenter):**
> *"Now, here is where Google Gemini shines. Instead of drowning the owner in raw numbers, the agent synthesizes this mathematical analysis into an **Executive Briefing**.*
>
> *Gemini highlights our immediate risks: Organic Whole Milk will face a stockout during the upcoming weekend rush, while Sourdough Flour requires emergency vendor reordering. Crucially, Gemini cannot hallucinate inventory numbers — it is strictly grounded in our deterministic analysis payload.*
>
> *Let's ask the agent a conversational question: 'Which supplier orders are most urgent today, and what is our immediate cash outlay?'*
>
> *(Types query and hits Enter)*
>
> *Within seconds, Gemini responds with a structured, executive summary: prioritizing the milk and flour, referencing the exact deterministic replenishment amounts, and calculating the required cash outlay."*

---

### Scene 4: The Human-in-the-Loop Approval Gate (2:25 – 3:15)
**Screen:** Switch to **Approvals** tab. Show the pending approval card for Organic Whole Milk. Click "Edit Quantity", change to 30, and approve.

> **Voiceover (Presenter):**
> *"AI should assist decisions, not hijack cash flow. Autonomous agents should never place external purchase orders or drain bank accounts unsupervised.*
>
> *This brings us to the **Ask Approval** stage. From the deterministic recommendation, ShopOps Agent generated an Approval Request for 32 units of Milk.*
>
> *As the shop owner, I have complete sovereignty. I notice our supplier ships in cases of 10. So right here in the UI, I edit the proposed quantity from 32 to 30 units. The estimated cost instantly updates to \$112.50.*
>
> *Satisfied, I click **Approve**. The request transitions from 'Pending' to 'Approved'."*

---

### Scene 5: Safe Execution, Verification & Invariants (3:15 – 4:05)
**Screen:** Click **Execute Reorder** button. Modal appears. Confirm. Navigate to **Reorder Tasks** and **Inventory** tabs.

> **Voiceover (Presenter):**
> *"Now we enter the **Execute and Verify** stages. 
>
> *Clicking 'Execute Reorder' opens a safety confirmation modal detailing the action. When I confirm, what happens?*
>
> *1. It creates an internal, traceable **Reorder Task** with status 'Created'.*
> *2. The approval request status transitions atomically to 'Executed'.*
> *3. **The Invariant Check:** Notice our on-hand inventory quantity remains at 8 units! ShopOps Agent never prematurely inflates stock before goods physically arrive at our loading dock.*
> *4. **Idempotency Check:** If someone tries to re-execute this approval, the system rejects it immediately with HTTP 400 — duplicate orders are impossible."*

---

### Scene 6: Architecture, Security & Closing (4:05 – 4:30)
**Screen:** Switch to code/architecture slide or terminal showing test suite results.

> **Voiceover (Presenter):**
> *"Under the hood, ShopOps Agent is built on FastAPI, Firebase Firestore & Authentication, Google Gemini API, and React with TypeScript. 
>
> *It features 100 passing automated backend tests, full end-to-end smoke verification, and a fail-closed security architecture where dev tokens cannot run in production.*
>
> *ShopOps Agent gives small retailers the predictive superpowers of a giant corporation with the safety, control, and peace of mind they need to thrive.*
>
> *Thank you! Visit our repository to run the local setup in under two minutes."*

---

## Judge Presentation Quick-Sheet

| Timestamp | Phase Highlighted | Key Takeaway for Judges |
|:---|:---|:---|
| **0:00 - 0:45** | Problem Context | Targets real-world pain point: small retail stockouts vs. working capital tie-up. |
| **0:45 - 1:30** | Deterministic Engine | Source-of-truth calculations are 100% deterministic. No AI hallucination on quantities or costs. |
| **1:30 - 2:25** | Gemini AI Grounding | Gemini acts as an executive copilot, synthesizing deterministic math into plain business insights. |
| **2:25 - 3:15** | Human-in-the-Loop | Owner maintains full sovereignty; can edit reorder quantities before approving. |
| **3:15 - 4:05** | Safe Execution & Invariants | Non-destructive execution: internal tasks created; inventory balances never artificially altered; idempotency enforced. |
| **4:05 - 4:30** | Production Readiness | 100 passing unit/integration tests, 12-step smoke test, fail-closed auth. |
