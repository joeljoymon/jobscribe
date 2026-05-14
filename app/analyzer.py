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