import sqlite3
from datetime import datetime

DATABASE_NAME = "gamewatch.db"

def test_migration():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("PRAGMA table_info(users)")
    cols = [r["name"] for r in c.fetchall()]
    if "lounge_code" not in cols:
        c.execute("ALTER TABLE users ADD COLUMN lounge_code TEXT")
    if "owner_id" not in cols:
        c.execute("ALTER TABLE users ADD COLUMN owner_id INTEGER")
    if "joined_lounge_code" not in cols:
        c.execute("ALTER TABLE users ADD COLUMN joined_lounge_code TEXT")

    c.execute("PRAGMA table_info(tvs)")
    tv_cols = [r["name"] for r in c.fetchall()]
    if "owner_id" not in tv_cols:
        c.execute("ALTER TABLE tvs ADD COLUMN owner_id INTEGER DEFAULT 20")

    c.execute("""
        CREATE TABLE IF NOT EXISTS lounges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            lounge_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            address TEXT,
            city TEXT DEFAULT 'Addis Ababa',
            phone TEXT,
            email TEXT,
            rate_per_game REAL DEFAULT 25,
            total_tvs INTEGER DEFAULT 2,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)

    c.execute("SELECT count(*) FROM lounges")
    if c.fetchone()[0] == 0:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("SELECT id FROM users WHERE role = 'OWNER' ORDER BY id ASC LIMIT 1")
        row = c.fetchone()
        owner_id = row["id"] if row else 20
        c.execute("""
            INSERT INTO lounges (owner_id, lounge_code, name, address, city, phone, email, rate_per_game, total_tvs, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (owner_id, "GW-BOLE-101", "Bole Medhanialem PlayStation Arena", "Bole Medhanialem, Behind Edna Mall", "Addis Ababa", "+251 900 000000", "support@gamewatch.et", 25, 2, now_str))
        c.execute("UPDATE users SET lounge_code = 'GW-BOLE-101' WHERE id = ?", (owner_id,))

        c.execute("""
            INSERT INTO lounges (owner_id, lounge_code, name, address, city, phone, email, rate_per_game, total_tvs, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (owner_id, "GW-PIAZZA-202", "Piazza Elite Gaming Lounge", "Piazza, Near Cathedral", "Addis Ababa", "+251 911 223344", "piazza@gamewatch.et", 30, 4, now_str))

        c.execute("""
            INSERT INTO lounges (owner_id, lounge_code, name, address, city, phone, email, rate_per_game, total_tvs, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (owner_id, "GW-CMC-303", "CMC Cyber Arena & Lounge", "CMC Michael, Tsehay Real Estate", "Addis Ababa", "+251 922 334455", "cmc@gamewatch.et", 25, 3, now_str))

    conn.commit()

    c.execute("SELECT * FROM lounges")
    lounges = [dict(r) for r in c.fetchall()]
    print(f"Successfully migrated schema! Found {len(lounges)} lounges:")
    for l in lounges:
        print(f" - [{l['lounge_code']}] {l['name']} (Owner #{l['owner_id']}, {l['total_tvs']} TVs)")

    conn.close()

if __name__ == "__main__":
    test_migration()
