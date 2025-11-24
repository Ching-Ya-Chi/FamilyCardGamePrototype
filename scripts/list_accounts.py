"""List accounts stored in the SQLite DB.

Usage: python scripts/list_accounts.py
"""
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from src.server.database import Database


def main():
    repo_root = HERE
    db_path = repo_root / "game.db"

    if not db_path.exists():
        print(f"Database not found: {db_path}")
        sys.exit(1)

    db = Database(str(db_path))
    conn = db.connect()

    try:
        cur = conn.execute("SELECT id, username, gold, created_at FROM users ORDER BY id")
    except Exception as e:
        print("Error querying users table:", e)
        sys.exit(1)

    rows = cur.fetchall()
    if not rows:
        print("No users found in DB.")
        return

    print("Users in DB:")
    for r in rows:
        print(dict(r))


if __name__ == "__main__":
    main()
