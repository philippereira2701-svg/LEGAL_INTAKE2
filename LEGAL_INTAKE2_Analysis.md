# LEGAL_INTAKE2 Project Analysis Report

## 1. Project Overview
**LEGAL_INTAKE2** is a specialized legal tech application designed to automate the intake and triage process for personal injury law firms.
*   **Problem Solved**: It replaces manual intake processes with an automated system that collects potential client data, uses AI to score and prioritize cases (triage), and automatically routes high-value cases to lawyers while managing client communication.
*   **Target Users**:
    *   **Potential Clients**: Users submitting their case details via the public intake form.
    *   **Lawyers/Paralegals**: Staff viewing the dashboard to monitor incoming leads and AI scores.
*   **Core Concepts**: Client Intake, Lead Scoring (AI), Triage (Auto-Book vs. Reject), Automated Notification (SMS/Email), Case Management Dashboard.
*   **Tech Stack**:
    *   **Frontend**: HTML5, Vanilla JavaScript, CSS (custom styling), Chart/Dashboard UI.
    *   **Backend**: Python (Flask).
    *   **Database**: SQLite (via SQLAlchemy ORM).
    *   **AI/ML**: Google Gemini API (via `google-genai` SDK).
    *   **Integrations**: Twilio (SMS), SMTP (Email).
*   **Architecture**: Monolithic Flask application with a Service-Layer pattern (Scorer, Router, Notifier services separate from Controller logic).

## 2. Frontend Analysis
The frontend consists of server-side rendered HTML templates with embedded vanilla JavaScript for interactivity.

### Pages & Components
1.  **`templates/form.html` (Public Intake Form)**
    *   **Purpose**: The public-facing wizard for clients to submit case details.
    *   **Renders**: A multi-step form (Personal Specs -> Incident Specs -> Damage Specs).
    *   **Functions**:
        *   `nextStep(s)`: Manages visibility of form sections (wizard navigation).
        *   `hideStatus()`: Resets the UI from error state back to the form.
        *   `form.onsubmit`: Async handler that collects DOM values, constructs a JSON payload, POSTs to `/intake`, and handles the success/error UI states.
    *   **Data Flow**: Captures user input -> POST to Backend -> Displays success/failure message.

2.  **`templates/dashboard.html` (Admin Dashboard)**
    *   **Purpose**: Real-time view for lawyers to monitor incoming leads.
    *   **Renders**: Statistics cards (Total Volume, Avg Quality), a data table of leads, and an activity feed. Includes a "Share QR" modal and a "Lead Details" side panel.
    *   **Functions**:
        *   `refreshData()`: Fetches data from `/api/stats` and `/api/leads` concurrently.
        *   `updateUI(stats, leads)`: Updates DOM elements with new data, renders the table rows and activity feed.
        *   `openLead(id)`: Populates and opens the side panel with detailed lead info (AI analysis, scores).
        *   `override(id, status)`: Calls `/api/lead/.../override` to manually update a lead's status.
    *   **Data Flow**: Polls Backend APIs (interval 10s) -> Updates Local State (`let leads = []`) -> Renders UI.

## 3. Backend Analysis
The backend is structured around `main.py` acting as the controller, with specialized service classes.

### Modules
1.  **`main.py` (Controller)**
    *   **Role**: Entry point, Route definitions, HTTP Request handling.
    *   **Key Functions**:
        *   `process_intake()`: Handles POST `/intake`. Orchestrates the entire flow: validates input -> calls `scorer` -> saves to `db` -> calls `notifier` & `router` -> returns JSON.
        *   `get_leads()`: Returns list of all leads as JSON.
        *   `dashboard()` / `client_form()`: Serves HTML templates.

2.  **`intake_scorer.py` (Service: AI)**
    *   **Role**: Interacts with Google Gemini API to grade cases.
    *   **Key Functions**:
        *   `score_lead(lead_data)`: Sends a prompt to Gemini; parses the JSON response into a Pydantic model (`IntakeScoringResult`).
        *   `_get_heuristic_score(data)`: Fallback logic (keyword search) if AI fails.

3.  **`lawyer_notifier.py` (Service: Notifications)**
    *   **Role**: Alerts firm staff.
    *   **Key Functions**:
        *   `notify_lawyer(lead_data)`: Decides channel based on score (Score >= 8 -> SMS; Score >= 5 -> Email).
        *   `send_sms()` / `send_email()`: Wrappers for Twilio and SMTP.

4.  **`action_router.py` (Service: Client Comm)**
    *   **Role**: Communicates back to the client.
    *   **Key Functions**:
        *   `route_action(lead)`: Sends automated messages to the client based on the AI's `recommended_action` (e.g., sends Calendly link if "AUTO_BOOK").

5.  **`database.py` (Data Access)**
    *   **Role**: ORM Layer.
    *   **Key Functions**:
        *   `insert_lead(data)`: Saves a new lead.
        *   `get_dashboard_stats()`: Aggregates metrics (conversion rate, avg score).

## 4. API Contract

