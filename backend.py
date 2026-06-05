from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
import logging
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "submissions.db"
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "png", "jpg", "jpeg", "zip"}

app = Flask(__name__, static_folder=".", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB upload limit

# Basic logging
logging.basicConfig(level=logging.INFO)


@app.after_request
def add_cors_headers(response):
    # Add permissive CORS headers to assist development/testing from different origins
    response.headers.setdefault("Access-Control-Allow-Origin", "*")
    response.headers.setdefault("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
    response.headers.setdefault(
        "Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With"
    )
    return response


def init_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS contact_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            message TEXT NOT NULL,
            submitted_at TEXT NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS quote_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            service_type TEXT NOT NULL,
            details TEXT,
            file_name TEXT,
            submitted_at TEXT NOT NULL
        )
        """
    )
    cursor.execute("PRAGMA table_info(quote_requests)")
    quote_cols = [row[1] for row in cursor.fetchall()]
    if "email" not in quote_cols:
        cursor.execute("ALTER TABLE quote_requests ADD COLUMN email TEXT")
    conn.commit()
    conn.close()


def current_iso_time() -> str:
    return datetime.now(timezone.utc).isoformat()


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def fetch_all_submissions() -> dict[str, list[dict[str, str | int | None]]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, name, email, message, submitted_at
        FROM contact_messages
        ORDER BY id DESC
        """
    )
    contacts = [dict(row) for row in cursor.fetchall()]

    cursor.execute(
        """
        SELECT id, name, email, service_type, details, file_name, submitted_at
        FROM quote_requests
        ORDER BY id DESC
        """
    )
    quotes = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return {"contacts": contacts, "quotes": quotes}


@app.route("/")
def root():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/admin")
def admin_dashboard():
    return send_from_directory(BASE_DIR, "admin.html")


@app.route("/api/contact", methods=["POST"])
def submit_contact():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip()
    message = (payload.get("message") or "").strip()

    if not name or not email or not message:
        return jsonify({"ok": False, "error": "Name, email, and message are required."}), 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO contact_messages (name, email, message, submitted_at)
        VALUES (?, ?, ?, ?)
        """,
        (name, email, message, current_iso_time()),
    )
    conn.commit()
    conn.close()

    return jsonify({"ok": True, "message": "Message submitted successfully."})


@app.route("/api/quote", methods=["POST"])
def submit_quote():
    try:
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip()
        service_type = (request.form.get("serviceType") or "").strip()
        details = (request.form.get("details") or "").strip()
        uploaded = request.files.get("fileUpload")
        saved_file_name: str | None = None

        logging.info("Received quote submission: name=%s service=%s file=%s", name, service_type, getattr(uploaded, 'filename', None))

        if not name or not service_type:
            return jsonify({"ok": False, "error": "Name and service type are required."}), 400

        if uploaded and uploaded.filename:
            original_name = secure_filename(uploaded.filename)
            if not allowed_file(original_name):
                allowed_list = ", ".join(sorted(ALLOWED_EXTENSIONS))
                return jsonify({"ok": False, "error": f"Unsupported file type. Allowed: {allowed_list}"}), 400
            stamped_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{original_name}"
            uploaded.save(UPLOAD_DIR / stamped_name)
            saved_file_name = stamped_name

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO quote_requests (name, email, service_type, details, file_name, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, email or None, service_type, details, saved_file_name, current_iso_time()),
        )
        conn.commit()
        conn.close()

        return jsonify({"ok": True, "message": "Quote request submitted successfully."})
    except Exception as exc:
        logging.exception("Error handling quote submission")
        return jsonify({"ok": False, "error": "Internal server error."}), 500


@app.route("/api/admin/submissions", methods=["GET"])
def admin_submissions():
    data = fetch_all_submissions()
    return jsonify({"ok": True, **data})


@app.route("/uploads/<path:filename>")
def uploaded_file(filename: str):
    # Serve uploaded files from the uploads directory
    return send_from_directory(UPLOAD_DIR, filename)


init_storage()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
