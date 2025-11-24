"""Import accounts from data/account.json into the SQLite DB used by the server.

Usage: python scripts/import_accounts.py
"""
import json
import sys
from pathlib import Path


# repo root is the parent of scripts/
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from src.server.database import Database
from src.server.auth import hash_password


def main():
    repo_root = HERE
    data_file = repo_root / "data" / "account.json"
    db_path = repo_root / "db" / "game.db"
    schema_path = repo_root / "db" / "schema.sql"

    if not data_file.exists():
        print(f"account.json not found: {data_file}")
        sys.exit(1)

    with data_file.open("r", encoding="utf-8") as fh:
        accounts = json.load(fh)

    db = Database(str(db_path))
    conn = db.connect(initialize_schema=str(schema_path))

    inserted = []
    with db.transaction():
        for a in accounts:
            username = a.get("username")
            password = a.get("password")
            if not username or password is None:
                print(f"skipping invalid account entry: {a}")
                continue
            # check exists
            cur = conn.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cur.fetchone():
                print(f"user already exists, skipping: {username}")
                continue
            ph = hash_password(str(password))
            conn.execute("INSERT INTO users (username, password_hash, gold) VALUES (?, ?, ?)", (username, ph, 10))
            inserted.append(username)

    if inserted:
        print(f"Inserted users: {', '.join(inserted)}")
    else:
        print("No new users inserted.")

    # print current users
    cur = conn.execute("SELECT id, username, gold, created_at FROM users ORDER BY id")
    rows = cur.fetchall()
    print("Current users in DB:")
    for r in rows:
        print(dict(r))


if __name__ == "__main__":
    main()
