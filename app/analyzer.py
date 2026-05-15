import os
import json
import pypdf
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

if not os.getenv("GROQ_API_KEY"):
    raise RuntimeError("GROQ_API_KEY not found. Check your .env file.")


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Reads a PDF file page by page and extracts all text.
    Returns a single string of the entire resume content.
    """
    text = ""
    with open(pdf_path, "rb") as file:
        reader = pypdf.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text.strip()


def analyze_resume_against_jd(resume_text: str, jd_text: str) -> dict:
    """
    Sends resume text and job description to Llama 3.3 70B via Groq.
    Returns a structured Python dictionary with the full gap analysis.

    The prompt instructs the model to return strict JSON only —
    no markdown, no extra text — so json.loads() can parse it cleanly.
    """

    prompt = f"""
You are an expert technical recruiter and career coach analyzing a fresher's resume.

Analyze the resume against the job description below.

JOB DESCRIPTION:
{jd_text}

RESUME:
{resume_text}

Return ONLY a valid JSON object with exactly this structure.
No markdown, no code blocks, no extra explanation — pure JSON only:
{{
    "match_score": <integer 0-100 representing overall fit>,
    "matched_skills": [<skills explicitly present in both resume and JD>],
    "missing_skills": [<skills required in JD but not found in resume>],
    "experience_match": "<one of: strong match | partial match | underqualified | overqualified>",
    "verdict": "<2-3 sentence honest assessment — should this person apply?>",
    "preparation_tips": [<3-5 specific things to learn or improve before applying>],
    "interview_questions": [<5 likely interview questions based on this JD and resume>]
}}

Rules:
- Base everything strictly on what is written. Do not assume unlisted skills.
- match_score should reflect realistic employability for this specific role.
- Be direct and honest, especially for fresher candidates.
- interview_questions should be specific to this JD, not generic.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are a technical recruiter. Always respond with pure valid JSON only. No markdown, no code fences, no explanation."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3,
        max_tokens=2000
    )

    raw_text = response.choices[0].message.content.strip()

    # Safety net — strip markdown code blocks if model adds them anyway
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        raw_text = "\n".join(lines[1:-1])

    return json.loads(raw_text)


def research_company(company: str, role: str) -> dict:
    """
    Researches a company and role using AI.
    Returns structured information about what the company does,
    what the role means, and what CS topics will be tested.
    """
    prompt = f"""
You are an expert career advisor with deep knowledge of the Indian tech industry.

Research this company and role for a fresher applicant.

Company: {company}
Role: {role}

Return ONLY a valid JSON object with exactly this structure:
{{
    "company_type": "<one of: startup/bank/fintech/product/service/consultancy/ecommerce>",
    "what_they_do": "<2-3 sentences about what this company does>",
    "role_summary": "<what this person will actually do day to day in 2-3 sentences>",
    "interview_style": "<how this type of company typically interviews freshers>",
    "cs_topics": {{
        "DBMS":     "<one of: heavy/medium/light/none>",
        "OS":       "<one of: heavy/medium/light/none>",
        "Networks": "<one of: heavy/medium/light/none>",
        "DSA":      "<one of: heavy/medium/light/none>",
        "System Design": "<one of: heavy/medium/light/none>"
    }},
    "fresher_expectations": "<what a fresher is realistically expected to know for this role>",
    "apply_tips": "<2-3 specific tips for a fresher applying to this role at this company>"
}}

Base this on general knowledge of this company type and role.
Be honest and specific. No generic advice.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are a career advisor. Always respond with pure valid JSON only."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3,
        max_tokens=1500
    )

    raw_text = response.choices[0].message.content.strip()
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        raw_text = "\n".join(lines[1:-1])

    return json.loads(raw_text)


def assess_readiness(resume_text: str, jd_text: str,
                     company_context: str = None) -> dict:
    """
    Assesses how ready a fresher is for a specific role.
    Returns readiness score, gaps, and preparation verdict.
    Company context from research improves accuracy.
    """

    context_section = ""
    if company_context:
        context_section = f"""
Company Research Context (use this to calibrate the assessment):
{company_context}
"""

    prompt = f"""
You are an honest technical recruiter assessing a fresher's interview readiness.

{context_section}

JOB DESCRIPTION:
{jd_text}

RESUME:
{resume_text}

Assess this fresher's readiness for this specific role.

Return ONLY a valid JSON object:
{{
    "overall_readiness_score": <integer 0-100>,
    "technical_skills_score": <integer 0-100>,
    "cs_fundamentals_score": <integer 0-100>,
    "projects_relevance_score": <integer 0-100>,
    "confidence_level": "<one of: not ready/building/ready/strong>",
    "strengths": [<list of specific strengths from resume that match this role>],
    "gaps": [<list of technical gaps ordered by importance for this role>],
    "cs_gaps": [<list of CS fundamentals gaps: OS/DBMS/Networks/DSA specific topics>],
    "verdict": "<one of: apply now/prepare first/not ready yet>",
    "estimated_days_to_ready": <integer — realistic days of focused study>,
    "honest_assessment": "<3-4 sentences of honest, direct assessment>"
}}

