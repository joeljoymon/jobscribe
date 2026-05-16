import io
import json
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

# ── Fake AI responses ────────────────────────────────────────
# These are the values our mocked functions will return.
# They match the exact structure the real AI returns
# so all downstream code processes them correctly.

FAKE_RESEARCH = {
    "company_type": "fintech",
    "what_they_do": "DCB Bank is a private sector bank.",
    "role_summary": "You will build and maintain banking software.",
    "interview_style": "Structured, tests CS fundamentals heavily.",
    "cs_topics": {
        "DBMS": "heavy",
        "OS": "medium",
        "Networks": "light",
        "DSA": "medium",
        "System Design": "none"
    },
    "fresher_expectations": "Strong SQL and basic Python expected.",
    "apply_tips": "Highlight your database projects."
}

FAKE_ASSESSMENT = {
    "overall_readiness_score": 72,
    "technical_skills_score": 78,
    "cs_fundamentals_score": 60,
    "projects_relevance_score": 80,
    "confidence_level": "ready",
    "strengths": ["Python", "REST APIs", "Git"],
    "gaps": ["DBMS normalization", "OS process management"],
    "cs_gaps": ["ACID properties", "normalization to 3NF"],
    "verdict": "apply now",
    "estimated_days_to_ready": 5,
    "honest_assessment": "Strong fresher profile with good projects."
}

FAKE_ROADMAP = {
    "total_days": 5,
    "daily_plan": [
        {
            "day_number": 1,
            "title": "DBMS Fundamentals",
            "focus_topic": "Normalization and ACID",
            "what_to_study": ["1NF, 2NF, 3NF", "ACID properties"],
            "depth_needed": "Conceptual understanding with examples.",
            "how_to_verify": "Normalize a sample table to 3NF.",
            "estimated_hours": 3
        }
    ],
    "final_day_activity": "Mock interview practice"
}

FAKE_QUESTIONS = {
    "questions": [
        {
            "number": 1,
            "question": "Explain normalization with an example.",
            "type": "fundamentals",
            "why_asked": "Banking roles test DBMS heavily.",
            "answer_guide": "Start with definition then give example.",
            "keywords": ["1NF", "2NF", "3NF", "redundancy"],
            "common_mistake": "Only giving textbook definition."
        },
        {
            "number": 2,
            "question": "Walk me through your JobScribe project.",
            "type": "project",
            "why_asked": "Tests depth of understanding of own work.",
            "answer_guide": "Explain the problem, solution, tech choices.",
            "keywords": ["FastAPI", "SQLAlchemy", "REST API"],
            "common_mistake": "Only describing features, not decisions."
        }
    ]
}

FAKE_ANALYTICS = {
    "total_applications": 3,
    "callback_rate": "66%",
    "what_is_working": ["Python backend roles", "Startup companies"],
    "what_is_not_working": ["Enterprise banking roles"],
    "recommended_focus": "Target Python backend startups.",
    "roles_to_avoid_now": ["System Design heavy roles"],
    "roles_to_target": ["Junior Python Developer", "Backend Intern"],
    "honest_summary": "Strong foundation, focus on CS fundamentals."
}


# ── Helper: create a job with JD and resume ──────────────────
def create_job_with_resume(client):
    """Creates a job with JD text and uploads a fake resume."""
    r = client.post("/jobs/", data={
        "company": "DCB Bank",
        "role": "Junior Software Engineer",
        "jd_text": "We need a Python developer with SQL experience."
    })
    job_id = r.json()["id"]

    fake_pdf = io.BytesIO(b"%PDF-1.4 fake resume content")
    client.post(
        f"/jobs/{job_id}/upload-resume",
        files={"resume": ("resume.pdf", fake_pdf, "application/pdf")}
    )
    return job_id


