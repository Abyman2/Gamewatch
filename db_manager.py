import sqlite3
from datetime import datetime
import math


DATABASE_NAME = "gamewatch.db"
PRICE_PER_GAME = 25


# ----------------------------------------
# CONNECTION
# ----------------------------------------

def get_connection():

    connection = sqlite3.connect(DATABASE_NAME)

    connection.row_factory = sqlite3.Row

    return connection


# ----------------------------------------
# LOUNGE CONFIGURATION
# ----------------------------------------

def get_lounge_config() -> dict:
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT key, value FROM lounge_config")
    rows = cursor.fetchall()
    connection.close()
    config = {r["key"]: r["value"] for r in rows}
    # Ensure default fallbacks
    if "price_per_game" not in config:
        config["price_per_game"] = "25"
    if "lounge_name" not in config:
        config["lounge_name"] = "GameWatch Lounge"
    if "currency" not in config:
        config["currency"] = "ETB"
    return config

def set_lounge_config(key: str, value: str):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO lounge_config (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    """, (key, str(value)))
    connection.commit()
    connection.close()
    return True

def update_lounge_configs(configs: dict):
    connection = get_connection()
    cursor = connection.cursor()
    for k, v in configs.items():
        cursor.execute("""
            INSERT INTO lounge_config (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """, (k, str(v)))
    connection.commit()
    connection.close()
    return True


# ----------------------------------------
# MULTI-TENANT LOUNGE & OWNER CODE MANAGEMENT
# ----------------------------------------

def calculate_distance_km(lat1, lon1, lat2, lon2):
    try:
        R = 6371.0
        dlat = math.radians(float(lat2) - float(lat1))
        dlon = math.radians(float(lon2) - float(lon1))
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(float(lat1))) * math.cos(math.radians(float(lat2))) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(R * c, 1)
    except Exception:
        return None

def init_lounges_table():
    connection = get_connection()
    cursor = connection.cursor()
    # Ensure users table has multi-tenant columns
    cursor.execute("PRAGMA table_info(users)")
    cols = [r["name"] for r in cursor.fetchall()]
    if "lounge_code" not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN lounge_code TEXT")
    if "owner_id" not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN owner_id INTEGER")
    if "joined_lounge_code" not in cols:
        cursor.execute("ALTER TABLE users ADD COLUMN joined_lounge_code TEXT")

    # Ensure tvs table has owner_id
    cursor.execute("PRAGMA table_info(tvs)")
    tv_cols = [r["name"] for r in cursor.fetchall()]
    if "owner_id" not in tv_cols:
        cursor.execute("ALTER TABLE tvs ADD COLUMN owner_id INTEGER DEFAULT 20")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lounges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            lounge_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            address TEXT,
            area TEXT DEFAULT 'Bole',
            city TEXT DEFAULT 'Addis Ababa',
            phone TEXT,
            email TEXT,
            rate_per_game REAL DEFAULT 25,
            total_tvs INTEGER DEFAULT 2,
            latitude REAL DEFAULT 9.01,
            longitude REAL DEFAULT 38.76,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)

    # Events table
    cursor.execute("""
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

    # Event registrations table
    cursor.execute("""
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

    # Promotions table
    cursor.execute("""
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

    connection.commit()
    connection.close()

def get_lounge_by_code(lounge_code: str) -> dict:
    if not lounge_code:
        return None
    init_lounges_table()
    code_clean = lounge_code.strip().upper()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM lounges WHERE lounge_code = ? LIMIT 1", (code_clean,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("SELECT * FROM users WHERE UPPER(lounge_code) = ? AND role = 'OWNER' LIMIT 1", (code_clean,))
        u_row = cursor.fetchone()
        if u_row:
            connection.close()
            return create_or_ensure_owner_lounge(u_row["id"])
    connection.close()
    return dict(row) if row else None

def get_owner_lounge(owner_id: int) -> dict:
    init_lounges_table()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM lounges WHERE owner_id = ? ORDER BY id ASC LIMIT 1", (owner_id,))
    row = cursor.fetchone()
    connection.close()
    return dict(row) if row else None

def update_owner_lounge(owner_id: int, name: str = None, address: str = None, area: str = None,
                        city: str = None, phone: str = None, email: str = None,
                        rate_per_game: float = None, total_tvs: int = None) -> dict:
    init_lounges_table()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM lounges WHERE owner_id = ? ORDER BY id ASC LIMIT 1", (owner_id,))
    existing = cursor.fetchone()

    # Determine coordinates from area if area changed
    coords_map = {
        "4 kilo": (9.0345, 38.7625),
        "arat kilo": (9.0345, 38.7625),
        "bole": (8.9952, 38.7885),
        "piazza": (9.0360, 38.7512),
        "cmc": (9.0220, 38.8470),
        "kazanchis": (9.0185, 38.7745),
        "megenagna": (9.0205, 38.8020),
        "sarbet": (8.9980, 38.7350),
        "gerji": (8.9880, 38.8150),
        "lebu": (8.9550, 38.7180)
    }

    lat, lon = (None, None)
    if area:
        area_key = area.strip().lower()
        for k, v in coords_map.items():
            if k in area_key:
                lat, lon = v
                break

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if existing:
        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name.strip())
        if address is not None:
            updates.append("address = ?")
            params.append(address.strip())
        if area is not None:
            updates.append("area = ?")
            params.append(area.strip())
        if city is not None:
            updates.append("city = ?")
            params.append(city.strip())
        if phone is not None:
            updates.append("phone = ?")
            params.append(phone.strip())
        if email is not None:
            updates.append("email = ?")
            params.append(email.strip())
        if rate_per_game is not None:
            updates.append("rate_per_game = ?")
            params.append(float(rate_per_game))
        if total_tvs is not None:
            updates.append("total_tvs = ?")
            params.append(int(total_tvs))
        if lat is not None and lon is not None:
            updates.append("latitude = ?")
            params.append(lat)
            updates.append("longitude = ?")
            params.append(lon)

        if updates:
            sql = f"UPDATE lounges SET {', '.join(updates)} WHERE id = ?"
            params.append(existing["id"])
            cursor.execute(sql, tuple(params))
            connection.commit()

        cursor.execute("SELECT * FROM lounges WHERE id = ?", (existing["id"],))
        updated = dict(cursor.fetchone())
        connection.close()
        return updated
    else:
        code = f"GW-OWNER-{owner_id:03d}"
        l_name = name or f"Lounge #{owner_id}"
        l_addr = address or "Addis Ababa"
        l_area = area or "Bole"
        l_lat, l_lon = coords_map.get(l_area.lower(), (9.01, 38.76))
        cursor.execute("""
            INSERT INTO lounges (owner_id, lounge_code, name, address, area, city, phone, email, rate_per_game, total_tvs, latitude, longitude, created_at)
            VALUES (?, ?, ?, ?, ?, 'Addis Ababa', ?, ?, ?, ?, ?, ?, ?)
        """, (owner_id, code, l_name, l_addr, l_area, phone or "+251 900 000000", email or "support@gamewatch.et", rate_per_game or 25, total_tvs or 2, l_lat, l_lon, now_str))
        cursor.execute("UPDATE users SET lounge_code = ? WHERE id = ?", (code, owner_id))
        connection.commit()
        cursor.execute("SELECT * FROM lounges WHERE id = ?", (cursor.lastrowid,))
        created = dict(cursor.fetchone())
        connection.close()
        return created

def get_all_lounges(search: str = "", user_lat: float = None, user_lng: float = None) -> list:
    init_lounges_table()
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT l.*, u.full_name as owner_name 
        FROM lounges l
        LEFT JOIN users u ON l.owner_id = u.id
        WHERE l.is_active = 1
        ORDER BY l.id ASC
    """)
    rows = cursor.fetchall()
    connection.close()

    lounges = [dict(r) for r in rows]

    # Calculate distance if user coords provided
    for l in lounges:
        lat = l.get("latitude")
        lon = l.get("longitude")
        if user_lat is not None and user_lng is not None and lat and lon:
            l["distance_km"] = calculate_distance_km(user_lat, user_lng, lat, lon)
        else:
            l["distance_km"] = None

    if search:
        s_clean = search.strip().lower()
        s_compact = s_clean.replace(" ", "").replace("-", "")

        def matches(l):
            name = (l.get("name") or "").lower()
            addr = (l.get("address") or "").lower()
            area = (l.get("area") or "").lower()
            code = (l.get("lounge_code") or "").lower()
            city = (l.get("city") or "").lower()

            # Direct word match
            if s_clean in name or s_clean in addr or s_clean in area or s_clean in code or s_clean in city:
                return True
            # Compact match (e.g. "4kilo" vs "4 kilo", "aratkilo" vs "arat kilo")
            compact_combined = f"{name}{addr}{area}{code}{city}".replace(" ", "").replace("-", "")
            if s_compact in compact_combined:
                return True
            # Keyword aliases for 4 kilo
            if ("4kilo" in s_compact or "aratkilo" in s_compact) and ("4 kilo" in area or "arat" in addr or "4kilo" in addr or "4kilo" in name):
                return True
            return False

        lounges = [l for l in lounges if matches(l)]

    # Sort by distance if available, else by ID
    if user_lat is not None and user_lng is not None:
        lounges.sort(key=lambda x: (x["distance_km"] is None, x["distance_km"] or 9999))

    return lounges

def verify_clerk_code(lounge_code: str) -> dict:
    if not lounge_code:
        return {"success": False, "valid": False, "message": "Lounge code is required."}
    lounge = get_lounge_by_code(lounge_code)
    if not lounge:
        return {"success": False, "valid": False, "message": "Invalid Lounge Access Code. Please ask your Lounge Owner for their verified code."}
    return {"success": True, "valid": True, "lounge": lounge}

def create_or_ensure_owner_lounge(owner_id: int, lounge_name: str = None) -> dict:
    init_lounges_table()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM lounges WHERE owner_id = ? LIMIT 1", (owner_id,))
    existing = cursor.fetchone()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if existing:
        connection.close()
        return dict(existing)
    
    code = f"GW-OWNER-{owner_id:03d}"
    name = lounge_name or f"Lounge #{owner_id}"
    cursor.execute("""
        INSERT INTO lounges (owner_id, lounge_code, name, address, area, city, phone, email, rate_per_game, total_tvs, latitude, longitude, created_at)
        VALUES (?, ?, ?, 'Addis Ababa', 'Bole', 'Addis Ababa', '+251 900 000000', 'support@gamewatch.et', 25, 2, 8.9952, 38.7885, ?)
    """, (owner_id, code, name, now_str))
    cursor.execute("UPDATE users SET lounge_code = ? WHERE id = ?", (code, owner_id))
    connection.commit()
    cursor.execute("SELECT * FROM lounges WHERE id = ?", (cursor.lastrowid,))
    new_l = dict(cursor.fetchone())
    connection.close()
    return new_l

def join_lounge(user_id: int, lounge_code: str) -> dict:
    lounge = get_lounge_by_code(lounge_code)
    if not lounge:
        return {"success": False, "message": f"Invalid Lounge Code '{lounge_code}'."}
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        UPDATE users 
        SET joined_lounge_code = ?, owner_id = ?, updated_at = ?
        WHERE id = ?
    """, (lounge["lounge_code"], lounge["owner_id"], now_str, user_id))
    connection.commit()
    connection.close()
    return {"success": True, "lounge": lounge}

# ----------------------------------------
# EVENTS & TOURNAMENT MANAGEMENT
# ----------------------------------------

def get_events(lounge_id: int = None, owner_id: int = None) -> list:
    init_lounges_table()
    connection = get_connection()
    cursor = connection.cursor()
    if lounge_id:
        cursor.execute("SELECT * FROM events WHERE lounge_id = ? ORDER BY id DESC", (lounge_id,))
    elif owner_id:
        cursor.execute("SELECT * FROM events WHERE owner_id = ? ORDER BY id DESC", (owner_id,))
    else:
        cursor.execute("SELECT * FROM events ORDER BY id DESC")
    rows = cursor.fetchall()
    connection.close()
    return [dict(r) for r in rows]

def get_event_by_id(event_id: int) -> dict:
    init_lounges_table()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM events WHERE id = ? LIMIT 1", (event_id,))
    row = cursor.fetchone()
    connection.close()
    return dict(row) if row else None

def create_event(owner_id: int, lounge_id: int, title: str, game: str = "EA FC 25",
                 event_date: str = "Upcoming Weekend", event_time: str = "3:00 PM",
                 entry_fee: float = 50, max_participants: int = 16,
                 prize_pool: str = "2,000 ETB", rules: str = "") -> dict:
    init_lounges_table()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO events (owner_id, lounge_id, title, game, event_date, event_time, entry_fee, max_participants, current_participants, prize_pool, status, rules, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, 'UPCOMING', ?, ?)
    """, (owner_id, lounge_id, title.strip(), game.strip(), event_date.strip(), event_time.strip(), float(entry_fee), int(max_participants), prize_pool.strip(), rules.strip(), now_str))
    connection.commit()
    new_id = cursor.lastrowid
    cursor.execute("SELECT * FROM events WHERE id = ?", (new_id,))
    event = dict(cursor.fetchone())
    connection.close()
    return {"success": True, "event": event}

def update_event(event_id: int, data: dict = None, **kwargs) -> dict:
    init_lounges_table()
    payload = {**(data or {}), **kwargs}
    connection = get_connection()
    cursor = connection.cursor()
    updates = []
    params = []
    allowed = ["title", "game", "event_date", "event_time", "entry_fee", "max_participants", "prize_pool", "status", "rules"]
    for k in allowed:
        if k in payload and payload[k] is not None:
            updates.append(f"{k} = ?")
            params.append(payload[k])
    if updates:
        params.append(event_id)
        cursor.execute(f"UPDATE events SET {', '.join(updates)} WHERE id = ?", tuple(params))
        connection.commit()
    cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    row = cursor.fetchone()
    connection.close()
    return {"success": True, "event": dict(row) if row else None}

def delete_event(event_id: int, owner_id: int = None) -> dict:
    init_lounges_table()
    connection = get_connection()
    cursor = connection.cursor()
    if owner_id:
        cursor.execute("""
            SELECT e.id FROM events e
            JOIN lounges l ON e.lounge_id = l.id
            WHERE e.id = ? AND l.owner_id = ?
        """, (event_id, owner_id))
        if not cursor.fetchone():
            connection.close()
            return {"success": False, "message": "Unauthorized or event not found."}
    cursor.execute("DELETE FROM event_registrations WHERE event_id = ?", (event_id,))
    cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
    connection.commit()
    connection.close()
    return {"success": True, "message": "Event deleted successfully."}

def register_for_event(event_id: int, customer_name: str, customer_phone: str = "",
                       user_id: int = None, fee_paid: int = 0, fee_amount: float = 0,
                       payment_method: str = "CASH") -> dict:
    init_lounges_table()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM events WHERE id = ? LIMIT 1", (event_id,))
    event = cursor.fetchone()
    if not event:
        connection.close()
        return {"success": False, "message": "Event not found."}

    max_p = event["max_participants"] or 16
    curr_p = event["current_participants"] or 0
    if curr_p >= max_p:
        connection.close()
        return {"success": False, "message": f"Tournament is fully booked ({curr_p}/{max_p})."}

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO event_registrations (event_id, customer_name, customer_phone, user_id, fee_paid, fee_amount, payment_method, checked_in, registered_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
    """, (event_id, customer_name.strip(), customer_phone.strip(), user_id, int(fee_paid), float(fee_amount or event["entry_fee"]), payment_method, now_str))
    
    # Increment participant count
    new_curr = curr_p + 1
    cursor.execute("UPDATE events SET current_participants = ? WHERE id = ?", (new_curr, event_id))
    connection.commit()
    reg_id = cursor.lastrowid
    connection.close()
    return {"success": True, "registration_id": reg_id, "current_participants": new_curr, "max_participants": max_p}

