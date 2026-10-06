import sqlite3
from datetime import datetime


DATABASE_NAME = "gamewatch.db"


def get_connection():
    return sqlite3.connect(DATABASE_NAME)


def initialize_database():

    connection = get_connection()

    cursor = connection.cursor()


    # --------------------------------
    # TVS
    # --------------------------------

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tvs (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        camera_id INTEGER DEFAULT 1,
        active INTEGER DEFAULT 0
    )
    """)


    # --------------------------------
    # SESSIONS
    # --------------------------------

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        tv_id INTEGER NOT NULL,

        start_time TEXT NOT NULL,

        end_time TEXT,

        completed_games INTEGER DEFAULT 0,

        status TEXT DEFAULT 'ACTIVE',

        FOREIGN KEY (tv_id) REFERENCES tvs(id)
    )
    """)


    # --------------------------------
    # USERS (Authentication & Role Source of Truth)
    # --------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        password_hash TEXT,
        auth_provider TEXT DEFAULT 'email',
        google_id TEXT,
        role TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        last_login_at TEXT,
        status TEXT DEFAULT 'ACTIVE'
    )
    """)

    # --------------------------------
    # LOUNGE CONFIG (Dynamic business settings)
    # --------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lounge_config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)

    # Populate default config if not present
    default_configs = [
        ("lounge_name", "GameWatch Lounge"),
        ("price_per_game", "25"),
        ("currency", "ETB"),
        ("payment_methods", "CASH,TELEBIRR,CBE"),
        ("telebirr_account_name", "Lounge Cashier"),
        ("telebirr_phone", ""),
        ("cbe_account_name", "Lounge Cashier"),
        ("cbe_account_number", ""),
        ("contact_phone", "+251 900 000000"),
        ("contact_email", "support@gamewatch.et"),
        ("contact_address", "Addis Ababa, Ethiopia")
    ]
    cursor.executemany("""
        INSERT OR IGNORE INTO lounge_config (key, value) VALUES (?, ?)
    """, default_configs)

    # --------------------------------
    # TRANSACTIONS
    # --------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER,
        tv_id INTEGER NOT NULL,
        completed_games INTEGER DEFAULT 0,
        completed_games_total REAL DEFAULT 0,
        unfinished_game_charge REAL DEFAULT 0,
        price_per_game REAL DEFAULT 25,
        discount REAL DEFAULT 0,
        subtotal REAL DEFAULT 0,
        total REAL NOT NULL,
        payment_method TEXT DEFAULT 'CASH',
        amount_received REAL DEFAULT 0,
        change_given REAL DEFAULT 0,
        payment_reference TEXT,
        payment_status TEXT DEFAULT 'PAID',
        clerk_name TEXT,
        customer_name TEXT,
        notes TEXT,
        adjustment_reason TEXT,
        payment_proof TEXT,
        checkout_time TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES sessions(id),
        FOREIGN KEY (tv_id) REFERENCES tvs(id)
    )
    """)

    # Check and add missing columns if transactions table already existed from earlier schema
    cursor.execute("PRAGMA table_info(transactions)")
    existing_cols = [row[1] for row in cursor.fetchall()]
    new_cols = [
        ("price_per_game", "REAL DEFAULT 25"),
        ("discount", "REAL DEFAULT 0"),
        ("subtotal", "REAL DEFAULT 0"),
        ("amount_received", "REAL DEFAULT 0"),
        ("change_given", "REAL DEFAULT 0"),
        ("payment_reference", "TEXT"),
        ("payment_status", "TEXT DEFAULT 'PAID'"),
        ("clerk_name", "TEXT"),
        ("customer_name", "TEXT"),
        ("notes", "TEXT"),
        ("adjustment_reason", "TEXT"),
        ("payment_proof", "TEXT")
    ]
    for col_name, col_type in new_cols:
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE transactions ADD COLUMN {col_name} {col_type}")

    # Check and add customer_name to sessions if not present
    cursor.execute("PRAGMA table_info(sessions)")
    sess_cols = [row[1] for row in cursor.fetchall()]
    if "customer_name" not in sess_cols:
        cursor.execute("ALTER TABLE sessions ADD COLUMN customer_name TEXT DEFAULT ''")

    # Check and add customer_name to tvs if not present
    cursor.execute("PRAGMA table_info(tvs)")
    tv_cols = [row[1] for row in cursor.fetchall()]
    if "customer_name" not in tv_cols:
        cursor.execute("ALTER TABLE tvs ADD COLUMN customer_name TEXT DEFAULT ''")

    # --------------------------------
    # PAYMENT LOG
    # --------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        method TEXT NOT NULL,
        status TEXT DEFAULT 'CONFIRMED',
        payment_time TEXT,
        FOREIGN KEY (transaction_id) REFERENCES transactions(id)
    )
    """)

    # --------------------------------
    # CAMERA EVENTS
    # --------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS camera_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tv_id INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        confidence REAL,
        event_time TEXT NOT NULL,
        FOREIGN KEY (tv_id) REFERENCES tvs(id)
    )
    """)

    # --------------------------------
    # SHIFTS (PRD Sections 9, 10, 12)
    # --------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shifts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        clerk_name TEXT NOT NULL,
        device TEXT DEFAULT 'Web App',
        start_time TEXT NOT NULL,
        end_time TEXT,
        status TEXT DEFAULT 'ACTIVE',
        games_handled INTEGER DEFAULT 0,
        adjustments_count INTEGER DEFAULT 0,
        cash_collected REAL DEFAULT 0,
        telebirr_collected REAL DEFAULT 0,
        cbe_collected REAL DEFAULT 0,
        expected_cash REAL DEFAULT 0,
        actual_cash REAL DEFAULT 0,
        cash_difference REAL DEFAULT 0,
        notes TEXT
    )
    """)

    # --------------------------------
    # AUDIT LOGS (PRD Rule 2, 10 & Section 57)
    # --------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        actor TEXT NOT NULL,
        action TEXT NOT NULL,
        tv_id INTEGER,
        previous_value TEXT,
        new_value TEXT,
        reason TEXT NOT NULL,
        explanation TEXT,
        device TEXT DEFAULT 'Web App'
    )
    """)

    connection.commit()
    connection.close()
    print("[OK] GameWatch database initialized with hardened schema!")


if __name__ == "__main__":
    initialize_database()