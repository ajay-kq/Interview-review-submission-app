import os
from datetime import datetime
from functools import wraps
from pathlib import Path

from bson.objectid import ObjectId
from dotenv import load_dotenv
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for, send_file
from flask_talisman import Talisman
from flask_wtf.csrf import CSRFProtect
from pymongo import MongoClient
from werkzeug.security import check_password_hash, generate_password_hash

from email_utils import default_email_subject, send_review_email
from pdf_report import build_pdf_report
from webhook import send_to_google_chat

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-to-a-secure-random-key")

# Security enhancements (VAPT)
csrf = CSRFProtect(app)
csp = {
    'default-src': [
        '\'self\'',
        'https://fonts.googleapis.com',
        'https://fonts.gstatic.com',
        'https://cdn.jsdelivr.net',
        'https://cdnjs.cloudflare.com'
    ],
    'script-src': [
        '\'self\'',
        'https://cdn.jsdelivr.net',
        'https://cdnjs.cloudflare.com',
        '\'unsafe-inline\''
    ],
    'style-src': [
        '\'self\'',
        'https://fonts.googleapis.com',
        'https://cdn.jsdelivr.net',
        'https://cdnjs.cloudflare.com',
        '\'unsafe-inline\''
    ],
    'img-src': ['\'self\'', 'data:']
}
Talisman(app, content_security_policy=csp, force_https=os.environ.get("FLASK_ENV") != "development")