def toggle_event_attendance(registration_id: int, checked_in: int = None) -> dict:
    init_lounges_table()
    connection = get_connection()
    cursor = connection.cursor()
    if checked_in is None:
        cursor.execute("SELECT checked_in FROM event_registrations WHERE id = ?", (registration_id,))
        row = cursor.fetchone()
        if not row:
            connection.close()
            return {"success": False, "message": "Registration not found"}
        checked_in = 0 if row["checked_in"] == 1 else 1

    cursor.execute("UPDATE event_registrations SET checked_in = ? WHERE id = ?", (checked_in, registration_id))
    connection.commit()
    connection.close()
    return {"success": True, "checked_in": checked_in}

def mark_event_fee_paid(registration_id: int, fee_paid: int = 1, payment_method: str = "CASH") -> dict:
    init_lounges_table()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("UPDATE event_registrations SET fee_paid = ?, payment_method = ? WHERE id = ?", (fee_paid, payment_method, registration_id))
    connection.commit()
    connection.close()
    return {"success": True, "fee_paid": fee_paid}

def get_event_participants(event_id: int) -> list:
    init_lounges_table()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM event_registrations WHERE event_id = ? ORDER BY id ASC", (event_id,))
    rows = cursor.fetchall()
    connection.close()
    return [dict(r) for r in rows]

