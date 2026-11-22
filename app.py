import os
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename
from config import UPLOAD_FOLDER, SECRET_KEY, ALLOWED_EXTENSIONS, MAX_CONTENT_LENGTH
from database import init_db, ResumeDB, ApplicationDB, ContactDB, TailoredResumeDB, ProfileDB, JobPortalDB, RoleProfileDB
from resume_parser import extract_text, parse_resume_sections
from ai_engine import ats_check, match_job, tailor_resume, find_hr_contacts, generate_cover_letter, extract_job_details
from ai_provider import load_settings, save_settings, get_provider, OllamaProvider
from job_search import search_jobs

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 3600

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
init_db()
JobPortalDB.seed_defaults()


def _ai_status():
    provider = get_provider()
    return {"available": provider.is_available(), "name": provider.name}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    stats = ApplicationDB.get_stats()
    resumes = ResumeDB.get_all()
    primary = ResumeDB.get_primary()
    ai = _ai_status()
    return render_template("index.html",
                           stats=stats,
                           resume_count=len(resumes),
                           primary_resume=primary,
                           ai_status=ai)


@app.route("/dashboard")
def dashboard():
    stats = ApplicationDB.get_stats()
    resumes = ResumeDB.get_all()
    recent_apps = ApplicationDB.get_all()[:5]
    primary = ResumeDB.get_primary()
    profile = ProfileDB.get()
    profile_strength = ProfileDB.strength_score()
    funnel = ApplicationDB.get_funnel()
    weekly = ApplicationDB.get_weekly_stats()
    ai = _ai_status()
    return render_template("dashboard.html",
                           stats=stats,
                           resumes=resumes,
                           resume_count=len(resumes),
                           recent_apps=recent_apps,
                           primary_resume=primary,
                           profile=profile,
                           profile_strength=profile_strength,
                           funnel=funnel,
                           weekly=weekly,
                           ai_status=ai)


# --- Profile Routes ---

@app.route("/profile")
def profile_page():
    profile = ProfileDB.get()
    strength = ProfileDB.strength_score()
    roles = RoleProfileDB.get_all()
    ai = _ai_status()
    return render_template("profile.html", profile=profile, strength=strength, roles=roles, ai_status=ai)


@app.route("/api/profile", methods=["POST"])
def update_profile():
    data = request.json
    ProfileDB.update(data)
    return jsonify({"ok": True, "strength": ProfileDB.strength_score()})


@app.route("/api/profile/import-resume", methods=["POST"])
def import_resume_to_profile():
    resume = ResumeDB.get_primary()
    if not resume:
        return jsonify({"error": "No primary resume set"}), 400
    parsed = resume.get("parsed_data")
    if parsed:
        try:
            parsed = json.loads(parsed) if isinstance(parsed, str) else parsed
        except json.JSONDecodeError:
            parsed = {}
    if not parsed:
        parsed = {}
    profile_data = {}
    if parsed.get("name"):
        profile_data["full_name"] = parsed["name"]
    if parsed.get("email"):
        profile_data["email"] = parsed["email"]
    if parsed.get("phone"):
        profile_data["phone"] = parsed["phone"]
    if parsed.get("summary"):
        profile_data["summary"] = parsed["summary"]
    if parsed.get("skills"):
        skills = parsed["skills"]
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]
        profile_data["skills"] = skills
    if profile_data:
        ProfileDB.update(profile_data)
    return jsonify({"ok": True, "imported": list(profile_data.keys()), "strength": ProfileDB.strength_score()})


# --- Resume Routes ---

@app.route("/resume", methods=["GET"])
def resume_page():
    resumes = ResumeDB.get_all()
    tailored = TailoredResumeDB.get_all()
    ai = _ai_status()
    return render_template("resume.html", resumes=resumes, tailored=tailored, ai_status=ai)


@app.route("/api/resume/upload", methods=["POST"])
def upload_resume():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed. Use PDF, DOCX, or TXT"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    try:
        raw_text = extract_text(filepath)
        parsed = parse_resume_sections(raw_text)
        resume_id = ResumeDB.save(filename, raw_text, parsed)
        ResumeDB.set_primary(resume_id)
        return jsonify({"id": resume_id, "filename": filename,
                        "parsed": parsed, "word_count": len(raw_text.split())})
    except Exception as e:
        return jsonify({"error": "Failed to process resume. Please try a different file format."}), 500


