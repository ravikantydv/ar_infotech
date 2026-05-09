import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash

DB_PATH = Path(__file__).resolve().parent / "instance" / "contacts.db"

name = "Admin"
email = "admin@ar_infotech.com"
password = "Admin@123"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
    INSERT INTO users (name, email, password_hash, is_admin)
    VALUES (?, ?, ?, ?)
""", (name, email, generate_password_hash(password), 1))

conn.commit()
conn.close()

print("Admin account created successfully.")