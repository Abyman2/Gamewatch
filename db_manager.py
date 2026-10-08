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
            tournament_format TEXT DEFAULT 'CHAMPIONS_LEAGUE',
            tournament_duration TEXT DEFAULT '1_MONTH',
            event_date TEXT NOT NULL,
            event_time TEXT NOT NULL,
            entry_fee REAL DEFAULT 200,
            loser_match_fee REAL DEFAULT 25,
            max_participants INTEGER DEFAULT 32,
            current_participants INTEGER DEFAULT 0,
            prize_pool TEXT DEFAULT '2,500 ETB',
            total_prize_amount REAL DEFAULT 2500,
            status TEXT DEFAULT 'UPCOMING',
            current_stage TEXT DEFAULT 'REGISTRATION',
            roster_locked INTEGER DEFAULT 0,
            draw_completed INTEGER DEFAULT 0,
            winner_id INTEGER,
            winner_name TEXT,
            rules TEXT,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("PRAGMA table_info(events)")
    event_cols = [r["name"] for r in cursor.fetchall()]
    if "tournament_format" not in event_cols:
        cursor.execute("ALTER TABLE events ADD COLUMN tournament_format TEXT DEFAULT 'CHAMPIONS_LEAGUE'")
    if "tournament_duration" not in event_cols:
        cursor.execute("ALTER TABLE events ADD COLUMN tournament_duration TEXT DEFAULT '1_MONTH'")
    if "loser_match_fee" not in event_cols:
        cursor.execute("ALTER TABLE events ADD COLUMN loser_match_fee REAL DEFAULT 25")
    if "total_prize_amount" not in event_cols:
        cursor.execute("ALTER TABLE events ADD COLUMN total_prize_amount REAL DEFAULT 2500")
    if "current_stage" not in event_cols:
        cursor.execute("ALTER TABLE events ADD COLUMN current_stage TEXT DEFAULT 'REGISTRATION'")
    if "roster_locked" not in event_cols:
        cursor.execute("ALTER TABLE events ADD COLUMN roster_locked INTEGER DEFAULT 0")
    if "draw_completed" not in event_cols:
        cursor.execute("ALTER TABLE events ADD COLUMN draw_completed INTEGER DEFAULT 0")
    if "winner_id" not in event_cols:
        cursor.execute("ALTER TABLE events ADD COLUMN winner_id INTEGER")
    if "winner_name" not in event_cols:
        cursor.execute("ALTER TABLE events ADD COLUMN winner_name TEXT")

    # Event registrations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS event_registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            customer_phone TEXT,
            user_id INTEGER,
            chosen_club TEXT DEFAULT 'Real Madrid',
            group_letter TEXT,
            seed_number INTEGER,
            fee_paid INTEGER DEFAULT 0,
            fee_amount REAL DEFAULT 0,
            payment_method TEXT DEFAULT 'CASH',
            checked_in INTEGER DEFAULT 0,
            matches_played INTEGER DEFAULT 0,
            won INTEGER DEFAULT 0,
            drawn INTEGER DEFAULT 0,
            lost INTEGER DEFAULT 0,
            goals_for INTEGER DEFAULT 0,
            goals_against INTEGER DEFAULT 0,
            goal_diff INTEGER DEFAULT 0,
            points INTEGER DEFAULT 0,
            is_eliminated INTEGER DEFAULT 0,
            registered_at TEXT NOT NULL,
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("PRAGMA table_info(event_registrations)")
    reg_cols = [r["name"] for r in cursor.fetchall()]
    if "chosen_club" not in reg_cols:
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN chosen_club TEXT DEFAULT 'Real Madrid'")
    if "group_letter" not in reg_cols:
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN group_letter TEXT")
    if "seed_number" not in reg_cols:
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN seed_number INTEGER")
    if "matches_played" not in reg_cols:
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN matches_played INTEGER DEFAULT 0")
    if "won" not in reg_cols:
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN won INTEGER DEFAULT 0")
    if "drawn" not in reg_cols:
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN drawn INTEGER DEFAULT 0")
    if "lost" not in reg_cols:
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN lost INTEGER DEFAULT 0")
    if "goals_for" not in reg_cols:
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN goals_for INTEGER DEFAULT 0")
    if "goals_against" not in reg_cols:
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN goals_against INTEGER DEFAULT 0")
    if "goal_diff" not in reg_cols:
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN goal_diff INTEGER DEFAULT 0")
    if "points" not in reg_cols:
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN points INTEGER DEFAULT 0")
    if "is_eliminated" not in reg_cols:
        cursor.execute("ALTER TABLE event_registrations ADD COLUMN is_eliminated INTEGER DEFAULT 0")

    # Tournament matches table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tournament_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            stage TEXT NOT NULL,
            group_letter TEXT,
            round_number INTEGER DEFAULT 1,
            match_number INTEGER,
            leg_number INTEGER DEFAULT 1,
            player1_id INTEGER,
            player1_name TEXT,
            player1_club TEXT,
            player2_id INTEGER,
            player2_name TEXT,
            player2_club TEXT,
            score1 INTEGER,
            score2 INTEGER,
            winner_id INTEGER,
            winner_name TEXT,
            loser_id INTEGER,
            loser_name TEXT,
            loser_fee_paid INTEGER DEFAULT 0,
            scheduled_date TEXT,
            scheduled_time TEXT,
            date_locked INTEGER DEFAULT 0,
            tv_station_id INTEGER DEFAULT 1,
            status TEXT DEFAULT 'SCHEDULED',
            notes TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE
        )
    """)

    # Ensure promotions table has ad traction columns
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS promotions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            lounge_id INTEGER,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            badge_text TEXT DEFAULT 'SPECIAL OFFER',
            promo_rate REAL DEFAULT 20,
            target_url TEXT DEFAULT '',
            sponsor_name TEXT DEFAULT '',
            impressions INTEGER DEFAULT 0,
            clicks INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)
    cursor.execute("PRAGMA table_info(promotions)")
    p_cols = [r["name"] for r in cursor.fetchall()]
    if "target_url" not in p_cols:
        cursor.execute("ALTER TABLE promotions ADD COLUMN target_url TEXT DEFAULT ''")
    if "sponsor_name" not in p_cols:
        cursor.execute("ALTER TABLE promotions ADD COLUMN sponsor_name TEXT DEFAULT ''")
    if "impressions" not in p_cols:
        cursor.execute("ALTER TABLE promotions ADD COLUMN impressions INTEGER DEFAULT 0")
    if "clicks" not in p_cols:
        cursor.execute("ALTER TABLE promotions ADD COLUMN clicks INTEGER DEFAULT 0")

    # Ensure events table has commission columns
    cursor.execute("PRAGMA table_info(events)")
    ev_cols = [r["name"] for r in cursor.fetchall()]
    if "commission_rate" not in ev_cols:
        cursor.execute("ALTER TABLE events ADD COLUMN commission_rate REAL DEFAULT 15.0")
    if "commission_amount" not in ev_cols:
        cursor.execute("ALTER TABLE events ADD COLUMN commission_amount REAL DEFAULT 0.0")

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
                 entry_fee: float = 200, max_participants: int = 32,
                 prize_pool: str = "2,500 ETB", rules: str = "",
                 tournament_format: str = "CHAMPIONS_LEAGUE",
                 tournament_duration: str = "1_MONTH",
                 loser_match_fee: float = 25.0,
                 total_prize_amount: float = 2500.0) -> dict:
    init_lounges_table()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO events (
            owner_id, lounge_id, title, game, tournament_format, tournament_duration,
            event_date, event_time, entry_fee, loser_match_fee, max_participants,
            current_participants, prize_pool, total_prize_amount, status, current_stage,
            roster_locked, draw_completed, rules, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, 'UPCOMING', 'REGISTRATION', 0, 0, ?, ?)
    """, (
        owner_id, lounge_id, title.strip(), game.strip(), tournament_format.strip(),
        tournament_duration.strip(), event_date.strip(), event_time.strip(),
        float(entry_fee), float(loser_match_fee), int(max_participants),
        prize_pool.strip(), float(total_prize_amount), rules.strip(), now_str
    ))
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
    allowed = [
        "title", "game", "tournament_format", "tournament_duration", "event_date",
        "event_time", "entry_fee", "loser_match_fee", "max_participants", "prize_pool",
        "total_prize_amount", "status", "current_stage", "roster_locked", "draw_completed",
        "winner_id", "winner_name", "rules"
    ]
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
    cursor.execute("DELETE FROM tournament_matches WHERE event_id = ?", (event_id,))
    cursor.execute("DELETE FROM event_registrations WHERE event_id = ?", (event_id,))
    cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
    connection.commit()
    connection.close()
    return {"success": True, "message": "Event deleted successfully."}