# ----------------------------------------
# PROMOTIONS & ANNOUNCEMENT ADS MANAGEMENT
# ----------------------------------------

def get_promotions(lounge_id: int = None, owner_id: int = None) -> list:
    init_lounges_table()
    connection = get_connection()
    cursor = connection.cursor()
    if lounge_id:
        cursor.execute("SELECT * FROM promotions WHERE lounge_id = ? ORDER BY id DESC", (lounge_id,))
    elif owner_id:
        cursor.execute("SELECT * FROM promotions WHERE owner_id = ? ORDER BY id DESC", (owner_id,))
    else:
        cursor.execute("SELECT * FROM promotions ORDER BY id DESC")
    rows = cursor.fetchall()
    connection.close()
    return [dict(r) for r in rows]

def get_active_promotion(lounge_id: int = None, owner_id: int = None) -> dict:
    init_lounges_table()
    connection = get_connection()
    cursor = connection.cursor()
    if lounge_id:
        cursor.execute("SELECT * FROM promotions WHERE lounge_id = ? AND is_active = 1 ORDER BY id DESC LIMIT 1", (lounge_id,))
    elif owner_id:
        cursor.execute("SELECT * FROM promotions WHERE owner_id = ? AND is_active = 1 ORDER BY id DESC LIMIT 1", (owner_id,))
    else:
        cursor.execute("SELECT * FROM promotions WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    connection.close()
    return dict(row) if row else None

def create_promotion(owner_id: int, lounge_id: int, title: str, description: str,
                     badge_text: str = "🔥 HAPPY HOUR SPECIAL", promo_rate: float = 20, is_active: int = 1) -> dict:
    init_lounges_table()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    connection = get_connection()
    cursor = connection.cursor()
    if is_active:
        cursor.execute("UPDATE promotions SET is_active = 0 WHERE owner_id = ?", (owner_id,))
    cursor.execute("""
        INSERT INTO promotions (owner_id, lounge_id, title, description, badge_text, promo_rate, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (owner_id, lounge_id, title.strip(), description.strip(), badge_text.strip(), float(promo_rate), int(is_active), now_str))
    connection.commit()
    new_id = cursor.lastrowid
    cursor.execute("SELECT * FROM promotions WHERE id = ?", (new_id,))
    row = dict(cursor.fetchone())
    connection.close()
    return {"success": True, "promotion": row}

def update_promotion(promo_id: int, data: dict = None, **kwargs) -> dict:
    init_lounges_table()
    payload = {**(data or {}), **kwargs}
    connection = get_connection()
    cursor = connection.cursor()
    updates = []
    params = []
    for k in ["title", "description", "badge_text", "promo_rate", "is_active"]:
        if k in payload and payload[k] is not None:
            updates.append(f"{k} = ?")
            params.append(payload[k])
    if updates:
        params.append(promo_id)
        cursor.execute(f"UPDATE promotions SET {', '.join(updates)} WHERE id = ?", tuple(params))
        connection.commit()
    cursor.execute("SELECT * FROM promotions WHERE id = ?", (promo_id,))
    row = cursor.fetchone()
    connection.close()
    return {"success": True, "promotion": dict(row) if row else None}

def delete_promotion(promo_id: int, owner_id: int = None) -> dict:
    init_lounges_table()
    connection = get_connection()
    cursor = connection.cursor()
    if owner_id:
        cursor.execute("""
            SELECT p.id FROM promotions p
            JOIN lounges l ON p.lounge_id = l.id
            WHERE p.id = ? AND l.owner_id = ?
        """, (promo_id, owner_id))
        if not cursor.fetchone():
            connection.close()
            return {"success": False, "message": "Unauthorized or promotion not found."}
    cursor.execute("DELETE FROM promotions WHERE id = ?", (promo_id,))
    connection.commit()
    connection.close()
    return {"success": True, "message": "Promotion deleted successfully."}

def deduct_completed_game(tv_id: int) -> dict:
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM sessions WHERE tv_id = ? AND status = 'ACTIVE' LIMIT 1", (tv_id,))
    session = cursor.fetchone()
    if session is None:
        connection.close()
        return {"success": False, "message": "No active session on this TV."}

    current_games = session["completed_games"] or 0
    if current_games <= 0:
        connection.close()
        return {"success": False, "message": "Session already has 0 games. Cannot deduct further."}

    new_games = current_games - 1
    cursor.execute("UPDATE sessions SET completed_games = ? WHERE id = ?", (new_games, session["id"]))
    connection.commit()
    connection.close()
    return {"success": True, "previous_games": current_games, "completed_games": new_games}


# ----------------------------------------
# USER & AUTHENTICATION MANAGEMENT
# ----------------------------------------

def create_user(full_name: str, email: str, phone: str = "", password_hash: str = None, 
                auth_provider: str = "email", google_id: str = None, role: str = None) -> dict:
    email_clean = email.strip().lower()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO users (full_name, email, phone, password_hash, auth_provider, google_id, role, created_at, updated_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
        """, (full_name.strip(), email_clean, phone.strip(), password_hash, auth_provider, google_id, role, now_str, now_str))
        connection.commit()
        user_id = cursor.lastrowid
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        new_user = dict(cursor.fetchone())
        connection.close()
        return {"success": True, "user": new_user}
    except sqlite3.IntegrityError:
        connection.close()
        return {"success": False, "message": "An account with this email already exists."}
    except Exception as e:
        connection.close()
        return {"success": False, "message": str(e)}

def get_user_by_email(email: str):
    if not email:
        return None
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ? LIMIT 1", (email.strip().lower(),))
    row = cursor.fetchone()
    connection.close()
    return dict(row) if row else None

def get_user_by_id(user_id: int):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ? LIMIT 1", (user_id,))
    row = cursor.fetchone()
    connection.close()
    return dict(row) if row else None

def get_user_by_google_id(google_id: str):
    if not google_id:
        return None
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM users WHERE google_id = ? LIMIT 1", (str(google_id),))
    row = cursor.fetchone()
    connection.close()
    return dict(row) if row else None

def update_user_role(user_id: int, role: str, lounge_code: str = None) -> dict:
    init_lounges_table()
    valid_roles = ["OWNER", "CLERK", "CUSTOMER"]
    role_norm = (role or "").strip().upper()
    if role_norm not in valid_roles:
        return {"success": False, "message": f"Invalid role. Must be one of: {', '.join(valid_roles)}"}
    
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    existing = cursor.fetchone()
    if not existing:
        connection.close()
        return {"success": False, "message": "User not found."}
    
    # Rule 5 & 22: ONE USER = ONE ROLE. Role cannot be switched once selected.
    if existing["role"] and existing["role"] in valid_roles:
        connection.close()
        return {
            "success": False, 
            "message": f"Role is permanently locked to {existing['role']}. Role switching is prohibited.",
            "current_role": existing["role"]
        }
    
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    owner_id = None
    joined_code = None
    gen_code = None

    if role_norm == "OWNER":
        cursor.execute("SELECT lounge_code FROM users WHERE id = ?", (user_id,))
        cur_c = cursor.fetchone()
        gen_code = cur_c["lounge_code"] if cur_c and cur_c["lounge_code"] else f"GW-OWNER-{user_id:03d}"
        cursor.execute("""
            UPDATE users
            SET role = ?, lounge_code = ?, updated_at = ?
            WHERE id = ?
        """, (role_norm, gen_code, now_str, user_id))
        connection.commit()
        connection.close()
        create_or_ensure_owner_lounge(user_id)
        return {"success": True, "role": role_norm, "lounge_code": gen_code}

    elif role_norm == "CLERK":
        if not lounge_code:
            connection.close()
            return {"success": False, "message": "Lounge Owner Access Code is required for Clerk accounts."}
        code_clean = lounge_code.strip().upper()
        cursor.execute("SELECT * FROM lounges WHERE lounge_code = ? LIMIT 1", (code_clean,))
        lounge = cursor.fetchone()
        if not lounge:
            connection.close()
            return {"success": False, "message": f"Invalid Lounge Code '{code_clean}'. No lounge found."}
        owner_id = lounge["owner_id"]
        joined_code = code_clean

    elif role_norm == "CUSTOMER":
        code_clean = (lounge_code or "GW-BOLE-101").strip().upper()
        cursor.execute("SELECT * FROM lounges WHERE lounge_code = ? LIMIT 1", (code_clean,))
        lounge = cursor.fetchone()
        if lounge:
            owner_id = lounge["owner_id"]
            joined_code = code_clean
        else:
            cursor.execute("SELECT * FROM lounges ORDER BY id ASC LIMIT 1")
            fl = cursor.fetchone()
            if fl:
                owner_id = fl["owner_id"]
                joined_code = fl["lounge_code"]

    cursor.execute("""
        UPDATE users
        SET role = ?, owner_id = ?, joined_lounge_code = ?, updated_at = ?
        WHERE id = ?
    """, (role_norm, owner_id, joined_code, now_str, user_id))
    connection.commit()
    connection.close()
    return {"success": True, "role": role_norm, "lounge_code": joined_code, "owner_id": owner_id}

def update_user_last_login(user_id: int):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now_str, user_id))
    connection.commit()
    connection.close()

