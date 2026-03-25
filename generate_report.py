from fpdf import FPDF
import datetime

class PDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 15)
        self.cell(0, 10, 'LEGAL_INTAKE2: Comprehensive Project Analysis', border=False, ln=True, align='C')
        self.set_font('helvetica', 'I', 10)
        self.cell(0, 10, f'Generated on: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}', border=False, ln=True, align='C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('helvetica', 'B', 12)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 10, title, ln=True, fill=True)
        self.ln(4)

    def chapter_body(self, body):
        self.set_font('helvetica', '', 11)
        self.multi_cell(0, 8, body)
        self.ln()

pdf = PDF()
pdf.add_page()

# Section 1: Executive Summary
pdf.chapter_title("1. Executive Technical Summary")
summary = (
    "LEGAL_INTAKE2 is a Full-Stack AI Lead Triage & Automation System specifically architected "
    "for Personal Injury law firms. The primary goal is to eliminate manual intake friction by "
    "using GenAI to grade, prioritize, and route high-value legal claims in real-time. "
    "The system is a production-ready blueprint for modern legal tech automation."
)
pdf.chapter_body(summary)

# Section 2: Architecture & Tech Stack
pdf.chapter_title("2. Architecture & Core Tech Stack")
tech_stack = (
    "- Backend: Python (Flask) utilizing a Service-Oriented Architecture (SOA) via the Service Layer Pattern.\n"
    "- Database: SQLAlchemy ORM with SQLite for persistent, ACID-compliant lead lifecycle tracking.\n"
    "- Intelligence: Deep integration with Google Gemini API (via 'google-genai' SDK), featuring automated model failover across 'flash-1.5', 'flash-8b', and 'pro' models.\n"
    "- Communications: Integrated Twilio (SMS) and Gmail SMTP (Email) for automated lawyer alerts and client auto-responses.\n"
    "- Frontend: Highly responsive Vanilla JS/CSS dashboard with real-time polling (10s intervals) to track high-priority intake events."
)
pdf.chapter_body(tech_stack)

# Section 3: AI Scoring Engine (The Pillars)
pdf.chapter_title("3. AI Scoring Engine (The Three Pillars)")
scoring = (
    "The core value proposition of LEGAL_INTAKE2 is its ability to 'read' legal claims like a human specialist. "
    "It evaluates every intake against three critical legal criteria:\n\n"
    "- Liability (Fault): AI determines the likelihood of a successful negligence claim (0-10).\n"
    "- Damages (Severity): AI analyzes injuries (fractures, surgeries, etc.) and medical treatment to estimate case value (0-10).\n"
    "- SOL (Statute of Limitations): AI checks the incident date against legal deadlines (0-10).\n\n"
    "The system produces a Triage Result (e.g., 'BOOK NOW', 'REJECT') and an actionable recommendation ('AUTO_BOOK', 'SOFT_REJECT')."
)
pdf.chapter_body(scoring)

pdf.add_page()

# Section 4: Automated Workflow Traces
pdf.chapter_title("4. End-to-End Workflow Traces")
workflow = (
    "High-Value Lead Workflow (The 'Golden Path'):\n"
    "1. Client Submission: A user submits a catastrophic injury case via the public intake form.\n"
    "2. Analysis: The Flask backend triggers the Gemini-powered IntakeScorer.\n"
    "3. Decision: Scorer returns a high score (8+) and 'AUTO_BOOK' recommendation.\n"
    "4. Lawyer Alert: LawyerNotifier immediately triggers a Twilio SMS alert to the firm's lead attorney.\n"
    "5. Client Booking: ActionRouter sends an immediate SMS/Email to the client with a Calendly booking link.\n"
    "6. Management: The lead appears on the Dashboard for immediate review and manual follow-up.\n\n"
    "Low-Value Lead Workflow (The 'Auto-Filter'):\n"
    "1. Client Submission: A user submits a case with poor liability (e.g., they were at fault).\n"
    "2. Rejection: AI identifies the weakness and returns 'SOFT_REJECT'.\n"
    "3. Communication: ActionRouter automatically sends a professional rejection email, protecting the firm's time while providing a courteous decline."
)
pdf.chapter_body(workflow)

# Section 5: API & Data Integrity
pdf.chapter_title("5. API Contract & Data Model")
api_data = (
    "The system exposes a clean RESTful API for lead management:\n"
    "- POST /intake: Main entry point for client data; triggers AI and automation pipelines.\n"
    "- GET /api/leads: Returns sorted JSON objects of all current and archived leads.\n"
    "- GET /api/stats: Provides aggregated KPI metrics (Conversion rate, Average quality score).\n"
    "- POST /api/lead/<id>/override: Allows lawyers to manually change intake statuses from the dashboard."
)
pdf.chapter_body(api_data)

# Section 6: Security & State Management
pdf.chapter_title("6. Security & State Management")
security = (
    "- Secrets Management: All sensitive credentials (API Keys, Twilio Tokens) are decoupled from the codebase via .env files.\n"
    "- Fail-Safe Mechanism: A custom heuristic scoring engine ('_get_heuristic_score') is provided as a fallback in case of AI service outages, ensuring the firm never loses a lead.\n"
    "- State Persistence: Full lifecycle tracking from 'pending' to 'notified' to 'actioned' is maintained in the SQLite database."
)
pdf.chapter_body(security)

# Section 7: Glossary
pdf.chapter_title("7. Project Glossary")
glossary = (
    "- Lead: A potential client submission.\n"
    "- Intake Scorer: The AI-powered engine for case triage.\n"
    "- Action Router: The system that manages client outreach (Calendly links, Rejection emails).\n"
    "- Lawyer Notifier: The internal alerting system for the legal team.\n"
    "- Pillar: One of the three legal grading criteria (Liability, Damages, SOL)."
)
pdf.chapter_body(glossary)

pdf.output("/home/philipslinux/LEGAL_INTAKE2/LEGAL_INTAKE2_Report.pdf")
print("PDF Report generated successfully.")