def register_for_event(event_id: int, customer_name: str, customer_phone: str = "",
                       user_id: int = None, fee_paid: int = 0, fee_amount: float = 0,
                       payment_method: str = "CASH", chosen_club: str = "Real Madrid") -> dict:
    init_lounges_table()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM events WHERE id = ? LIMIT 1", (event_id,))
    event = cursor.fetchone()
    if not event:
        connection.close()
        return {"success": False, "message": "Event not found."}

    max_p = event["max_participants"] or 32
    curr_p = event["current_participants"] or 0
    if curr_p >= max_p:
        connection.close()
        return {"success": False, "message": f"Tournament is fully booked ({curr_p}/{max_p})."}

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO event_registrations (
            event_id, customer_name, customer_phone, user_id, chosen_club,
            fee_paid, fee_amount, payment_method, checked_in, registered_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
    """, (
        event_id, customer_name.strip(), customer_phone.strip(), user_id,
        chosen_club.strip() or "Real Madrid", int(fee_paid),
        float(fee_amount or event["entry_fee"]), payment_method, now_str
    ))
    
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

# -------------------------------------------------------------
# TOURNAMENT CHAMPIONS LEAGUE 2010 & LOTTERY DRAW SUITE
# -------------------------------------------------------------

DEMO_CLUBS_POOL = [
    "Real Madrid", "Manchester City", "Arsenal", "Barcelona",
    "Bayern Munich", "Liverpool", "Paris Saint-Germain", "Inter Milan",
    "Chelsea", "AC Milan", "Atletico Madrid", "Bayer Leverkusen",
    "Juventus", "Borussia Dortmund", "Aston Villa", "Napoli",
    "Tottenham", "AS Roma", "FC Porto", "SL Benfica",
    "Sporting CP", "Ajax", "Newcastle United", "Real Sociedad",
    "AS Monaco", "Galatasaray", "Lazio", "Fenerbahce",
    "Sevilla", "Girona", "Atalanta", "PSV Eindhoven"
]

DEMO_GAMERS_POOL = [
    ("Abel Tesfaye", "0911234001"), ("Dawit Bekele", "0911234002"),
    ("Sami Haile", "0911234003"), ("Henok Alemayehu", "0911234004"),
    ("Natnael Girma", "0911234005"), ("Eyob Tadesse", "0911234006"),
    ("Biruk Mengistu", "0911234007"), ("Robel Desta", "0911234008"),
    ("Yohannes Kassa", "0911234009"), ("Aman Worku", "0911234010"),
    ("Brook Assefa", "0911234011"), ("Kirubel Mulugeta", "0911234012"),
    ("Mikias Fikre", "0911234013"), ("Yared Solomon", "0911234014"),
    ("Blen Kebede", "0911234015"), ("Kaleb Zewde", "0911234016"),
    ("Nahom Berhanu", "0911234017"), ("Surafel Tefera", "0911234018"),
    ("Binyam Negash", "0911234019"), ("Dagmawi Ayele", "0911234020"),
    ("Fasika Welde", "0911234021"), ("Yonatan Sisay", "0911234022"),
    ("Samuel Belay", "0911234023"), ("Nebiyu Getachew", "0911234024"),
    ("Leul Kassahun", "0911234025"), ("Kidus Yohannes", "0911234026"),
    ("Temesgen Endale", "0911234027"), ("Bereket Wolde", "0911234028"),
    ("Ephrem Hailu", "0911234029"), ("Ermias Fisseha", "0911234030"),
    ("Hailemariam G.", "0911234031"), ("Tewodros Kassaye", "0911234032")
]

def seed_demo_roster(event_id: int) -> dict:
    """Fills the tournament roster up to max_participants with realistic gamers and clubs for instant testing."""
    init_lounges_table()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    event = cursor.fetchone()
    if not event:
        connection.close()
        return {"success": False, "message": "Tournament not found."}
    
    max_p = event["max_participants"] or 32
    cursor.execute("SELECT customer_name FROM event_registrations WHERE event_id = ?", (event_id,))
    existing_names = set(r["customer_name"] for r in cursor.fetchall())
    
    curr = len(existing_names)
    needed = max_p - curr
    if needed <= 0:
        connection.close()
        return {"success": True, "message": f"Roster already full ({curr}/{max_p}).", "count": curr}

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry_fee = event["entry_fee"] or 200
    added = 0
    import random
    
    for i, (name, phone) in enumerate(DEMO_GAMERS_POOL):
        if added >= needed:
            break
        if name in existing_names:
            continue
        club = DEMO_CLUBS_POOL[(curr + added) % len(DEMO_CLUBS_POOL)]
        cursor.execute("""
            INSERT INTO event_registrations (
                event_id, customer_name, customer_phone, chosen_club, fee_paid,
                fee_amount, payment_method, checked_in, registered_at
            )
            VALUES (?, ?, ?, ?, 1, ?, 'CASH', 1, ?)
        """, (event_id, name, phone, club, float(entry_fee), now_str))
        added += 1

    total_now = curr + added
    cursor.execute("UPDATE events SET current_participants = ? WHERE id = ?", (total_now, event_id))
    connection.commit()
    connection.close()
    return {"success": True, "message": f"Successfully registered {added} gamers to roster ({total_now}/{max_p}).", "count": total_now}

def lock_tournament_roster(event_id: int) -> dict:
    """Locks the roster so that no more registrations can occur and the lottery ball draw can be held."""
    init_lounges_table()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("UPDATE events SET roster_locked = 1 WHERE id = ?", (event_id,))
    connection.commit()
    connection.close()
    return {"success": True, "message": "Roster locked! Tournament is ready for the Lottery Ball Draw."}

def execute_tournament_lottery_draw(event_id: int) -> dict:
    """
    Simulates the Glass Sphere / Lottery Tumbler ball draw:
    Randomly assigns registered participants into Groups of 4 (e.g. Groups A to H for 32 players),
    generates all 96 group stage matches (double round-robin 12 matches per group),
    and pre-generates the 29 knockout stage matches (Round of 16, QF, SF, Final) = 125 games total!
    """
    import random
    from datetime import timedelta
    init_lounges_table()
    connection = get_connection()
    cursor = connection.cursor()
    
    cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    event = cursor.fetchone()
    if not event:
        connection.close()
        return {"success": False, "message": "Tournament not found."}

    cursor.execute("SELECT * FROM event_registrations WHERE event_id = ? ORDER BY id ASC", (event_id,))
    regs = [dict(r) for r in cursor.fetchall()]
    if len(regs) < 4:
        connection.close()
        return {"success": False, "message": f"Need at least 4 registered players to hold a draw (currently {len(regs)})."}

    # Clear any previous matches for this event
    cursor.execute("DELETE FROM tournament_matches WHERE event_id = ?", (event_id,))

    # Shuffle for fairness (pure random lottery ball tumbling)
    random.shuffle(regs)

    fmt = (event["tournament_format"] or "CHAMPIONS_LEAGUE").upper()
    now_dt = datetime.now()
    duration = event["tournament_duration"] or "1_MONTH"
    
    # Calculate days spread
    total_days = 30
    if duration == "2_WEEKS":
        total_days = 14
    elif duration == "2_MONTHS":
        total_days = 60

    if fmt == "CHAMPIONS_LEAGUE":
        # Group stage: groups of 4
        # Determine number of groups: 32 -> 8 groups (A-H), 16 -> 4 groups (A-D), 8 -> 2 groups (A-B)
        num_players = len(regs)
        num_groups = min(8, max(1, num_players // 4))
        group_letters = [chr(65 + i) for i in range(num_groups)]  # ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        
        groups_map = {letter: [] for letter in group_letters}
        for idx, p in enumerate(regs):
            g_letter = group_letters[idx % num_groups]
            seed_num = (idx // num_groups) + 1
            groups_map[g_letter].append(p)
            cursor.execute("""
                UPDATE event_registrations 
                SET group_letter = ?, seed_number = ?, matches_played = 0, won = 0, drawn = 0, lost = 0,
                    goals_for = 0, goals_against = 0, goal_diff = 0, points = 0, is_eliminated = 0
                WHERE id = ?
            """, (g_letter, seed_num, p["id"]))

        # Generate group stage fixtures (Double Round Robin: home & away, 12 matches per group of 4)
        match_idx = 1
        days_for_groups = int(total_days * 0.70)
        
        for g_letter, g_players in groups_map.items():
            gp_len = len(g_players)
            # Pairings for 4 players: (0,1), (2,3), (0,2), (3,1), (0,3), (1,2)
            # Home leg:
            pairs_leg1 = [
                (0, 1), (2, 3),
                (0, 2), (3, 1),
                (0, 3), (1, 2)
            ]
            # Away leg (reversed):
            pairs_leg2 = [
                (1, 0), (3, 2),
                (2, 0), (1, 3),
                (3, 0), (2, 1)
            ]

            all_pairs = []
            for p_a, p_b in pairs_leg1:
                if p_a < gp_len and p_b < gp_len:
                    all_pairs.append((p_a, p_b, 1))
            for p_a, p_b in pairs_leg2:
                if p_a < gp_len and p_b < gp_len:
                    all_pairs.append((p_a, p_b, 2))

            for (p_a_idx, p_b_idx, leg) in all_pairs:
                p1 = g_players[p_a_idx]
                p2 = g_players[p_b_idx]
                
                # Suggested date evenly distributed
                day_offset = (match_idx % max(1, days_for_groups)) + 1
                sched_dt = now_dt + timedelta(days=day_offset)
                sched_date_str = sched_dt.strftime("%a, %b %d")
                sched_time_str = f"{(4 + (match_idx % 4)):02d}:00 PM"
                st_id = (match_idx % 2) + 1  # Station 1 or Station 2
                
                cursor.execute("""
                    INSERT INTO tournament_matches (
                        event_id, stage, group_letter, round_number, match_number, leg_number,
                        player1_id, player1_name, player1_club, player2_id, player2_name, player2_club,
                        scheduled_date, scheduled_time, tv_station_id, status, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'SCHEDULED', ?)
                """, (
                    event_id, f"GROUP_{g_letter}", g_letter, leg, match_idx, leg,
                    p1["id"], p1["customer_name"], p1["chosen_club"],
                    p2["id"], p2["customer_name"], p2["chosen_club"],
                    sched_date_str, sched_time_str, st_id, now_dt.strftime("%Y-%m-%d %H:%M:%S")
                ))
                match_idx += 1

        # Pre-generate Knockout Stage matches
        # Round of 16 (8 ties x 2 legs = 16 matches)
        r16_ties = [
            ("Winner Group A", "Runner-up Group B"),
            ("Winner Group C", "Runner-up Group D"),
            ("Winner Group E", "Runner-up Group F"),
            ("Winner Group G", "Runner-up Group H"),
            ("Winner Group B", "Runner-up Group A"),
            ("Winner Group D", "Runner-up Group C"),
            ("Winner Group F", "Runner-up Group E"),
            ("Winner Group H", "Runner-up Group G"),
        ]
        ko_start_day = int(total_days * 0.72)
        for tie_i, (t1, t2) in enumerate(r16_ties):
            for leg_i in [1, 2]:
                sched_dt = now_dt + timedelta(days=ko_start_day + tie_i + (leg_i * 2))
                cursor.execute("""
                    INSERT INTO tournament_matches (
                        event_id, stage, round_number, match_number, leg_number,
                        player1_name, player1_club, player2_name, player2_club,
                        scheduled_date, scheduled_time, tv_station_id, status, notes, created_at
                    )
                    VALUES (?, 'ROUND_OF_16', 3, ?, ?, ?, 'TBD', ?, 'TBD', ?, '05:00 PM', 1, 'SCHEDULED', ?, ?)
                """, (
                    event_id, match_idx, leg_i, t1, t2,
                    sched_dt.strftime("%a, %b %d"), f"R16 Tie #{tie_i+1} Leg {leg_i}",
                    now_dt.strftime("%Y-%m-%d %H:%M:%S")
                ))
                match_idx += 1

        # Quarterfinals (4 ties x 2 legs = 8 matches)
        qf_start_day = int(total_days * 0.85)
        for qf_i in range(4):
            for leg_i in [1, 2]:
                sched_dt = now_dt + timedelta(days=qf_start_day + qf_i + (leg_i * 2))
                cursor.execute("""
                    INSERT INTO tournament_matches (
                        event_id, stage, round_number, match_number, leg_number,
                        player1_name, player1_club, player2_name, player2_club,
                        scheduled_date, scheduled_time, tv_station_id, status, notes, created_at
                    )
                    VALUES (?, 'QUARTER_FINAL', 4, ?, ?, ?, 'TBD', ?, 'TBD', ?, '06:00 PM', 1, 'SCHEDULED', ?, ?)
                """, (
                    event_id, match_idx, leg_i, f"QF {qf_i+1} Player A", f"QF {qf_i+1} Player B",
                    sched_dt.strftime("%a, %b %d"), f"Quarterfinal #{qf_i+1} Leg {leg_i}",
                    now_dt.strftime("%Y-%m-%d %H:%M:%S")
                ))
                match_idx += 1

        # Semifinals (2 ties x 2 legs = 4 matches)
        sf_start_day = int(total_days * 0.93)
        for sf_i in range(2):
            for leg_i in [1, 2]:
                sched_dt = now_dt + timedelta(days=sf_start_day + sf_i + (leg_i * 2))
                cursor.execute("""
                    INSERT INTO tournament_matches (
                        event_id, stage, round_number, match_number, leg_number,
                        player1_name, player1_club, player2_name, player2_club,
                        scheduled_date, scheduled_time, tv_station_id, status, notes, created_at
                    )
                    VALUES (?, 'SEMI_FINAL', 5, ?, ?, ?, 'TBD', ?, 'TBD', ?, '06:30 PM', 1, 'SCHEDULED', ?, ?)
                """, (
                    event_id, match_idx, leg_i, f"SF {sf_i+1} Player A", f"SF {sf_i+1} Player B",
                    sched_dt.strftime("%a, %b %d"), f"Semifinal #{sf_i+1} Leg {leg_i}",
                    now_dt.strftime("%Y-%m-%d %H:%M:%S")
                ))
                match_idx += 1

        # Grand Final (1 match)
        final_dt = now_dt + timedelta(days=total_days)
        cursor.execute("""
            INSERT INTO tournament_matches (
                event_id, stage, round_number, match_number, leg_number,
                player1_name, player1_club, player2_name, player2_club,
                scheduled_date, scheduled_time, tv_station_id, status, notes, created_at
            )
            VALUES (?, 'GRAND_FINAL', 6, ?, 1, 'Finalist 1', 'TBD', 'Finalist 2', 'TBD', ?, '07:00 PM', 1, 'SCHEDULED', 'Championship Match', ?)
        """, (
            event_id, match_idx, final_dt.strftime("%a, %b %d"),
            now_dt.strftime("%Y-%m-%d %H:%M:%S")
        ))
        
        cursor.execute("""
            UPDATE events 
            SET draw_completed = 1, roster_locked = 1, current_stage = 'GROUP_STAGE', status = 'IN_PROGRESS'
            WHERE id = ?
        """, (event_id,))

    else:
        # Knockout single elimination
        num_players = len(regs)
        # Pair adjacent players
        match_idx = 1
        for i in range(0, num_players - 1, 2):
            p1 = regs[i]
            p2 = regs[i+1]
            sched_dt = now_dt + timedelta(days=(match_idx % total_days) + 1)
            cursor.execute("""
                INSERT INTO tournament_matches (
                    event_id, stage, round_number, match_number, leg_number,
                    player1_id, player1_name, player1_club, player2_id, player2_name, player2_club,
                    scheduled_date, scheduled_time, tv_station_id, status, created_at
                )
                VALUES (?, 'ROUND_1', 1, ?, 1, ?, ?, ?, ?, ?, ?, ?, '04:00 PM', 1, 'SCHEDULED', ?)
            """, (
                event_id, match_idx, p1["id"], p1["customer_name"], p1["chosen_club"],
                p2["id"], p2["customer_name"], p2["chosen_club"],
                sched_dt.strftime("%a, %b %d"), now_dt.strftime("%Y-%m-%d %H:%M:%S")
            ))
            match_idx += 1
            
        cursor.execute("""
            UPDATE events 
            SET draw_completed = 1, roster_locked = 1, current_stage = 'KNOCKOUT_STAGE', status = 'IN_PROGRESS'
            WHERE id = ?
        """, (event_id,))

    connection.commit()
    connection.close()
    return {"success": True, "message": "UEFA Lottery Ball Draw complete! Groups seeded and match fixtures generated."}

def get_tournament_full_hub(event_id: int, is_owner: bool = False) -> dict:
    """Returns the complete tournament state: event, participants, standings, fixtures, bracket, and business analytics."""
    init_lounges_table()
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
    event_row = cursor.fetchone()
    if not event_row:
        connection.close()
        return {"success": False, "message": "Tournament not found."}
    event = dict(event_row)

    # Participants
    cursor.execute("""
        SELECT * FROM event_registrations 
        WHERE event_id = ? 
        ORDER BY group_letter ASC, points DESC, goal_diff DESC, goals_for DESC, id ASC
    """, (event_id,))
    participants = [dict(r) for r in cursor.fetchall()]

    # Group standings map
    groups_dict = {}
    for p in participants:
        g = p.get("group_letter") or "UNASSIGNED"
        if g not in groups_dict:
            groups_dict[g] = []
        groups_dict[g].append(p)

    # Sort each group by PTS desc, GD desc, GF desc, and mark top 2 as qualified
    for g, p_list in groups_dict.items():
        if g != "UNASSIGNED":
            p_list.sort(key=lambda x: (x.get("points") or 0, x.get("goal_diff") or 0, x.get("goals_for") or 0), reverse=True)
            for idx, p in enumerate(p_list):
                p["group_rank"] = idx + 1
                p["is_top_2"] = (idx < 2)

    # Matches
    cursor.execute("""
        SELECT * FROM tournament_matches 
        WHERE event_id = ? 
        ORDER BY id ASC
    """, (event_id,))
    matches = [dict(r) for r in cursor.fetchall()]

    # Business Analytics (Strictly for Lounge Owner)
    analytics = None
    if is_owner:
        total_p = event.get("max_participants") or 32
        reg_count = len(participants)
        entry_fee = float(event.get("entry_fee") or 200)
        loser_fee = float(event.get("loser_match_fee") or 25)
        
        # Projected matches:
        fmt = (event.get("tournament_format") or "CHAMPIONS_LEAGUE").upper()
        if fmt == "CHAMPIONS_LEAGUE":
            total_proj_matches = 125 if total_p >= 32 else 61
        else:
            total_proj_matches = 31 if total_p >= 32 else 15
            
        completed_matches = len([m for m in matches if m.get("status") == "COMPLETED"])
        paid_regs = len([p for p in participants if p.get("fee_paid") == 1])

        entry_rev_proj = total_p * entry_fee
        entry_rev_collected = paid_regs * entry_fee
        match_rev_proj = total_proj_matches * loser_fee
        match_rev_collected = completed_matches * loser_fee

        gross_proj = entry_rev_proj + match_rev_proj
        gross_collected = entry_rev_collected + match_rev_collected

        prize_pool = float(event.get("total_prize_amount") or 2500)
        net_profit_proj = gross_proj - prize_pool
        net_profit_collected = gross_collected - prize_pool

        margin_pct = round((net_profit_proj / gross_proj * 100), 1) if gross_proj > 0 else 0

        analytics = {
            "entry_fee_etb": entry_fee,
            "max_players": total_p,
            "registered_players": reg_count,
            "paid_players": paid_regs,
            "entry_revenue_projected": entry_rev_proj,
            "entry_revenue_collected": entry_rev_collected,
            "loser_match_fee_etb": loser_fee,
            "total_matches_projected": total_proj_matches,
            "completed_matches_count": completed_matches,
            "match_revenue_projected": match_rev_proj,
            "match_revenue_collected": match_rev_collected,
            "gross_revenue_projected": gross_proj,
            "gross_revenue_collected": gross_collected,
            "prize_pool_expense": prize_pool,
            "net_owner_profit_projected": net_profit_proj,
            "net_owner_profit_collected": net_profit_collected,
            "profit_margin_percent": margin_pct,
            "group_stage_games": 96 if fmt == "CHAMPIONS_LEAGUE" else 0,
            "knockout_stage_games": 29 if fmt == "CHAMPIONS_LEAGUE" else total_proj_matches
        }

    connection.close()
    return {
        "success": True,
        "event": event,
        "participants": participants,
        "groups": groups_dict,
        "matches": matches,
        "business_analytics": analytics
    }

def record_match_result(match_id: int, score1: int, score2: int, notes: str = "") -> dict:
    """Owner inputs the match result, updating standings, advancing bracket, and auditing loser fee."""
    init_lounges_table()
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM tournament_matches WHERE id = ?", (match_id,))
    match = cursor.fetchone()
    if not match:
        connection.close()
        return {"success": False, "message": "Match not found."}

    event_id = match["event_id"]
    p1_id = match["player1_id"]
    p2_id = match["player2_id"]
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    winner_id = None
    winner_name = None
    loser_id = None
    loser_name = None

    if score1 > score2:
        winner_id = p1_id
        winner_name = match["player1_name"]
        loser_id = p2_id
        loser_name = match["player2_name"]
    elif score2 > score1:
        winner_id = p2_id
        winner_name = match["player2_name"]
        loser_id = p1_id
        loser_name = match["player1_name"]

    cursor.execute("""
        UPDATE tournament_matches
        SET score1 = ?, score2 = ?, winner_id = ?, winner_name = ?,
            loser_id = ?, loser_name = ?, loser_fee_paid = 1,
            status = 'COMPLETED', notes = ?, completed_at = ?
        WHERE id = ?
    """, (score1, score2, winner_id, winner_name, loser_id, loser_name, notes, now_str, match_id))

    # Update Group Stage standings if this was a group match
    if match["group_letter"] and p1_id and p2_id:
        def update_player_stats(p_id, goals_scored, goals_conceded, result_type):
            cursor.execute("SELECT * FROM event_registrations WHERE id = ?", (p_id,))
            p = cursor.fetchone()
            if not p: return
            p_played = (p["matches_played"] or 0) + 1
            p_won = (p["won"] or 0) + (1 if result_type == "W" else 0)
            p_drawn = (p["drawn"] or 0) + (1 if result_type == "D" else 0)
            p_lost = (p["lost"] or 0) + (1 if result_type == "L" else 0)
            p_gf = (p["goals_for"] or 0) + goals_scored
            p_ga = (p["goals_against"] or 0) + goals_conceded
            p_gd = p_gf - p_ga
            p_pts = (p["points"] or 0) + (3 if result_type == "W" else (1 if result_type == "D" else 0))

            cursor.execute("""
                UPDATE event_registrations
                SET matches_played = ?, won = ?, drawn = ?, lost = ?,
                    goals_for = ?, goals_against = ?, goal_diff = ?, points = ?
                WHERE id = ?
            """, (p_played, p_won, p_drawn, p_lost, p_gf, p_ga, p_gd, p_pts, p_id))

        if score1 > score2:
            update_player_stats(p1_id, score1, score2, "W")
            update_player_stats(p2_id, score2, score1, "L")
        elif score2 > score1:
            update_player_stats(p1_id, score1, score2, "L")
            update_player_stats(p2_id, score2, score1, "W")
        else:
            update_player_stats(p1_id, score1, score2, "D")
            update_player_stats(p2_id, score2, score1, "D")

    # If this was the Grand Final, crown champion
    if match["stage"] == "GRAND_FINAL" and winner_name:
        cursor.execute("""
            UPDATE events 
            SET winner_id = ?, winner_name = ?, status = 'COMPLETED', current_stage = 'COMPLETED'
            WHERE id = ?
        """, (winner_id, winner_name, event_id))

    connection.commit()
    connection.close()
    return {"success": True, "message": f"Match result recorded ({score1}-{score2}). Live standings updated."}

def update_match_schedule(match_id: int, scheduled_date: str, scheduled_time: str, tv_station_id: int = 1) -> dict:
    """Owner locks in agreed match date and time after discussing with the players."""
    init_lounges_table()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        UPDATE tournament_matches
        SET scheduled_date = ?, scheduled_time = ?, tv_station_id = ?, date_locked = 1
        WHERE id = ?
    """, (scheduled_date.strip(), scheduled_time.strip(), int(tv_station_id or 1), match_id))
    connection.commit()
    connection.close()
    return {"success": True, "message": f"Agreed match schedule locked for {scheduled_date} at {scheduled_time} (TV {tv_station_id})."}

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
                     badge_text: str = "🔥 HAPPY HOUR SPECIAL", promo_rate: float = 20, is_active: int = 1,
                     target_url: str = "", sponsor_name: str = "") -> dict:
    init_lounges_table()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    connection = get_connection()
    cursor = connection.cursor()
    if is_active:
        cursor.execute("UPDATE promotions SET is_active = 0 WHERE owner_id = ?", (owner_id,))
    cursor.execute("""
        INSERT INTO promotions (owner_id, lounge_id, title, description, badge_text, promo_rate, target_url, sponsor_name, impressions, clicks, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?)
    """, (owner_id, lounge_id, title.strip(), description.strip(), badge_text.strip(), float(promo_rate), (target_url or "").strip(), (sponsor_name or "").strip(), int(is_active), now_str))
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
    for k in ["title", "description", "badge_text", "promo_rate", "is_active", "target_url", "sponsor_name"]:
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