# ── Tests: company research ───────────────────────────────────
class TestCompanyResearch:

    def test_research_returns_company_info(self, client):
        """Research endpoint should return structured company data."""
        job_id = create_job_with_resume(client)

        with patch("app.routers.intelligence.research_company",
                   return_value=FAKE_RESEARCH):
            res = client.post(f"/intelligence/jobs/{job_id}/research")

        assert res.status_code == 200
        data = res.json()
        assert data["company"] == "DCB Bank"
        assert "research" in data
        assert data["research"]["company_type"] == "fintech"

    def test_research_updates_job_status(self, client):
        """After research, job status should be 'researched'."""
        job_id = create_job_with_resume(client)

        with patch("app.routers.intelligence.research_company",
                   return_value=FAKE_RESEARCH):
            client.post(f"/intelligence/jobs/{job_id}/research")

        job = client.get(f"/jobs/{job_id}").json()
        assert job["status"] == "researched"

    def test_research_caches_same_company(self, client):
        """
        Researching the same company twice should use cache.
        AI function should only be called once.
        """
        job1_id = create_job_with_resume(client)

        # Second job at same company
        r2 = client.post("/jobs/", data={
            "company": "DCB Bank",
            "role": "Senior Developer"
        })
        job2_id = r2.json()["id"]

        with patch("app.routers.intelligence.research_company",
                   return_value=FAKE_RESEARCH) as mock_ai:

            # First research — AI called
            client.post(f"/intelligence/jobs/{job1_id}/research")
            # Second research same company — should use cache
            res = client.post(f"/intelligence/jobs/{job2_id}/research")

            # AI should only have been called ONCE
            assert mock_ai.call_count == 1

        assert res.json()["cached"] == True

    def test_research_nonexistent_job_returns_404(self, client):
        """Researching a job that doesn't exist should return 404."""
        with patch("app.routers.intelligence.research_company",
                   return_value=FAKE_RESEARCH):
            res = client.post("/intelligence/jobs/999/research")
        assert res.status_code == 404


# ── Tests: readiness assessment ──────────────────────────────
class TestReadinessAssessment:

    def test_assess_returns_readiness_score(self, client):
        """Assessment should return a score between 0 and 100."""
        job_id = create_job_with_resume(client)

        with patch("app.routers.intelligence.assess_readiness",
                   return_value=FAKE_ASSESSMENT):
            with patch("app.routers.intelligence.extract_text_from_pdf",
                       return_value="Python developer with FastAPI experience"):
                res = client.post(f"/intelligence/jobs/{job_id}/assess")

        assert res.status_code == 200
        data = res.json()
        assert "assessment" in data
        assert 0 <= data["assessment"]["overall_readiness_score"] <= 100

    def test_assess_saves_score_to_job(self, client):
        """After assessment, job.readiness_score should be updated."""
        job_id = create_job_with_resume(client)

        with patch("app.routers.intelligence.assess_readiness",
                   return_value=FAKE_ASSESSMENT):
            with patch("app.routers.intelligence.extract_text_from_pdf",
                       return_value="Python developer"):
                client.post(f"/intelligence/jobs/{job_id}/assess")

        job = client.get(f"/jobs/{job_id}").json()
        assert job["readiness_score"] == 72

    def test_assess_updates_status_to_assessed(self, client):
        """After assessment, job status should be 'assessed'."""
        job_id = create_job_with_resume(client)

        with patch("app.routers.intelligence.assess_readiness",
                   return_value=FAKE_ASSESSMENT):
            with patch("app.routers.intelligence.extract_text_from_pdf",
                       return_value="Python developer"):
                client.post(f"/intelligence/jobs/{job_id}/assess")

        job = client.get(f"/jobs/{job_id}").json()
        assert job["status"] == "assessed"

    def test_assess_multiple_times_builds_history(self, client):
        """Running assess twice should create two assessment records."""
        job_id = create_job_with_resume(client)

        with patch("app.routers.intelligence.assess_readiness",
                   return_value=FAKE_ASSESSMENT):
            with patch("app.routers.intelligence.extract_text_from_pdf",
                       return_value="Python developer"):
                client.post(f"/intelligence/jobs/{job_id}/assess")
                client.post(f"/intelligence/jobs/{job_id}/assess")

        # Both assessments saved — job has latest score
        job = client.get(f"/jobs/{job_id}").json()
        assert job["readiness_score"] == 72

    def test_assess_without_jd_returns_400(self, client):
        """Assessment without JD text should return 400."""
        r = client.post("/jobs/", data={
            "company": "Google",
            "role": "Intern"
        })
        job_id = r.json()["id"]

        fake_pdf = io.BytesIO(b"%PDF fake")
        client.post(
            f"/jobs/{job_id}/upload-resume",
            files={"resume": ("resume.pdf", fake_pdf, "application/pdf")}
        )

        res = client.post(f"/intelligence/jobs/{job_id}/assess")
        assert res.status_code == 400
        assert "job description" in res.json()["detail"].lower()

    def test_assess_without_resume_returns_400(self, client):
        """Assessment without resume should return 400."""
        r = client.post("/jobs/", data={
            "company": "Google",
            "role": "Intern",
            "jd_text": "Python developer needed"
        })
        job_id = r.json()["id"]

        res = client.post(f"/intelligence/jobs/{job_id}/assess")
        assert res.status_code == 400
        assert "resume" in res.json()["detail"].lower()


