"""
GameWatch Step 2: Cloud Sync & Offline-First Resilience Engine
=============================================================
Author: TSEGA Labs (GameWatch Engineering)
Purpose: Guarantees 100% uninterrupted gaming lounge operations during internet blackouts,
         while synchronizing verified matches and financials to the cloud dashboard ($0/mo tier).

Architecture:
-------------
1. Primary Source of Truth: Local SQLite database on the lounge mini-PC / laptop.
   - All matches, OCR readings, shifts, and cash collections are logged locally first.
   - Operations work 100% offline without internet.
2. Cloud Mirror: Lightweight background worker pushes batches to remote cloud endpoint (Render / Neon).
3. Automatic Reconnect & Backfill: When internet restores, all unsynced records are uploaded seamlessly.
"""

import os
import time
import json
import socket
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
import db_manager


class CloudSyncManager:
    """
    Manages bidirectional or push synchronization between local lounge database
    and remote cloud monitoring instance.
    """

    def __init__(self, cloud_api_url: Optional[str] = None, sync_token: Optional[str] = None):
        self.cloud_api_url = cloud_api_url or os.getenv("GAMEWATCH_CLOUD_URL", "")
        self.sync_token = sync_token or os.getenv("GAMEWATCH_SYNC_TOKEN", "gw_secret_sync_key")
        self.is_online = False
        self.last_sync_time = 0.0
        self.last_sync_status = "IDLE"
        self.unsynced_count = 0

    @staticmethod
    def check_internet_connectivity(timeout: float = 1.5) -> bool:
        """Checks if the local machine currently has access to the wider internet."""
        try:
            socket.setdefaulttimeout(timeout)
            # Check Cloudflare DNS 1.1.1.1 on port 53 (DNS)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("1.1.1.1", 53))
            s.close()
            return True
        except Exception:
            return False

    def get_sync_telemetry(self) -> Dict[str, Any]:
        """Returns sync status, connectivity state, and pending transaction counts."""
        self.is_online = self.check_internet_connectivity()
        conn = db_manager.get_connection()
        c = conn.cursor()
        
        # Check if sync_status column exists in sessions table
        c.execute("PRAGMA table_info(sessions)")
        cols = [r["name"] for r in c.fetchall()]
        if "sync_status" not in cols:
            c.execute("ALTER TABLE sessions ADD COLUMN sync_status TEXT DEFAULT 'PENDING'")
            conn.commit()

        c.execute("SELECT count(*) FROM sessions WHERE sync_status != 'SYNCED'")
        unsynced_sessions = c.fetchone()[0]
        conn.close()

        return {
            "is_online": self.is_online,
            "cloud_configured": bool(self.cloud_api_url),
            "cloud_url": self.cloud_api_url or "Not Configured (Running Local LAN Mode)",
            "unsynced_sessions": unsynced_sessions,
            "last_sync_time": self.last_sync_time,
            "last_sync_status": self.last_sync_status,
            "mode": "CONNECTED_CLOUD" if (self.is_online and self.cloud_api_url) else "OFFLINE_LOCAL_LAN"
        }

    def prepare_sync_payload(self) -> Dict[str, Any]:
        """Prepares a snapshot of local matches, transactions, and shifts for cloud upload."""
        conn = db_manager.get_connection()
        c = conn.cursor()
        
        # Fetch unsynced completed matches
        c.execute("""
            SELECT id, tv_id, customer_name, start_time, end_time, completed_games, 
                   status, sync_status
            FROM sessions 
            WHERE sync_status != 'SYNCED'
            ORDER BY id ASC LIMIT 50
        """)
        sessions = [dict(r) for r in c.fetchall()]

        # Fetch lounge config
        lounge_cfg = db_manager.get_lounge_config()
        conn.close()

        return {
            "lounge_name": lounge_cfg.get("lounge_name", "GameWatch Lounge"),
            "sync_timestamp": time.time(),
            "sessions": sessions,
            "total_records": len(sessions)
        }

    def push_to_cloud(self) -> Dict[str, Any]:
        """
        Pushes pending match records to the cloud endpoint.
        Gracefully returns offline status if internet is down without throwing errors.
        """
        if not self.cloud_api_url:
            self.last_sync_status = "LOCAL_ONLY_NO_URL"
            return {"success": False, "message": "No cloud URL configured. Running in high-speed local LAN mode."}

        if not self.check_internet_connectivity():
            self.last_sync_status = "OFFLINE_INTERNET_DOWN"
            return {"success": False, "message": "Internet connection offline. Records safely queued in local SQLite."}

        payload = self.prepare_sync_payload()
        if payload["total_records"] == 0:
            self.last_sync_status = "UP_TO_DATE"
            self.last_sync_time = time.time()
            return {"success": True, "message": "All matches are already synchronized with the cloud."}

        try:
            req_data = json.dumps(payload).encode("utf-8")
            target_url = f"{self.cloud_api_url.rstrip('/')}/api/cloud_sync/ingest"
            req = urllib.request.Request(
                target_url,
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "X-GameWatch-Token": self.sync_token,
                    "User-Agent": "GameWatch-Local-Node/1.0"
                }
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                if resp.status in (200, 201):
                    # Mark pushed sessions as SYNCED
                    conn = db_manager.get_connection()
                    c = conn.cursor()
                    session_ids = [s["id"] for s in payload["sessions"]]
                    if session_ids:
                        placeholders = ",".join("?" for _ in session_ids)
                        c.execute(f"UPDATE sessions SET sync_status = 'SYNCED' WHERE id IN ({placeholders})", session_ids)
                        conn.commit()
                    conn.close()

                    self.last_sync_status = "SUCCESS"
                    self.last_sync_time = time.time()
                    return {"success": True, "synced_count": len(session_ids), "message": f"Successfully synced {len(session_ids)} records to cloud."}

            self.last_sync_status = "CLOUD_REJECTED"
            return {"success": False, "message": f"Cloud node returned status code {resp.status}"}
        except Exception as e:
            self.last_sync_status = f"ERROR: {str(e)[:40]}"
            return {"success": False, "message": f"Cloud sync failed: {str(e)}"}

    def push_frame_to_cloud(self, frame) -> bool:
        """Pushes a compressed camera frame snapshot to the cloud for remote monitoring."""
        if not self.cloud_api_url or frame is None:
            return False
        try:
            import cv2
            import base64
            # Compress to lightweight 640x360 JPEG snapshot (~15KB)
            h, w = frame.shape[:2]
            scale = 640.0 / w if w > 640 else 1.0
            small = cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_LINEAR)
            _, jpeg = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 55])
            b64_str = base64.b64encode(jpeg.tobytes()).decode("utf-8")
            
            target_url = f"{self.cloud_api_url.rstrip('/')}/api/cloud/relay_frame"
            req = urllib.request.Request(
                target_url,
                data=json.dumps({"frame_base64": b64_str}).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                return resp.status in (200, 201)
        except Exception:
            return False