def record_promotion_impression(promo_id: int) -> dict:
    init_lounges_table()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("UPDATE promotions SET impressions = COALESCE(impressions, 0) + 1 WHERE id = ?", (promo_id,))
    connection.commit()
    cursor.execute("SELECT id, impressions, clicks FROM promotions WHERE id = ?", (promo_id,))
    row = cursor.fetchone()
    connection.close()
    return {"success": True, "ad": dict(row) if row else None}

def record_promotion_click(promo_id: int) -> dict:
    init_lounges_table()
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("UPDATE promotions SET clicks = COALESCE(clicks, 0) + 1 WHERE id = ?", (promo_id,))
    connection.commit()
    cursor.execute("SELECT id, target_url, impressions, clicks, sponsor_name FROM promotions WHERE id = ?", (promo_id,))
    row = cursor.fetchone()
    connection.close()
    return {"success": True, "ad": dict(row) if row else None}

def get_promotions_analytics(owner_id: int = None) -> list:
    init_lounges_table()
    connection = get_connection()
    cursor = connection.cursor()
    if owner_id:
        cursor.execute("SELECT * FROM promotions WHERE owner_id = ? ORDER BY id DESC", (owner_id,))
    else:
        cursor.execute("SELECT * FROM promotions ORDER BY id DESC")
    rows = cursor.fetchall()
    connection.close()
    result = []
    for r in rows:
        d = dict(r)
        imp = int(d.get("impressions") or 0)
        clk = int(d.get("clicks") or 0)
        ctr = round((clk / imp * 100.0), 2) if imp > 0 else 0.0
        d["ctr_pct"] = ctr
        result.append(d)
    return result