Rules:
- Be calibrated to fresher level — don't expect senior knowledge
- Gaps must be specific: not 'learn DBMS' but 'learn normalization and ACID'
- estimated_days must be realistic for 3-4 hours of study per day
- If resume shows strong projects, weight that heavily
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are a technical recruiter. Always respond with pure valid JSON only."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3,
        max_tokens=2000
    )

    raw_text = response.choices[0].message.content.strip()
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        raw_text = "\n".join(lines[1:-1])

    return json.loads(raw_text)


def generate_roadmap(gaps: list, cs_gaps: list,
                     estimated_days: int, company: str, role: str) -> dict:
    """
    Generates a day by day preparation plan.
    Based on specific gaps from the readiness assessment.
    Calibrated to the right depth for this specific role.
    """

    prompt = f"""
You are a career coach creating a focused preparation plan.

Company: {company}
Role: {role}
Days available: {estimated_days}
Technical gaps: {json.dumps(gaps)}
CS fundamentals gaps: {json.dumps(cs_gaps)}

Create a day by day preparation plan.

Return ONLY a valid JSON object with NO extra text:
{{
    "total_days": <integer>,
    "daily_plan": [
        {{
            "day_number": <integer>,
            "title": "<short title>",
            "focus_topic": "<main topic>",
            "what_to_study": [<maximum 3 specific subtopics>],
            "depth_needed": "<one sentence on what level is enough>",
            "how_to_verify": "<one specific mini exercise>",
            "estimated_hours": <integer 2-4>
        }}
    ]
}}

Rules:
- Maximum {estimated_days} days
- Only topics relevant to THIS role
- Each day achievable in 3-4 hours
- Keep each field concise — one sentence maximum
- Last day is always revision and mock practice
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are a career coach. Always respond with pure valid JSON only."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3,
        max_tokens=4000
    )

    raw_text = response.choices[0].message.content.strip()
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        raw_text = "\n".join(lines[1:-1])

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Groq returned invalid JSON for roadmap. "
                        f"Error: {e}. "
                        f"Raw response was: {raw_text[:500]}")

    return json.loads(raw_text)


def generate_interview_questions(resume_text: str, jd_text: str,
                                  company: str, role: str,
                                  readiness_context: str = None) -> dict:
    """
    Generates 10 personalized interview questions.
    Questions are calibrated to the user's readiness level.
    Includes project-specific and situation questions
    based on what's actually on the resume.
    """

    readiness_section = ""
    if readiness_context:
        readiness_section = f"""
Readiness Assessment (calibrate question difficulty to this level):
{readiness_context}
"""

    prompt = f"""
You are an interviewer at {company} conducting a fresher interview
for the role of {role}.

{readiness_section}

JOB DESCRIPTION:
{jd_text}

CANDIDATE RESUME:
{resume_text}

Generate 10 interview questions personalized to this candidate.

Mix:
- 3 technical questions (based on JD requirements, at their level)
- 2 CS fundamentals questions (relevant to this role type)
- 2 project questions (specifically about projects on their resume)
- 2 situation questions (based on their actual experience)
- 1 motivation question (why this company/role)

Return ONLY a valid JSON object:
{{
    "questions": [
        {{
            "number": <integer 1-10>,
            "question": "<the actual question>",
            "type": "<technical/fundamentals/project/situation/motivation>",
            "why_asked": "<why an interviewer asks this specific question>",
            "answer_guide": "<what a strong answer looks like>",
            "keywords": [<important terms to include in answer>],
            "common_mistake": "<what weak candidates typically say>"
        }}
    ]
}}

Rules:
- Project questions must reference ACTUAL projects from the resume
- Situation questions must reference ACTUAL experience from resume
- Difficulty calibrated to readiness level — not too hard, not too easy
- Questions must feel like they come from THIS company, not generic
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are a technical interviewer. Always respond with pure valid JSON only."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.4,
        max_tokens=3000
    )

    raw_text = response.choices[0].message.content.strip()
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        raw_text = "\n".join(lines[1:-1])

    return json.loads(raw_text)


def analyze_outcomes(jobs_summary: list) -> dict:
    """
    Analyses application history to find patterns.
    Tells user what's working, what's not, and where to focus.
    """

    prompt = f"""
You are a career advisor analyzing a fresher's job application history.

Application history:
{json.dumps(jobs_summary, indent=2)}

Find patterns and give honest, actionable insights.

Return ONLY a valid JSON object:
{{
    "total_applications": <integer>,
    "callback_rate": "<percentage string>",
    "what_is_working": [<list of patterns leading to callbacks>],
    "what_is_not_working": [<list of patterns leading to rejections>],
    "recommended_focus": "<specific recommendation for next applications>",
    "roles_to_avoid_now": [<roles the candidate is not ready for yet>],
    "roles_to_target": [<roles most likely to succeed based on profile>],
    "honest_summary": "<3-4 sentences of direct honest career advice>"
}}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are a career advisor. Always respond with pure valid JSON only."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3,
        max_tokens=1500
    )

    raw_text = response.choices[0].message.content.strip()
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        raw_text = "\n".join(lines[1:-1])

    return json.loads(raw_text)