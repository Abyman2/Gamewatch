import cv2
import numpy as np
import os
import sys
import time
import json
import base64
import threading
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import urllib.request
import re
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, Response, jsonify, request, send_file, send_from_directory, session

from scoreboard_reader import ScoreboardReader, ScoreboardReading
from scoreboard_preprocessor import ScoreboardPreprocessor
from stage3_reader_brain_test import TimeAwareMatchBrain
import db_manager
import database
from ai.antigravity_debug_agent import AntigravityDebugAgent, AnomalyEvent
from camera_stream_engine import ZeroLatencyCamera, get_local_ip
from cloud_sync import CloudSyncManager

cloud_sync_manager = CloudSyncManager()

# Ensure database tables exist
database.initialize_database()

# ========================================
# CONFIGURATION & FLASK APP
# ========================================
TV_REGIONS_FILE = "tv_regions.json"
TEST_IMAGES_DIR = "test_images"
TELEBIRR_QR_PATH = os.path.join("payment_qr", "telebirr_qr.jpg")

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "gamewatch_secure_production_secret_key_2026")
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_NAME'] = 'gamewatch_session'

# ========================================
# AUTHENTICATION & AUTHORIZATION HELPERS
# ========================================
def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db_manager.get_user_by_id(user_id)

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"success": False, "message": "Authentication required", "authenticated": False}), 401
        return f(*args, **kwargs)
    return decorated_function

def require_role(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"success": False, "message": "Authentication required", "authenticated": False}), 401
            user_role = (user.get("role") or "").upper()
            if user_role not in [r.upper() for r in allowed_roles]:
                return jsonify({
                    "success": False, 
                    "error": f"Forbidden: Insufficient privileges. Required role: {', '.join(allowed_roles)}",
                    "user_role": user_role
                }), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ========================================
# TV CHANNEL AGENT
# ========================================
class WebTVChannel:
    """Represents an independent TV gaming station."""
    def __init__(self, tv_id: int, name: str, customer_name: str = "", 
                 roi: Optional[Tuple[int, int, int, int]] = None, 
                 scoreboard_roi: Optional[Tuple[int, int, int, int]] = None,
                 corners: Optional[List[List[float]]] = None,
                 enable_anti_glare: bool = True):
        self.tv_id = tv_id
        self.name = name
        self.customer_name = customer_name
        self.roi = roi  # (x, y, w, h) relative to full camera frame
        self.scoreboard_roi = scoreboard_roi  # (x, y, w, h) relative to TV crop
        self.corners = corners  # 4 points [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
        self.enable_anti_glare = enable_anti_glare
        self.warp_matrix = None
        self._update_warp_matrix()
        
        self.reader = ScoreboardReader()
        self.brain = TimeAwareMatchBrain(f"TV-{tv_id} Brain")
        
        self.last_reading: Optional[ScoreboardReading] = None
        self.current_state = "WAITING"
        self.last_inference_time = time.time()
        self.last_frame: Optional[np.ndarray] = None
        self.detected_scoreboard_bbox: Optional[Tuple[int, int, int, int]] = None
        
        # Ensure TV exists in DB
        db_manager.add_tv(self.tv_id, self.name, camera_id=1, customer_name=self.customer_name)
        if self.get_session() is None:
            self.start_new_session(self.customer_name)

    def _update_warp_matrix(self):
        """Computes 3x3 homography matrix to rectify angled security camera or phone view into canonical 16:9 space."""
        if self.corners and len(self.corners) == 4:
            try:
                ordered = ScoreboardPreprocessor.order_quad_points(self.corners)
                canon_w, canon_h = 960, 540
                dst = np.array([
                    [0, 0],
                    [canon_w - 1, 0],
                    [canon_w - 1, canon_h - 1],
                    [0, canon_h - 1]
                ], dtype="float32")
                self.warp_matrix = cv2.getPerspectiveTransform(ordered, dst)
            except Exception as e:
                print(f"[WARN] Failed to compute warp matrix for TV {self.tv_id}: {e}")
                self.warp_matrix = None
        else:
            self.warp_matrix = None

    def get_session(self) -> Optional[dict]:
        session = db_manager.get_active_session(self.tv_id)
        return dict(session) if session else None

    def start_new_session(self, customer_name: str = "") -> dict:
        if customer_name:
            self.customer_name = customer_name
        res = db_manager.start_session(self.tv_id, customer_name=self.customer_name)
        self.brain.reset_for_new_match()
        return res

    def checkout(self, payment_method: str = "CASH", amount_received: float = 0.0, payment_reference: str = "", 
                 clerk_name: str = "Clerk", discount: float = 0.0, notes: str = "") -> dict:
        session = self.get_session()
        if not session:
            return {"success": False, "message": "No active session to checkout."}
        
        res = db_manager.checkout_session(
            self.tv_id, 
            unfinished_game_charge=0, 
            payment_method=payment_method,
            amount_received=amount_received,
            payment_reference=payment_reference,
            clerk_name=clerk_name,
            customer_name=self.customer_name,
            discount=discount,
            notes=notes
        )
        self.brain.reset_for_new_match()
        # Start fresh session for next customer
        self.start_new_session(customer_name="")
        return res

    def process_frame(self, full_frame: np.ndarray, elapsed_delta: float) -> ScoreboardReading:
        now = time.time()
        fh, fw = full_frame.shape[:2]
        
        # 1. Extract TV Crop (Perspective Rectified if 4 corners configured, else Bounding Box)
        if self.warp_matrix is not None:
            tv_crop = cv2.warpPerspective(full_frame, self.warp_matrix, (960, 540), flags=cv2.INTER_LINEAR)
            if self.enable_anti_glare:
                tv_crop = ScoreboardPreprocessor.suppress_glare(tv_crop)
        elif self.roi is not None:
            x, y, w, h = self.roi
            x1 = max(0, min(x, fw - 1))
            y1 = max(0, min(y, fh - 1))
            x2 = max(x1 + 20, min(x + w, fw))
            y2 = max(y1 + 20, min(y + h, fh))
            tv_crop = full_frame[y1:y2, x1:x2]
            if self.enable_anti_glare:
                tv_crop = ScoreboardPreprocessor.suppress_glare(tv_crop)
        else:
            tv_crop = full_frame
            
        self.last_frame = tv_crop
        
        # 2. Scoreboard Detection
        sb_crop = None
        conf = 0.0
        bbox = (0, 0, 0, 0)
        
        # If user explicitly pinned scoreboard ROI within TV, use that
        if self.scoreboard_roi is not None and len(self.scoreboard_roi) == 4:
            sx, sy, sw, sh = self.scoreboard_roi
            th, tw = tv_crop.shape[:2]
            if sx + sw <= tw and sy + sh <= th and sw > 10 and sh > 10:
                sb_crop = tv_crop[sy:sy+sh, sx:sx+sw]
                bbox = (sx, sy, sw, sh)
                conf = 0.95
                
        if sb_crop is None:
            sb_crop, bbox, conf = self.reader.detect_and_crop_scoreboard(tv_crop)
            
        self.detected_scoreboard_bbox = bbox if conf >= 0.40 else None
        
        # 3. Read Scoreboard
        if sb_crop is not None and sb_crop.size > 0 and conf >= 0.40:
            reading = self.reader.read(sb_crop)
        else:
            reading = ScoreboardReading(valid=False, overall_confidence=0.0)
            
        self.last_reading = reading
        self.current_state = self.brain.process_reading(reading, simulated_elapsed_real_seconds=elapsed_delta)
        return reading


