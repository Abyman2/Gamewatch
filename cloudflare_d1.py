'''
GameWatch Cloudflare D1 Serverless Database Integration
======================================================
Author: TSEGA Labs (GameWatch Engineering)
Purpose: Provides 100% permanent, zero-cost cloud persistence for GameWatch 
         using Cloudflare D1 (Serverless SQLite on the Cloudflare Global Edge Network).

Economics:
- .00 / month forever
- 5,000,000 read queries / day (Free tier)
- 100,000 write queries / day (Free tier)
- 10 GB persistent cloud storage (Free tier)
- 0ms cold starts & never sleeps (unlike Render free instances)
- 100% native SQLite syntax compatibility with gamewatch.db
'''

import os
import sys
import json
import sqlite3
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple


def load_env_file(filepath: str = ".env"):
    '''Simple zero-dependency .env loader.'''
    if not os.path.exists(filepath):
        return
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key and key not in os.environ:
                        os.environ[key] = val
    except Exception as e:
        print(f"[Cloudflare D1] Note: Unable to read {filepath}: {e}")


# Automatically check for local .env
load_env_file()


# Complete GameWatch Schema DDL (16 Tables, SQLite & Cloudflare D1 Native)
SCHEMA_DDL = [
    '''
    CREATE TABLE IF NOT EXISTS tvs (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        camera_id INTEGER DEFAULT 1,
        active INTEGER DEFAULT 0,
        customer_name TEXT DEFAULT '',
        owner_id INTEGER DEFAULT 20
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tv_id INTEGER NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT,
        completed_games INTEGER DEFAULT 0,
        status TEXT DEFAULT 'ACTIVE',
        customer_name TEXT DEFAULT '',
        sync_status TEXT DEFAULT 'PENDING'
    );
    ''',
    '''
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
        status TEXT DEFAULT 'ACTIVE',
        lounge_code TEXT,
        owner_id INTEGER,
        joined_lounge_code TEXT
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS lounge_config (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    ''',
    '''
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
        checkout_time TEXT NOT NULL
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        method TEXT NOT NULL,
        status TEXT DEFAULT 'CONFIRMED',
        payment_time TEXT
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS camera_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tv_id INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        confidence REAL,
        event_time TEXT NOT NULL
    );
    ''',
    '''
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
    );
    ''',
    '''
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
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS waiting_list (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT NOT NULL,
        phone TEXT,
        preferred_station TEXT DEFAULT 'Any Station',
        joined_time TEXT NOT NULL,
        status TEXT DEFAULT 'WAITING'
    );
    ''',
    '''
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
    );
    ''',
    '''
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
    );
    ''',
    '''
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
    );
    ''',
    '''
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
        registered_at TEXT NOT NULL
    );
    ''',
    '''
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
        completed_at TEXT
    );
    ''',
    '''
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
    );
    '''
]


