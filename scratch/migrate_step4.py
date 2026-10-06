import sqlite3
from datetime import datetime

def run_migration():
    conn = sqlite3.connect("gamewatch.db")
    c = conn.cursor()

    # 1. Update lounges table schema
    c.execute("PRAGMA table_info(lounges)")
    lounge_cols = [r[1] for r in c.fetchall()]
    if "area" not in lounge_cols:
        c.execute("ALTER TABLE lounges ADD COLUMN area TEXT DEFAULT 'Bole'")
    if "latitude" not in lounge_cols:
        c.execute("ALTER TABLE lounges ADD COLUMN latitude REAL DEFAULT 9.01")
    if "longitude" not in lounge_cols:
        c.execute("ALTER TABLE lounges ADD COLUMN longitude REAL DEFAULT 38.76")

    # 2. Update existing lounges with real areas and coordinates
    # Owner 50 (abyman) -> 4 Kilo
    c.execute("""
        UPDATE lounges 
        SET name = 'Abyman GameZone', 
            area = '4 Kilo', 
            address = 'Addis Ababa, 4 Kilo (near AAU King George Street)', 
            latitude = 9.0345, 
            longitude = 38.7625,
            phone = '0921615614',
            email = 'abyman24680@gmail.com'
        WHERE owner_id = 50 OR lounge_code = 'GW-OWNER-050'
    """)

    # Bole lounge
    c.execute("""
        UPDATE lounges 
        SET area = 'Bole', latitude = 8.9952, longitude = 38.7885
        WHERE lounge_code = 'GW-BOLE-101'
    """)
    # Piazza lounge
    c.execute("""
        UPDATE lounges 
        SET area = 'Piazza', latitude = 9.0360, longitude = 38.7512
        WHERE lounge_code = 'GW-PIAZZA-202'
    """)
    # CMC lounge
    c.execute("""
        UPDATE lounges 
        SET area = 'CMC', latitude = 9.0220, longitude = 38.8470
        WHERE lounge_code = 'GW-CMC-303'
    """)

    # Add 4 Kilo seed lounge if not present
    c.execute("SELECT id FROM lounges WHERE lounge_code = 'GW-4KILO-404'")
    if not c.fetchone():
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""
            INSERT INTO lounges (owner_id, lounge_code, name, address, area, city, phone, email, rate_per_game, total_tvs, latitude, longitude, created_at)
            VALUES (20, 'GW-4KILO-404', '4 Kilo Campus Gaming Hub', 'Arat Kilo, Near Science Faculty', '4 Kilo', 'Addis Ababa', '+251 933 445566', '4kilo@gamewatch.et', 25, 3, 9.0348, 38.7620, ?)
        """, (now_str,))

    # 3. Create events table
    c.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            lounge_id INTEGER,
            title TEXT NOT NULL,
            game TEXT DEFAULT 'EA FC 25',
            event_date TEXT NOT NULL,
            event_time TEXT NOT NULL,
            entry_fee REAL DEFAULT 50,
            max_participants INTEGER DEFAULT 16,
            current_participants INTEGER DEFAULT 0,
            prize_pool TEXT DEFAULT '2,000 ETB',
            status TEXT DEFAULT 'UPCOMING',
            rules TEXT,
            created_at TEXT NOT NULL
        )
    """)

    # 4. Create event_registrations table
    c.execute("""
        CREATE TABLE IF NOT EXISTS event_registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            customer_phone TEXT,
            user_id INTEGER,
            fee_paid INTEGER DEFAULT 0,
            fee_amount REAL DEFAULT 0,
            payment_method TEXT DEFAULT 'CASH',
            checked_in INTEGER DEFAULT 0,
            registered_at TEXT NOT NULL,
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
        )
    """)

    # 5. Create promotions table
    c.execute("""
        CREATE TABLE IF NOT EXISTS promotions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            lounge_id INTEGER,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            badge_text TEXT DEFAULT 'SPECIAL OFFER',
            promo_rate REAL DEFAULT 20,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)

    # Seed sample event for Owner 50 if empty
    c.execute("SELECT count(*) FROM events")
    if c.fetchone()[0] == 0:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""
            INSERT INTO events (owner_id, lounge_id, title, game, event_date, event_time, entry_fee, max_participants, current_participants, prize_pool, status, rules, created_at)
            VALUES (50, 10, '4 Kilo EA FC 25 Showdown', 'EA FC 25', 'This Saturday', '3:00 PM', 50, 16, 5, '3,500 ETB', 'UPCOMING', '1v1 Knockout tournament. Tactical defending allowed.', ?)
        """, (now_str,))
        ev_id = c.lastrowid
        # Seed a few participants
        participants = [
            ("Dawit Tadesse", "0911223344", 1, 50, "CASH", 1),
            ("Yonas Bekele", "0922334455", 1, 50, "TELEBIRR", 1),
            ("Natnael K.", "0933445566", 0, 50, "CASH", 0),
            ("Ermias M.", "0944556677", 1, 50, "CASH", 0),
            ("Biniam S.", "0955667788", 0, 50, "TELEBIRR", 0),
        ]
        for name, phone, paid, fee, meth, cin in participants:
            c.execute("""
                INSERT INTO event_registrations (event_id, customer_name, customer_phone, fee_paid, fee_amount, payment_method, checked_in, registered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (ev_id, name, phone, paid, fee, meth, cin, now_str))

    # Seed sample promotion for Owner 50 if empty
    c.execute("SELECT count(*) FROM promotions")
    if c.fetchone()[0] == 0:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""
            INSERT INTO promotions (owner_id, lounge_id, title, description, badge_text, promo_rate, is_active, created_at)
            VALUES (50, 10, 'Play for only 15 ETB / Match!', 'Monday – Friday before 4:00 PM (Regular: 25 ETB)', '🔥 HAPPY HOUR SPECIAL', 15, 1, ?)
        """, (now_str,))

    conn.commit()
    conn.close()
    print("Migration completed successfully!")

if __name__ == "__main__":
    run_migration()
