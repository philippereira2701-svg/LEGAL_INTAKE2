# LEGAL_INTAKE2 Backend and API Architecture Summary

## 1) Project Purpose and Core Idea

This project is an AI-assisted legal intake platform for personal injury law firms. The system collects client incident details, triages case quality, stores lead records, and triggers follow-up actions such as attorney notifications and client communications.

At a high level, the product solves three operational pain points:

- Fast intake capture from prospective clients.
- Consistent lead qualification using deterministic rules plus AI scoring.
- Immediate operational response (dashboarding, messaging, and routing decisions).

The codebase currently contains two backend patterns:

- A legacy monolithic flow centered around `main.py`.
- A newer multi-tenant architecture centered around `app.py`, `api.py`, and `workers.py`.

Because both are present, understanding "how the backend works" requires seeing how each layer is intended to function and where there are integration gaps.

## 2) High-Level Architecture

The backend stack is Python/Flask with SQLAlchemy, Celery, Redis, and Gemini AI.

Primary components:

- Web framework: Flask (`app.py` application factory and routes).
- API layer: Flask Blueprint in `api.py` under `/api/*`.
- Auth layer: JWT + bcrypt in `auth.py`.
- Data layer: SQLAlchemy models/session in `database.py`.
- Async processing: Celery tasks in `workers.py`.
- AI scoring: Gemini + Pydantic schema validation (`intake_scorer.py` and `workers.py`).
- Deterministic pre-AI gate: `rule_engine.py`.
- Notification channels: Twilio SMS and SMTP/Gmail email.
- Optional analytics offload client: `dungbeetle_client.py`.
- Migration baseline: Alembic revision in `migrations/versions/001_initial.py`.

Operationally, there are two execution paths:

1. **Legacy synchronous path (`main.py`)**
   - Intake POST to `/intake`.
   - Immediate scoring and DB insert in request cycle.
   - Router + notifier triggered directly.

2. **Current asynchronous path (`app.py` + `api.py` + `workers.py`)**
   - Public intake POST to `/api/intake/<firm_slug>`.
   - Request validated and enqueued via Celery.
   - Worker applies rules, AI scoring, persistence, and notifications asynchronously.

The second path is the intended production architecture because it is multi-tenant and more scalable.

## 3) Request Lifecycle: How the New Backend Flow Works

### 3.1 App bootstrap

`app.py` uses an application factory (`create_app`) and performs:

- Environment validation (`DATABASE_URL`, `REDIS_URL`, `GEMINI_API_KEY`, `JWT_SECRET_KEY`, `FLASK_SECRET_KEY`).
- Blueprint registration (`api_bp` mounted at `/api`).
- Frontend route wiring (`/login`, `/dashboard`, `/intake/<firm_slug>`, `/leads/<lead_id>`).
- Authentication decorators for protected pages.

### 3.2 Public intake endpoint

`POST /api/intake/<firm_slug>` in `api.py`:

- Finds tenant by `firm_slug`.
- Validates request body with `IntakeFormSchema` (Pydantic).
- Enforces contact requirement (phone or email required).
- Enqueues async processing via `process_intake_task.delay(tenant_id, form_data)`.
- Returns `{"status": "received"}` quickly.

This keeps the web request lightweight and shifts heavy AI/notification work to background workers.

### 3.3 Worker orchestration

`process_intake_task` in `workers.py` runs the core business pipeline:

1. Rule engine preprocess (`RuleEngine.process`):
   - Sanitizes user text.
   - Detects prompt-injection patterns.
   - Applies hard disqualifiers (expired SOL, already represented, outside US jurisdiction, no damages).

2. Gemini scoring (if not disqualified):
   - Sends incident narrative to Gemini.
   - Expects JSON response with scoring fields.
   - Parses and merges AI output.

3. Score adjustment:
   - Applies deterministic modifiers (`apply_modifiers`) to derive final score.

4. Persistence:
   - Saves lead + event logs through database manager methods.

5. Notification chain:
   - Chains client notification task then lawyer notification task.

### 3.4 Notification strategy

`notify_client_task`:

- Score >= 8: SMS with immediate booking CTA.
- Score >= 5: email acknowledging attorney review.
- Score < 5: decline-style email.

`notify_lawyer_task`:

- Score >= 8: urgent SMS to lawyer.
- Score >= 5: summary email to lawyer.
- Logs communication and event metadata.

A periodic retry task is configured to revisit failed communications.

## 4) Authentication, Authorization, and Tenant Isolation

### 4.1 Login flow

`POST /api/auth/login`:

- Looks up user by email.
- Verifies bcrypt password hash.
- Generates JWT with `tenant_id`, `user_id`, and `role`.
- Returns token as `httpOnly`, `secure`, `SameSite=Lax` cookie (`access_token`).

### 4.2 Protected routes

`require_auth` in `auth.py`:

- Accepts token from cookie or `Authorization: Bearer ...`.
- Verifies JWT signature and expiration.
- Sets request context globals (`g.tenant_id`, `g.user_id`, `g.role`).