def update_user_password(user_id: int, password_hash: str) -> bool:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?", (password_hash, now_str, user_id))
    connection.commit()
    connection.close()
    return True

def get_all_users():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id, full_name, email, phone, role, auth_provider, created_at, last_login_at, status FROM users ORDER BY id ASC")
    rows = cursor.fetchall()
    connection.close()
    return [dict(r) for r in rows]



# ----------------------------------------
# TV FUNCTIONS
# ----------------------------------------

def add_tv(tv_id, name, camera_id=1, customer_name=""):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO tvs (id, name, camera_id, active, customer_name)
        VALUES (?, ?, ?, 0, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name,
            customer_name=COALESCE(NULLIF(excluded.customer_name, ''), tvs.customer_name)
    """, (
        tv_id,
        name,
        camera_id,
        customer_name
    ))

    connection.commit()

    connection.close()


def get_all_tvs():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT * FROM tvs
        ORDER BY id
    """)

    tvs = cursor.fetchall()

    connection.close()

    return tvs


def delete_tv(tv_id):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM tvs WHERE id = ?", (tv_id,))
    cursor.execute("UPDATE sessions SET status = 'CANCELLED' WHERE tv_id = ? AND status = 'ACTIVE'", (tv_id,))
    connection.commit()
    connection.close()
    return {"success": True, "message": f"TV {tv_id} deleted."}


# ----------------------------------------
# SESSION FUNCTIONS
# ----------------------------------------