| Method | Endpoint | Description | Request Body | Response |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/` | Serves Dashboard HTML | N/A | HTML |
| `GET` | `/apply` | Serves Intake Form HTML | N/A | HTML |
| `GET` | `/api/stats` | Dashboard metrics | N/A | JSON: `{ total_leads, avg_score... }` |
| `GET` | `/api/leads` | List of all leads | N/A | JSON: `[ { id, client_name, ai_score... } ]` |
| `POST` | `/intake` | Submit new case | JSON: `{ name, description, injuries... }` | JSON: `{ status: "success", action: "..." }` |
| `POST` | `/api/lead/<id>/override` | Manual status update | JSON: `{ status: "approved" }` | JSON: `{ status: "success" }` |

## 5. Data Models
### Database (SQLAlchemy - `database.py`)
*   **Model**: `Lead`
    *   **Fields**:
        *   `id` (Integer, PK)
        *   `client_name`, `client_phone`, `client_email` (Contact info)
        *   `incident_description`, `location`, `injuries`, `insurance` (Case specs)
        *   `ai_score` (Int), `ai_tier` (String), `ai_summary` (Text), `red_flags` (JSON Text)
        *   `recommended_action`, `action_taken` (Workflow status)
    *   **Concept**: Represents a single intake submission and its lifecycle state.

### AI Exchange (Pydantic - `intake_scorer.py`)
*   **Model**: `IntakeScoringResult`
    *   **Structure**: Nested objects for `liability`, `damages`, `statute_of_limitations` (each with score/reasoning).
    *   **Purpose**: Validates the structured output from the GenAI model.

## 6. Workflow Traces
### Workflow: New Client Intake Submission
1.  **Actor**: User (Client) on `form.html`
    *   **Action**: Fills multi-step form and clicks "Submit".
    *   **Data**: JSON payload (Personal + Incident + Damage specs).
2.  **Layer**: API (`main.py` -> `process_intake`)
    *   **Action**: Receives POST request. Validates payload existence.
3.  **Layer**: Backend Service (`intake_scorer.py`)
    *   **Action**: Constructs prompt -> Calls Google Gemini API -> Returns structured `IntakeScoringResult`.
4.  **Layer**: Database (`database.py`)
    *   **Action**: Saves raw client data + AI analysis results to `leads` table. Returns new `lead_id`.
5.  **Layer**: Backend Service (`lawyer_notifier.py`)
    *   **Action**: Checks score. If High (8+), sends SMS to Lawyer. If Medium (5+), sends Email.
6.  **Layer**: Backend Service (`action_router.py`)
    *   **Action**: Checks `recommended_action`.
        *   If `AUTO_BOOK`: Sends SMS/Email to **Client** with Calendly link.
        *   If `SOFT_REJECT`: Sends polite rejection email.
7.  **Outcome**: Client sees success message on UI; Lawyer receives alert; Database is updated.

## 7. Auth & Security
*   **Authentication**: None observed for the Dashboard. It is exposed at `/`.
    *   *Security Concern*: No login protection for sensitive client data.
*   **API Security**: No token/session checks on API endpoints.
*   **Secrets**: Managed via `.env` (API keys, Twilio creds), which is good practice.
*   **Input Validation**: Basic existence checks in `main.py`. AI Prompt injection is a potential risk (`process_intake` passes raw user input to LLM).

## 8. State Management
*   **Frontend**:
    *   **Local**: `dashboard.html` uses a global variable `let leads = []` to store the fetched list for client-side filtering/rendering.
    *   **Form**: `form.html` manages visibility state via CSS classes (`.active`) on DOM elements; data is gathered from the DOM at submission time.
*   **Backend**: Stateless HTTP. State is persisted in SQLite (`legal_intake.db`).

## 9. Third-Party Integrations
1.  **Google Gemini API**:
    *   **Purpose**: Core intelligence engine for scoring and summarizing legal cases.
    *   **Location**: `intake_scorer.py`.
2.  **Twilio**:
    *   **Purpose**: Sending SMS notifications to lawyers and clients.
    *   **Location**: `lawyer_notifier.py`, `action_router.py`.
3.  **Gmail SMTP**:
    *   **Purpose**: Sending email notifications.
    *   **Location**: `lawyer_notifier.py`, `action_router.py`.

## 10. Architecture Summary
The system follows a **Monolithic Service-Oriented** style within a Flask app.
*   **Presentation Layer**: Flask Templates (`.html` files) serving the UI.
*   **Controller Layer**: `main.py` routing requests to services.
*   **Service Layer**: Distinct Python classes (`IntakeScorer`, `LawyerNotifier`, `ActionRouter`) encapsulating business logic.
*   **Data Layer**: SQLAlchemy managing SQLite connections.

**Data Flow**:
User Input -> Controller -> AI Service -> Database -> Notification Services -> Client/Lawyer.

## 11. Glossary
*   **Lead**: A potential client submission.
*   **Intake**: The process of collecting case details.
*   **AI Score**: A 0-10 aggregate rating of case viability.
*   **Tier**: Classification of a lead (e.g., "BOOK NOW", "REJECT").
*   **Pillar**: A specific legal criterion graded by AI (Liability, Damages, Statute of Limitations).
*   **Red Flags**: Critical issues identified by AI (e.g., "Already represented", "At fault").
*   **Action Router**: System component responsible for automated client outreach.