`require_role` supports role-based authorization with admin override.

### 4.3 Tenant model and intended isolation

The migration defines multi-tenant schema with UUID identifiers and row-level security (RLS) policies in PostgreSQL:

- `tenants`, `users`, `leads`, `lead_events`, `communications`.
- RLS policies bind rows to `current_setting('app.tenant_id')`.

Design intent: each law firm sees only its own leads and communication records.

## 5) Data Model and Persistence Design

From migration and runtime models, important entities are:

- **Tenant**: firm profile, contact channels, operational settings.
- **User**: login identity linked to tenant.
- **Lead**: intake data, AI/rule scores, triage status.
- **LeadEvent**: workflow/audit timeline.
- **Communication**: outbound message history, retries, provider IDs.

The project also maintains lightweight dashboard metrics:

- Total leads.
- Average score.
- High-priority count.
- Conversion-related rates.

In legacy mode (`main.py`), simpler tables and synchronous inserts are used.

## 6) API Surface and Frontend Usage

### 6.1 New API endpoints (Blueprint in `api.py`)

- `POST /api/intake/<firm_slug>`: public intake submission.
- `POST /api/auth/login`: issue authenticated session token.
- `GET /api/dashboard/stats`: protected KPI metrics.
- `GET /api/leads?page=N`: protected paginated lead list.
- `GET /api/health`: health check.

### 6.2 Legacy API endpoints (`main.py`)

- `POST /intake`: synchronous intake.
- `GET /api/stats`: admin dashboard stats (API-key guarded).
- `GET /api/leads`: admin leads list (API-key guarded).
- `GET /admin`: admin page (API-key guarded).

### 6.3 Frontend integration patterns

Current templates show mixed usage:

- `templates/login.html` correctly calls `POST /api/auth/login`.
- `templates/form.html` posts to `POST /api/intake/lexbridge`.
- `templates/dashboard.html` fetches legacy endpoints (`/api/stats` and `/api/leads`) with `?key=...`.
- `static/js/match-wizard.js` posts to legacy `/intake`.

This indicates a transition state where some pages use the new stack while others still consume legacy routes.

## 7) External Services and Their Roles

- **Gemini API**:
  - Structured triage scoring in both sync and async paths.
  - Fallback behavior exists (heuristic mode in `intake_scorer.py`) when AI is unavailable.

- **Redis + Celery**:
  - Queue and execute background jobs.
  - If Redis is not reachable, eager mode can run tasks synchronously for local testing.

- **Twilio**:
  - Sends high-priority SMS to clients/lawyers.
  - Used in routing and notification layers.

- **SMTP/Gmail**:
  - Sends non-urgent updates and lawyer summaries.

- **DungBeetle**:
  - Optional async SQL reporting client for heavy read workloads.

## 8) Reliability, Security, and Operational Characteristics

Strengths visible in current design:

- Input validation via Pydantic schema.
- Authentication with JWT and bcrypt.
- Rule-engine guard before AI invocation.
- Asynchronous orchestration for scale and resilience.
- Retry semantics in Celery tasks.
- Multi-tenant schema and intended RLS.

Important practical caveats from code inspection:

- `main.py` and `app.py` represent different generations of architecture.
- Some templates/scripts still call legacy routes.
- `database.py` runtime models are simplified compared with richer migration schema.
- Worker code expects methods/entities not fully reflected in the simplified runtime manager (likely an in-progress refactor).
- Environment key names differ between modules in a few places (`TWILIO_SID` vs `TWILIO_ACCOUNT_SID`, etc.).

So the project’s basic idea is clear and strong, but full production alignment requires consolidating the legacy/new paths into one consistent execution model.

## 9) End-to-End Mental Model (Simple View)

If you explain this project to a new engineer:

1. A prospective client submits intake details.
2. The system sanitizes and screens the input with deterministic legal/business rules.
3. AI estimates case quality and produces structured reasoning.
4. Scores are normalized to a final decision grade.
5. Lead and audit data are saved under the law firm’s tenant.
6. Client and attorney notifications are sent based on urgency tier.
7. Staff uses dashboard APIs to monitor pipeline and act on leads.

That is the core product loop: **capture -> evaluate -> persist -> notify -> manage**.

## 10) Conclusion

LEGAL_INTAKE2 is a legal-intake automation backend built around a modern pattern: tenant-aware APIs, AI-assisted scoring, and asynchronous workflow execution. The codebase currently includes both legacy and newer implementations, but the intended architecture is the newer `app.py` + `api.py` + `workers.py` pipeline. APIs are used by web templates for login, intake submission, and dashboard data retrieval, while background tasks integrate AI and communications providers to drive near-real-time legal lead operations.

For long-term maintainability, the main strategic task is architecture convergence: migrate remaining legacy endpoint consumers to the newer API surface and ensure one authoritative data model across runtime ORM and migrations.