def start_session(tv_id, customer_name=""):

    connection = get_connection()

    cursor = connection.cursor()


    # Check if TV exists
    cursor.execute("""
        SELECT * FROM tvs
        WHERE id = ?
    """, (tv_id,))

    tv = cursor.fetchone()

    if tv is None:

        connection.close()

        return {
            "success": False,
            "message": "TV not found."
        }


    # Check if already active
    cursor.execute("""
        SELECT * FROM sessions
        WHERE tv_id = ?
        AND status = 'ACTIVE'
    """, (tv_id,))

    existing_session = cursor.fetchone()

    if existing_session:

        connection.close()

        return {
            "success": False,
            "message": "TV already has an active session."
        }


    start_time = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    cust_to_save = customer_name or (tv["customer_name"] if "customer_name" in tv.keys() else "")

    cursor.execute("""
        INSERT INTO sessions
        (
            tv_id,
            start_time,
            completed_games,
            status,
            customer_name
        )
        VALUES (?, ?, 0, 'ACTIVE', ?)
    """, (
        tv_id,
        start_time,
        cust_to_save
    ))


    cursor.execute("""
        UPDATE tvs
        SET active = 1,
            customer_name = COALESCE(NULLIF(?, ''), customer_name)
        WHERE id = ?
    """, (cust_to_save, tv_id))


    connection.commit()

    connection.close()


    return {
        "success": True,
        "message": f"TV {tv_id} session started."
    }


def get_active_session(tv_id):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT * FROM sessions
        WHERE tv_id = ?
        AND status = 'ACTIVE'
    """, (tv_id,))


    session = cursor.fetchone()

    connection.close()

    return session


def add_completed_game(tv_id):

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute("""
        SELECT * FROM sessions
        WHERE tv_id = ?
        AND status = 'ACTIVE'
    """, (tv_id,))


    session = cursor.fetchone()


    if session is None:

        connection.close()

        return {
            "success": False,
            "message": "No active session on this TV."
        }


    cursor.execute("""
        UPDATE sessions
        SET completed_games =
        completed_games + 1
        WHERE id = ?
    """, (
        session["id"],
    ))


    connection.commit()


    cursor.execute("""
        SELECT completed_games
        FROM sessions
        WHERE id = ?
    """, (
        session["id"],
    ))


    updated_session = cursor.fetchone()

    connection.close()


    return {
        "success": True,
        "completed_games":
            updated_session[
                "completed_games"
            ]
    }


def get_active_sessions():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            sessions.*,
            tvs.name AS tv_name

        FROM sessions

        JOIN tvs
        ON sessions.tv_id = tvs.id

        WHERE sessions.status = 'ACTIVE'

        ORDER BY sessions.tv_id
    """)


    sessions = cursor.fetchall()

    connection.close()

    return sessions


# ----------------------------------------
# CHECKOUT & DETAILED TRANSACTION RECORDING
# ----------------------------------------

def checkout_session(
    tv_id,
    unfinished_game_charge=0,
    payment_method="CASH",
    amount_received=0.0,
    payment_reference="",
    clerk_name="Clerk",
    customer_name="",
    discount=0.0,
    notes="",
    adjustment_reason=""
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT * FROM sessions
        WHERE tv_id = ?
        AND status = 'ACTIVE'
    """, (tv_id,))
    session = cursor.fetchone()

    if session is None:
        connection.close()
        return {
            "success": False,
            "message": "No active session."
        }

    # Dynamic pricing from lounge configuration
    config = get_lounge_config()
    try:
        active_rate = float(config.get("price_per_game", 25))
    except Exception:
        active_rate = 25.0

    completed_games = session["completed_games"] or 0
    completed_games_total = completed_games * active_rate
    subtotal = completed_games_total + float(unfinished_game_charge or 0)
    discount = float(discount or 0)
    total = max(0.0, subtotal - discount)
    
    # Customer name determination
    cust_final = customer_name or (session["customer_name"] if "customer_name" in session.keys() and session["customer_name"] else "Walk-in Gamer")
    
    # Financial details for Cash vs Digital
    payment_method_norm = (payment_method or "CASH").upper()
    amount_received = float(amount_received or 0)
    if "CASH" in payment_method_norm:
        if amount_received <= 0:
            amount_received = total
        change_given = round(max(0.0, amount_received - total), 2)
    else:
        amount_received = total
        change_given = 0.0

    checkout_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Create detailed transaction record
    cursor.execute("""
        INSERT INTO transactions
        (
            session_id,
            tv_id,
            completed_games,
            completed_games_total,
            unfinished_game_charge,
            price_per_game,
            discount,
            subtotal,
            total,
            payment_method,
            amount_received,
            change_given,
            payment_reference,
            payment_status,
            clerk_name,
            customer_name,
            notes,
            adjustment_reason,
            checkout_time
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PAID', ?, ?, ?, ?, ?)
    """, (
        session["id"],
        tv_id,
        completed_games,
        completed_games_total,
        unfinished_game_charge,
        active_rate,
        discount,
        subtotal,
        total,
        payment_method_norm,
        amount_received,
        change_given,
        payment_reference.strip(),
        clerk_name.strip() or "Clerk",
        cust_final,
        notes.strip(),
        adjustment_reason.strip(),
        checkout_time
    ))

    transaction_id = cursor.lastrowid

    # 2. Create payment record
    cursor.execute("""
        INSERT INTO payments
        (
            transaction_id,
            amount,
            method,
            status,
            payment_time
        )
        VALUES (?, ?, ?, 'CONFIRMED', ?)
    """, (
        transaction_id,
        total,
        payment_method_norm,
        checkout_time
    ))

    # 3. Close session
    cursor.execute("""
        UPDATE sessions
        SET
            end_time = ?,
            status = 'COMPLETED'
        WHERE id = ?
    """, (
        checkout_time,
        session["id"]
    ))

    # 4. Make TV available and clear active customer
    cursor.execute("""
        UPDATE tvs
        SET active = 0, customer_name = ''
        WHERE id = ?
    """, (tv_id,))

    connection.commit()
    connection.close()

    # 5. Record immutable audit log
    record_audit_log(
        actor=clerk_name or "Clerk",
        action="CHECKOUT",
        tv_id=tv_id,
        previous_value=f"Session #{session['id']} ACTIVE",
        new_value=f"Transaction #{transaction_id:06d} PAID",
        reason=f"Checkout {payment_method_norm} Total: {total} ETB",
        explanation=f"Games: {completed_games}, Recv: {amount_received} ETB, Change: {change_given} ETB. Customer: {cust_final}",
        device="Web App"
    )

    return {
        "success": True,
        "transaction_id": transaction_id,
        "transaction": {
            "id": transaction_id,
            "formatted_id": f"GW-{transaction_id:06d}",
            "completed_games": completed_games,
            "total": total,
            "payment_method": payment_method_norm,
            "amount_received": amount_received,
            "change_given": change_given
        },
        "formatted_id": f"#GW-{transaction_id:06d}",
        "completed_games": completed_games,
        "completed_total": completed_games_total,
        "price_per_game": active_rate,
        "subtotal": subtotal,
        "discount": discount,
        "total": total,
        "payment_method": payment_method_norm,
        "amount_received": amount_received,
        "change_given": change_given,
        "payment_reference": payment_reference,
        "customer_name": cust_final,
        "clerk_name": clerk_name,
        "checkout_time": checkout_time
    }


# ----------------------------------------
# TRANSACTION HISTORY & DETAILED LOOKUP
# ----------------------------------------

def get_transactions():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT t.*, 
               COALESCE(NULLIF(t.customer_name, ''), NULLIF(s.customer_name, ''), 'Walk-in Gamer') AS customer_name,
               COALESCE(NULLIF(tv.name, ''), 'TV ' || t.tv_id) AS tv_name,
               s.start_time AS session_start,
               s.end_time AS session_end
        FROM transactions t
        LEFT JOIN sessions s ON t.session_id = s.id
        LEFT JOIN tvs tv ON t.tv_id = tv.id
        ORDER BY t.id DESC
    """)
    rows = cursor.fetchall()
    connection.close()

    results = []
    for r in rows:
        d = dict(r)
        d["formatted_id"] = f"#GW-{d['id']:06d}"
        d["amount_received"] = float(d.get("amount_received") or d.get("total") or 0)
        d["change_given"] = float(d.get("change_given") or 0)
        d["payment_reference"] = d.get("payment_reference") or ""
        d["clerk_name"] = d.get("clerk_name") or "Clerk"
        d["price_per_game"] = float(d.get("price_per_game") or 25)
        d["subtotal"] = float(d.get("subtotal") or d.get("total") or 0)
        d["discount"] = float(d.get("discount") or 0)
        d["payment_status"] = d.get("payment_status") or "PAID"
        results.append(d)
    return results

def get_transaction_by_id(tx_id: int):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT t.*, 
               COALESCE(NULLIF(t.customer_name, ''), NULLIF(s.customer_name, ''), 'Walk-in Gamer') AS customer_name,
               COALESCE(NULLIF(tv.name, ''), 'TV ' || t.tv_id) AS tv_name,
               s.start_time AS session_start,
               s.end_time AS session_end
        FROM transactions t
        LEFT JOIN sessions s ON t.session_id = s.id
        LEFT JOIN tvs tv ON t.tv_id = tv.id
        WHERE t.id = ?
        LIMIT 1
    """, (tx_id,))
    row = cursor.fetchone()
    connection.close()
    if not row:
        return None
    
    d = dict(row)
    d["formatted_id"] = f"#GW-{d['id']:06d}"
    d["amount_received"] = float(d.get("amount_received") or d.get("total") or 0)
    d["change_given"] = float(d.get("change_given") or 0)
    d["payment_reference"] = d.get("payment_reference") or ""
    d["clerk_name"] = d.get("clerk_name") or "Clerk"
    d["price_per_game"] = float(d.get("price_per_game") or 25)
    d["subtotal"] = float(d.get("subtotal") or d.get("total") or 0)
    d["discount"] = float(d.get("discount") or 0)
    d["payment_status"] = d.get("payment_status") or "PAID"
    
    # Calculate duration
    if d.get("session_start") and d.get("checkout_time"):
        try:
            t1 = datetime.strptime(d["session_start"], "%Y-%m-%d %H:%M:%S")
            t2 = datetime.strptime(d["checkout_time"], "%Y-%m-%d %H:%M:%S")
            mins = int((t2 - t1).total_seconds() / 60)
            d["duration_str"] = f"{mins} min" if mins > 0 else "< 1 min"
        except Exception:
            d["duration_str"] = "--"
    else:
        d["duration_str"] = "--"
        
    return d



# ----------------------------------------
# WAITING LIST (Customer Queue)
# ----------------------------------------

def init_waiting_list_table():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS waiting_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            phone TEXT,
            preferred_station TEXT DEFAULT 'Any Station',
            joined_time TEXT NOT NULL,
            status TEXT DEFAULT 'WAITING'
        )
    """)
    connection.commit()
    connection.close()

