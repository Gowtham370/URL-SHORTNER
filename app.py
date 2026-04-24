from flask import Flask, redirect, request, jsonify, render_template
from models import URL, Base
from utils import encode_base62
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

app = Flask(__name__)

# 🔹 Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///urls.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)

def get_session():
    return Session()

# 🔹 Dashboard UI
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/create")
def create_page():
    return render_template("create.html")

# 🔹 Home route
@app.route("/")
def home():
    return jsonify({"message": "URL Shortener Running 🚀"})

# 🔹 Create short URL
@app.route("/shorten", methods=["POST"])
def shorten():
    session = get_session()
    data = request.get_json()

    if not data or "url" not in data:
        return jsonify({"error": "URL is required"}), 400

    original_url = data.get("url")
    custom_code = data.get("custom")

    # 🔥 Custom short code
    if custom_code:
        existing = session.query(URL).filter_by(short_code=custom_code).first()
        if existing:
            return jsonify({"error": "Custom code already taken"}), 400

        new_url = URL(
            original_url=original_url,
            short_code=custom_code
        )
        session.add(new_url)
        session.commit()

        return jsonify({
            "short_url": f"{request.host_url}{custom_code}"
        })

    # 🔹 Auto-generated short code
    new_url = URL(original_url=original_url)
    session.add(new_url)
    session.commit()

    short_code = encode_base62(new_url.id)
    new_url.short_code = short_code
    session.commit()

    return jsonify({
        "short_url": f"{request.host_url}{short_code}"
    })

# 🔥 Redirect + Analytics (NO Redis for now)
@app.route("/<short_code>")
def redirect_url(short_code):
    session = get_session()

    url = session.query(URL).filter_by(short_code=short_code).first()

    if not url:
        return "URL not found", 404

    # 🔥 Update analytics
    url.clicks += 1
    url.last_accessed = datetime.utcnow()
    session.commit()

    return redirect(url.original_url)

# 🔹 Stats API
@app.route("/stats/<short_code>")
def stats(short_code):
    session = get_session()

    url = session.query(URL).filter_by(short_code=short_code).first()

    if not url:
        return jsonify({"error": "Not found"}), 404

    return jsonify({
        "short_code": url.short_code,
        "original_url": url.original_url,
        "clicks": url.clicks,
        "created_at": str(url.created_at),
        "last_accessed": str(url.last_accessed) if url.last_accessed else None
    })

# 🔹 Get all URLs
@app.route("/all")
def get_all_urls():
    session = get_session()

    urls = session.query(URL).all()

    result = []
    for url in urls:
        result.append({
            "short_code": url.short_code,
            "original_url": url.original_url,
            "clicks": url.clicks,
            "created_at": str(url.created_at),
            "last_accessed": str(url.last_accessed) if url.last_accessed else None
        })

    return jsonify(result)

# 🔹 Run app
if __name__ == "__main__":
    app.run(debug=True)