# Secure Session Cookies
app.config.update(
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") != "development",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)

BASE_DIR = Path(__file__).resolve().parent
# Vercel uses a read-only filesystem; use /tmp for reports
if os.environ.get("VERCEL"):
    REPORTS_DIR = Path("/tmp/reports")
else:
    REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# Database Connection
MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/interview_submission_db")
mongo_client = MongoClient(MONGODB_URI)

try:
    db = mongo_client.get_default_database()
except Exception:
    db = mongo_client["interview_submission_db"]

def init_db():
    if db.users.count_documents({"username": "admin"}) == 0:
        db.users.insert_one({
            "username": "admin",
            "password_hash": generate_password_hash("admin")
        })

    if db.skills.count_documents({}) == 0:
        default_skills = [
            {"key": "aws", "label": "AWS"},
            {"key": "windows", "label": "Windows"},
            {"key": "linux", "label": "Linux"},
            {"key": "virtualization", "label": "Virtualization"},
            {"key": "storage", "label": "Storage"},
            {"key": "networking", "label": "Basic - Networking"},
            {"key": "devops", "label": "DevOps"},
            {"key": "cloud", "label": "Cloud"},
            {"key": "scenario_based", "label": "Scenario-Based"},
            {"key": "scenario_troubleshooting", "label": "Scenario Troubleshooting"},
            {"key": "general_it_admin", "label": "General - IT Administration"},
            {"key": "basic_it_admin", "label": "Basic - IT Administration"},
            {"key": "infra_mgmt", "label": "Infrastructure Management"},
        ]
        db.skills.insert_many(default_skills)

    config_defaults = {
        "webhook_url": "",
        "smtp_server": "",
        "smtp_port": "587",
        "smtp_username": "",
        "smtp_password": "",
        "email_from": "",
        "email_from_name": "",
        "email_to_default": "",
        "email_cc_default": "",
        "email_bcc_default": "",
        "email_note_reply_to": "",
        "email_regards_name": "",
    }
    
    if db.app_config.count_documents({"_id": "config"}) == 0:
        config_defaults["_id"] = "config"
        db.app_config.insert_one(config_defaults)

def get_config(key, default=""):
    config = db.app_config.find_one({"_id": "config"})
    if config and key in config:
        return config[key]
    return default

def set_config(key, value):
    db.app_config.update_one(
        {"_id": "config"},
        {"$set": {key: value}},
        upsert=True
    )

def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper

def normalize_candidate_name(name: str) -> str:
    name = (name or "").strip()
    if not name:
        return ""

    if name.upper().startswith("MR. "):
        return "Mr. " + name[4:].strip()
    if name.upper() == "MR.":
        return "Mr."
    if not name.startswith("Mr. "):
        return f"Mr. {name}"
    return name

def collect_selected_skills(form_data, skills):
    selected_skill_rows = []
    for skill in skills:
        selected = form_data.get(f"{skill['key']}_selected")
        rating = form_data.get(f"{skill['key']}_rating")
        if selected == "1" and rating:
            rating_int = int(rating)
            selected_skill_rows.append({
                "skill_key": skill["key"],
                "skill_label": skill["label"],
                "rating": rating_int,
                "score_10": rating_int * 2
            })
    return selected_skill_rows

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = db.users.find_one({"username": username})
        if user and check_password_hash(user["password_hash"], password):
            session["logged_in"] = True
            session["username"] = username
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "error")
        return redirect(url_for("login"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def dashboard():
    reviews_cursor = db.reviews.find().sort([("_id", -1)])
    reviews = []
    for r in reviews_cursor:
        r["id"] = str(r["_id"])
        reviews.append(r)
    return render_template("dashboard.html", reviews=reviews)

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        current_password = request.form.get("current_password", "").strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        user = db.users.find_one({"username": session["username"]})
        
        if not check_password_hash(user["password_hash"], current_password):
            flash("Current password is incorrect.", "error")
        elif new_password != confirm_password:
            flash("New passwords do not match.", "error")
        elif len(new_password) < 6:
            flash("New password must be at least 6 characters.", "error")
        else:
            db.users.update_one(
                {"username": session["username"]},
                {"$set": {"password_hash": generate_password_hash(new_password)}}
            )
            flash("Password updated successfully.", "success")
            return redirect(url_for("profile"))

    return render_template("profile.html", username=session["username"])

@app.route("/skills", methods=["GET"])
@login_required
def manage_skills():
    skills = list(db.skills.find())
    for s in skills:
        s["id"] = str(s["_id"])
    return render_template("skills.html", skills=skills)

@app.route("/skills/add", methods=["POST"])
@login_required
def add_skill():
    key = request.form.get("key", "").strip().lower().replace(" ", "_")
    label = request.form.get("label", "").strip()

    if not key or not label:
        flash("Skill key and label are required.", "error")
        return redirect(url_for("manage_skills"))

    if db.skills.find_one({"key": key}):
        flash("Skill key already exists.", "error")
        return redirect(url_for("manage_skills"))

    db.skills.insert_one({"key": key, "label": label})
    flash("Skill added successfully.", "success")
    return redirect(url_for("manage_skills"))

@app.route("/skills/delete/<skill_id>", methods=["POST"])
@login_required
def delete_skill(skill_id):
    db.skills.delete_one({"_id": ObjectId(skill_id)})
    flash("Skill deleted successfully.", "success")
    return redirect(url_for("manage_skills"))

@app.route("/configurations", methods=["GET", "POST"])
@login_required
def configurations():
    if request.method == "POST":
        set_config("webhook_url", request.form.get("webhook_url", "").strip())
        set_config("smtp_server", request.form.get("smtp_server", "").strip())
        set_config("smtp_port", request.form.get("smtp_port", "").strip() or "587")
        set_config("smtp_username", request.form.get("smtp_username", "").strip())
        set_config("smtp_password", request.form.get("smtp_password", "").strip())
        set_config("email_from", request.form.get("email_from", "").strip())
        set_config("email_from_name", request.form.get("email_from_name", "").strip())
        set_config("email_to_default", request.form.get("email_to_default", "").strip())
        set_config("email_cc_default", request.form.get("email_cc_default", "").strip())
        set_config("email_bcc_default", request.form.get("email_bcc_default", "").strip())
        set_config("email_note_reply_to", request.form.get("email_note_reply_to", "").strip())
        set_config("email_regards_name", request.form.get("email_regards_name", "").strip())
        flash("Configurations saved successfully.", "success")

    config = db.app_config.find_one({"_id": "config"}) or {}
    
    return render_template("configurations.html", config=config)

@app.route("/reset_database", methods=["POST"])
@login_required
def reset_database():
    password = request.form.get("admin_password", "").strip()
    user = db.users.find_one({"username": session["username"]})
    
    if check_password_hash(user["password_hash"], password):
        db.reviews.delete_many({})
        db.ratings.delete_many({})  # Just in case there are lingering legacy ratings
        db.skills.delete_many({})
        db.app_config.delete_many({})
        init_db()  # Reinsert defaults
        flash("Database has been reset successfully.", "success")
    else:
        flash("Incorrect password. Database reset failed.", "error")
        
    return redirect(url_for("configurations"))

@app.route("/create")
@login_required
def create_review():
    skills = list(db.skills.find())
    return render_template("create_review.html", skills=skills)

@app.route("/submit", methods=["POST"])
@login_required
def submit_review():
    skills = list(db.skills.find())
    selected_skill_rows = collect_selected_skills(request.form, skills)

    review_doc = {
        "candidate_name": normalize_candidate_name(request.form.get("candidate_name", "")),
        "position": request.form.get("position", "").strip(),
        "interview_date": request.form.get("interview_date", "").strip(),
        "interviewer_name": request.form.get("interviewer_name", "").strip(),
        "profile_summary": request.form.get("profile_summary", "").strip(),
        "technical_evaluation": request.form.get("technical_evaluation", "").strip(),
        "observations": request.form.get("observations", "").strip(),
        "overall_assessment": request.form.get("overall_assessment", "").strip(),
        "recommendation": request.form.get("recommendation", "").strip(),
        "ratings": selected_skill_rows,
        "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    }

    db.reviews.insert_one(review_doc)

    flash("Interview review submitted successfully.", "success")
    return redirect(url_for("dashboard"))

@app.route("/edit/<review_id>")
@login_required
def edit_review(review_id):
    review = db.reviews.find_one({"_id": ObjectId(review_id)})
    
    if not review:
        flash("Candidate review not found.", "error")
        return redirect(url_for("dashboard"))

    review["id"] = str(review["_id"])
    skills = list(db.skills.find())
    
    rating_map = {row["skill_key"]: row["rating"] for row in review.get("ratings", [])}
    
    return render_template("edit_review.html", review=review, skills=skills, rating_map=rating_map)

@app.route("/update/<review_id>", methods=["POST"])
@login_required
def update_review(review_id):
    skills = list(db.skills.find())
    selected_skill_rows = collect_selected_skills(request.form, skills)

    update_fields = {
        "candidate_name": normalize_candidate_name(request.form.get("candidate_name", "")),
        "position": request.form.get("position", "").strip(),
        "interview_date": request.form.get("interview_date", "").strip(),
        "interviewer_name": request.form.get("interviewer_name", "").strip(),
        "profile_summary": request.form.get("profile_summary", "").strip(),
        "technical_evaluation": request.form.get("technical_evaluation", "").strip(),
        "observations": request.form.get("observations", "").strip(),
        "overall_assessment": request.form.get("overall_assessment", "").strip(),
        "recommendation": request.form.get("recommendation", "").strip(),
        "ratings": selected_skill_rows
    }

    db.reviews.update_one(
        {"_id": ObjectId(review_id)},
        {"$set": update_fields}
    )

    flash("Interview review updated successfully.", "success")
    return redirect(url_for("dashboard"))

@app.route("/send_webhook/<review_id>", methods=["POST"])
@login_required
def send_webhook_manual(review_id):
    review = db.reviews.find_one({"_id": ObjectId(review_id)})
    webhook_url = get_config("webhook_url", "")

    if not review:
        flash("Candidate review not found.", "error")
        return redirect(url_for("dashboard"))

    if not webhook_url:
        flash("Webhook URL is not configured. Please update it in Configurations.", "error")
        return redirect(url_for("dashboard"))

    ratings_for_webhook = [{
        "skill": r["skill_label"],
        "rating": r["rating"],
        "score_10": r["score_10"],
    } for r in review.get("ratings", [])]

    webhook_ok, webhook_msg = send_to_google_chat(
        webhook_url=webhook_url,
        candidate_name=review.get("candidate_name"),
        position=review.get("position"),
        interview_date=review.get("interview_date"),
        interviewer_name=review.get("interviewer_name"),
        selected_skills=ratings_for_webhook,
        recommendation=review.get("recommendation"),
        profile_summary=review.get("profile_summary"),
        technical_evaluation=review.get("technical_evaluation")
    )

    if webhook_ok:
        flash("Webhook sent successfully.", "success")
    else:
        flash(f"Webhook failed: {webhook_msg}", "error")

    return redirect(url_for("dashboard"))

@app.route("/email/<review_id>")
@login_required
def email_review_page(review_id):
    review = db.reviews.find_one({"_id": ObjectId(review_id)})
    
    if not review:
        flash("Candidate review not found.", "error")
        return redirect(url_for("dashboard"))

    review["id"] = str(review["_id"])
    subject = default_email_subject(review.get("candidate_name"), review.get("interview_date"))
    return render_template("email_review.html", review=review, subject=subject)

@app.route("/send_email/<review_id>", methods=["POST"])
@login_required
def send_email_manual(review_id):
    review = db.reviews.find_one({"_id": ObjectId(review_id)})
    
    smtp_server = get_config("smtp_server", "")
    smtp_port = int(get_config("smtp_port", "587") or "587")
    smtp_username = get_config("smtp_username", "")
    smtp_password = get_config("smtp_password", "")
    email_from = get_config("email_from", "")
    email_from_name = get_config("email_from_name", "")
    
    # Construct "From" field with alias if provided
    full_from = f"{email_from_name} <{email_from}>" if email_from_name else email_from

    email_to = get_config("email_to_default", "")
    email_cc = get_config("email_cc_default", "")
    email_bcc = get_config("email_bcc_default", "")
    note_reply_to = get_config("email_note_reply_to", "")
    regards_name = get_config("email_regards_name", "")

    if not review:
        flash("Candidate review not found.", "error")
        return redirect(url_for("dashboard"))

    if not smtp_server or not smtp_username or not smtp_password or not email_from or not email_to:
        flash("Email configuration is incomplete. Please update it in Configurations.", "error")
        return redirect(url_for("configurations"))

    subject = request.form.get("subject", "").strip()
    attach_pdf = request.form.get("attach_pdf") == "yes"

    pdf_path = None
    if attach_pdf:
        safe_date = (review.get("interview_date") or "no-date").replace("/", "-").replace(" ", "_")
        pdf_path = REPORTS_DIR / f"candidate_review_{safe_date}.pdf"
        build_pdf_report(review, review.get("ratings", []), pdf_path)

    ok, msg = send_review_email(
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        smtp_username=smtp_username,
        smtp_password=smtp_password,
        email_from=full_from,
        email_to=email_to,
        email_cc=email_cc,
        email_bcc=email_bcc,
        subject=subject,
        review=review,
        ratings=review.get("ratings", []),
        attachment_path=pdf_path,
        note_reply_to=note_reply_to,
        regards_name=regards_name
    )

    if ok:
        flash("Email sent successfully.", "success")
    else:
        flash(f"Email sending failed: {msg}", "error")

    return redirect(url_for("dashboard"))

@app.route("/delete/<review_id>", methods=["POST"])
@login_required
def delete_review(review_id):
    db.reviews.delete_one({"_id": ObjectId(review_id)})
    flash("Candidate review deleted successfully.", "success")
    return redirect(url_for("dashboard"))

@app.route("/pdf/<review_id>")
@login_required
def download_pdf(review_id):
    review = db.reviews.find_one({"_id": ObjectId(review_id)})
    
    if not review:
        flash("Candidate review not found.", "error")
        return redirect(url_for("dashboard"))

    candidate = (review.get("candidate_name") or "candidate").replace(" ", "_").replace(".", "")
    safe_date = (review.get("interview_date") or "no-date").replace("/", "-").replace(" ", "_")

    pdf_path = REPORTS_DIR / f"{candidate}_review_{safe_date}.pdf"
    build_pdf_report(review, review.get("ratings", []), pdf_path)

    return send_file(pdf_path, as_attachment=True)

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)