class CloudflareD1Client:
    '''
    Direct Client for Cloudflare D1 Serverless SQLite via Cloudflare API v4.
    '''

    def __init__(
        self,
        account_id: Optional[str] = None,
        database_id: Optional[str] = None,
        api_token: Optional[str] = None
    ):
        self.account_id = account_id or os.getenv("CLOUDFLARE_ACCOUNT_ID", "").strip()
        self.database_id = database_id or os.getenv("CLOUDFLARE_D1_DATABASE_ID", "").strip()
        self.api_token = api_token or os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
        self.api_base = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/d1/database/{self.database_id}"

    def is_configured(self) -> bool:
        '''Returns True if credentials are fully configured.'''
        return bool(self.account_id and self.database_id and self.api_token)

    def _request(self, endpoint: str, payload: dict, timeout: float = 10.0) -> dict:
        '''Internal helper to dispatch requests to Cloudflare API v4.'''
        if not self.is_configured():
            return {
                "success": False,
                "error": "Cloudflare D1 is not fully configured (missing CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_D1_DATABASE_ID, or CLOUDFLARE_API_TOKEN)."
            }

        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        data_bytes = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "User-Agent": "GameWatch-CloudflareD1/1.0"
        }

        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except urllib.error.HTTPError as he:
            err_body = he.read().decode("utf-8", errors="ignore")
            try:
                parsed = json.loads(err_body)
                err_msgs = [e.get("message", str(e)) for e in parsed.get("errors", [])]
                return {
                    "success": False,
                    "status_code": he.code,
                    "error": "; ".join(err_msgs) if err_msgs else f"HTTP {he.code}: {err_body}"
                }
            except Exception:
                return {
                    "success": False,
                    "status_code": he.code,
                    "error": f"HTTP {he.code}: {err_body}"
                }
        except urllib.error.URLError as ue:
            return {"success": False, "error": f"Network Error: {ue.reason}"}
        except Exception as ex:
            return {"success": False, "error": str(ex)}

    def execute_query(self, sql: str, params: Optional[List[Any]] = None) -> dict:
        '''
        Executes a single SQL query against Cloudflare D1.
        Returns rows under 'rows' and metadata under 'meta'.
        '''
        payload = {"sql": sql}
        if params is not None:
            payload["params"] = params

        res = self._request("query", payload)
        if not res.get("success"):
            return res

        # Standard Cloudflare v4 D1 format: result is a list containing query outcomes
        result_list = res.get("result", [])
        if isinstance(result_list, list) and len(result_list) > 0:
            first_out = result_list[0]
            return {
                "success": first_out.get("success", True),
                "rows": first_out.get("results", []),
                "meta": first_out.get("meta", {})
            }
        elif isinstance(result_list, dict):
            return {
                "success": result_list.get("success", True),
                "rows": result_list.get("results", []),
                "meta": result_list.get("meta", {})
            }

        return {"success": True, "rows": [], "meta": {}}

    def test_connection(self) -> dict:
        '''Tests connectivity to Cloudflare D1 database.'''
        if not self.is_configured():
            return {
                "success": False,
                "status": "NOT_CONFIGURED",
                "message": "Cloudflare D1 credentials missing in environment variables."
            }

        res = self.execute_query("SELECT 1 AS ping, datetime('now') AS cloud_time")
        if res.get("success"):
            rows = res.get("rows", [])
            cloud_time = rows[0].get("cloud_time") if rows else "unknown"
            return {
                "success": True,
                "status": "CONNECTED",
                "database_id": self.database_id,
                "cloud_time": cloud_time,
                "message": "Successfully connected to Cloudflare D1 edge database."
            }
        else:
            return {
                "success": False,
                "status": "ERROR",
                "error": res.get("error", "Failed to query Cloudflare D1"),
                "message": "Cloudflare D1 connection test failed."
            }

    def init_schema(self) -> dict:
        '''Ensures all 16 tables exist on Cloudflare D1.'''
        if not self.is_configured():
            return {"success": False, "error": "Cloudflare D1 not configured."}

        created = 0
        errors = []

        for stmt in SCHEMA_DDL:
            stmt_clean = stmt.strip()
            if not stmt_clean:
                continue
            res = self.execute_query(stmt_clean)
            if res.get("success"):
                created += 1
            else:
                errors.append(res.get("error"))

        if errors:
            return {
                "success": False,
                "tables_created": created,
                "total_tables": len(SCHEMA_DDL),
                "errors": errors
            }

        return {
            "success": True,
            "tables_created": created,
            "total_tables": len(SCHEMA_DDL),
            "message": f"Successfully initialized {created} tables on Cloudflare D1."
        }

    def push_table_records(self, table_name: str, records: List[dict]) -> dict:
        '''Inserts or replaces rows into a specified Cloudflare D1 table.'''
        if not records:
            return {"success": True, "inserted": 0}

        success_count = 0
        error_list = []

        # Process in batches
        for row in records:
            keys = list(row.keys())
            cols = ", ".join(keys)
            placeholders = ", ".join("?" for _ in keys)
            sql = f"INSERT OR REPLACE INTO {table_name} ({cols}) VALUES ({placeholders})"
            values = [row[k] for k in keys]

            res = self.execute_query(sql, values)
            if res.get("success"):
                success_count += 1
            else:
                error_list.append(res.get("error"))

        return {
            "success": len(error_list) == 0,
            "inserted": success_count,
            "errors": error_list[:5]
        }

    def push_local_to_d1(self, db_path: str = "gamewatch.db") -> dict:
        '''Pushes all records from local gamewatch.db to Cloudflare D1.'''
        if not os.path.exists(db_path):
            return {"success": False, "error": f"Local database {db_path} not found."}

        schema_res = self.init_schema()
        if not schema_res.get("success"):
            return schema_res

        tables = [
            "lounge_config", "users", "lounges", "tvs", "sessions",
            "transactions", "payments", "shifts", "audit_logs",
            "waiting_list", "camera_sources", "events",
            "event_registrations", "tournament_matches", "promotions"
        ]

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        stats = {}
        for tbl in tables:
            try:
                cur.execute(f"SELECT * FROM {tbl}")
                rows = [dict(r) for r in cur.fetchall()]
                if rows:
                    push_res = self.push_table_records(tbl, rows)
                    stats[tbl] = push_res.get("inserted", 0)
                else:
                    stats[tbl] = 0
            except Exception as e:
                stats[tbl] = f"Error: {e}"

        conn.close()
        return {
            "success": True,
            "message": "Local database records synchronized to Cloudflare D1.",
            "stats": stats
        }

    def pull_d1_to_local(self, db_path: str = "gamewatch.db") -> dict:
        '''
        Pulls all tables and records from Cloudflare D1 and updates local gamewatch.db.
        Crucial for instant disaster recovery and container restart resilience!
        '''
        if not self.is_configured():
            return {"success": False, "error": "Cloudflare D1 is not configured."}

        tables = [
            "lounge_config", "users", "lounges", "tvs", "sessions",
            "transactions", "payments", "shifts", "audit_logs",
            "waiting_list", "camera_sources", "events",
            "event_registrations", "tournament_matches", "promotions"
        ]

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        pulled_stats = {}

        for tbl in tables:
            try:
                res = self.execute_query(f"SELECT * FROM {tbl}")
                if not res.get("success"):
                    pulled_stats[tbl] = 0
                    continue

                rows = res.get("rows", [])
                if not rows:
                    pulled_stats[tbl] = 0
                    continue

                for row in rows:
                    keys = list(row.keys())
                    cols = ", ".join(keys)
                    placeholders = ", ".join("?" for _ in keys)
                    sql = f"INSERT OR REPLACE INTO {tbl} ({cols}) VALUES ({placeholders})"
                    values = [row[k] for k in keys]
                    cur.execute(sql, values)

                conn.commit()
                pulled_stats[tbl] = len(rows)
            except Exception as e:
                pulled_stats[tbl] = f"Error: {e}"

        conn.close()
        return {
            "success": True,
            "message": "Successfully hydrated local SQLite from Cloudflare D1.",
            "pulled": pulled_stats
        }

    def get_cloud_telemetry(self) -> dict:
        '''Returns telemetry regarding Cloudflare D1 configuration, latency, and row counts.'''
        configured = self.is_configured()
        if not configured:
            return {
                "configured": False,
                "status": "LOCAL_SQLITE_MODE",
                "message": "Running on local SQLite. Add CLOUDFLARE_D1_DATABASE_ID for permanent cloud sync."
            }

        conn_test = self.test_connection()
        if not conn_test.get("success"):
            return {
                "configured": True,
                "status": "CONNECTION_FAILED",
                "error": conn_test.get("error"),
                "message": conn_test.get("message")
            }

        # Query counts
        counts = {}
        for tbl in ["users", "lounges", "events", "transactions", "tournament_matches"]:
            res = self.execute_query(f"SELECT count(*) as total FROM {tbl}")
            if res.get("success") and res.get("rows"):
                counts[tbl] = res["rows"][0].get("total", 0)
            else:
                counts[tbl] = 0

        return {
            "configured": True,
            "status": "LIVE_EDGE_ACTIVE",
            "database_id": self.database_id,
            "cloud_time": conn_test.get("cloud_time"),
            "table_counts": counts,
            "message": "Connected to Cloudflare D1 edge database. Data is permanently persistent."
        }


# Singleton client instance
_d1_instance: Optional[CloudflareD1Client] = None

def get_d1_client() -> CloudflareD1Client:
    global _d1_instance
    if _d1_instance is None:
        _d1_instance = CloudflareD1Client()
    return _d1_instance