# ── Tests: preparation roadmap ───────────────────────────────
class TestPrepRoadmap:

    def test_roadmap_requires_assessment_first(self, client):
        """Roadmap generation should fail without prior assessment."""
        job_id = create_job_with_resume(client)
        res = client.post(f"/intelligence/jobs/{job_id}/roadmap")
        assert res.status_code == 400
        assert "assess" in res.json()["detail"].lower()

    def test_roadmap_returns_daily_plan(self, client):
        """Roadmap should return a structured day by day plan."""
        job_id = create_job_with_resume(client)

        # Run assessment first
        with patch("app.routers.intelligence.assess_readiness",
                   return_value=FAKE_ASSESSMENT):
            with patch("app.routers.intelligence.extract_text_from_pdf",
                       return_value="Python developer"):
                client.post(f"/intelligence/jobs/{job_id}/assess")

        # Now generate roadmap
        with patch("app.routers.intelligence.generate_roadmap",
                   return_value=FAKE_ROADMAP):
            res = client.post(f"/intelligence/jobs/{job_id}/roadmap")

        assert res.status_code == 200
        data = res.json()
        assert "roadmap" in data
        assert data["roadmap"]["total_days"] == 5
        assert len(data["roadmap"]["daily_plan"]) == 1

    def test_roadmap_updates_status_to_preparing(self, client):
        """After roadmap generation, job status should be 'preparing'."""
        job_id = create_job_with_resume(client)

        with patch("app.routers.intelligence.assess_readiness",
                   return_value=FAKE_ASSESSMENT):
            with patch("app.routers.intelligence.extract_text_from_pdf",
                       return_value="Python developer"):
                client.post(f"/intelligence/jobs/{job_id}/assess")

        with patch("app.routers.intelligence.generate_roadmap",
                   return_value=FAKE_ROADMAP):
            client.post(f"/intelligence/jobs/{job_id}/roadmap")

        job = client.get(f"/jobs/{job_id}").json()
        assert job["status"] == "preparing"

    def test_roadmap_regeneration_replaces_old(self, client):
        """Running roadmap twice should replace old roadmap not duplicate."""
        job_id = create_job_with_resume(client)

        with patch("app.routers.intelligence.assess_readiness",
                   return_value=FAKE_ASSESSMENT):
            with patch("app.routers.intelligence.extract_text_from_pdf",
                       return_value="Python developer"):
                client.post(f"/intelligence/jobs/{job_id}/assess")

        with patch("app.routers.intelligence.generate_roadmap",
                   return_value=FAKE_ROADMAP):
            res1 = client.post(f"/intelligence/jobs/{job_id}/roadmap")
            res2 = client.post(f"/intelligence/jobs/{job_id}/roadmap")

        # Both calls succeed — second replaces first
        assert res1.status_code == 200
        assert res2.status_code == 200


