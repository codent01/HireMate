import sqlite3
import json
from datetime import datetime
from config import DATABASE_PATH


def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                raw_text TEXT,
                parsed_data TEXT,
                ats_score INTEGER,
                ats_report TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                is_primary INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS saved_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                company TEXT,
                location TEXT,
                work_model TEXT,
                salary TEXT,
                description TEXT,
                url TEXT,
                source TEXT,
                match_score INTEGER,
                match_details TEXT,
                saved_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_title TEXT NOT NULL,
                company TEXT,
                location TEXT,
                url TEXT,
                status TEXT DEFAULT 'saved',
                applied_date TEXT,
                response_date TEXT,
                interview_date TEXT,
                notes TEXT,
                resume_used TEXT,
                match_score INTEGER,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                title TEXT,
                company TEXT,
                email TEXT,
                linkedin TEXT,
                source TEXT,
                notes TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS tailored_resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_id INTEGER,
                job_title TEXT,
                company TEXT,
                tailored_content TEXT,
                match_score INTEGER,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (resume_id) REFERENCES resumes(id)
            );

            CREATE TABLE IF NOT EXISTS profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                full_name TEXT DEFAULT '',
                email TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                location TEXT DEFAULT '',
                title TEXT DEFAULT '',
                website TEXT DEFAULT '',
                linkedin TEXT DEFAULT '',
                github TEXT DEFAULT '',
                summary TEXT DEFAULT '',
                skills TEXT DEFAULT '[]',
                languages TEXT DEFAULT '[]',
                experience TEXT DEFAULT '[]',
                education TEXT DEFAULT '[]',
                certifications TEXT DEFAULT '[]',
                projects TEXT DEFAULT '[]',
                updated_at TEXT DEFAULT (datetime('now'))
            );

            INSERT OR IGNORE INTO profile (id) VALUES (1);

            CREATE TABLE IF NOT EXISTS job_portals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                logo_letter TEXT DEFAULT '',
                color TEXT DEFAULT '#f97316',
                is_active INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS role_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                target_title TEXT DEFAULT '',
                summary TEXT DEFAULT '',
                skills TEXT DEFAULT '[]',
                highlight_experience TEXT DEFAULT '[]',
                keywords TEXT DEFAULT '[]',
                is_default INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
        """)
        conn.commit()
    finally:
        conn.close()


class ResumeDB:
    @staticmethod
    def save(filename, raw_text, parsed_data=None):
        conn = get_db()
        try:
            cur = conn.execute(
                "INSERT INTO resumes (filename, raw_text, parsed_data) VALUES (?, ?, ?)",
                (filename, raw_text, json.dumps(parsed_data) if parsed_data else None),
            )
            rid = cur.lastrowid
            conn.commit()
            return rid
        finally:
            conn.close()

    @staticmethod
    def update_ats(resume_id, score, report):
        conn = get_db()
        try:
            conn.execute(
                "UPDATE resumes SET ats_score=?, ats_report=? WHERE id=?",
                (score, json.dumps(report) if isinstance(report, dict) else report, resume_id),
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def set_primary(resume_id):
        conn = get_db()
        try:
            conn.execute("UPDATE resumes SET is_primary=0")
            conn.execute("UPDATE resumes SET is_primary=1 WHERE id=?", (resume_id,))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_primary():
        conn = get_db()
        try:
            row = conn.execute("SELECT * FROM resumes WHERE is_primary=1 ORDER BY id DESC LIMIT 1").fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_all():
        conn = get_db()
        try:
            rows = conn.execute("SELECT * FROM resumes ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get(resume_id):
        conn = get_db()
        try:
            row = conn.execute("SELECT * FROM resumes WHERE id=?", (resume_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


class ApplicationDB:
    @staticmethod
    def create(data):
        conn = get_db()
        try:
            cur = conn.execute(
                """INSERT INTO applications (job_title, company, location, url, status,
                   applied_date, notes, match_score) VALUES (?,?,?,?,?,?,?,?)""",
                (data.get("job_title"), data.get("company"), data.get("location"),
                 data.get("url"), data.get("status", "saved"), data.get("applied_date"),
                 data.get("notes"), data.get("match_score")),
            )
            aid = cur.lastrowid
            conn.commit()
            return aid
        finally:
            conn.close()

    @staticmethod
    def update(app_id, data):
        conn = get_db()
        try:
            fields = []
            values = []
            for key in ("status", "applied_date", "response_date", "interview_date", "notes", "match_score"):
                if key in data:
                    fields.append(f"{key}=?")
                    values.append(data[key])
            if fields:
                fields.append("updated_at=datetime('now')")
                values.append(app_id)
                conn.execute(f"UPDATE applications SET {', '.join(fields)} WHERE id=?", values)
                conn.commit()
        finally:
            conn.close()

    @staticmethod
    def delete(app_id):
        conn = get_db()
        try:
            conn.execute("DELETE FROM applications WHERE id=?", (app_id,))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_all():
        conn = get_db()
        try:
            rows = conn.execute("SELECT * FROM applications ORDER BY updated_at DESC").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_stats():
        conn = get_db()
        try:
            total = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
            by_status = {}
            for row in conn.execute("SELECT status, COUNT(*) as cnt FROM applications GROUP BY status").fetchall():
                by_status[row["status"]] = row["cnt"]
            return {"total": total, "by_status": by_status}
        finally:
            conn.close()

    @staticmethod
    def get_weekly_stats(weeks=8):
        conn = get_db()
        try:
            rows = conn.execute("""
                SELECT strftime('%%Y-%%W', created_at) as week,
                       COUNT(*) as count
                FROM applications
                WHERE created_at >= date('now', ?)
                GROUP BY week ORDER BY week
            """, (f"-{weeks * 7} days",)).fetchall()
            return [{"week": r["week"], "count": r["count"]} for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_funnel():
        conn = get_db()
        try:
            stages = ["saved", "applied", "screening", "interview", "offer"]
            funnel = []
            for stage in stages:
                count = conn.execute(
                    "SELECT COUNT(*) FROM applications WHERE status=?", (stage,)
                ).fetchone()[0]
                funnel.append({"stage": stage, "count": count})
            return funnel
        finally:
            conn.close()


class ContactDB:
    @staticmethod
    def create(data):
        conn = get_db()
        try:
            cur = conn.execute(
                "INSERT INTO contacts (name, title, company, email, linkedin, source, notes) VALUES (?,?,?,?,?,?,?)",
                (data.get("name"), data.get("title"), data.get("company"),
                 data.get("email"), data.get("linkedin"), data.get("source"), data.get("notes")),
            )
            cid = cur.lastrowid
            conn.commit()
            return cid
        finally:
            conn.close()

    @staticmethod
    def get_all():
        conn = get_db()
        try:
            rows = conn.execute("SELECT * FROM contacts ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def search(company):
        conn = get_db()
        try:
            rows = conn.execute(
                "SELECT * FROM contacts WHERE company LIKE ? ORDER BY created_at DESC",
                (f"%{company}%",),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def delete(contact_id):
        conn = get_db()
        try:
            conn.execute("DELETE FROM contacts WHERE id=?", (contact_id,))
            conn.commit()
        finally:
            conn.close()


class TailoredResumeDB:
    @staticmethod
    def save(resume_id, job_title, company, content, score):
        conn = get_db()
        try:
            cur = conn.execute(
                "INSERT INTO tailored_resumes (resume_id, job_title, company, tailored_content, match_score) VALUES (?,?,?,?,?)",
                (resume_id, job_title, company, content, score),
            )
            tid = cur.lastrowid
            conn.commit()
            return tid
        finally:
            conn.close()

    @staticmethod
    def get_all():
        conn = get_db()
        try:
            rows = conn.execute("SELECT * FROM tailored_resumes ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


class ProfileDB:
    @staticmethod
    def get():
        conn = get_db()
        try:
            row = conn.execute("SELECT * FROM profile WHERE id=1").fetchone()
            if not row:
                return {}
            data = dict(row)
            for field in ("skills", "languages", "experience", "education", "certifications", "projects"):
                try:
                    data[field] = json.loads(data[field]) if data[field] else []
                except (json.JSONDecodeError, TypeError):
                    data[field] = []
            return data
        finally:
            conn.close()

    @staticmethod
    def update(data):
        conn = get_db()
        try:
            for field in ("skills", "languages", "experience", "education", "certifications", "projects"):
                if field in data and isinstance(data[field], (list, dict)):
                    data[field] = json.dumps(data[field])
            fields = []
            values = []
            allowed = ("full_name", "email", "phone", "location", "title", "website",
                       "linkedin", "github", "summary", "skills", "languages",
                       "experience", "education", "certifications", "projects")
            for key in allowed:
                if key in data:
                    fields.append(f"{key}=?")
                    values.append(data[key])
            if fields:
                fields.append("updated_at=datetime('now')")
                values.append(1)
                conn.execute(f"UPDATE profile SET {', '.join(fields)} WHERE id=?", values)
                conn.commit()
        finally:
            conn.close()

    @staticmethod
    def strength_score():
        profile = ProfileDB.get()
        if not profile:
            return 0
        score = 0
        weights = {
            "full_name": 10, "email": 5, "phone": 5, "title": 10,
            "summary": 15, "location": 5, "linkedin": 5,
        }
        for field, weight in weights.items():
            if profile.get(field):
                score += weight
        list_weights = {
            "skills": (15, 3), "experience": (15, 1), "education": (10, 1),
            "projects": (5, 1),
        }
        for field, (weight, min_items) in list_weights.items():
            items = profile.get(field, [])
            if len(items) >= min_items:
                score += weight
        return min(100, score)


class JobPortalDB:
    @staticmethod
    def get_all():
        conn = get_db()
        try:
            rows = conn.execute("SELECT * FROM job_portals ORDER BY sort_order, name").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_active():
        conn = get_db()
        try:
            rows = conn.execute("SELECT * FROM job_portals WHERE is_active=1 ORDER BY sort_order, name").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def create(data):
        conn = get_db()
        try:
            cur = conn.execute(
                "INSERT INTO job_portals (name, url, logo_letter, color) VALUES (?,?,?,?)",
                (data.get("name"), data.get("url"), data.get("logo_letter", ""), data.get("color", "#f97316")),
            )
            pid = cur.lastrowid
            conn.commit()
            return pid
        finally:
            conn.close()

    @staticmethod
    def update(portal_id, data):
        conn = get_db()
        try:
            fields, values = [], []
            for key in ("name", "url", "logo_letter", "color", "is_active", "sort_order"):
                if key in data:
                    fields.append(f"{key}=?")
                    values.append(data[key])
            if fields:
                values.append(portal_id)
                conn.execute(f"UPDATE job_portals SET {', '.join(fields)} WHERE id=?", values)
                conn.commit()
        finally:
            conn.close()

    @staticmethod
    def delete(portal_id):
        conn = get_db()
        try:
            conn.execute("DELETE FROM job_portals WHERE id=?", (portal_id,))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def seed_defaults():
        conn = get_db()
        try:
            count = conn.execute("SELECT COUNT(*) FROM job_portals").fetchone()[0]
            if count > 0:
                return
            defaults = [
                ("LinkedIn", "https://www.linkedin.com/jobs/search/?keywords={q}&location={location}", "Li", "#0A66C2"),
                ("Indeed", "https://www.indeed.com/jobs?q={q}&l={location}", "In", "#2164F3"),
                ("Naukri", "https://www.naukri.com/{q}-jobs-in-{location}", "Na", "#4A90D9"),
                ("Glassdoor", "https://www.glassdoor.com/Job/jobs.htm?sc.keyword={q}&locT=C&locKeyword={location}", "Gd", "#0CAA41"),
                ("Wellfound", "https://wellfound.com/role/r/{q}", "Wf", "#000000"),
                ("Remotive", "https://remotive.com/remote-jobs?query={q}", "Re", "#1DB954"),
                ("We Work Remotely", "https://weworkremotely.com/remote-jobs/search?term={q}", "WR", "#1E3A5F"),
                ("Internshala", "https://internshala.com/internships/{q}-internship", "Is", "#00A5EC"),
            ]
            for name, url, letter, color in defaults:
                conn.execute(
                    "INSERT INTO job_portals (name, url, logo_letter, color, sort_order) VALUES (?,?,?,?,?)",
                    (name, url, letter, color, defaults.index((name, url, letter, color))),
                )
            conn.commit()
        finally:
            conn.close()


class RoleProfileDB:
    @staticmethod
    def get_all():
        conn = get_db()
        try:
            rows = conn.execute("SELECT * FROM role_profiles ORDER BY is_default DESC, name").fetchall()
            result = []
            for row in rows:
                d = dict(row)
                for field in ("skills", "highlight_experience", "keywords"):
                    try:
                        d[field] = json.loads(d[field]) if d[field] else []
                    except (json.JSONDecodeError, TypeError):
                        d[field] = []
                result.append(d)
            return result
        finally:
            conn.close()

    @staticmethod
    def get(role_id):
        conn = get_db()
        try:
            row = conn.execute("SELECT * FROM role_profiles WHERE id=?", (role_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            for field in ("skills", "highlight_experience", "keywords"):
                try:
                    d[field] = json.loads(d[field]) if d[field] else []
                except (json.JSONDecodeError, TypeError):
                    d[field] = []
            return d
        finally:
            conn.close()

    @staticmethod
    def create(data):
        conn = get_db()
        try:
            skills = json.dumps(data.get("skills", []))
            highlights = json.dumps(data.get("highlight_experience", []))
            keywords = json.dumps(data.get("keywords", []))
            cur = conn.execute(
                """INSERT INTO role_profiles (name, target_title, summary, skills, highlight_experience, keywords)
                   VALUES (?,?,?,?,?,?)""",
                (data.get("name"), data.get("target_title", ""), data.get("summary", ""),
                 skills, highlights, keywords),
            )
            rid = cur.lastrowid
            conn.commit()
            return rid
        finally:
            conn.close()

    @staticmethod
    def update(role_id, data):
        conn = get_db()
        try:
            for field in ("skills", "highlight_experience", "keywords"):
                if field in data and isinstance(data[field], (list, dict)):
                    data[field] = json.dumps(data[field])
            fields, values = [], []
            for key in ("name", "target_title", "summary", "skills", "highlight_experience", "keywords", "is_default"):
                if key in data:
                    fields.append(f"{key}=?")
                    values.append(data[key])
            if fields:
                fields.append("updated_at=datetime('now')")
                values.append(role_id)
                conn.execute(f"UPDATE role_profiles SET {', '.join(fields)} WHERE id=?", values)
                conn.commit()
        finally:
            conn.close()

    @staticmethod
    def delete(role_id):
        conn = get_db()
        try:
            conn.execute("DELETE FROM role_profiles WHERE id=?", (role_id,))
            conn.commit()
        finally:
            conn.close()
