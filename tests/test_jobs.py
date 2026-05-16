import io
import json
import pytest
from fastapi.testclient import TestClient


# ── Tests for: create job ────────────────────────────────────
class TestCreateJob:

    def test_create_job_successfully(self, client):
        """Creating a job with valid data should return 200 and the job."""
        response = client.post("/jobs/", data={
            "company": "Google",
            "role": "Backend Intern"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["company"] == "Google"
        assert data["role"] == "Backend Intern"
        assert data["status"] == "interested"
        assert data["id"] == 1

    def test_create_job_auto_sets_applied_status(self, client):
        """Status should always default to 'applied' on creation."""
        response = client.post("/jobs/", data={
            "company": "Flipkart",
            "role": "SDE Intern"
        })
        assert response.json()["status"] == "interested"

    def test_create_job_missing_company_fails(self, client):
        """Creating a job without company should fail."""
        response = client.post("/jobs/", data={"role": "Backend Intern"})
        assert response.status_code == 422

    def test_create_job_missing_role_fails(self, client):
        """Creating a job without role should fail."""
        response = client.post("/jobs/", data={"company": "Google"})
        assert response.status_code == 422

    def test_create_job_with_jd_text(self, client):
        """JD text should be saved correctly."""
        response = client.post("/jobs/", data={
            "company": "Swiggy",
            "role": "Python Dev",
            "jd_text": "We need a Python developer with FastAPI experience"
        })
        assert response.status_code == 200
        assert "Python" in response.json()["jd_text"]


# ── Tests for: list jobs ─────────────────────────────────────
class TestListJobs:

    def test_list_empty(self, client):
        """Empty database should return empty list."""
        response = client.get("/jobs/")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_returns_all_jobs(self, client):
        """All created jobs should appear in the list."""
        client.post("/jobs/", data={"company": "Google", "role": "Intern"})
        client.post("/jobs/", data={"company": "Flipkart", "role": "SDE"})
        response = client.get("/jobs/")
        assert len(response.json()) == 2

    def test_list_ordered_newest_first(self, client):
        """Jobs should be listed newest first."""
        client.post("/jobs/", data={"company": "First", "role": "Role"})
        client.post("/jobs/", data={"company": "Second", "role": "Role"})
        jobs = client.get("/jobs/").json()
        assert jobs[0]["company"] == "Second"


# ── Tests for: get single job ────────────────────────────────
class TestGetJob:

    def test_get_existing_job(self, client):
        """Fetching a valid job ID should return that job."""
        client.post("/jobs/", data={"company": "Google", "role": "Intern"})
        response = client.get("/jobs/1")
        assert response.status_code == 200
        assert response.json()["company"] == "Google"

    def test_get_nonexistent_job_returns_404(self, client):
        """Fetching a job that doesn't exist should return 404."""
        response = client.get("/jobs/999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


# ── Tests for: update job ────────────────────────────────────
class TestUpdateJob:

    def test_update_status_to_interview(self, client):
        """Status should update correctly."""
        client.post("/jobs/", data={"company": "Google", "role": "Intern"})
        response = client.patch("/jobs/1", data={"status": "interview"})
        assert response.status_code == 200
        assert response.json()["status"] == "interview"

    def test_update_all_valid_statuses(self, client):
        """Every valid status should be accepted."""
        client.post("/jobs/", data={"company": "Google", "role": "Intern"})
        for status in ["applied", "interview", "offer", "rejected", "ghosted"]:
            response = client.patch("/jobs/1", data={"status": status})
            assert response.status_code == 200
            assert response.json()["status"] == status

    def test_update_invalid_status_rejected(self, client):
        """Invalid status values should be rejected with 400."""
        client.post("/jobs/", data={"company": "Google", "role": "Intern"})
        response = client.patch("/jobs/1", data={"status": "maybe"})
        assert response.status_code == 400

    def test_update_notes_only(self, client):
        """Updating notes should not affect other fields."""
        client.post("/jobs/", data={"company": "Google", "role": "Intern"})
        response = client.patch("/jobs/1", data={"notes": "Great company"})
        assert response.status_code == 200
        assert response.json()["notes"] == "Great company"
        assert response.json()["status"] == "interested"

    def test_update_nonexistent_job_returns_404(self, client):
        """Updating a job that doesn't exist should return 404."""
        response = client.patch("/jobs/999", data={"status": "interview"})
        assert response.status_code == 404


# ── Tests for: delete job ────────────────────────────────────
class TestDeleteJob:

    def test_delete_existing_job(self, client):
        """Deleting a valid job should succeed."""
        client.post("/jobs/", data={"company": "Google", "role": "Intern"})
        response = client.delete("/jobs/1")
        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

    def test_deleted_job_no_longer_exists(self, client):
        """After deletion, job should not be retrievable."""
        client.post("/jobs/", data={"company": "Google", "role": "Intern"})
        client.delete("/jobs/1")
        response = client.get("/jobs/1")
        assert response.status_code == 404

    def test_delete_nonexistent_job_returns_404(self, client):
        """Deleting a job that doesn't exist should return 404."""
        response = client.delete("/jobs/999")
        assert response.status_code == 404


# ── Tests for: resume upload ─────────────────────────────────
class TestResumeUpload:

    def test_upload_valid_pdf(self, client):
        """Uploading a PDF should save the resume path."""
        client.post("/jobs/", data={"company": "Google", "role": "Intern"})

        # Create a fake PDF file in memory
        fake_pdf = io.BytesIO(b"%PDF-1.4 fake pdf content")
        response = client.post(
            "/jobs/1/upload-resume",
            files={"resume": ("resume.pdf", fake_pdf, "application/pdf")}
        )
        assert response.status_code == 200
        assert response.json()["resume_path"] is not None

    def test_upload_non_pdf_rejected(self, client):
        """Non-PDF files should be rejected with 400."""
        client.post("/jobs/", data={"company": "Google", "role": "Intern"})

        fake_doc = io.BytesIO(b"fake word doc content")
        response = client.post(
            "/jobs/1/upload-resume",
            files={"resume": ("resume.docx", fake_doc, "application/octet-stream")}
        )
        assert response.status_code == 400

    def test_upload_to_nonexistent_job_returns_404(self, client):
        """Uploading to a job that doesn't exist should return 404."""
        fake_pdf = io.BytesIO(b"%PDF fake")
        response = client.post(
            "/jobs/999/upload-resume",
            files={"resume": ("resume.pdf", fake_pdf, "application/pdf")}
        )
        assert response.status_code == 404


# ── Negative tests ───────────────────────────────────────────
class TestNegativeCases:

    def test_analyze_without_jd_fails(self, client):
        """Analysis should fail with clear error if no JD exists."""
        client.post("/jobs/", data={"company": "Google", "role": "Intern"})
        response = client.post("/jobs/1/analyze")
        assert response.status_code == 400
        assert "job description" in response.json()["detail"].lower()

    def test_analyze_without_resume_fails(self, client):
        """Analysis should fail with clear error if no resume uploaded."""
        client.post("/jobs/", data={
            "company": "Google",
            "role": "Intern",
            "jd_text": "We need a Python developer"
        })
        response = client.post("/jobs/1/analyze")
        assert response.status_code == 400
        assert "resume" in response.json()["detail"].lower()

    def test_create_two_jobs_get_different_ids(self, client):
        """Each job should get a unique auto-incremented ID."""
        r1 = client.post("/jobs/", data={"company": "Google", "role": "Intern"})
        r2 = client.post("/jobs/", data={"company": "Flipkart", "role": "SDE"})
        assert r1.json()["id"] != r2.json()["id"]

    def test_delete_does_not_affect_other_jobs(self, client):
        """Deleting one job should not affect other jobs."""
        client.post("/jobs/", data={"company": "Google", "role": "Intern"})
        client.post("/jobs/", data={"company": "Flipkart", "role": "SDE"})
        client.delete("/jobs/1")
        response = client.get("/jobs/2")
        assert response.status_code == 200
        assert response.json()["company"] == "Flipkart"