@app.route("/api/resume/<int:resume_id>/ats-check", methods=["POST"])
def run_ats_check(resume_id):
    resume = ResumeDB.get(resume_id)
    if not resume:
        return jsonify({"error": "Resume not found"}), 404
    try:
        result = ats_check(resume["raw_text"])
        ResumeDB.update_ats(resume_id, result.get("score", 0), result)
        return jsonify(result)
    except Exception:
        result = {"score": 0, "summary": "AI analysis failed. Check your AI provider settings.", "strengths": [], "issues": [], "recommendations": []}
        return jsonify(result)


@app.route("/api/resume/<int:resume_id>/set-primary", methods=["POST"])
def set_primary_resume(resume_id):
    ResumeDB.set_primary(resume_id)
    return jsonify({"ok": True})


@app.route("/api/resume/match", methods=["POST"])
def match_resume_job():
    data = request.json
    resume = ResumeDB.get_primary()
    if not resume:
        return jsonify({"error": "No primary resume set. Upload a resume first."}), 400
    try:
        result = match_job(resume["raw_text"], data.get("job_description", ""))
        return jsonify(result)
    except Exception:
        return jsonify({"overall_score": 0, "verdict": "AI analysis failed", "tips": ["Check AI provider settings"]})


@app.route("/api/resume/tailor", methods=["POST"])
def tailor_resume_route():
    data = request.json
    resume = ResumeDB.get_primary()
    if not resume:
        return jsonify({"error": "No primary resume set"}), 400
    try:
        result = tailor_resume(
            resume["raw_text"],
            data.get("job_description", ""),
            data.get("job_title", ""),
            data.get("company", ""),
        )
        tid = TailoredResumeDB.save(
            resume["id"], data.get("job_title", ""), data.get("company", ""),
            result.get("tailored_resume", ""), result.get("match_score", 0),
        )
        result["id"] = tid
        return jsonify(result)
    except Exception:
        return jsonify({"tailored_resume": "", "match_score": 0, "changes_made": ["AI analysis failed"]})


@app.route("/api/resume/cover-letter", methods=["POST"])
def generate_cover_letter_route():
    data = request.json
    resume = ResumeDB.get_primary()
    if not resume:
        return jsonify({"error": "No primary resume set"}), 400
    try:
        letter = generate_cover_letter(
            resume["raw_text"],
            data.get("job_description", ""),
            data.get("job_title", ""),
            data.get("company", ""),
        )
        return jsonify({"cover_letter": letter})
    except Exception:
        return jsonify({"cover_letter": "AI generation failed. Check your AI provider settings."})


# --- Job Routes ---

@app.route("/jobs")
def jobs_page():
    ai = _ai_status()
    portals = JobPortalDB.get_all()
    resume = ResumeDB.get_primary()
    resume_skills = []
    resume_title = ""
    if resume and resume.get("parsed_data"):
        try:
            parsed = json.loads(resume["parsed_data"]) if isinstance(resume["parsed_data"], str) else resume["parsed_data"]
            resume_skills = parsed.get("skills", [])
        except (json.JSONDecodeError, TypeError):
            pass
    return render_template("jobs.html", ai_status=ai, portals=portals,
                           has_resume=resume is not None,
                           resume_skills=resume_skills)


@app.route("/api/jobs/search")
def search_jobs_route():
    query = request.args.get("q", "")
    location = request.args.get("location", "")
    work_model = request.args.get("work_model", "")
    experience = request.args.get("experience", "")
    page = int(request.args.get("page", 1))
    results = search_jobs(query, location, work_model, experience, page)
    return jsonify({"jobs": results, "total": len(results)})


@app.route("/api/jobs/recommended")
def recommended_jobs_route():
    import re as _re
    resume = ResumeDB.get_primary()
    if not resume:
        return jsonify({"jobs": [], "query_used": ""})
    parsed = {}
    if resume.get("parsed_data"):
        try:
            parsed = json.loads(resume["parsed_data"]) if isinstance(resume["parsed_data"], str) else resume["parsed_data"]
        except (json.JSONDecodeError, TypeError):
            pass
    skills = parsed.get("skills", [])
    exp_text = parsed.get("sections", {}).get("experience", "")
    title_hint = ""
    _title_pat = _re.compile(r"(?i)(designer|engineer|developer|manager|analyst|architect|scientist|specialist|director|intern|consultant|coordinator|officer|strategist|administrator)")
    other_text = parsed.get("sections", {}).get("other", "")
    for text_block in [other_text, exp_text]:
        for line in text_block.split("\n")[:15]:
            line = line.strip()
            if not line or len(line) < 5 or len(line) > 100:
                continue
            if _title_pat.search(line) and "|" in line:
                title_hint = line.split("|")[0].strip()
                break
            if _title_pat.search(line) and line[0].isupper() and not line.startswith(("Designed", "Built", "Developed", "Created", "Led", "Managed", "Collaborated", "Evaluated", "Supported", "Worked")):
                title_hint = line
                break
        if title_hint:
            break
    query = title_hint if title_hint else " ".join(skills[:4]) if skills else "Designer"
    location = request.args.get("location", "")
    results = search_jobs(query, location, "", "", 1)
    return jsonify({"jobs": results, "total": len(results), "query_used": query})