def add_to_waiting_list(customer_name: str, phone: str = "", preferred_station: str = "Any Station"):
    init_waiting_list_table()
    connection = get_connection()
    cursor = connection.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO waiting_list (customer_name, phone, preferred_station, joined_time, status)
        VALUES (?, ?, ?, ?, 'WAITING')
    """, (customer_name, phone, preferred_station, now_str))
    connection.commit()
    new_id = cursor.lastrowid
    connection.close()
    return {"success": True, "id": new_id, "message": f"{customer_name} added to waiting list."}

def get_waiting_list():
    init_waiting_list_table()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT * FROM waiting_list
        WHERE status = 'WAITING'
        ORDER BY id ASC
    """)
    rows = cursor.fetchall()
    connection.close()
    return [dict(r) for r in rows]

def remove_from_waiting_list(entry_id: int):
    init_waiting_list_table()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("UPDATE waiting_list SET status = 'SEATED' WHERE id = ?", (entry_id,))
    connection.commit()
    connection.close()
    return {"success": True}


# ----------------------------------------
# DAILY SUMMARY
# ----------------------------------------

def get_daily_summary():
    connection = get_connection()
    cursor = connection.cursor()
    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT
            COUNT(*) AS transactions,
            COALESCE(SUM(completed_games), 0) AS total_games,
            COALESCE(SUM(total), 0) AS total_revenue
        FROM transactions
        WHERE DATE(checkout_time) = ?
    """, (today,))
    overall = cursor.fetchone()

    cursor.execute("""
        SELECT
            payment_method,
            COALESCE(SUM(total), 0) AS total,
            COUNT(*) AS count
        FROM transactions
        WHERE DATE(checkout_time) = ?
        GROUP BY payment_method
    """, (today,))
    payment_breakdown = cursor.fetchall()
    connection.close()

    cash_total = 0.0
    telebirr_total = 0.0
    cbe_total = 0.0
    for row in payment_breakdown:
        m = (row["payment_method"] or "").upper()
        amt = float(row["total"] or 0)
        if "CASH" in m:
            cash_total += amt
        elif "TELEBIRR" in m:
            telebirr_total += amt
        elif "CBE" in m:
            cbe_total += amt

    return {
        "transactions": overall["transactions"],
        "total_games": overall["total_games"],
        "total_revenue": overall["total_revenue"],
        "cash_revenue": cash_total,
        "telebirr_revenue": telebirr_total,
        "cbe_revenue": cbe_total,
        "payments": [dict(p) for p in payment_breakdown]
    }
# ----------------------------------------
# PAYMENT PROOF
# ----------------------------------------

def add_payment_proof(
    transaction_id,
    proof_path
):

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute("""
        UPDATE transactions

        SET payment_proof = ?

        WHERE id = ?
    """, (
        proof_path,
        transaction_id
    ))


    connection.commit()


    updated_rows = cursor.rowcount

    connection.close()


    if updated_rows == 0:

        return {
            "success": False,
            "message":
                "Transaction not found."
        }


    return {
        "success": True,
        "message":
            "Payment proof attached."
    }


# ----------------------------------------
# SHIFTS & AUDIT LOGS (PRD v1.0 Sections 9, 12, 21, 22, 57)
# ----------------------------------------

def record_audit_log(actor, action, tv_id=None, previous_value="", new_value="", reason="", explanation="", device="Web App"):
    connection = get_connection()
    cursor = connection.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO audit_logs (timestamp, actor, action, tv_id, previous_value, new_value, reason, explanation, device)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (now_str, actor, action, tv_id, str(previous_value), str(new_value), reason, explanation, device))
    connection.commit()
    log_id = cursor.lastrowid
    connection.close()
    return log_id


def get_recent_audit_logs(limit=30):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        SELECT * FROM audit_logs
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    connection.close()
    return [dict(r) for r in rows]


def start_shift(clerk_name="Hana", device="Web App"):
    connection = get_connection()
    cursor = connection.cursor()
    
    # Check if there is already an active shift
    cursor.execute("SELECT * FROM shifts WHERE status = 'ACTIVE' ORDER BY id DESC LIMIT 1")
    existing = cursor.fetchone()
    if existing:
        connection.close()
        return {"success": True, "message": "Shift already active", "shift": dict(existing)}
        
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO shifts (clerk_name, device, start_time, status)
        VALUES (?, ?, ?, 'ACTIVE')
    """, (clerk_name, device, start_time))
    connection.commit()
    shift_id = cursor.lastrowid
    connection.close()
    
    record_audit_log(
        actor=clerk_name,
        action="SHIFT_START",
        reason="Scheduled Shift Started",
        explanation=f"{clerk_name} clocked in at {start_time}",
        device=device
    )
    
    return {
        "success": True,
        "message": f"Shift started for {clerk_name}",
        "shift": {
            "id": shift_id,
            "clerk_name": clerk_name,
            "start_time": start_time,
            "status": "ACTIVE"
        }
    }