def get_platform_master_stats() -> dict:
    init_lounges_table()
    connection = get_connection()
    cursor = connection.cursor()

    # User breakdown by role
    cursor.execute("SELECT role, COUNT(*) as count FROM users GROUP BY role")
    role_counts = {r["role"] or "UNASSIGNED": int(r["count"]) for r in cursor.fetchall()}

    cursor.execute("SELECT COUNT(*) as total FROM users")
    total_users = int(cursor.fetchone()["total"] or 0)

    # Lounge count
    cursor.execute("SELECT COUNT(*) as total FROM lounges")
    total_lounges = int(cursor.fetchone()["total"] or 0)

    # Transaction volume & matches
    cursor.execute("""
        SELECT 
            COUNT(*) as total_txs,
            COALESCE(SUM(total), 0) as total_volume,
            COALESCE(SUM(completed_games), 0) as total_games
        FROM transactions
    """)
    tx_row = cursor.fetchone()

    # Tournaments & prize pools
    cursor.execute("SELECT COUNT(*) as total_events, COALESCE(SUM(total_prize_amount), 0) as total_prizes FROM events")
    ev_row = cursor.fetchone()

    # All registered users list (clean projection)
    cursor.execute("""
        SELECT id, full_name, email, phone, role, auth_provider, created_at, last_login_at, status 
        FROM users 
        ORDER BY id DESC
    """)
    all_users = [dict(u) for u in cursor.fetchall()]

    # Ad traction overview
    cursor.execute("SELECT id, title, sponsor_name, target_url, impressions, clicks, is_active FROM promotions")
    ads = []
    for a in cursor.fetchall():
        ad_dict = dict(a)
        imp = int(ad_dict.get("impressions") or 0)
        clk = int(ad_dict.get("clicks") or 0)
        ad_dict["ctr_pct"] = round((clk / imp * 100.0), 2) if imp > 0 else 0.0
        ads.append(ad_dict)

    connection.close()

    return {
        "success": True,
        "total_users": total_users,
        "owners_count": role_counts.get("OWNER", 0),
        "clerks_count": role_counts.get("CLERK", 0),
        "customers_count": role_counts.get("CUSTOMER", 0),
        "unassigned_count": role_counts.get("UNASSIGNED", 0),
        "total_lounges": total_lounges,
        "total_transactions": int(tx_row["total_txs"] or 0) if tx_row else 0,
        "total_gaming_volume": float(tx_row["total_volume"] or 0.0) if tx_row else 0.0,
        "total_games_played": int(tx_row["total_games"] or 0) if tx_row else 0,
        "total_tournaments": int(ev_row["total_events"] or 0) if ev_row else 0,
        "total_prize_money": float(ev_row["total_prizes"] or 0.0) if ev_row else 0.0,
        "users": all_users,
        "ads": ads
    }

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
    # Exception: Allow an unbound CLERK to submit and bind their required lounge access code
    is_clerk_binding = (existing["role"] == "CLERK" and role_norm == "CLERK" and not existing["joined_lounge_code"])
    if existing["role"] and existing["role"] in valid_roles and not is_clerk_binding:
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