@app.route("/api/jobs/save", methods=["POST"])
def save_job():
    data = request.json
    app_id = ApplicationDB.create({
        "job_title": data.get("title"),
        "company": data.get("company"),
        "location": data.get("location"),
        "url": data.get("url"),
        "status": "saved",
        "match_score": data.get("match_score"),
    })
    return jsonify({"id": app_id})


# --- Tracker Routes ---

@app.route("/tracker")
def tracker_page():
    apps = ApplicationDB.get_all()
    stats = ApplicationDB.get_stats()
    ai = _ai_status()
    return render_template("tracker.html", applications=apps, stats=stats, ai_status=ai)


@app.route("/api/tracker/add", methods=["POST"])
def add_application():
    data = request.json
    app_id = ApplicationDB.create(data)
    return jsonify({"id": app_id})


@app.route("/api/tracker/<int:app_id>/update", methods=["POST"])
def update_application(app_id):
    data = request.json
    ApplicationDB.update(app_id, data)
    return jsonify({"ok": True})


@app.route("/api/tracker/<int:app_id>/delete", methods=["POST"])
def delete_application(app_id):
    ApplicationDB.delete(app_id)
    return jsonify({"ok": True})


# --- HR Finder Routes ---

@app.route("/find-hr")
def find_hr_page():
    contacts = ContactDB.get_all()
    ai = _ai_status()
    return render_template("find_hr.html", contacts=contacts, ai_status=ai)


@app.route("/api/find-hr", methods=["POST"])
def find_hr_route():
    data = request.json
    try:
        result = find_hr_contacts(data.get("company", ""), data.get("job_title", ""))
        return jsonify(result)
    except Exception:
        return jsonify({"search_tips": ["AI analysis failed. Check Settings."]})


@app.route("/api/contacts/save", methods=["POST"])
def save_contact():
    data = request.json
    cid = ContactDB.create(data)
    return jsonify({"id": cid})


@app.route("/api/contacts/delete/<int:contact_id>", methods=["POST"])
def delete_contact(contact_id):
    ContactDB.delete(contact_id)
    return jsonify({"ok": True})


# --- Tools Routes ---

@app.route("/tools")
def tools_page():
    ai = _ai_status()
    return render_template("tools.html", ai_status=ai)


@app.route("/tools/ats-checker")
def ats_checker_page():
    ai = _ai_status()
    return render_template("ats_checker.html", ai_status=ai)


# --- Settings Routes ---

@app.route("/settings")
def settings_page():
    settings = load_settings()
    provider = get_provider(settings)
    available = provider.is_available()
    models = []
    if settings.get("ai_provider") == "ollama" and isinstance(provider, OllamaProvider):
        models = provider.list_models()
    return render_template("settings.html",
                           settings=settings,
                           ai_available=available,
                           ai_name=provider.name,
                           ollama_models=models,
                           ai_status={"available": available, "name": provider.name})


@app.route("/api/settings", methods=["POST"])
def update_settings():
    data = request.json
    settings = load_settings()
    settings.update(data)
    save_settings(settings)
    return jsonify({"ok": True})


@app.route("/api/settings/test", methods=["POST"])
def test_ai_connection():
    data = request.json
    settings = load_settings()
    settings.update(data)
    provider = get_provider(settings)
    available = provider.is_available()
    if available:
        result = provider.chat("Say 'Connection successful!' in exactly those words.")
        return jsonify({"ok": True, "available": True, "name": provider.name,
                        "response": result or "Connected but no response"})
    return jsonify({"ok": False, "available": False, "name": provider.name,
                    "error": "Could not connect to AI provider"})


@app.route("/api/settings/ollama-models")
def list_ollama_models():
    settings = load_settings()
    provider = OllamaProvider(
        base_url=settings.get("ollama_url", "http://localhost:11434"),
    )
    models = provider.list_models()
    return jsonify({"models": models})


