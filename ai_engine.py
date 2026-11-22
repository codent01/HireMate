import json
import re
from ai_provider import get_provider


def _call_ai(prompt, system="You are an expert career coach and resume analyst."):
    provider = get_provider()
    return provider.chat(prompt, system)


def ats_check(resume_text):
    prompt = f"""Analyze this resume for ATS (Applicant Tracking System) compatibility.
Return a JSON object with these exact fields:
{{
    "score": <number 0-100>,
    "summary": "<one paragraph overview>",
    "strengths": ["<strength1>", "<strength2>", ...],
    "issues": [
        {{"issue": "<description>", "impact": "<high/medium/low>", "fix": "<how to fix>", "points": <potential score increase>}}
    ],
    "keyword_density": "<assessment>",
    "formatting_score": <number 0-100>,
    "content_score": <number 0-100>,
    "structure_score": <number 0-100>,
    "recommendations": ["<rec1>", "<rec2>", ...]
}}

Resume:
{resume_text}

Return ONLY valid JSON, no markdown formatting."""

    result = _call_ai(prompt)
    if not result:
        return _fallback_ats_check(resume_text)
    try:
        cleaned = re.sub(r"```json\s*|\s*```", "", result).strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return _fallback_ats_check(resume_text)


def match_job(resume_text, job_description):
    prompt = f"""Score how well this resume matches the job description.
Return a JSON object:
{{
    "overall_score": <number 0-100>,
    "verdict": "<Strong Match / Good Match / Moderate Match / Weak Match>",
    "skills_match": {{"score": <0-100>, "matched": ["skill1", ...], "missing": ["skill1", ...]}},
    "experience_match": {{"score": <0-100>, "assessment": "<text>"}},
    "education_match": {{"score": <0-100>, "assessment": "<text>"}},
    "keyword_overlap": ["keyword1", ...],
    "gaps": ["<gap1>", "<gap2>", ...],
    "tips": ["<tip1>", "<tip2>", ...]
}}

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}

Return ONLY valid JSON, no markdown."""

    result = _call_ai(prompt)
    if not result:
        return {"overall_score": 0, "verdict": "AI unavailable", "tips": ["Configure an AI provider in Settings"]}
    try:
        cleaned = re.sub(r"```json\s*|\s*```", "", result).strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"overall_score": 0, "verdict": "Parse error"}


def tailor_resume(resume_text, job_description, job_title="", company=""):
    prompt = f"""Rewrite this resume to be tailored for the specific job below.
Keep all factual information accurate but optimize:
- Professional summary to target this role
- Bullet points to emphasize relevant experience
- Skills section to match job requirements
- Keywords from the job description naturally woven in

Return a JSON object:
{{
    "tailored_resume": "<the full tailored resume text>",
    "match_score": <estimated match score 0-100>,
    "changes_made": ["<change1>", "<change2>", ...],
    "keywords_added": ["<keyword1>", ...]
}}

ORIGINAL RESUME:
{resume_text}

TARGET JOB: {job_title} at {company}
JOB DESCRIPTION:
{job_description}

Return ONLY valid JSON, no markdown."""

    result = _call_ai(prompt)
    if not result:
        return {"tailored_resume": resume_text, "match_score": 0, "changes_made": ["AI unavailable"]}
    try:
        cleaned = re.sub(r"```json\s*|\s*```", "", result).strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"tailored_resume": resume_text, "match_score": 0, "changes_made": ["Parse error"]}


def find_hr_contacts(company, job_title=""):
    prompt = f"""For the company "{company}"{f' and the role "{job_title}"' if job_title else ''},
suggest the types of people to contact and how to find them.
Return a JSON object:
{{
    "search_tips": ["<tip1>", "<tip2>", ...],
    "suggested_titles": ["<title1>", "<title2>", ...],
    "email_patterns": ["<pattern1>", ...],
    "linkedin_search_query": "<suggested search string>",
    "outreach_template": "<email template>"
}}

Return ONLY valid JSON, no markdown."""

    result = _call_ai(prompt)
    if not result:
        return {"search_tips": ["Configure an AI provider in Settings to enable this feature"]}
    try:
        cleaned = re.sub(r"```json\s*|\s*```", "", result).strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"search_tips": ["Could not parse AI response"]}


def generate_cover_letter(resume_text, job_description, job_title="", company=""):
    prompt = f"""Write a compelling cover letter for this job application.

RESUME:
{resume_text}

JOB: {job_title} at {company}
JOB DESCRIPTION:
{job_description}

Write a professional, personalized cover letter (3-4 paragraphs).
Return ONLY the cover letter text, no JSON or markdown formatting."""

    result = _call_ai(prompt)
    return result or "AI unavailable. Configure an AI provider in Settings to generate cover letters."


def extract_job_details(job_text):
    prompt = f"""Extract structured details from this job posting.
Return a JSON object:
{{
    "title": "<job title>",
    "company": "<company name>",
    "location": "<location>",
    "work_model": "<remote/hybrid/onsite>",
    "requirements": ["<req1>", "<req2>", ...],
    "nice_to_have": ["<item1>", ...],
    "salary": "<salary range if mentioned>",
    "summary": "<2 sentence summary>"
}}

JOB POSTING:
{job_text}

Return ONLY valid JSON, no markdown."""

    result = _call_ai(prompt)
    if not result:
        return None
    try:
        cleaned = re.sub(r"```json\s*|\s*```", "", result).strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def _fallback_ats_check(text):
    score = 50
    issues = []
    strengths = []
    words = text.split()
    word_count = len(words)

    if word_count < 200:
        issues.append({"issue": "Resume is too short", "impact": "high", "fix": "Add more detail to work experience", "points": 10})
    elif word_count > 300:
        strengths.append("Good resume length")
        score += 5

    sections_found = 0
    for label in ["experience", "education", "skill", "summary", "project"]:
        if label in text.lower():
            sections_found += 1
    if sections_found >= 3:
        strengths.append(f"Has {sections_found} key sections")
        score += sections_found * 3
    else:
        issues.append({"issue": "Missing key sections", "impact": "high", "fix": "Add Experience, Education, Skills sections", "points": 15})

    action_verbs = ["led", "managed", "developed", "created", "implemented", "designed",
                    "achieved", "improved", "increased", "reduced", "built", "launched"]
    verb_count = sum(1 for v in action_verbs if v in text.lower())
    if verb_count >= 3:
        strengths.append(f"Uses {verb_count} action verbs")
        score += 5
    else:
        issues.append({"issue": "Few action verbs", "impact": "medium", "fix": "Start bullet points with strong action verbs", "points": 6})

    if re.search(r"\d+%|\d+x|\$[\d,]+", text):
        strengths.append("Includes quantified achievements")
        score += 10
    else:
        issues.append({"issue": "No quantified results", "impact": "high", "fix": "Add numbers: percentages, dollar amounts, team sizes", "points": 10})

    score = min(100, max(0, score))
    return {
        "score": score,
        "summary": f"Basic ATS analysis (AI not configured). Score: {score}/100.",
        "strengths": strengths,
        "issues": issues,
        "keyword_density": "Unable to assess without AI",
        "formatting_score": score,
        "content_score": score,
        "structure_score": score,
        "recommendations": [i["fix"] for i in issues[:3]],
    }