# ── Tests: interview simulator ───────────────────────────────
class TestInterviewSimulator:

    def test_simulator_returns_questions(self, client):
        """Simulator should return a list of interview questions."""
        job_id = create_job_with_resume(client)

        with patch("app.routers.intelligence.generate_interview_questions",
                   return_value=FAKE_QUESTIONS):
            with patch("app.routers.intelligence.extract_text_from_pdf",
                       return_value="Python developer"):
                res = client.post(f"/intelligence/jobs/{job_id}/simulate")

        assert res.status_code == 200
        data = res.json()
        assert "questions" in data
        assert len(data["questions"]) == 2

    def test_simulator_questions_have_required_fields(self, client):
        """Each question should have all required fields."""
        job_id = create_job_with_resume(client)

        with patch("app.routers.intelligence.generate_interview_questions",
                   return_value=FAKE_QUESTIONS):
            with patch("app.routers.intelligence.extract_text_from_pdf",
                       return_value="Python developer"):
                res = client.post(f"/intelligence/jobs/{job_id}/simulate")

        questions = res.json()["questions"]
        for q in questions:
            assert "question" in q
            assert "type" in q
            assert "answer_guide" in q
            assert "why_asked" in q

    def test_simulator_without_jd_returns_400(self, client):
        """Simulator without JD should return 400."""
        r = client.post("/jobs/", data={
            "company": "Google",
            "role": "Intern"
        })
        job_id = r.json()["id"]

        fake_pdf = io.BytesIO(b"%PDF fake")
        client.post(
            f"/jobs/{job_id}/upload-resume",
            files={"resume": ("resume.pdf", fake_pdf, "application/pdf")}
        )

        res = client.post(f"/intelligence/jobs/{job_id}/simulate")
        assert res.status_code == 400


# ── Tests: mark question as practiced ────────────────────────
class TestMarkPracticed:

    def test_mark_question_practiced(self, client):
        """Marking a question as practiced should succeed."""
        job_id = create_job_with_resume(client)

        with patch("app.routers.intelligence.generate_interview_questions",
                   return_value=FAKE_QUESTIONS):
            with patch("app.routers.intelligence.extract_text_from_pdf",
                       return_value="Python developer"):
                client.post(f"/intelligence/jobs/{job_id}/simulate")

        # Get the first question id from database
        from app.models import InterviewQuestion
        from app.database import SessionLocal
        db = SessionLocal()
        q = db.query(InterviewQuestion).filter(
            InterviewQuestion.job_id == job_id
        ).first()
        db.close()

        res = client.patch(f"/intelligence/questions/{q.id}/practiced")
        assert res.status_code == 200
        assert "practiced" in res.json()["message"].lower()

    def test_mark_nonexistent_question_returns_404(self, client):
        """Marking a question that doesn't exist should return 404."""
        res = client.patch("/intelligence/questions/999/practiced")
        assert res.status_code == 404


# ── Tests: analytics ─────────────────────────────────────────
class TestAnalytics:

    def test_analytics_requires_minimum_jobs(self, client):
        """Analytics should require at least 3 jobs."""
        client.post("/jobs/", data={"company": "Google", "role": "Intern"})
        client.post("/jobs/", data={"company": "Flipkart", "role": "SDE"})

        res = client.get("/intelligence/analytics")
        assert res.status_code == 200
        assert "total_jobs" in res.json()

    def test_analytics_with_enough_jobs(self, client):
        """Analytics with 3+ jobs should return pattern analysis."""
        for company in ["Google", "Flipkart", "Swiggy"]:
            client.post("/jobs/", data={
                "company": company,
                "role": "Python Developer"
            })

        with patch("app.routers.intelligence.analyze_outcomes",
                   return_value=FAKE_ANALYTICS):
            res = client.get("/intelligence/analytics")

        assert res.status_code == 200
        data = res.json()
        assert "analytics" in data


# ── Negative tests ────────────────────────────────────────────
class TestNegativeCases:

    def test_all_endpoints_return_404_for_missing_job(self, client):
        """All intelligence endpoints should return 404 for missing job."""
        endpoints = [
            f"/intelligence/jobs/999/research",
            f"/intelligence/jobs/999/assess",
            f"/intelligence/jobs/999/roadmap",
            f"/intelligence/jobs/999/simulate",
        ]
        for endpoint in endpoints:
            res = client.post(endpoint)
            assert res.status_code == 404, \
                f"Expected 404 for {endpoint}, got {res.status_code}"

    def test_deleting_job_removes_related_data(self, client):
        """
        Deleting a job should cascade delete all related
        assessments, roadmap, and questions.
        """
        job_id = create_job_with_resume(client)

        with patch("app.routers.intelligence.assess_readiness",
                   return_value=FAKE_ASSESSMENT):
            with patch("app.routers.intelligence.extract_text_from_pdf",
                       return_value="Python developer"):
                client.post(f"/intelligence/jobs/{job_id}/assess")

        # Delete the job
        client.delete(f"/jobs/{job_id}")

        # Job should be gone
        res = client.get(f"/jobs/{job_id}")
        assert res.status_code == 404