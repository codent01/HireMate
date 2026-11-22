import requests
import json
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup


def search_jobs(query, location="", work_model="", experience="", page=1):
    """Search jobs from multiple free sources."""
    jobs = []
    jobs.extend(_search_remotive(query) if work_model == "remote" else [])
    jobs.extend(_search_github_jobs(query, location))
    jobs.extend(_search_findwork(query, location))

    if not jobs:
        jobs = _generate_sample_jobs(query, location, work_model, experience)

    if work_model:
        jobs = [j for j in jobs if work_model.lower() in j.get("work_model", "").lower()] or jobs

    start = (page - 1) * 20
    return jobs[start:start + 20]


def _search_remotive(query):
    try:
        resp = requests.get(
            "https://remotive.com/api/remote-jobs",
            params={"search": query, "limit": 20},
            timeout=10,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        jobs = []
        for j in data.get("jobs", [])[:20]:
            jobs.append({
                "title": j.get("title", ""),
                "company": j.get("company_name", ""),
                "location": j.get("candidate_required_location", "Remote"),
                "work_model": "Remote",
                "salary": j.get("salary", "Not disclosed"),
                "description": j.get("description", "")[:500],
                "url": j.get("url", ""),
                "source": "Remotive",
                "posted": j.get("publication_date", ""),
            })
        return jobs
    except Exception:
        return []


def _search_github_jobs(query, location=""):
    try:
        params = {"description": query}
        if location:
            params["location"] = location
        resp = requests.get(
            "https://jobs.github.com/positions.json",
            params=params,
            timeout=10,
        )
        if resp.status_code != 200:
            return []
        jobs = []
        for j in resp.json()[:20]:
            jobs.append({
                "title": j.get("title", ""),
                "company": j.get("company", ""),
                "location": j.get("location", ""),
                "work_model": "Remote" if "remote" in j.get("location", "").lower() else "On-site",
                "salary": "Not disclosed",
                "description": BeautifulSoup(j.get("description", ""), "html.parser").get_text()[:500],
                "url": j.get("url", ""),
                "source": "GitHub Jobs",
                "posted": j.get("created_at", ""),
            })
        return jobs
    except Exception:
        return []


def _search_findwork(query, location=""):
    try:
        resp = requests.get(
            "https://findwork.dev/api/jobs/",
            params={"search": query, "location": location},
            headers={"Accept": "application/json"},
            timeout=10,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        jobs = []
        for j in data.get("results", [])[:20]:
            jobs.append({
                "title": j.get("role", ""),
                "company": j.get("company_name", ""),
                "location": j.get("location", ""),
                "work_model": "Remote" if j.get("remote") else "On-site",
                "salary": "Not disclosed",
                "description": (j.get("text") or "")[:500],
                "url": j.get("url", ""),
                "source": "FindWork",
                "posted": j.get("date_posted", ""),
            })
        return jobs
    except Exception:
        return []


def _generate_sample_jobs(query, location, work_model, experience):
    companies = [
        ("Google", "Mountain View, CA"), ("Microsoft", "Redmond, WA"),
        ("Amazon", "Seattle, WA"), ("Apple", "Cupertino, CA"),
        ("Meta", "Menlo Park, CA"), ("Netflix", "Los Gatos, CA"),
        ("Stripe", "San Francisco, CA"), ("Shopify", "Remote"),
        ("Spotify", "Stockholm / Remote"), ("Atlassian", "Sydney / Remote"),
        ("Razorpay", "Bangalore, India"), ("Flipkart", "Bangalore, India"),
        ("Infosys", "Bangalore, India"), ("TCS", "Mumbai, India"),
        ("Zomato", "Gurgaon, India"), ("PhonePe", "Bangalore, India"),
        ("CRED", "Bangalore, India"), ("Swiggy", "Bangalore, India"),
        ("OpenAI", "San Francisco, CA"), ("Anthropic", "San Francisco, CA"),
    ]
    models = ["Remote", "Hybrid", "On-site"]
    salaries = ["$80K-$120K", "$100K-$150K", "$120K-$180K", "$150K-$220K",
                "INR 12-20 LPA", "INR 18-30 LPA", "INR 25-45 LPA", "Not disclosed"]

    jobs = []
    for i, (company, loc) in enumerate(companies):
        wm = work_model if work_model else models[i % 3]
        jobs.append({
            "title": f"{query or 'Software Engineer'}" if i % 3 == 0 else
                     f"Senior {query or 'Software Engineer'}" if i % 3 == 1 else
                     f"Lead {query or 'Software Engineer'}",
            "company": company,
            "location": location if location else loc,
            "work_model": wm,
            "salary": salaries[i % len(salaries)],
            "description": f"We are looking for a talented {query or 'professional'} to join {company}. "
                          f"You will work on cutting-edge projects and collaborate with world-class teams. "
                          f"Requirements include strong problem-solving skills and relevant experience.",
            "url": f"https://careers.{company.lower().replace(' ', '')}.com/jobs/{i+1}",
            "source": "Sample",
            "posted": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"),
        })
    return jobs
