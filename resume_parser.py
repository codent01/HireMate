import os
import re


def extract_text_from_pdf(filepath):
    from PyPDF2 import PdfReader
    reader = PdfReader(filepath)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text.strip()


def extract_text_from_docx(filepath):
    from docx import Document
    doc = Document(filepath)
    text = "\n".join(p.text for p in doc.paragraphs)
    return text.strip()


def extract_text(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(filepath)
    elif ext in (".docx", ".doc"):
        return extract_text_from_docx(filepath)
    elif ext == ".txt":
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    raise ValueError(f"Unsupported file type: {ext}")


def parse_resume_sections(text):
    sections = {
        "contact": "",
        "summary": "",
        "experience": "",
        "education": "",
        "skills": "",
        "certifications": "",
        "projects": "",
        "other": "",
    }

    section_patterns = {
        "contact": r"(?i)(contact|personal\s+info|details)",
        "summary": r"(?i)(summary|objective|profile|about)",
        "experience": r"(?i)(experience|work\s+history|employment|professional)",
        "education": r"(?i)(education|academic|qualification|degree)",
        "skills": r"(?i)(skills|technical|competenc|proficienc|technologies)",
        "certifications": r"(?i)(certif|license|credential|award)",
        "projects": r"(?i)(project|portfolio|work\s+sample)",
    }

    lines = text.split("\n")
    current_section = "other"

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        matched = False
        for section, pattern in section_patterns.items():
            if re.search(pattern, stripped) and len(stripped) < 60:
                current_section = section
                matched = True
                break
        if not matched:
            sections[current_section] += stripped + "\n"

    skills_text = sections.get("skills", "") + " " + sections.get("other", "")
    skill_keywords = extract_skills(skills_text)

    return {
        "sections": {k: v.strip() for k, v in sections.items()},
        "skills": skill_keywords,
        "word_count": len(text.split()),
        "has_contact": bool(sections["contact"]),
        "has_summary": bool(sections["summary"]),
        "has_experience": bool(sections["experience"]),
        "has_education": bool(sections["education"]),
        "has_skills": bool(sections["skills"]),
    }


def extract_skills(text):
    common_skills = [
        "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
        "react", "angular", "vue", "node.js", "express", "django", "flask", "fastapi",
        "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ci/cd",
        "git", "linux", "agile", "scrum", "jira",
        "machine learning", "deep learning", "nlp", "computer vision", "data science",
        "tensorflow", "pytorch", "pandas", "numpy", "scikit-learn",
        "html", "css", "sass", "tailwind", "bootstrap",
        "rest api", "graphql", "microservices", "serverless",
        "figma", "sketch", "adobe", "photoshop", "illustrator",
        "product management", "project management", "data analysis",
        "communication", "leadership", "problem solving", "teamwork",
    ]
    text_lower = text.lower()
    return [s for s in common_skills if s in text_lower]
