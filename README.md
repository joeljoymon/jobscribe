# JobScribe V2

> End-to-end career intelligence platform for freshers — from deciding whether to apply, to walking into the interview confident.


[![Run Tests](https://github.com/joeljoymon/jobscribe/actions/workflows/tests.yml/badge.svg)](https://github.com/joeljoymon/jobscribe/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/python-3.10-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136-green)
![License](https://img.shields.io/github/license/joeljoymon/jobscribe)

**Live Demo:** https://jobscribe-joel.onrender.com

---

## The Problem

Freshers apply to 20-30 companies blindly — same resume everywhere,
no idea why they don't hear back, no idea if they're even ready for
the role they're applying to.

JobScribe V2 answers three questions before you apply:
1. Am I ready for this role right now?
2. If not, how long will it take and what exactly do I study?
3. What will they ask me in the interview?
---

## What's New in V2

V1 was a job tracker with AI skill gap analysis.

V2 is a full career intelligence platform:

| Feature | V1 | V2 |
|---|---|---|
| Track applications | ✔ | ✔ |
| Resume vs JD analysis | ✔ | ✔ |
| Company research | ✗ | ✔ |
| Readiness assessment | ✗ | ✔ |
| Preparation roadmap | ✗ | ✔ |
| Interview simulator | ✗ | ✔ |
| Outcome analytics | ✗ | ✔ |
| Assessment history | ✗ | ✔ |
| Company research cache | ✗ | ✔ |

---

## The Full User Journey

| Step | Action | What You Get |
|---|---|---|
| 1 | **Add a job** you're interested in | Job saved with status `interested` |
| 2 | **Research the company** | What they do, interview style, which CS topics they test and at what depth |
| 3 | **Check your readiness** | Overall score (0-100%), breakdown by category, specific gaps, honest verdict: `apply now` / `prepare first` |
| 4 | **Follow the preparation roadmap** | Day by day study plan calibrated to your gaps and the right depth for this specific role |
| 5 | **Run the interview simulator** | 10 questions tailored to YOUR resume and THIS JD — technical, CS fundamentals, project-specific, situation questions with answer guides |
| 6 | **Apply with confidence** | Update status as things progress: `applied` → `interview` → `offer` |
| 7 | **Analytics learns your patterns** | Which roles get callbacks, which don't — what to focus on next |

## Screenshots

![Dashboard](screenshots/dashboard.png)

![Analysis Report](screenshots/analysis.png)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI |
| Database | SQLite via SQLAlchemy ORM |
| AI | Llama 3.3 70B via Groq API |
| PDF parsing | pypdf |
| Frontend | Jinja2 templates, HTML/CSS |
| Testing | pytest - 48 tests with mocking |
| CI/CD | GitHub Actions |
| Deployment | Render |

---

## Running Locally

```bash
# Clone the repo
git clone https://github.com/joeljoymon/jobscribe.git
cd jobscribe

# Create virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Add environment variables
# Create a .env file with:
# GROQ_API_KEY=your_key_here
# Get a free key at https://console.groq.com/keys

# Run the server
uvicorn app.main:app --reload

# Open in browser
# http://127.0.0.1:8000
```

---

## API Endpoints

### V1 — Job Tracker

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Dashboard |
| POST | `/jobs/` | Add a job application |
| GET | `/jobs/` | List all applications |
| GET | `/jobs/{id}` | Get one application |
| PATCH | `/jobs/{id}` | Update status or notes |
| DELETE | `/jobs/{id}` | Remove application |
| POST | `/jobs/{id}/upload-resume` | Upload resume PDF |
| POST | `/jobs/{id}/analyze` | Run V1 skill gap analysis |

### V2 — Intelligence Layer

| Method | Endpoint | Description |
|---|---|---|
| POST | `/intelligence/jobs/{id}/research` | Research company and role |
| POST | `/intelligence/jobs/{id}/assess` | Run readiness assessment |
| POST | `/intelligence/jobs/{id}/roadmap` | Generate prep roadmap |
| POST | `/intelligence/jobs/{id}/simulate` | Generate interview questions |
| PATCH | `/intelligence/questions/{id}/practiced` | Mark question practiced |
| GET | `/intelligence/analytics` | Outcome pattern analysis |

Full interactive docs at `/docs`.

---

## Project Structure

```
jobscribe/
├── app/
│   ├── main.py              ← FastAPI app, HTML routes, auto-migration
│   ├── models.py            ← 5 SQLAlchemy database tables
│   ├── schemas.py           ← Pydantic request/response shapes
│   ├── database.py          ← connection, session, migration
│   ├── analyzer.py          ← all Groq AI functions
│   └── routers/
│       ├── jobs.py          ← V1 CRUD endpoints
│       └── intelligence.py  ← V2 intelligence endpoints
├── templates/
│   ├── base.html            ← shared layout and styles
│   ├── dashboard.html       ← applications list with summary cards
│   ├── job_detail.html      ← job hub with V2 workflow buttons
│   ├── add_job.html         ← add new application form
│   ├── research.html        ← company research results
│   ├── assessment.html      ← readiness score breakdown
│   ├── roadmap.html         ← day by day preparation plan
│   ├── simulator.html       ← interview questions with answer guides
│   └── analytics.html       ← outcome pattern analysis
├── tests/
│   ├── conftest.py          ← test database setup and fixtures
│   ├── test_jobs.py         ← 25 V1 tests
│   └── test_intelligence.py ← 23 V2 tests with mocking
├── .github/
│   └── workflows/
│       └── tests.yml        ← CI runs 48 tests on every push
├── requirements.txt
└── README.md
```

---

## Database Design

```
jobs (core table)
│
├──→ readiness_assessments (many)
│     Multiple assessments per job — tracks score history
│
├──→ prep_roadmaps (one per job)
│     Day by day plan based on latest assessment gaps
│
├──→ interview_questions (many per job)
│     Each question stored separately — user marks practiced
│
└──→ company_research (one per company name)

Cached — same company researched twice uses cache
Saves API quota, instant response on repeat lookup
```

---

## What I Learned Building This

**V1**
- REST API design with FastAPI from scratch
- Database modeling with SQLAlchemy ORM
- Dependency injection pattern
- PDF text extraction with pypdf
- Pydantic validation and schema separation
- Writing tests with pytest and dependency overrides
- CI/CD with GitHub Actions
- Deploying Python web apps to Render

**V2**
- Multi-table database relationships and foreign keys
- Database caching pattern (company research)
- Auto-migration on startup for production databases
- Multi-step AI prompt chaining
- Mocking external dependencies in tests
- Feature branch Git workflow
- Product thinking — V1 to V2 evolution

---

## Application Status Pipeline

```
interested  → added the job, exploring
researched  → ran company research
assessed    → ran readiness check
preparing   → following the roadmap
ready       → readiness score above 70%
applied     → submitted the application
interview   → got a call
offer       → received an offer
rejected    → did not get through
ghosted     → no response after weeks
withdrawn   → decided not to pursue
```

---

## How to Use JobScribe

JobScribe uses browser session identity — no login or account creation
required. Your data is tied to your browser session automatically.

### Getting Started

Open the live URL in your browser and start adding jobs immediately.
Your session is created automatically on your first visit and persists
for one year.

```
First visit → session created automatically
Add jobs    → data saved to your session
Return tomorrow, next week, next month → same data waiting for you
```

### Important: Protecting Your Data

Since JobScribe uses browser cookies instead of a login system,
there are a few things to keep in mind:

| Action | What Happens | What to Do Instead |
|---|---|---|
| Clear browser cookies/cache | ⚠️ Session lost — your jobs are no longer accessible | Only clear cookies for specific sites, not all |
| Open in Incognito/Private mode | ⚠️ New empty session — your data is not visible | Use your regular browser window |
| Switch to a different browser | ⚠️ Different session — your data is not visible | Stick to one browser (Chrome, Brave, or Firefox) |
| Clear site data for JobScribe | ⚠️ Session lost — your jobs are no longer accessible | Avoid clearing site data for this URL |
| Open on a different device | ⚠️ Different session — your data is not visible | Use the same browser on the same device |

### What Works Perfectly

```
✔ Close the browser tab and reopen        → same data
✔ Restart your computer and reopen        → same data
✔ Open multiple tabs in the same browser  → same data
✔ Leave it for days or weeks and return   → same data
```

### If You Lose Your Session

If you accidentally clear your cookies your jobs are no longer
accessible from that browser. The data still exists in the database
but is linked to your old session ID which is now gone from your
browser.

To avoid this:

- When clearing browser data, choose **"Cookies from specific sites"**
  and exclude `jobscribe-joel.onrender.com`
- In Chrome: Settings → Privacy → Clear browsing data →
  click "See all site data" → delete only what you need
- Do not use "Clear all cookies" — use site-specific deletion instead

### Why No Login?

JobScribe intentionally skips login to remove friction. You don't
need to remember a password or verify an email — just open the URL
and your data is there. The trade-off is that your session is tied
to one browser on one device. For a personal job tracking tool used
on your main browser, this works perfectly.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.


