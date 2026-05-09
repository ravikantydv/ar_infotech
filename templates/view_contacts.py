import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "instance" / "contacts.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("SELECT id, name, email, phone, business, service, message, created_at FROM contacts ORDER BY id DESC")
rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()