def get_active_shift():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM shifts WHERE status = 'ACTIVE' ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    if not row:
        connection.close()
        return None
        
    shift = dict(row)
    start_t = shift["start_time"]
    
    # Calculate live games completed during this shift
    cursor.execute("""
        SELECT COUNT(*) as total_games FROM sessions 
        WHERE start_time >= ?
    """, (start_t,))
    sg = cursor.fetchone()
    games_handled = sg["total_games"] if sg else 0
    
    # Calculate adjustments recorded during this shift
    cursor.execute("""
        SELECT COUNT(*) as total_adj FROM audit_logs
        WHERE timestamp >= ? AND action IN ('MANUAL_GAME_ADD', 'MATCH_RESET', 'DISCOUNT_APPLIED')
    """, (start_t,))
    sa = cursor.fetchone()
    adjustments_count = sa["total_adj"] if sa else 0
    
    # Calculate payments collected during this shift
    cursor.execute("""
        SELECT payment_method, SUM(total) as revenue FROM transactions
        WHERE checkout_time >= ?
        GROUP BY payment_method
    """, (start_t,))
    p_rows = cursor.fetchall()
    
    cash_col = 0.0
    telebirr_col = 0.0
    cbe_col = 0.0
    for pr in p_rows:
        m = (pr["payment_method"] or "").upper()
        rev = float(pr["revenue"] or 0)
        if "CASH" in m:
            cash_col += rev
        elif "TELEBIRR" in m:
            telebirr_col += rev
        elif "CBE" in m:
            cbe_col += rev
            
    connection.close()
    
    shift["games_handled"] = games_handled
    shift["adjustments_count"] = adjustments_count
    shift["cash_collected"] = cash_col
    shift["telebirr_collected"] = telebirr_col
    shift["cbe_collected"] = cbe_col
    shift["expected_cash"] = cash_col
    shift["total_collected"] = cash_col + telebirr_col + cbe_col
    return shift


def end_shift(shift_id, actual_cash=0.0, notes="", clerk_name="Hana"):
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM shifts WHERE id = ?", (shift_id,))
    row = cursor.fetchone()
    if not row:
        connection.close()
        return {"success": False, "message": "Shift not found"}
        
    shift = dict(row)
    start_t = shift["start_time"]
    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Calculate final cash
    cursor.execute("""
        SELECT SUM(total) as cash_rev FROM transactions
        WHERE checkout_time >= ? AND payment_method LIKE '%CASH%'
    """, (start_t,))
    cr = cursor.fetchone()
    expected_cash = float(cr["cash_rev"] or 0.0) if cr else 0.0
    actual_cash = float(actual_cash)
    diff = round(actual_cash - expected_cash, 2)
    
    cursor.execute("""
        UPDATE shifts
        SET end_time = ?,
            status = 'COMPLETED',
            expected_cash = ?,
            actual_cash = ?,
            cash_difference = ?,
            notes = ?
        WHERE id = ?
    """, (end_time, expected_cash, actual_cash, diff, notes, shift_id))
    connection.commit()
    connection.close()
    
    record_audit_log(
        actor=clerk_name,
        action="SHIFT_END",
        reason=f"End of Shift. Cash Diff: {diff} ETB",
        explanation=f"Expected: {expected_cash} ETB, Actual: {actual_cash} ETB. Notes: {notes}",
        device="Web App"
    )
    
    return {
        "success": True,
        "message": f"Shift ended successfully. Reconciliation difference: {diff} ETB",
        "difference": diff,
        "expected_cash": expected_cash,
        "actual_cash": actual_cash
    }

# ----------------------------------------
# CAMERA & VIDEO SOURCE CONNECTORS
# ----------------------------------------

def init_camera_sources_table():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS camera_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            source_type TEXT NOT NULL,
            address TEXT NOT NULL,
            tv_id INTEGER DEFAULT 1,
            status TEXT DEFAULT 'READY',
            resolution TEXT DEFAULT '1920x1080',
            fps INTEGER DEFAULT 30,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)
    # Seed default sources if empty
    cursor.execute("SELECT count(*) FROM camera_sources")
    if cursor.fetchone()[0] == 0:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO camera_sources (name, source_type, address, tv_id, status, resolution, fps, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("Built-in / USB Camera 0", "USB", "0", 1, "CONNECTED", "1280x720", 30, 1, now_str))
        cursor.execute("""
            INSERT INTO camera_sources (name, source_type, address, tv_id, status, resolution, fps, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("Phone IP Cam (DroidCam)", "PHONE", "http://192.168.1.105:4747/video", 2, "READY", "1920x1080", 30, 0, now_str))
    connection.commit()
    connection.close()

def get_camera_sources():
    init_camera_sources_table()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM camera_sources ORDER BY id ASC")
    rows = cursor.fetchall()
    connection.close()
    return [dict(r) for r in rows]

def add_camera_source(name: str, source_type: str, address: str, tv_id: int = 1):
    init_camera_sources_table()
    connection = get_connection()
    cursor = connection.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO camera_sources (name, source_type, address, tv_id, status, resolution, fps, is_active, created_at)
        VALUES (?, ?, ?, ?, 'READY', '1920x1080', 30, 1, ?)
    """, (name, source_type.upper(), address.strip(), tv_id, now_str))
    connection.commit()
    new_id = cursor.lastrowid
    connection.close()
    return {
        "success": True,
        "id": new_id,
        "source": {"id": new_id, "name": name, "source_type": source_type.upper(), "address": address.strip(), "tv_id": tv_id},
        "message": f"Camera connector '{name}' registered successfully."
    }

def update_camera_source(source_id: int, status: str = None, resolution: str = None, fps: int = None, is_active: int = None):
    init_camera_sources_table()
    connection = get_connection()
    cursor = connection.cursor()
    updates = []
    params = []
    if status is not None:
        updates.append("status = ?")
        params.append(status)
    if resolution is not None:
        updates.append("resolution = ?")
        params.append(resolution)
    if fps is not None:
        updates.append("fps = ?")
        params.append(fps)
    if is_active is not None:
        updates.append("is_active = ?")
        params.append(is_active)
    if updates:
        params.append(source_id)
        cursor.execute(f"UPDATE camera_sources SET {', '.join(updates)} WHERE id = ?", params)
        connection.commit()
    connection.close()
    return {"success": True}