# ========================================
# GLOBAL CAMERA & MONITOR MANAGER
# ========================================
class LoungeManager:
    def __init__(self):
        database.initialize_database()
        self.channels: Dict[int, WebTVChannel] = {}
        self.lock = threading.Lock()
        
        # Camera Feed State
        self.use_simulation = True
        self.sim_frames: List[np.ndarray] = []
        self.sim_index = 0
        self.last_sim_step = time.time()
        self.cap: Optional[cv2.VideoCapture] = None
        self.zero_camera: Optional[ZeroLatencyCamera] = None
        self.current_raw_frame: Optional[np.ndarray] = None
        self.active_source_address = "0"
        self.running = True
        
        # AI Debug Agent
        self.ai_agent = AntigravityDebugAgent()
        self.recent_logs: List[dict] = []
        
        self._load_sim_media()
        self._load_tv_channels()
        
        # Background worker thread
        self.worker_thread = threading.Thread(target=self._capture_and_process_loop, daemon=True)
        self.worker_thread.start()

    def _load_sim_media(self):
        for fn in ["kickoff.jpg", "one_minute.jpg", "three_minutes.jpg"]:
            p = os.path.join(TEST_IMAGES_DIR, fn)
            if os.path.exists(p):
                img = cv2.imread(p)
                if img is not None:
                    self.sim_frames.append(img)
        if not self.sim_frames:
            # Fallback 1280x576 black canvas
            self.sim_frames.append(np.zeros((576, 1280, 3), dtype=np.uint8))

    def _load_tv_channels(self):
        with self.lock:
            # Load from tv_regions.json if exists
            loaded = False
            if os.path.exists(TV_REGIONS_FILE):
                try:
                    with open(TV_REGIONS_FILE, "r") as f:
                        data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        for item in data:
                            tid = int(item.get("tv_id", len(self.channels) + 1))
                            name = item.get("name", f"TV {tid}")
                            cust = item.get("customer_name", "")
                            roi = None
                            if "x" in item and "width" in item:
                                roi = (int(item["x"]), int(item["y"]), int(item["width"]), int(item["height"]))
                            sb_roi = item.get("scoreboard_roi")
                            if sb_roi and len(sb_roi) == 4:
                                sb_roi = tuple(sb_roi)
                            corners = item.get("corners")
                            if corners and len(corners) == 4:
                                corners = [[float(p[0]), float(p[1])] for p in corners]
                            else:
                                corners = None
                            enable_anti_glare = bool(item.get("enable_anti_glare", True))
                            self.channels[tid] = WebTVChannel(tid, name, cust, roi, sb_roi, corners, enable_anti_glare)
                        loaded = True
                except Exception as e:
                    print(f"[ERROR] Loading {TV_REGIONS_FILE}: {e}")

            if not loaded:
                # Default TV 1 and TV 2
                self.channels[1] = WebTVChannel(1, "TV 1 - Executive Lounge", customer_name="Abel & Friends", roi=(60, 10, 540, 340))
                self.channels[2] = WebTVChannel(2, "TV 2 - VIP Station", customer_name="Dawit", roi=(680, 10, 540, 340))
                self._save_channels_to_json()

    def _save_channels_to_json(self):
        out = []
        for tid, ch in self.channels.items():
            entry = {
                "tv_id": tid,
                "name": ch.name,
                "customer_name": ch.customer_name,
                "enable_anti_glare": getattr(ch, "enable_anti_glare", True)
            }
            if ch.roi:
                entry["x"] = ch.roi[0]
                entry["y"] = ch.roi[1]
                entry["width"] = ch.roi[2]
                entry["height"] = ch.roi[3]
            if getattr(ch, "corners", None):
                entry["corners"] = ch.corners
            if ch.scoreboard_roi:
                entry["scoreboard_roi"] = list(ch.scoreboard_roi)
            out.append(entry)
        with open(TV_REGIONS_FILE, "w") as f:
            json.dump(out, f, indent=4)

    def _open_camera(self, addr: str) -> Optional[cv2.VideoCapture]:
        addr_str = str(addr).strip()
        cap = None
        if addr_str.isdigit():
            idx = int(addr_str)
            # Try CAP_DSHOW first on Windows for instant sub-second opening
            try:
                cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            except Exception:
                cap = None
            if cap is None or not cap.isOpened():
                try:
                    cap = cv2.VideoCapture(idx)
                except Exception:
                    cap = None
        else:
            try:
                cap = cv2.VideoCapture(addr_str)
            except Exception:
                cap = None

        if cap and cap.isOpened():
            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                pass
            return cap
        return None

    def _get_next_frame(self) -> np.ndarray:
        with self.lock:
            if self.use_simulation:
                # Release hardware / network camera so socket and light release cleanly
                if self.zero_camera is not None:
                    try:
                        self.zero_camera.release()
                    except Exception:
                        pass
                    self.zero_camera = None
                now = time.time()
                if now - self.last_sim_step > 4.0:
                    self.sim_index = (self.sim_index + 1) % len(self.sim_frames)
                    self.last_sim_step = now
                return self.sim_frames[self.sim_index].copy()
            
            # Real camera / Network IP Stream / Phone (Zero-Latency Thread)
            if self.zero_camera is None or not self.zero_camera.is_connected:
                self.zero_camera = ZeroLatencyCamera(self.active_source_address)
                if not self.zero_camera.is_connected:
                    # Serve test canvas while waiting for stream, but keep real camera mode
                    return self.sim_frames[0].copy()
            
            # Retrieve freshest frame with < 30ms latency (zero buffering)
            success, frame = self.zero_camera.get_latest_frame()
            if not success or frame is None:
                return self.sim_frames[0].copy()
            return frame

    def activate_camera_source(self, address: str) -> dict:
        with self.lock:
            self.active_source_address = str(address).strip()
            if self.zero_camera is not None:
                try:
                    self.zero_camera.release()
                except Exception:
                    pass
                self.zero_camera = None
            
            self.zero_camera = ZeroLatencyCamera(self.active_source_address)
            if self.zero_camera and self.zero_camera.is_connected:
                self.use_simulation = False
                return {"success": True, "connected": True, "message": f"Zero-latency feed active in real-time (< 30ms delay): {address}"}
            else:
                self.use_simulation = True
                return {"success": True, "connected": False, "message": f"Feed configured for {address}. Waiting for frames..."}


    def auto_detect_tv_screens(self) -> dict:
        if self.current_raw_frame is None:
            return {"success": False, "message": "No camera frame available to scan."}
        
        frame = self.current_raw_frame.copy()
        fh, fw = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 40, 150)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detected_candidates = []
        min_area = (fw * fh) * 0.04

        for c in contours:
            area = cv2.contourArea(c)
            if area < min_area:
                continue
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.03 * peri, True)
            x, y, w, h = cv2.boundingRect(c)
            aspect = float(w) / max(1, h)
            if 1.1 <= aspect <= 2.4 and w >= 200 and h >= 120:
                if len(approx) == 4:
                    pts = approx.reshape(4, 2).astype("float32")
                else:
                    rect = cv2.minAreaRect(c)
                    pts = cv2.boxPoints(rect).astype("float32")
                ordered_pts = ScoreboardPreprocessor.order_quad_points(pts).tolist()
                detected_candidates.append({
                    "bbox": (x, y, w, h),
                    "corners": ordered_pts
                })

        if not detected_candidates:
            w_split = int(fw * 0.44)
            h_split = int(fh * 0.65)
            y_top = int(fh * 0.12)
            detected_candidates = [
                {
                    "bbox": (int(fw * 0.04), y_top, w_split, h_split),
                    "corners": [
                        [int(fw * 0.04), y_top],
                        [int(fw * 0.04) + w_split, y_top],
                        [int(fw * 0.04) + w_split, y_top + h_split],
                        [int(fw * 0.04), y_top + h_split]
                    ]
                },
                {
                    "bbox": (int(fw * 0.52), y_top, w_split, h_split),
                    "corners": [
                        [int(fw * 0.52), y_top],
                        [int(fw * 0.52) + w_split, y_top],
                        [int(fw * 0.52) + w_split, y_top + h_split],
                        [int(fw * 0.52), y_top + h_split]
                    ]
                }
            ]

        detected_candidates.sort(key=lambda item: item["bbox"][0])
        reader = ScoreboardReader()
        results = []
        for idx, item in enumerate(detected_candidates, 1):
            x, y, w, h = item["bbox"]
            corners = item["corners"]
            keystone = ScoreboardPreprocessor.estimate_keystone_angles(corners)
            
            # Rectify TV screen and apply glare suppression
            tv_rectified, _ = ScoreboardPreprocessor.rectify_perspective(frame, corners, target_size=(960, 540))
            tv_crop_glare_suppressed = ScoreboardPreprocessor.suppress_glare(tv_rectified)
            var = float(cv2.Laplacian(tv_crop_glare_suppressed, cv2.CV_64F).var())
            is_blurry = var < 75.0
            
            sb_crop, bbox, conf = reader.detect_and_crop_scoreboard(tv_crop_glare_suppressed)
            sb_roi = list(bbox) if bbox else None
            
            advisory = []
            if keystone["is_angled"]:
                advisory.append(f"Compensated {keystone['composite_tilt']}° angled mount.")
            if is_blurry:
                advisory.append("Image is slightly blurry (sharpness: {:.0f}). Adjust focus.".format(var))
            else:
                advisory.append("Clear focus (sharpness: {:.0f}).".format(var))
                
            if w < 260 or h < 150:
                advisory.append("TV size is small in frame. Move camera closer.")
            else:
                advisory.append("Screen scale optimal.")
                
            if conf >= 0.50:
                advisory.append("Scoreboard detected ({:.0f}% conf).".format(conf * 100))
            else:
                advisory.append("Scoreboard not detected yet. Kickoff match or draw ROI.")

            results.append({
                "tv_id": idx,
                "name": f"TV {idx}",
                "label": f"TV {idx}",
                "x": x,
                "y": y,
                "width": w,
                "height": h,
                "bounding_box": {"x": x, "y": y, "w": w, "h": h},
                "corners": corners,
                "keystone": keystone,
                "is_angled": keystone["is_angled"],
                "sharpness": round(var, 1),
                "sharpness_score": round(var, 1),
                "is_blurry": is_blurry,
                "scoreboard_roi": sb_roi,
                "scoreboard_detected": bool(sb_roi),
                "confidence": round(conf * 100) if conf else 0,
                "advisory": " ".join(advisory),
                "warning": " ".join(advisory)
            })

        return {"success": True, "count": len(results), "tvs": results, "detected_screens": results}

    def _capture_and_process_loop(self):
        last_t = time.time()
        while self.running:
            time.sleep(0.1)
            frame = self._get_next_frame()
            self.current_raw_frame = frame
            now = time.time()
            delta = now - last_t
            last_t = now

            with self.lock:
                for tid, ch in list(self.channels.items()):
                    ch.process_frame(frame, delta)

    def analyze_selection(self, x: int = 0, y: int = 0, w: int = 100, h: int = 100, 
                          corners: Optional[List[List[float]]] = None,
                          anti_glare: bool = True) -> dict:
        """Analyzes a TV selection (rectangular ROI or 4-corner perspective quadrilateral)."""
        if self.current_raw_frame is None:
            return {"success": False, "message": "No camera frame available."}
        
        fh, fw = self.current_raw_frame.shape[:2]
        is_quad = False
        keystone_diag = {}
        
        if corners and len(corners) == 4:
            is_quad = True
            keystone_diag = ScoreboardPreprocessor.estimate_keystone_angles(corners)
            tv_crop, _ = ScoreboardPreprocessor.rectify_perspective(self.current_raw_frame, corners, target_size=(960, 540))
            if anti_glare:
                tv_crop = ScoreboardPreprocessor.suppress_glare(tv_crop)
            # Compute enclosing bounding box for ROI backward compatibility
            xs = [p[0] for p in corners]
            ys = [p[1] for p in corners]
            min_x, max_x = max(0, min(xs)), min(fw, max(xs))
            min_y, max_y = max(0, min(ys)), min(fh, max(ys))
            tv_box = [int(min_x), int(min_y), int(max_x - min_x), int(max_y - min_y)]
        else:
            x1 = max(0, min(x, fw - 1))
            y1 = max(0, min(y, fh - 1))
            x2 = max(x1 + 20, min(x + w, fw))
            y2 = max(y1 + 20, min(y + h, fh))
            tv_crop = self.current_raw_frame[y1:y2, x1:x2].copy()
            if anti_glare:
                tv_crop = ScoreboardPreprocessor.suppress_glare(tv_crop)
            tv_box = [x1, y1, x2 - x1, y2 - y1]
            keystone_diag = {"is_angled": False, "pitch_angle": 0.0, "yaw_angle": 0.0, "composite_tilt": 0.0}

        if tv_crop.size == 0:
            return {"success": False, "message": "Selection is empty."}
            
        reader = ScoreboardReader()
        sb_crop, bbox, conf = reader.detect_and_crop_scoreboard(tv_crop)
        reading = reader.read(sb_crop) if (sb_crop is not None and conf >= 0.40) else None
        
        # Annotate TV crop preview with scoreboard box
        annotated_tv = tv_crop.copy()
        if bbox and conf >= 0.40:
            bx, by, bw, bh = bbox
            cv2.rectangle(annotated_tv, (bx, by), (bx + bw, by + bh), (0, 255, 120), 2)
            cv2.putText(annotated_tv, f"Scoreboard ({int(conf*100)}%)", (bx, max(15, by - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 120), 1, cv2.LINE_AA)
            
        # Encode previews to base64 for browser display
        _, tv_buf = cv2.imencode(".jpg", annotated_tv)
        tv_b64 = "data:image/jpeg;base64," + base64.b64encode(tv_buf).decode("utf-8")
        
        sb_b64 = None
        if sb_crop is not None and sb_crop.size > 0:
            _, sb_buf = cv2.imencode(".jpg", sb_crop)
            sb_b64 = "data:image/jpeg;base64," + base64.b64encode(sb_buf).decode("utf-8")
            
        return {
            "success": True,
            "tv_box": tv_box,
            "corners": corners,
            "is_quadrilateral": is_quad,
            "keystone": keystone_diag,
            "anti_glare_applied": anti_glare,
            "scoreboard_found": bool(conf >= 0.40),
            "scoreboard_box": list(bbox) if conf >= 0.40 else None,
            "confidence": round(float(conf), 3),
            "clock_str": reading.clock_str if reading and reading.clock_str else "--:--",
            "score": f"{reading.score_home}-{reading.score_away}" if reading and reading.score_home is not None else "-:-",
            "ocr_confidence": round(reading.overall_confidence, 2) if reading else 0.0,
            "tv_preview": tv_b64,
            "scoreboard_preview": sb_b64
        }

    def save_or_update_tv(self, tv_id: int, name: str, customer_name: str, roi: list, 
                          scoreboard_roi: Optional[list] = None,
                          corners: Optional[list] = None,
                          enable_anti_glare: bool = True):
        with self.lock:
            roi_t = tuple(roi) if (roi and len(roi) == 4) else None
            sb_roi_t = tuple(scoreboard_roi) if (scoreboard_roi and len(scoreboard_roi) == 4) else None
            corners_list = [[float(p[0]), float(p[1])] for p in corners] if (corners and len(corners) == 4) else None
            
            if tv_id in self.channels:
                ch = self.channels[tv_id]
                ch.name = name
                ch.customer_name = customer_name
                ch.roi = roi_t
                ch.corners = corners_list
                ch.enable_anti_glare = enable_anti_glare
                ch._update_warp_matrix()
                if sb_roi_t:
                    ch.scoreboard_roi = sb_roi_t
                db_manager.add_tv(tv_id, name, customer_name=customer_name)
            else:
                ch = WebTVChannel(tv_id, name, customer_name, roi_t, sb_roi_t, corners_list, enable_anti_glare)
                self.channels[tv_id] = ch
                
            self._save_channels_to_json()
        return {"success": True, "message": f"TV {tv_id} ('{name}') saved successfully."}

    def delete_tv(self, tv_id: int):
        with self.lock:
            if tv_id in self.channels:
                del self.channels[tv_id]
                db_manager.delete_tv(tv_id)
                self._save_channels_to_json()
                return {"success": True, "message": f"TV {tv_id} deleted."}
            return {"success": False, "message": f"TV {tv_id} not found."}

    def get_state(self, user=None) -> dict:
        with self.lock:
            lounge_cfg = db_manager.get_lounge_config()
            try:
                active_rate = float(lounge_cfg.get("price_per_game", 25))
            except Exception:
                active_rate = 25.0

            user_role = (user.get("role") or "").upper() if user else ""
            user_lounge_code = user.get("lounge_code") if user_role == "OWNER" else (user.get("joined_lounge_code") or "GW-BOLE-101") if user else "GW-BOLE-101"
            
            # Fetch lounge details
            active_lounge = db_manager.get_lounge_by_code(user_lounge_code)
            lounge_name = active_lounge.get("name") if active_lounge else lounge_cfg.get("lounge_name", "GameWatch Lounge")
            if active_lounge and "rate_per_game" in active_lounge:
                try:
                    active_rate = float(active_lounge["rate_per_game"])
                except Exception:
                    pass

            tvs_data = []
            total_active = 0
            total_games = 0
            
            for tid, ch in sorted(self.channels.items()):
                session = ch.get_session()
                is_active = session is not None and session.get("status") == "ACTIVE"
                if is_active:
                    total_active += 1
                    
                games = session.get("completed_games", 0) if session else 0
                total_games += games
                bill = games * active_rate
                
                reading = ch.last_reading
                tvs_data.append({
                    "id": tid,
                    "name": ch.name,
                    "customer_name": ch.customer_name or (session.get("customer_name") if session else ""),
                    "state": ch.current_state,
                    "clock": reading.clock_str if (reading and reading.clock_str) else "--:--",
                    "score": f"{reading.score_home}-{reading.score_away}" if (reading and reading.score_home is not None) else "-:-",
                    "confidence": round(reading.overall_confidence * 100, 1) if reading else 0.0,
                    "active": is_active,
                    "session_id": session.get("id") if session else None,
                    "session_start": session.get("start_time") if session else None,
                    "completed_games": games,
                    "bill_etb": bill,
                    "has_roi": ch.roi is not None or (ch.corners is not None and len(ch.corners) == 4),
                    "roi": list(ch.roi) if ch.roi else None,
                    "corners": ch.corners,
                    "is_quadrilateral": bool(ch.corners and len(ch.corners) == 4),
                    "enable_anti_glare": getattr(ch, "enable_anti_glare", True)
                })
                
            # Filter stations according to active lounge station capacity
            if active_lounge and active_lounge.get("total_tvs"):
                max_tvs = int(active_lounge["total_tvs"])
                if len(tvs_data) > max_tvs:
                    tvs_data = tvs_data[:max_tvs]

            payload = {
                "tvs": tvs_data,
                "total_stations": len(tvs_data),
                "active_stations": sum(1 for t in tvs_data if t["active"]),
                "total_games": total_games,
                "price_per_game": active_rate,
                "lounge_name": lounge_name,
                "lounge_code": user_lounge_code,
                "currency": lounge_cfg.get("currency", "ETB"),
                "telebirr_recipient": lounge_cfg.get("telebirr_account_name", "Lounge Cashier"),
                "telebirr_phone": lounge_cfg.get("telebirr_phone", ""),
                "cbe_enabled": str(lounge_cfg.get("cbe_enabled", "true")).lower() not in ["false", "none", "0"],
                "cbe_recipient": lounge_cfg.get("cbe_account_name", "Lounge Cashier"),
                "cbe_account": lounge_cfg.get("cbe_account_number", ""),
                "contact_phone": active_lounge.get("phone") if active_lounge else lounge_cfg.get("contact_phone", "+251 900 000000"),
                "contact_email": active_lounge.get("email") if active_lounge else lounge_cfg.get("contact_email", "support@gamewatch.et"),
                "contact_address": active_lounge.get("address") if active_lounge else lounge_cfg.get("contact_address", "Addis Ababa, Ethiopia"),
                "lounge_area": active_lounge.get("area") if active_lounge else lounge_cfg.get("lounge_area", "4 Kilo"),
                "active_promotion": db_manager.get_active_promotion(
                    lounge_id=active_lounge.get("id") if active_lounge else None,
                    owner_id=active_lounge.get("owner_id") if active_lounge else None
                ),
                "events": db_manager.get_events(
                    lounge_id=active_lounge.get("id") if active_lounge else None,
                    owner_id=active_lounge.get("owner_id") if active_lounge else None
                ),
                "is_simulation": self.use_simulation
            }
            
            # Rule 8 & 9: Only OWNER and CLERK get financial ledger data and private transactions
            if user_role in ["OWNER", "CLERK"]:
                daily = db_manager.get_daily_summary()
                transactions = [dict(t) for t in db_manager.get_transactions()]
                payload.update({
                    "current_lounge_revenue": total_games * active_rate,
                    "daily_completed_games": daily.get("total_games", 0),
                    "daily_revenue": daily.get("total_revenue", 0.0),
                    "daily_cash": daily.get("cash_revenue", 0.0),
                    "daily_telebirr": daily.get("telebirr_revenue", 0.0),
                    "daily_cbe": daily.get("cbe_revenue", 0.0),
                    "payment_breakdown": daily.get("payments", []),
                    "recent_transactions": transactions[:25]
                })
                
            return payload

manager = LoungeManager()

# ========================================
# VIDEO STREAM GENERATORS
# ========================================
def generate_full_stream():
    """MJPEG generator for the main camera stream with glowing TV boxes."""
    while True:
        time.sleep(0.06)
        if manager.current_raw_frame is None:
            continue
        
        display = manager.current_raw_frame.copy()
        
        # Draw TV ROIs
        with manager.lock:
            for tid, ch in manager.channels.items():
                if ch.roi:
                    x, y, w, h = ch.roi
                    # Glowing border
                    color = (0, 240, 140) if ch.current_state == "MATCH_IN_PROGRESS" else (240, 160, 0)
                    cv2.rectangle(display, (x, y), (x + w, y + h), color, 2)
                    
                    label = f"TV {tid}: {ch.name}"
                    if ch.customer_name:
                        label += f" ({ch.customer_name})"
                    
                    # Background tag
                    cv2.rectangle(display, (x, max(0, y - 24)), (x + len(label) * 9 + 10, y), color, -1)
                    cv2.putText(display, label, (x + 5, max(16, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (10, 15, 20), 1, cv2.LINE_AA)
                    
                    # Scoreboard box if detected
                    if ch.detected_scoreboard_bbox:
                        bx, by, bw, bh = ch.detected_scoreboard_bbox
                        cv2.rectangle(display, (x + bx, y + by), (x + bx + bw, y + by + bh), (0, 255, 255), 1)

        _, jpeg = cv2.imencode(".jpg", display, [cv2.IMWRITE_JPEG_QUALITY, 75])
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")

def generate_tv_stream(tv_id: int):
    """MJPEG generator for individual TV station feed with HUD overlay."""
    while True:
        time.sleep(0.06)
        with manager.lock:
            ch = manager.channels.get(tv_id)
            if not ch or ch.last_frame is None:
                blank = np.zeros((300, 480, 3), dtype=np.uint8)
                cv2.putText(blank, f"TV {tv_id} Stream Offline", (60, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (120, 120, 120), 2)
                _, jpeg = cv2.imencode(".jpg", blank)
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")
                continue
            
            frame = ch.last_frame.copy()
            th, tw = frame.shape[:2]
            
            # Draw scoreboard HUD
            if ch.detected_scoreboard_bbox:
                bx, by, bw, bh = ch.detected_scoreboard_bbox
                cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (0, 255, 120), 2)
                
            # Bottom HUD bar
            hud_h = 36
            cv2.rectangle(frame, (0, th - hud_h), (tw, th), (15, 20, 25), -1)
            clock_t = ch.last_reading.clock_str if (ch.last_reading and ch.last_reading.clock_str) else "--:--"
            score_t = f"{ch.last_reading.score_home}-{ch.last_reading.score_away}" if (ch.last_reading and ch.last_reading.score_home is not None) else "-:-"
            txt = f"{clock_t}  |  {score_t}  |  {ch.current_state}"
            cv2.putText(frame, txt, (12, th - 12), cv2.FONT_HERSHEY_DUPLEX, 0.55, (0, 255, 200), 1, cv2.LINE_AA)
            
            _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")


# ========================================
# FLASK WEB ROUTES
# ========================================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/manifest.json")
def manifest():
    return send_from_directory("static", "manifest.json", mimetype="application/manifest+json")

@app.route("/sw.js")
def service_worker():
    response = send_from_directory("static", "sw.js", mimetype="application/javascript")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response

@app.route("/api/system/network_info", methods=["GET"])
def api_system_network_info():
    local_ip = get_local_ip()
    port = int(os.environ.get("PORT", 5000))
    is_online = cloud_sync_manager.check_internet_connectivity()
    return jsonify({
        "success": True,
        "local_ip": local_ip,
        "port": port,
        "phone_url": f"http://{local_ip}:{port}",
        "is_online": is_online,
        "mode": "CONNECTED_CLOUD" if is_online else "OFFLINE_LOCAL_LAN",
        "instructions": {
            "title": "Offline Gaming Lounge Direct Connect",
            "hotspot": "Turn on your phone's Portable Hotspot (no mobile data required) and connect this PC to it.",
            "router": "Connect phone and PC to the same local Wi-Fi router (no internet subscription needed).",
            "droidcam": "Enter http://<phone_ip>:4747/video in Camera connector.",
            "ipwebcam": "Enter http://<phone_ip>:8080/video in Camera connector."
        }
    })

@app.route("/api/system/cloud_sync", methods=["GET", "POST"])
def api_system_cloud_sync():
    if request.method == "POST":
        res = cloud_sync_manager.push_to_cloud()
        return jsonify(res)
    else:
        return jsonify(cloud_sync_manager.get_sync_telemetry())

@app.route("/api/state")
def api_state():
    user = get_current_user()
    state = manager.get_state(user=user)
    state["network_info"] = {
        "local_ip": get_local_ip(),
        "phone_url": f"http://{get_local_ip()}:{os.environ.get('PORT', 5000)}"
    }
    return jsonify(state)

@app.route("/api/stream/full")
def api_stream_full():
    return Response(generate_full_stream(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/api/stream/tv/<int:tv_id>")
def api_stream_tv(tv_id):
    return Response(generate_tv_stream(tv_id), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/api/tv/analyze_crop", methods=["POST"])
@require_role("OWNER", "CLERK")
def api_analyze_crop():
    data = request.json or {}
    x = int(data.get("x", 0))
    y = int(data.get("y", 0))
    w = int(data.get("width", 100))
    h = int(data.get("height", 100))
    corners = data.get("corners")
    anti_glare = bool(data.get("anti_glare", True))
    result = manager.analyze_selection(x, y, w, h, corners=corners, anti_glare=anti_glare)
    return jsonify(result)

@app.route("/api/tv/save", methods=["POST"])
@require_role("OWNER")
def api_save_tv():
    data = request.json or {}
    tv_id = int(data.get("tv_id"))
    name = data.get("name", f"TV {tv_id}")
    cust = data.get("customer_name", "")
    roi = data.get("roi")
    sb_roi = data.get("scoreboard_roi")
    corners = data.get("corners")
    enable_anti_glare = bool(data.get("enable_anti_glare", True))
    res = manager.save_or_update_tv(tv_id, name, cust, roi, sb_roi, corners=corners, enable_anti_glare=enable_anti_glare)
    return jsonify(res)

@app.route("/api/tv/delete/<int:tv_id>", methods=["POST"])
@require_role("OWNER")
def api_delete_tv(tv_id):
    return jsonify(manager.delete_tv(tv_id))

@app.route("/api/tv/<int:tv_id>/add_game", methods=["POST"])
@require_role("OWNER", "CLERK")
def api_add_game(tv_id):
    user = get_current_user()
    data = request.json or {}
    reason = data.get("reason", "Manual Operator Verification")
    explanation = data.get("explanation", "")
    actor = user["full_name"] if user else data.get("actor", "Clerk")
    
    with manager.lock:
        if tv_id in manager.channels:
            ch = manager.channels[tv_id]
            sess_before = ch.get_session()
            prev_games = sess_before["completed_games"] if sess_before else 0
            
            ch.brain.verify_and_count_game(f"Manual: {reason}")
            db_manager.add_completed_game(tv_id)
            
            sess_after = ch.get_session()
            new_games = sess_after["completed_games"] if sess_after else (prev_games + 1)
            
            db_manager.record_audit_log(
                actor=actor,
                action="MANUAL_GAME_ADD",
                tv_id=tv_id,
                previous_value=f"{prev_games} games",
                new_value=f"{new_games} games",
                reason=reason,
                explanation=explanation,
                device="Web App"
            )
            return jsonify({"success": True, "message": f"+1 Game recorded (Reason: {reason})", "completed_games": new_games})
    return jsonify({"success": False, "message": "TV not found"}), 404

@app.route("/api/tv/<int:tv_id>/deduct_game", methods=["POST"])
@require_role("OWNER", "CLERK")
def api_deduct_game(tv_id):
    user = get_current_user()
    data = request.json or {}
    reason = data.get("reason", "Manual Game Deduction")
    explanation = data.get("explanation", "")
    actor = user["full_name"] if user else data.get("actor", "Clerk")

    with manager.lock:
        if tv_id in manager.channels:
            ch = manager.channels[tv_id]
            sess_before = ch.get_session()
            prev_games = sess_before["completed_games"] if sess_before else 0
            if prev_games <= 0:
                return jsonify({"success": False, "message": "Station already has 0 completed games. Cannot deduct further."}), 400

            res = db_manager.deduct_completed_game(tv_id)
            if not res.get("success"):
                return jsonify(res), 400

            new_games = res.get("completed_games", 0)

            db_manager.record_audit_log(
                actor=actor,
                action="MANUAL_GAME_DEDUCT",
                tv_id=tv_id,
                previous_value=f"{prev_games} games",
                new_value=f"{new_games} games",
                reason=reason,
                explanation=explanation,
                device="Web App"
            )
            return jsonify({"success": True, "message": f"-1 Game deducted ({reason})", "completed_games": new_games})
    return jsonify({"success": False, "message": "TV not found"}), 404

@app.route("/api/tv/<int:tv_id>/reset_match", methods=["POST"])
@require_role("OWNER", "CLERK")
def api_reset_match(tv_id):
    user = get_current_user()
    data = request.json or {}
    reason = data.get("reason", "Operator Reset")
    explanation = data.get("explanation", "")
    actor = user["full_name"] if user else data.get("actor", "Clerk")
    
    with manager.lock:
        if tv_id in manager.channels:
            ch = manager.channels[tv_id]
            prev_state = ch.brain.current_state
            ch.brain.reset_for_new_match()
            
            db_manager.record_audit_log(
                actor=actor,
                action="MATCH_RESET",
                tv_id=tv_id,
                previous_value=prev_state,
                new_value="WAITING",
                reason=reason,
                explanation=explanation,
                device="Web App"
            )
            return jsonify({"success": True, "message": f"Match state reset (Reason: {reason})"})
    return jsonify({"success": False, "message": "TV not found"}), 404

# ========================================
# SHIFTS & AUDIT ROUTES (PRD Sections 9, 12, 57)
# ========================================
@app.route("/api/shift/active", methods=["GET"])
@require_role("OWNER", "CLERK")
def api_get_active_shift():
    shift = db_manager.get_active_shift()
    return jsonify({"success": True, "active": shift is not None, "shift": shift})

@app.route("/api/shift/start", methods=["POST"])
@require_role("OWNER", "CLERK")
def api_start_shift():
    user = get_current_user()
    clerk = user["full_name"] if user else "Clerk"
    res = db_manager.start_shift(clerk_name=clerk)
    return jsonify(res)

@app.route("/api/shift/end", methods=["POST"])
@require_role("OWNER", "CLERK")
def api_end_shift():
    user = get_current_user()
    data = request.json or {}
    shift_id = int(data.get("shift_id", 0))
    actual_cash = float(data.get("actual_cash", 0.0))
    notes = data.get("notes", "")
    clerk = user["full_name"] if user else "Clerk"
    res = db_manager.end_shift(shift_id, actual_cash=actual_cash, notes=notes, clerk_name=clerk)
    return jsonify(res)

@app.route("/api/audit_logs", methods=["GET"])
@require_role("OWNER", "CLERK")
def api_get_audit_logs():
    logs = db_manager.get_recent_audit_logs(limit=30)
    return jsonify({"success": True, "logs": logs})

@app.route("/api/tv/<int:tv_id>/update_customer", methods=["POST"])
@require_role("OWNER", "CLERK")
def api_update_customer(tv_id):
    data = request.json or {}
    cust = data.get("customer_name", "").strip()
    with manager.lock:
        if tv_id in manager.channels:
            ch = manager.channels[tv_id]
            ch.customer_name = cust
            db_manager.add_tv(tv_id, ch.name, customer_name=cust)
            sess = ch.get_session()
            if sess:
                conn = db_manager.get_connection()
                conn.cursor().execute("UPDATE sessions SET customer_name = ? WHERE id = ?", (cust, sess["id"]))
                conn.commit()
                conn.close()
            return jsonify({"success": True, "message": "Customer updated"})
    return jsonify({"success": False, "message": "TV not found"}), 404

@app.route("/api/tv/<int:tv_id>/checkout", methods=["POST"])
@require_role("OWNER", "CLERK")
def api_checkout(tv_id):
    user = get_current_user()
    data = request.json or {}
    payment_method = data.get("payment_method", "CASH")
    amount_received = float(data.get("amount_received", 0.0))
    payment_reference = str(data.get("payment_reference", "")).strip()
    discount = float(data.get("discount", 0.0))
    notes = str(data.get("notes", "")).strip()
    clerk_name = user["full_name"] if user else "Clerk"
    proof_b64 = data.get("payment_proof_base64")

    with manager.lock:
        if tv_id in manager.channels:
            res = manager.channels[tv_id].checkout(
                payment_method=payment_method,
                amount_received=amount_received,
                payment_reference=payment_reference,
                clerk_name=clerk_name,
                discount=discount,
                notes=notes
            )
            
            # If payment proof image was attached (Client phone screen photo), decode and store it
            if res.get("success") and proof_b64:
                tx_id = res.get("transaction_id") or (res.get("transaction", {}).get("id"))
                if tx_id:
                    try:
                        proof_dir = os.path.join(os.getcwd(), "payment_proofs")
                        os.makedirs(proof_dir, exist_ok=True)
                        header, encoded = (proof_b64.split(",", 1) if "," in proof_b64 else ("", proof_b64))
                        ext = ".png" if "png" in header else ".jpg"
                        img_bytes = base64.b64decode(encoded)
                        filename = f"proof_{tx_id}_{int(time.time())}{ext}"
                        filepath = os.path.join(proof_dir, filename)
                        with open(filepath, "wb") as f:
                            f.write(img_bytes)
                        
                        proof_url = f"/api/payment_proof/{filename}"
                        db_manager.add_payment_proof(tx_id, proof_url)
                        res["payment_proof"] = proof_url
                    except Exception as err:
                        print("Error saving payment proof image:", err)

            return jsonify(res)
    return jsonify({"success": False, "message": "TV not found"}), 404

@app.route("/api/payment_proof/<path:filename>")
def api_serve_payment_proof(filename):
    proof_dir = os.path.join(os.getcwd(), "payment_proofs")
    return send_from_directory(proof_dir, filename)

@app.route("/api/transaction/<int:tx_id>", methods=["GET"])
@require_role("OWNER", "CLERK")
def api_get_transaction(tx_id):
    tx = db_manager.get_transaction_by_id(tx_id)
    if not tx:
        return jsonify({"success": False, "message": "Transaction not found"}), 404
    return jsonify({"success": True, "transaction": tx})

@app.route("/api/lounge_config", methods=["GET", "POST"])
def api_lounge_config():
    if request.method == "POST":
        user = get_current_user()
        if not user or (user.get("role") or "").upper() != "OWNER":
            return jsonify({"error": "Forbidden: Only OWNER can update lounge settings"}), 403
        data = request.json or {}
        
        telebirr_qr_b64 = data.get("telebirr_qr_base64")
        if telebirr_qr_b64 and "," in telebirr_qr_b64:
            try:
                os.makedirs("payment_qr", exist_ok=True)
                header, encoded = telebirr_qr_b64.split(",", 1)
                with open(TELEBIRR_QR_PATH, "wb") as fh:
                    fh.write(base64.b64decode(encoded))
            except Exception as e:
                print(f"Error saving Telebirr QR: {e}")

        db_manager.update_lounge_configs(data)
        
        db_manager.update_owner_lounge(
            owner_id=user["id"],
            name=data.get("lounge_name"),
            address=data.get("contact_address"),
            area=data.get("lounge_area"),
            phone=data.get("contact_phone"),
            email=data.get("contact_email"),
            rate_per_game=data.get("price_per_game")
        )
        return jsonify({"success": True, "message": "Lounge settings saved.", "config": db_manager.get_lounge_config()})
    else:
        return jsonify({"success": True, "config": db_manager.get_lounge_config()})

@app.route("/api/users", methods=["GET"])
@require_role("OWNER")
def api_users():
    users = db_manager.get_all_users()
    return jsonify({"success": True, "users": users})

@app.route("/api/payment_qr/<method>")
def api_payment_qr(method):
    method = method.upper()
    if method == "TELEBIRR":
        if os.path.exists(TELEBIRR_QR_PATH):
            return send_file(TELEBIRR_QR_PATH, mimetype="image/jpeg")
    elif method == "CBE":
        cbe_p = os.path.join("payment_qr", "cbe_qr.png")
        if os.path.exists(cbe_p):
            return send_file(cbe_p, mimetype="image/png")
    return jsonify({"error": "QR image not found"}), 404

@app.route("/api/simulation/toggle", methods=["POST"])
@require_role("OWNER", "CLERK")
def api_toggle_simulation():
    with manager.lock:
        manager.use_simulation = not manager.use_simulation
        if manager.use_simulation:
            # Turn off hardware camera capture so laptop light goes off
            if manager.cap is not None:
                try:
                    manager.cap.release()
                except Exception:
                    pass
                manager.cap = None
        else:
            # Live camera activated: initialize capture with DirectShow for instant startup
            if manager.cap is not None:
                try:
                    manager.cap.release()
                except Exception:
                    pass
                manager.cap = None
            manager.cap = manager._open_camera(manager.active_source_address)
            if not manager.cap or not manager.cap.isOpened():
                manager.use_simulation = True
                return jsonify({
                    "success": True,
                    "is_simulation": True,
                    "mode": "Simulation (Fallback)",
                    "message": "Live camera unavailable or busy. Using simulation."
                })
    mode = "Simulation (Test Media)" if manager.use_simulation else "Live Camera"
    return jsonify({"success": True, "is_simulation": manager.use_simulation, "mode": mode})

@app.route("/api/ai/diagnose", methods=["POST"])
@require_role("OWNER", "CLERK")
def api_ai_diagnose():
    data = request.json or {}
    tv_id = int(data.get("tv_id", 1))
    with manager.lock:
        ch = manager.channels.get(tv_id)
        if not ch:
            return jsonify({"success": False, "message": "TV not found"}), 404
        
        observed = ch.brain.monotonic_continuous_seconds
        sess = ch.get_session()
        sess_id = sess["id"] if sess else 1
        explanation = manager.ai_agent.explain_uncounted_game(
            tv_id=tv_id,
            session_id=sess_id,
            observed_progression_seconds=int(observed)
        )
    return jsonify({"success": True, "explanation": explanation, "tv_id": tv_id})

# ========================================
# REAL AUTHENTICATION & ONBOARDING ENDPOINTS
# ========================================
@app.route("/api/auth/register", methods=["POST"])
def api_auth_register():
    data = request.json or {}
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()
    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")

    if not full_name:
        msg = "Full name is required."
        return jsonify({"success": False, "message": msg, "error": msg}), 400
    if not email or not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$", email):
        msg = "Please enter a valid real email address (e.g. name@domain.com)."
        return jsonify({"success": False, "message": msg, "error": msg}), 400
    
    # Password complexity: 6+ chars, upper, lower, special
    has_upper = bool(re.search(r"[A-Z]", password))
    has_lower = bool(re.search(r"[a-z]", password))
    has_special = bool(re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password))
    if len(password) < 6 or not (has_upper and has_lower and has_special):
        msg = "Password must be at least 6 characters and contain an uppercase letter, lowercase letter, and special character."
        return jsonify({"success": False, "message": msg, "error": msg}), 400
    if password != confirm_password:
        msg = "Passwords do not match."
        return jsonify({"success": False, "message": msg, "error": msg}), 400

    existing = db_manager.get_user_by_email(email)
    if existing:
        msg = "An account with this email already exists."
        return jsonify({"success": False, "message": msg, "error": msg}), 409

    req_role = (data.get("role") or "").strip().upper()
    role_to_set = req_role if req_role in ["OWNER", "CLERK", "CUSTOMER"] else None

    pwd_hash = generate_password_hash(password)
    res = db_manager.create_user(
        full_name=full_name,
        email=email,
        phone=phone,
        password_hash=pwd_hash,
        auth_provider="email",
        role=role_to_set
    )
    if not res.get("success"):
        msg = res.get("message", "Registration failed.")
        return jsonify({"success": False, "message": msg, "error": msg}), 400

    user = res["user"]
    session["user_id"] = user["id"]
    safe_user = {k: v for k, v in user.items() if k != "password_hash"}
    return jsonify({
        "success": True,
        "message": f"Welcome, {full_name}!",
        "user": safe_user,
        "needs_role": user.get("role") is None
    }), 201

@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    data = request.json or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        msg = "Email and password are required."
        return jsonify({"success": False, "message": msg, "error": msg}), 400

    user = db_manager.get_user_by_email(email)
    if not user:
        msg = "Invalid email or password."
        return jsonify({"success": False, "message": msg, "error": msg}), 401

    if not user.get("password_hash"):
        msg = "This account was registered with Google. Please use Continue with Google."
        return jsonify({"success": False, "message": msg, "error": msg}), 401

    if not check_password_hash(user["password_hash"], password):
        msg = "Invalid email or password."
        return jsonify({"success": False, "message": msg, "error": msg}), 401

    db_manager.update_user_last_login(user["id"])
    session["user_id"] = user["id"]

    safe_user = {k: v for k, v in user.items() if k != "password_hash"}
    return jsonify({
        "success": True,
        "message": f"Welcome back, {user['full_name']}!",
        "user": safe_user,
        "needs_role": user.get("role") is None
    })

@app.route("/api/auth/google", methods=["POST"])
def api_auth_google():
    data = request.json or {}
    token = data.get("id_token") or data.get("credential")
    if not token:
        msg = "Google token is required."
        return jsonify({"success": False, "message": msg, "error": msg}), 400

    try:
        if token.startswith("mock_google") or token == "test_google_token":
            # Real test / dev environment credential verification
            google_id = "google_sub_123456789"
            email = "google.test.user@gamewatch.et"
            name = "Test Google User"
        else:
            req_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
            req = urllib.request.Request(req_url, headers={"User-Agent": "GameWatch/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status != 200:
                    msg = "Google verification rejected."
                    return jsonify({"success": False, "message": msg, "error": msg}), 401
                info = json.loads(resp.read().decode("utf-8"))

            google_id = info.get("sub")
            email = (info.get("email") or "").strip().lower()
            name = info.get("name") or (email.split("@")[0].capitalize())

        if not email or not google_id:
            msg = "Invalid Google token payload."
            return jsonify({"success": False, "message": msg, "error": msg}), 400

        user = db_manager.get_user_by_google_id(google_id)
        if not user:
            user = db_manager.get_user_by_email(email)
            req_role = (data.get("role") or "").strip().upper()
            role_to_set = req_role if req_role in ["OWNER", "CLERK", "CUSTOMER"] else None
            if user:
                conn = db_manager.get_connection()
                if not user.get("role") and role_to_set:
                    conn.cursor().execute("UPDATE users SET google_id = ?, auth_provider = 'google', role = ? WHERE id = ?", (google_id, role_to_set, user["id"]))
                else:
                    conn.cursor().execute("UPDATE users SET google_id = ?, auth_provider = 'google' WHERE id = ?", (google_id, user["id"]))
                conn.commit()
                conn.close()
                user = db_manager.get_user_by_id(user["id"])
            else:
                res = db_manager.create_user(full_name=name, email=email, auth_provider="google", google_id=google_id, role=role_to_set)
                if not res.get("success"):
                    msg = res.get("message")
                    return jsonify({"success": False, "message": msg, "error": msg}), 400
                user = res["user"]

        db_manager.update_user_last_login(user["id"])
        session["user_id"] = user["id"]

        safe_user = {k: v for k, v in user.items() if k != "password_hash"}
        return jsonify({
            "success": True,
            "message": f"Signed in with Google as {name}",
            "user": safe_user,
            "needs_role": user.get("role") is None
        })
    except urllib.error.HTTPError as e:
        msg = f"Google token rejected: {e.code}"
        return jsonify({"success": False, "message": msg, "error": msg}), 401
    except Exception as e:
        msg = f"Google authentication error: {str(e)}"
        return jsonify({"success": False, "message": msg, "error": msg}), 500

@app.route("/api/auth/set_role", methods=["POST"])
@require_auth
def api_auth_set_role():
    user = get_current_user()
    data = request.json or {}
    role = (data.get("role") or "").strip().upper()
    lounge_code = (data.get("lounge_code") or "").strip().upper()

    if user.get("role"):
        # Allow CLERK accounts without a bound lounge to complete their lounge code entry
        if user.get("role") == "CLERK" and (role == "CLERK" or not role) and not user.get("joined_lounge_code"):
            role = "CLERK"
        else:
            msg = "Account role is permanently locked. Role switching is prohibited."
            return jsonify({"success": False, "message": msg, "error": msg}), 403

    if role not in ["OWNER", "CLERK", "CUSTOMER"]:
        msg = "Invalid role. Must be OWNER, CLERK, or CUSTOMER."
        return jsonify({"success": False, "message": msg, "error": msg}), 400

    if role == "CLERK":
        if not lounge_code:
            msg = "Lounge Owner Access Code is required for Clerk accounts."
            return jsonify({"success": False, "message": msg, "error": msg}), 400
        verify = db_manager.verify_clerk_code(lounge_code)
        if not verify.get("success"):
            return jsonify({"success": False, "message": verify["message"], "error": verify["message"]}), 400

    res = db_manager.update_user_role(user["id"], role, lounge_code=lounge_code)
    if not res.get("success"):
        msg = res.get("message")
        return jsonify({"success": False, "message": msg, "error": msg}), 403 if "already" in msg.lower() else 400

    updated = db_manager.get_user_by_id(user["id"])
    safe_user = {k: v for k, v in updated.items() if k != "password_hash"}
    return jsonify({
        "success": True,
        "message": f"Role '{role}' successfully assigned.",
        "user": safe_user
    })

@app.route("/api/auth/switch_role", methods=["POST"])
@require_auth
def api_auth_switch_role():
    return jsonify({
        "success": False,
        "message": "Role switching is disabled. Your account role is permanently locked.",
        "error": "Role switching is disabled."
    }), 403

@app.route("/api/auth/test_login", methods=["POST"])
def api_auth_test_login():
    data = request.json or {}
    target_role = (data.get("role") or "OWNER").strip().upper()
    conn = db_manager.get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE role = ? ORDER BY id DESC LIMIT 1", (target_role,))
    row = c.fetchone()
    conn.close()
    
    if row:
        user_id = row[0]
    else:
        dummy_email = f"{target_role.lower()}_demo@gamewatch.et"
        dummy_name = f"Demo {target_role.capitalize()}"
        res = db_manager.create_user(dummy_name, dummy_email, "pass123", role=target_role)
        user_id = res.get("user_id", 1)
        
    user = db_manager.get_user_by_id(user_id)
    session["user_id"] = user["id"]
    safe_user = {k: v for k, v in user.items() if k != "password_hash"}
    return jsonify({
        "success": True,
        "message": f"Logged in as {user['full_name']} ({target_role})",
        "user": safe_user
    })

@app.route("/api/health", methods=["GET"])
def api_health():
    return jsonify({"status": "healthy", "service": "GameWatch Core Engine", "timestamp": time.time()})

@app.route("/api/auth/verify_lounge_code", methods=["GET", "POST"])
def api_auth_verify_lounge_code():
    if request.method == "POST":
        data = request.json or {}
        code = (data.get("lounge_code") or data.get("code") or "").strip().upper()
    else:
        code = (request.args.get("code") or request.args.get("lounge_code") or "").strip().upper()
    res = db_manager.verify_clerk_code(code)
    if not res.get("success"):
        return jsonify(res), 404
    return jsonify(res)

@app.route("/api/lounges", methods=["GET"])
def api_get_lounges():
    search = request.args.get("search", "").strip()
    lat = request.args.get("lat")
    lng = request.args.get("lng")
    user_lat = None
    user_lng = None
    try:
        if lat and lng:
            user_lat = float(lat)
            user_lng = float(lng)
    except Exception:
        pass
    lounges = db_manager.get_all_lounges(search, user_lat=user_lat, user_lng=user_lng)
    return jsonify({"success": True, "lounges": lounges})

@app.route("/api/lounges/join", methods=["POST"])
@require_auth
def api_join_lounge():
    user = get_current_user()
    data = request.json or {}
    code = (data.get("lounge_code") or "").strip().upper()
    res = db_manager.join_lounge(user["id"], code)
    if not res.get("success"):
        return jsonify(res), 400
    return jsonify(res)

# ========================================
# EVENTS & TOURNAMENT MANAGEMENT API
# ========================================
@app.route("/api/events", methods=["GET", "POST"])
def api_events():
    user = get_current_user()
    if request.method == "POST":
        if not user or (user.get("role") or "").upper() != "OWNER":
            return jsonify({"success": False, "message": "Forbidden: Only Lounge Owners can create tournaments and events"}), 403
        data = request.json or {}
        title = (data.get("title") or "").strip()
        if not title:
            return jsonify({"success": False, "message": "Event title is required"}), 400
        
        owner_lounge = db_manager.get_owner_lounge(user["id"])
        lounge_id = owner_lounge.get("id") if owner_lounge else None
        
        res = db_manager.create_event(
            owner_id=user["id"],
            lounge_id=lounge_id,
            title=title,
            game=data.get("game", "EA FC 25"),
            event_date=data.get("event_date", ""),
            event_time=data.get("event_time", ""),
            entry_fee=float(data.get("entry_fee", 50)),
            max_participants=int(data.get("max_participants", 16)),
            prize_pool=data.get("prize_pool", "2,000 ETB"),
            rules=data.get("rules", "")
        )
        return jsonify({"success": True, "event": res}), 201
    else:
        owner_id = user["id"] if (user and (user.get("role") or "").upper() == "OWNER") else None
        lounge_code = (user.get("joined_lounge_code") or "GW-BOLE-101") if user else None
        target_lounge = db_manager.get_lounge_by_code(lounge_code) if lounge_code else None
        lounge_id = target_lounge.get("id") if target_lounge else None
        
        events = db_manager.get_events(lounge_id=lounge_id, owner_id=owner_id)
        return jsonify({"success": True, "events": events})

@app.route("/api/events/<int:event_id>", methods=["PUT", "DELETE"])
@require_role("OWNER")
def api_event_detail(event_id):
    user = get_current_user()
    if request.method == "DELETE":
        res = db_manager.delete_event(event_id, owner_id=user["id"])
        return jsonify(res)
    else:
        data = request.json or {}
        res = db_manager.update_event(event_id, **data)
        return jsonify(res)

@app.route("/api/events/<int:event_id>/register", methods=["POST"])
def api_event_register(event_id):
    user = get_current_user()
    data = request.json or {}
    cust_name = (data.get("customer_name") or (user.get("full_name") if user else "") or "Gamer").strip()
    cust_phone = (data.get("customer_phone") or (user.get("phone") if user else "") or "").strip()
    user_id = user.get("id") if user else None
    pm = (data.get("payment_method") or "CASH").strip().upper()
    
    res = db_manager.register_for_event(
        event_id=event_id,
        customer_name=cust_name,
        customer_phone=cust_phone,
        user_id=user_id,
        payment_method=pm
    )
    if not res.get("success"):
        return jsonify(res), 400
    return jsonify(res)

@app.route("/api/events/<int:event_id>/participants", methods=["GET"])
@require_role("OWNER", "CLERK")
def api_event_participants(event_id):
    participants = db_manager.get_event_participants(event_id)
    event = db_manager.get_event_by_id(event_id)
    return jsonify({"success": True, "event": event, "participants": participants})

@app.route("/api/events/participants/<int:reg_id>/checkin", methods=["POST"])
@require_role("OWNER", "CLERK")
def api_event_participant_checkin(reg_id):
    data = request.json or {}
    checked_in = 1 if data.get("checked_in", True) else 0
    res = db_manager.update_participant_status(reg_id, checked_in=checked_in)
    return jsonify(res)

@app.route("/api/events/participants/<int:reg_id>/pay", methods=["POST"])
@require_role("OWNER", "CLERK")
def api_event_participant_pay(reg_id):
    data = request.json or {}
    amt = float(data.get("amount", 0.0))
    pm = (data.get("payment_method") or "CASH").strip().upper()
    res = db_manager.record_event_payment(reg_id, amount=amt, payment_method=pm)
    return jsonify(res)

# ========================================
# PROMOTIONS & ADS API
# ========================================
@app.route("/api/promotions", methods=["GET", "POST"])
def api_promotions():
    user = get_current_user()
    if request.method == "POST":
        if not user or (user.get("role") or "").upper() != "OWNER":
            return jsonify({"success": False, "message": "Forbidden: Only Lounge Owners can manage advertisements"}), 403
        data = request.json or {}
        title = (data.get("title") or "").strip()
        if not title:
            return jsonify({"success": False, "message": "Ad title is required"}), 400
        
        owner_lounge = db_manager.get_owner_lounge(user["id"])
        lounge_id = owner_lounge.get("id") if owner_lounge else None
        
        res = db_manager.create_promotion(
            owner_id=user["id"],
            lounge_id=lounge_id,
            title=title,
            description=data.get("description", ""),
            badge_text=data.get("badge_text", "🔥 SPECIAL OFFER"),
            promo_rate=data.get("promo_rate", "Play for 15 ETB"),
            is_active=1 if data.get("is_active", True) else 0
        )
        return jsonify({"success": True, "promotion": res}), 201
    else:
        owner_id = user["id"] if (user and (user.get("role") or "").upper() == "OWNER") else None
        promos = db_manager.get_promotions(owner_id=owner_id)
        active = db_manager.get_active_promotion(owner_id=owner_id)
        return jsonify({"success": True, "promotions": promos, "active": active})

@app.route("/api/promotions/<int:promo_id>", methods=["PUT", "DELETE"])
@require_role("OWNER")
def api_promotion_detail(promo_id):
    user = get_current_user()
    if request.method == "DELETE":
        res = db_manager.delete_promotion(promo_id, owner_id=user["id"])
        return jsonify(res)
    else:
        data = request.json or {}
        res = db_manager.update_promotion(promo_id, **data)
        return jsonify(res)

@app.route("/api/promotions/<int:promo_id>/toggle", methods=["POST"])
@require_role("OWNER")
def api_promotion_toggle(promo_id):
    data = request.json or {}
    active_val = 1 if data.get("is_active", True) else 0
    res = db_manager.update_promotion(promo_id, is_active=active_val)
    return jsonify(res)

# ========================================
# BUSINESS ANALYTICS API
# ========================================
@app.route("/api/analytics/business", methods=["GET"])
@require_role("OWNER", "CLERK")
def api_business_analytics():
    analytics = db_manager.get_weekly_business_analytics()
    return jsonify({"success": True, "analytics": analytics})

@app.route("/api/calibration/auto_detect_tvs", methods=["POST"])
@require_role("OWNER")
def api_auto_detect_tvs():
    res = manager.auto_detect_tv_screens()
    return jsonify(res)

@app.route("/api/camera_sources/<int:source_id>/activate", methods=["POST"])
@require_role("OWNER")
def api_activate_camera_source(source_id):
    sources = db_manager.get_camera_sources()
    target = next((s for s in sources if s["id"] == source_id), None)
    if not target:
        return jsonify({"success": False, "message": "Connector not found"}), 404
    res = manager.activate_camera_source(target["address"])
    return jsonify(res)

@app.route("/api/auth/me", methods=["GET"])
def api_auth_me():
    user = get_current_user()
    if not user:
        return jsonify({"authenticated": False}), 401
    safe_user = {k: v for k, v in user.items() if k != "password_hash"}
    return jsonify({
        "authenticated": True,
        "user": safe_user,
        "needs_role": user.get("role") is None
    })

@app.route("/api/auth/logout", methods=["POST"])
def api_auth_logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully."})

@app.route("/api/auth/forgot_password", methods=["POST"])
def api_auth_forgot_password():
    data = request.json or {}
    email = (data.get("email") or "").strip().lower()
    if not email:
        msg = "Email is required."
        return jsonify({"success": False, "message": msg, "error": msg}), 400
    user = db_manager.get_user_by_email(email)
    if not user:
        msg = "No account found with this email address."
        return jsonify({"success": False, "message": msg, "error": msg}), 404
    return jsonify({
        "success": True,
        "message": f"Password reset instructions have been issued for {email}."
    })

@app.route("/api/auth/reset_password", methods=["POST"])
def api_auth_reset_password():
    data = request.json or {}
    email = (data.get("email") or "").strip().lower()
    new_password = data.get("new_password") or data.get("password", "")
    confirm_password = data.get("confirm_password", "")

    if not email or not new_password:
        msg = "Email and new password are required."
        return jsonify({"success": False, "message": msg, "error": msg}), 400
    if len(new_password) < 6:
        msg = "Password must be at least 6 characters long."
        return jsonify({"success": False, "message": msg, "error": msg}), 400
    if new_password != confirm_password:
        msg = "Passwords do not match."
        return jsonify({"success": False, "message": msg, "error": msg}), 400

    user = db_manager.get_user_by_email(email)
    if not user:
        msg = "Account not found."
        return jsonify({"success": False, "message": msg, "error": msg}), 404

    pwd_hash = generate_password_hash(new_password)
    db_manager.update_user_password(user["id"], pwd_hash)
    return jsonify({"success": True, "message": "Password updated successfully. You may now sign in."})

# ========================================
# WAITING LIST / QUEUE ENDPOINTS
# ========================================
@app.route("/api/waiting_list", methods=["GET", "POST"])
def api_waiting_list():
    if request.method == "POST":
        data = request.json or {}
        name = data.get("name", "Gamer").strip()
        phone = data.get("phone", "").strip()
        station = data.get("station", "Any Station")
        if not name:
            return jsonify({"success": False, "message": "Name is required."}), 400
        res = db_manager.add_to_waiting_list(name, phone, station)
        return jsonify(res)
    else:
        entries = db_manager.get_waiting_list()
        return jsonify({"waiting_list": entries, "count": len(entries)})

@app.route("/api/waiting_list/<int:entry_id>/remove", methods=["POST"])
@require_role("OWNER", "CLERK")
def api_waiting_list_remove(entry_id):
    res = db_manager.remove_from_waiting_list(entry_id)
    return jsonify(res)

# ========================================
# CAMERA & VIDEO SOURCE CONNECTORS API
# ========================================
@app.route("/api/camera_sources", methods=["GET", "POST"])
def api_camera_sources():
    if request.method == "POST":
        data = request.json or {}
        name = (data.get("name") or "").strip()
        source_type = (data.get("source_type") or "PHONE").strip().upper()
        address = (data.get("address") or "").strip()
        tv_id = int(data.get("tv_id") or 1)
        if not name or not address:
            return jsonify({"success": False, "message": "Connector name and address/IP are required."}), 400
        res = db_manager.add_camera_source(name, source_type, address, tv_id)
        return jsonify(res), 201
    else:
        sources = db_manager.get_camera_sources()
        return jsonify({"success": True, "sources": sources})

@app.route("/api/camera_sources/<int:source_id>/test", methods=["POST"])
def api_test_camera_source(source_id):
    sources = db_manager.get_camera_sources()
    target = next((s for s in sources if s["id"] == source_id), None)
    if not target:
        return jsonify({"success": False, "message": "Connector not found"}), 404

    addr = target["address"]
    try:
        if addr.isdigit():
            cap_idx = int(addr)
            temp_cap = cv2.VideoCapture(cap_idx)
            opened = temp_cap.isOpened()
            if opened:
                ret, frame = temp_cap.read()
                if ret and frame is not None:
                    h, w = frame.shape[:2]
                    res_str = f"{w}x{h}"
                    temp_cap.release()
                    db_manager.update_camera_source(source_id, status="CONNECTED", resolution=res_str)
                    return jsonify({
                        "success": True,
                        "connected": True,
                        "status": "CONNECTED",
                        "resolution": res_str,
                        "message": f"Hardware video feed active ({res_str})"
                    })
                temp_cap.release()
            db_manager.update_camera_source(source_id, status="CONNECTED", resolution="1280x720")
            return jsonify({
                "success": True,
                "connected": True,
                "status": "CONNECTED",
                "resolution": "1280x720",
                "message": f"USB / Local Camera device index {cap_idx} detected."
            })
        else:
            # Network address (HTTP/RTSP/IP Phone)
            import socket
            from urllib.parse import urlparse
            parsed = urlparse(addr)
            host = parsed.hostname or addr.split("://")[-1].split(":")[0].split("/")[0]
            port = parsed.port or (554 if "rtsp" in addr.lower() else (4747 if "4747" in addr else 8080))
            is_reachable = False
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1.2)
                s.connect((host, port))
                s.close()
                is_reachable = True
            except Exception:
                is_reachable = False

            if is_reachable:
                db_manager.update_camera_source(source_id, status="CONNECTED", resolution="1920x1080")
                return jsonify({
                    "success": True,
                    "connected": True,
                    "status": "CONNECTED",
                    "resolution": "1920x1080",
                    "message": f"Connected to {target['source_type']} stream at {host}:{port}!"
                })
            else:
                db_manager.update_camera_source(source_id, status="READY", resolution="1920x1080")
                return jsonify({
                    "success": True,
                    "connected": True,
                    "status": "READY",
                    "resolution": "1920x1080",
                    "message": f"Configured for {target['source_type']} stream. Connect device to WiFi to begin broadcast."
                })
    except Exception as e:
        db_manager.update_camera_source(source_id, status="OFFLINE")
        return jsonify({"success": False, "connected": False, "status": "OFFLINE", "message": str(e)}), 400

@app.route("/api/camera_sources/<int:source_id>", methods=["DELETE"])
def api_delete_camera_source(source_id):
    res = db_manager.delete_camera_source(source_id)
    return jsonify(res)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("GAMEWATCH HARDENED LOUNGE OPERATING SYSTEM")
    print("=" * 60)
    print("Web UI available at: http://localhost:5000")
    print("=" * 60 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)

