from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from pathlib import Path
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
DB_PATH = INSTANCE_DIR / "contacts.db"


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config["SECRET_KEY"] = "change-this-to-a-secure-secret-key"

    INSTANCE_DIR.mkdir(exist_ok=True)
    init_db()

    @app.context_processor
    def inject_year():
        return {"current_year": datetime.now().year}

    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.route("/services")
    def services():
        return render_template("services.html")

    @app.route("/portfolio")
    def portfolio():
        return render_template("portfolio.html")

    @app.route("/contact", methods=["GET", "POST"])
    def contact():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip()
            phone = request.form.get("phone", "").strip()
            business = request.form.get("business", "").strip()
            service = request.form.get("service", "").strip()
            message = request.form.get("message", "").strip()

            if not name or not email or not message:
                flash("Name, email, and message are required.", "error")
                return redirect(url_for("contact"))

            save_contact(name, email, phone, business, service, message)
            flash("Your message has been submitted successfully.", "success")
            return redirect(url_for("thankyou"))

        return render_template("contact.html")

    @app.route("/thank-you")
    def thankyou():
        return render_template("thankyou.html")

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "").strip()

            if not name or not email or not password:
                flash("All fields are required.", "error")
                return redirect(url_for("signup"))

            existing_user = get_user_by_email(email)
            if existing_user:
                flash("Account already exists. Please login.", "error")
                return redirect(url_for("login"))

            password_hash = generate_password_hash(password)
            create_user(name, email, password_hash)

            flash("Signup successful. Welcome to AR Infotech.", "success")
            return redirect(url_for("welcome"))

        return render_template("signup.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "").strip()

            user = get_user_by_email(email)

            if not user:
                flash("User does not exist. Please sign up first.", "error")
                return redirect(url_for("signup"))

            if not check_password_hash(user["password_hash"], password):
                flash("Invalid password.", "error")
                return redirect(url_for("login"))

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["is_admin"] = user["is_admin"]

            log_login(
                user_id=user["id"],
                ip_address=request.remote_addr or "",
                user_agent=request.headers.get("User-Agent", "")
            )

            flash(f"Welcome back, {user['name']}.", "success")

            if user["is_admin"] == 1:
                return redirect(url_for("admin_dashboard"))

            return redirect(url_for("dashboard"))

        return render_template("login.html")
    
    @app.route("/welcome")
    def welcome():
        return render_template("welcome.html")
    
    @app.route("/dashboard")
    def dashboard():
        if "user_id" not in session:
            flash("Please login first.", "error")
            return redirect(url_for("login"))

        return render_template("dashboard.html", user_name=session.get("user_name"))

    @app.route("/logout")
    def logout():
        session.clear()
        flash("You have been logged out.", "success")
        return redirect(url_for("home"))
    
    @app.before_request
    def track_visitor():
        from flask import request, session

        if request.endpoint == "static":
            return

        user_id = session.get("user_id")
        log_page_visit(
            user_id=user_id,
            page_url=request.path,
            endpoint=request.endpoint or "",
            method=request.method,
            ip_address=request.remote_addr or "",
            user_agent=request.headers.get("User-Agent", "")
        )
    
    @app.route("/admin")
    def admin_dashboard():
        if "user_id" not in session or session.get("is_admin") != 1:
            flash("Admin access only.", "error")
            return redirect(url_for("login"))

        users = get_all_users()
        contacts = get_all_contacts()
        logins = get_login_history()
        visits = get_page_visits()

        return render_template(
            "admin_dashboard.html",
            users=users,
            contacts=contacts,
            logins=logins,
            visits=visits
        )

    return app

def create_user(name: str, email: str, password_hash: str, is_admin: int = 0) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (name, email, password_hash, is_admin)
        VALUES (?, ?, ?, ?)
    """, (name, email, password_hash, is_admin))
    conn.commit()
    conn.close()


def get_user_by_email(email: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    return user


def get_user_by_id(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user


def log_login(user_id: int, ip_address: str, user_agent: str) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO login_history (user_id, ip_address, user_agent)
        VALUES (?, ?, ?)
    """, (user_id, ip_address, user_agent))
    conn.commit()
    conn.close()


def log_page_visit(user_id, page_url: str, endpoint: str, method: str, ip_address: str, user_agent: str) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO page_visits (user_id, page_url, endpoint, method, ip_address, user_agent)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, page_url, endpoint, method, ip_address, user_agent))
    conn.commit()
    conn.close()


def get_all_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, email, is_admin, created_at
        FROM users
        ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_all_contacts():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, email, phone, business, service, message, created_at
        FROM contacts
        ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_login_history():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT lh.id, u.name, u.email, lh.login_time, lh.ip_address, lh.user_agent
        FROM login_history lh
        JOIN users u ON u.id = lh.user_id
        ORDER BY lh.id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_page_visits():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT pv.id, u.name, u.email, pv.page_url, pv.endpoint, pv.method,
               pv.visited_at, pv.ip_address, pv.user_agent
        FROM page_visits pv
        LEFT JOIN users u ON u.id = pv.user_id
        ORDER BY pv.id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            business TEXT,
            service TEXT,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS login_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            user_agent TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS page_visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            page_url TEXT NOT NULL,
            endpoint TEXT,
            method TEXT,
            visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            user_agent TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()

def save_contact(name: str, email: str, phone: str, business: str, service: str, message: str) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO contacts (name, email, phone, business, service, message)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, email, phone, business, service, message))
    conn.commit()
    conn.close()


def create_user(name: str, email: str, password_hash: str) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (name, email, password_hash)
        VALUES (?, ?, ?)
    """, (name, email, password_hash))
    conn.commit()
    conn.close()


def get_user_by_email(email: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    return user


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)