def delete_camera_source(source_id: int):
    init_camera_sources_table()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM camera_sources WHERE id = ?", (source_id,))
    connection.commit()
    connection.close()
    return {"success": True, "message": "Camera connector removed."}

# ----------------------------------------
# BUSINESS INTELLIGENCE & WEEKLY ANALYTICS
# ----------------------------------------

def get_weekly_business_analytics(lounge_id: int = None) -> dict:
    connection = get_connection()
    cursor = connection.cursor()
    from datetime import datetime, timedelta

    today = datetime.now().date()
    days_data = []
    total_week_revenue = 0.0
    total_week_games = 0
    total_week_transactions = 0

    for i in range(6, -1, -1):
        day_date = today - timedelta(days=i)
        day_str = day_date.strftime("%Y-%m-%d")
        day_label = day_date.strftime("%a")

        cursor.execute("""
            SELECT 
                COUNT(*) as tx_count,
                COALESCE(SUM(completed_games), 0) as games_count,
                COALESCE(SUM(total), 0) as day_revenue
            FROM transactions
            WHERE DATE(checkout_time) = ?
        """, (day_str,))
        row = cursor.fetchone()
        rev = float(row["day_revenue"] or 0)
        games = int(row["games_count"] or 0)
        txs = int(row["tx_count"] or 0)

        days_data.append({
            "date": day_str,
            "day": day_label,
            "revenue": rev,
            "games": games,
            "transactions": txs
        })
        total_week_revenue += rev
        total_week_games += games
        total_week_transactions += txs

    prev_week_revenue = 0.0
    for i in range(13, 6, -1):
        day_date = today - timedelta(days=i)
        day_str = day_date.strftime("%Y-%m-%d")
        cursor.execute("""
            SELECT COALESCE(SUM(total), 0) as day_revenue
            FROM transactions
            WHERE DATE(checkout_time) = ?
        """, (day_str,))
        row = cursor.fetchone()
        prev_week_revenue += float(row["day_revenue"] or 0)

    growth_pct = 0.0
    if prev_week_revenue > 0:
        growth_pct = round(((total_week_revenue - prev_week_revenue) / prev_week_revenue) * 100, 1)
    elif total_week_revenue > 0:
        growth_pct = 100.0

    cursor.execute("""
        SELECT 
            strftime('%H', checkout_time) as hour,
            COUNT(*) as tx_count,
            COALESCE(SUM(completed_games), 0) as games_count,
            COALESCE(SUM(total), 0) as hour_revenue
        FROM transactions
        GROUP BY hour
        ORDER BY games_count DESC
    """)
    hourly_rows = cursor.fetchall()
    hourly_dist = []
    peak_hour_str = "4:00 PM – 8:00 PM"
    peak_capacity_str = "84% peak capacity"
    if hourly_rows and hourly_rows[0]["games_count"] > 0:
        try:
            top_h = int(hourly_rows[0]["hour"] or 16)
            top_h_12 = top_h % 12 or 12
            ampm = "PM" if top_h >= 12 else "AM"
            end_h = (top_h + 3) % 24
            end_h_12 = end_h % 12 or 12
            end_ampm = "PM" if end_h >= 12 else "AM"
            peak_hour_str = f"{top_h_12}:00 {ampm} – {end_h_12}:00 {end_ampm}"
            peak_capacity_str = f"{hourly_rows[0]['games_count']} matches"
        except Exception:
            pass

    for h in range(10, 24):
        h_str = f"{h:02d}"
        match = next((r for r in hourly_rows if r["hour"] == h_str), None)
        hourly_dist.append({
            "hour": h,
            "label": f"{h}:00",
            "games": int(match["games_count"]) if match else 0,
            "revenue": float(match["hour_revenue"]) if match else 0.0
        })

    cursor.execute("""
        SELECT 
            tv_id,
            COUNT(*) as session_count,
            COALESCE(SUM(completed_games), 0) as games,
            COALESCE(SUM(total), 0) as revenue
        FROM transactions
        GROUP BY tv_id
    """)
    station_rows = cursor.fetchall()
    stations_perf = []
    for s in station_rows:
        stations_perf.append({
            "tv_id": s["tv_id"],
            "name": f"TV {s['tv_id']}",
            "games": int(s["games"] or 0),
            "revenue": float(s["revenue"] or 0),
            "sessions": int(s["session_count"] or 0)
        })
    if not stations_perf:
        stations_perf = [
            {"tv_id": 1, "name": "TV 1 (Executive Lounge)", "games": total_week_games, "revenue": total_week_revenue, "sessions": total_week_transactions},
            {"tv_id": 2, "name": "TV 2 (Main Hall Station)", "games": 0, "revenue": 0.0, "sessions": 0}
        ]

    cursor.execute("""
        SELECT 
            payment_method,
            COALESCE(SUM(total), 0) as total,
            COUNT(*) as count
        FROM transactions
        GROUP BY payment_method
    """)
    pm_rows = cursor.fetchall()
    pm_breakdown = []
    for pm in pm_rows:
        amt = float(pm["total"] or 0)
        pct = round((amt / total_week_revenue * 100), 1) if total_week_revenue > 0 else 0
        pm_breakdown.append({
            "method": pm["payment_method"] or "CASH",
            "amount": amt,
            "count": int(pm["count"] or 0),
            "percentage": pct
        })
    if not pm_breakdown:
        pm_breakdown = [
            {"method": "CASH", "amount": total_week_revenue, "count": total_week_transactions, "percentage": 100.0}
        ]

    ai_insights = [
        {
            "type": "PRICING",
            "icon": "⚡",
            "title": "Peak Hour Demand Optimization",
            "recommendation": f"Peak gaming traffic concentrates between {peak_hour_str}. Consider introducing a +5 ETB/match peak rate or dynamic weekend tournament to boost weekly margin by ~18%."
        },
        {
            "type": "PAYMENT",
            "icon": "📱",
            "title": "Digital Payment Settlement",
            "recommendation": "Encouraging Telebirr QR scan at the counter expedites checkout turnaround and minimizes end-of-shift register discrepancies."
        },
        {
            "type": "CAPACITY",
            "icon": "🎯",
            "title": "Station Load Balancing",
            "recommendation": "Station 1 currently accounts for most played sessions. Direct walk-in FIFA/FC players to TV 2 to balance controller wear and prevent player wait times."
        }
    ]

    connection.close()

    return {
        "weekly_revenue": total_week_revenue,
        "previous_week_revenue": prev_week_revenue,
        "growth_percentage": growth_pct,
        "total_games": total_week_games,
        "total_transactions": total_week_transactions,
        "days": days_data,
        "hourly_distribution": hourly_dist,
        "peak_hours": peak_hour_str,
        "peak_capacity": peak_capacity_str,
        "station_performance": stations_perf,
        "payment_breakdown": pm_breakdown,
        "ai_insights": ai_insights
    }