# --- Apply Workflow Route ---

@app.route("/apply")
def apply_page():
    ai = _ai_status()
    profile = ProfileDB.get()
    roles = RoleProfileDB.get_all()
    return render_template("apply.html", ai_status=ai, profile=profile, roles=roles)


@app.route("/api/apply/extract", methods=["POST"])
def extract_job():
    data = request.json
    job_text = data.get("job_text", "")
    if not job_text:
        return jsonify({"error": "No job text provided"}), 400
    try:
        result = extract_job_details(job_text)
        if result:
            return jsonify(result)
        return jsonify({"error": "Could not extract job details. Check AI settings."}), 500
    except Exception:
        return jsonify({"error": "AI extraction failed"}), 500


@app.route("/api/apply/full", methods=["POST"])
def full_apply_workflow():
    data = request.json
    resume = ResumeDB.get_primary()
    if not resume:
        return jsonify({"error": "No resume uploaded"}), 400

    job_desc = data.get("job_description", "")
    job_title = data.get("job_title", "")
    company = data.get("company", "")

    result = {}
    try:
        match = match_job(resume["raw_text"], job_desc)
        result["match"] = match
    except Exception:
        result["match"] = {"overall_score": 0, "verdict": "AI unavailable"}

    try:
        tailored = tailor_resume(resume["raw_text"], job_desc, job_title, company)
        result["tailored"] = tailored
        TailoredResumeDB.save(resume["id"], job_title, company,
                              tailored.get("tailored_resume", ""), tailored.get("match_score", 0))
    except Exception:
        result["tailored"] = {"tailored_resume": resume["raw_text"], "match_score": 0}

    try:
        letter = generate_cover_letter(resume["raw_text"], job_desc, job_title, company)
        result["cover_letter"] = letter
    except Exception:
        result["cover_letter"] = "AI generation failed."

    ApplicationDB.create({
        "job_title": job_title,
        "company": company,
        "url": data.get("url", ""),
        "status": "saved",
        "match_score": result.get("match", {}).get("overall_score", 0),
        "notes": f"Auto-created from apply workflow",
    })

    return jsonify(result)


# --- Job Portal Routes ---

@app.route("/api/portals")
def get_portals():
    return jsonify({"portals": JobPortalDB.get_all()})


@app.route("/api/portals/add", methods=["POST"])
def add_portal():
    data = request.json
    if not data.get("name") or not data.get("url"):
        return jsonify({"error": "Name and URL are required"}), 400
    pid = JobPortalDB.create(data)
    return jsonify({"id": pid})


@app.route("/api/portals/<int:portal_id>/update", methods=["POST"])
def update_portal(portal_id):
    data = request.json
    JobPortalDB.update(portal_id, data)
    return jsonify({"ok": True})


@app.route("/api/portals/<int:portal_id>/delete", methods=["POST"])
def delete_portal(portal_id):
    JobPortalDB.delete(portal_id)
    return jsonify({"ok": True})


# --- Role Profile Routes ---

@app.route("/api/roles")
def get_roles():
    return jsonify({"roles": RoleProfileDB.get_all()})


@app.route("/api/roles/add", methods=["POST"])
def add_role():
    data = request.json
    if not data.get("name"):
        return jsonify({"error": "Role name is required"}), 400
    rid = RoleProfileDB.create(data)
    return jsonify({"id": rid})


@app.route("/api/roles/<int:role_id>")
def get_role(role_id):
    role = RoleProfileDB.get(role_id)
    if not role:
        return jsonify({"error": "Role not found"}), 404
    return jsonify(role)


@app.route("/api/roles/<int:role_id>/update", methods=["POST"])
def update_role(role_id):
    data = request.json
    RoleProfileDB.update(role_id, data)
    return jsonify({"ok": True})


@app.route("/api/roles/<int:role_id>/delete", methods=["POST"])
def delete_role(role_id):
    RoleProfileDB.delete(role_id)
    return jsonify({"ok": True})


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  HireMate - Your Personal AI Job-Search Assistant")
    print("=" * 60)
    ai = _ai_status()
    if ai["available"]:
        print(f"\n  [OK] AI Provider: {ai['name']}")
    else:
        print(f"\n  [!] AI not connected. Go to Settings to configure.")
    print("\n  Open: http://localhost:5000")
    print("=" * 60 + "\n")
    app.run(debug=True, port=5000)
