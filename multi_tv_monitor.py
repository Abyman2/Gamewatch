import cv2
import numpy as np
import os
import time
import json
import argparse
from datetime import datetime
from typing import Dict, List, Tuple, Optional

from scoreboard_reader import ScoreboardReader, ScoreboardReading
from stage3_reader_brain_test import TimeAwareMatchBrain
import db_manager
import database


# ========================================
# CONFIGURATION
# ========================================

PRICE_PER_GAME = 25  # ETB
DASHBOARD_WIDTH = 1280
DASHBOARD_HEIGHT = 720
TV_REGIONS_FILE = "tv_regions.json"
TEST_IMAGES_DIR = "test_images"


# ========================================
# TV CHANNEL AGENT
# ========================================

class TVChannel:
    """
    Dedicated Vision & Billing Channel for a single Gaming Lounge TV.
    Maintains independent scoreboard reader, time-aware match brain, and DB session.
    """

    def __init__(self, tv_id: int, tv_name: str, roi: Optional[Tuple[int, int, int, int]] = None):
        self.tv_id = tv_id
        self.tv_name = tv_name
        self.roi = roi  # (x, y, width, height) relative to camera frame

        # Independent Recognition Engine & Match Brain
        self.reader = ScoreboardReader()
        self.brain = TimeAwareMatchBrain(f"TV-{tv_id} Brain")

        # Telemetry & State
        self.last_reading: Optional[ScoreboardReading] = None
        self.current_state = "WAITING"
        self.last_inference_time = time.time()
        self.last_frame: Optional[np.ndarray] = None
        self.scoreboard_bbox: Optional[Tuple[int, int, int, int]] = None

        # Ensure TV exists in database
        db_manager.add_tv(self.tv_id, self.tv_name)

    def get_session(self) -> Optional[dict]:
        """Fetch current active session from database."""
        session = db_manager.get_active_session(self.tv_id)
        return dict(session) if session else None

    def start_new_session(self) -> dict:
        """Start a new gaming session for this TV."""
        res = db_manager.start_session(self.tv_id)
        self.brain.reset_for_new_match()
        return res

    def checkout(self, payment_method: str = "CASH") -> dict:
        """Checkout and finalize active session."""
        session = self.get_session()
        if not session:
            return {"success": False, "message": "No active session."}
        res = db_manager.checkout_session(session["id"], payment_method=payment_method)
        self.brain.reset_for_new_match()
        return res

    def process_frame(
        self,
        full_camera_frame: np.ndarray,
        throttle_interval: float = 0.5
    ) -> ScoreboardReading:
        """Extract TV ROI, detect scoreboard, and update match brain."""
        now = time.time()

        # 1. Extract TV Crop
        if self.roi is not None:
            x, y, w, h = self.roi
            # Clamp to frame boundaries
            fh, fw = full_camera_frame.shape[:2]
            x1 = max(0, min(x, fw - 1))
            y1 = max(0, min(y, fh - 1))
            x2 = max(x1 + 10, min(x + w, fw))
            y2 = max(y1 + 10, min(y + h, fh))
            tv_crop = full_camera_frame[y1:y2, x1:x2]
        else:
            tv_crop = full_camera_frame

        self.last_frame = tv_crop

        # 2. Check Throttle
        elapsed = now - self.last_inference_time
        if elapsed < throttle_interval:
            return self.last_reading or ScoreboardReading(valid=False)

        self.last_inference_time = now

        # 3. Detect Scoreboard in TV Crop
        sb_crop, bbox, conf = self.reader.detect_and_crop_scoreboard(tv_crop)
        self.scoreboard_bbox = bbox if conf >= 0.50 else None

        # 4. Read Scoreboard
        if sb_crop is not None and sb_crop.size > 0 and conf >= 0.50:
            reading = self.reader.read(sb_crop)
        else:
            reading = ScoreboardReading(valid=False, overall_confidence=0.0)

        # 5. Update Time-Aware Brain
        self.current_state = self.brain.process_reading(
            reading,
            simulated_elapsed_real_seconds=elapsed
        )
        self.last_reading = reading

        # 6. Auto-Confirm Completed Games into Database
        if self.brain.accumulated_game_seconds >= 120 and self.current_state in ("MATCH_IN_PROGRESS", "EXTRA_TIME"):
            # Check if match naturally completed in simulation or live
            pass

        return reading

    def record_completed_game(self, reason: str = "Match Duration Verified"):
        """Record a confirmed game in brain and persist to SQLite."""
        self.brain.verify_and_count_game(reason)
        res = db_manager.add_completed_game(self.tv_id)
        return res


# ========================================
# MULTI-TV COMMAND CENTER MONITOR
# ========================================

class MultiTVMonitor:
    """
    Unified Multi-TV Monitoring & Billing Dashboard.
    Coordinates vision channels, builds real-time command center canvas,
    and handles operator checkout / billing workflows.
    """

    def __init__(self, simulate: bool = False, headless: bool = False):
        self.simulate = simulate
        self.headless = headless
        self.channels: Dict[int, TVChannel] = {}
        self.sim_frames: List[np.ndarray] = []
        self.sim_index = 0
        self.sim_last_switch = time.time()
        self.notification_msg = "GameWatch Multi-TV Monitor Initialized."
        self.notification_time = time.time()

        # Database initialization
        database.initialize_database()

        # Load TV Channels
        self._init_tv_channels()

        # Load simulation frames if needed
        self._load_simulation_media()

    def _init_tv_channels(self):
        """Configure TV 1 and TV 2 channels with calibrated or default regions."""
        # TV 1: uses calibrated region if available, else active screen region
        ch1 = TVChannel(1, "TV 1 (Real Madrid vs Bayern)", roi=(128, 0, 1024, 576))
        # TV 2: gaming station 2
        ch2 = TVChannel(2, "TV 2 (Tournament Station)", roi=None)

        self.channels[1] = ch1
        self.channels[2] = ch2

        # Ensure active sessions exist for demo
        for tv_id, ch in self.channels.items():
            if ch.get_session() is None:
                ch.start_new_session()

    def _load_simulation_media(self):
        """Pre-load test frames for simulation mode."""
        for fn in ["kickoff.jpg", "one_minute.jpg", "three_minutes.jpg"]:
            p = os.path.join(TEST_IMAGES_DIR, fn)
            if os.path.exists(p):
                img = cv2.imread(p)
                if img is not None:
                    self.sim_frames.append(img)

        if not self.sim_frames:
            # Fallback black canvas
            self.sim_frames.append(np.zeros((576, 1280, 3), dtype=np.uint8))

    def set_notification(self, msg: str):
        """Display temporary status notification on dashboard."""
        self.notification_msg = msg
        self.notification_time = time.time()
        print(f"[DASHBOARD] {msg}")

    def render_dashboard(self) -> np.ndarray:
        """
        Assemble rich Command Center dashboard UI (1280x720):
        - Header with total revenue, active TVs, real-time clock
        - Left Card: TV 1 Live Feed + Telemetry + Bill
        - Right Card: TV 2 Live Feed + Telemetry + Bill
        - Bottom Bar: Operator Hotkeys and Activity Log
        """
        canvas = np.zeros((DASHBOARD_HEIGHT, DASHBOARD_WIDTH, 3), dtype=np.uint8)
        canvas[:] = (24, 26, 30)  # Sleek dark slate background

        now_str = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")

        # ----------------------------------------------------
        # 1. TOP HEADER BANNER
        # ----------------------------------------------------
        header_h = 60
        header_bg = np.zeros((header_h, DASHBOARD_WIDTH, 3), dtype=np.uint8)
        header_bg[:] = (16, 18, 22)
        canvas[0:header_h, :] = header_bg
        cv2.line(canvas, (0, header_h), (DASHBOARD_WIDTH, header_h), (45, 50, 60), 1)

        # Title & Logo
        cv2.putText(canvas, "GAMEWATCH", (25, 38), cv2.FONT_HERSHEY_DUPLEX, 0.85, (0, 255, 200), 2, cv2.LINE_AA)
        cv2.putText(canvas, "|  LOUNGE COMMAND CENTER", (210, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (160, 170, 185), 1, cv2.LINE_AA)

        # Active TVs & Total Revenue Summary
        active_tvs = sum(1 for ch in self.channels.values() if ch.get_session() is not None)
        total_games = sum((ch.get_session()["completed_games"] if ch.get_session() else 0) for ch in self.channels.values())
        total_revenue = total_games * PRICE_PER_GAME

        stats_str = f"Active TVs: {active_tvs}/{len(self.channels)}  |  Total Games: {total_games}  |  Revenue: {total_revenue} ETB"
        cv2.putText(canvas, stats_str, (520, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(canvas, now_str, (DASHBOARD_WIDTH - 220, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (140, 150, 165), 1, cv2.LINE_AA)

        # ----------------------------------------------------
        # 2. TV CARDS (SIDE BY SIDE)
        # ----------------------------------------------------
        card_w = (DASHBOARD_WIDTH - 60) // 2
        card_h = 550
        card_y = header_h + 20

        channel_list = list(self.channels.values())
        for idx, ch in enumerate(channel_list[:2]):
            card_x = 20 + idx * (card_w + 20)
            self._render_tv_card(canvas, ch, card_x, card_y, card_w, card_h)

        # ----------------------------------------------------
        # 3. BOTTOM OPERATOR ACTION BAR
        # ----------------------------------------------------
        bar_y = DASHBOARD_HEIGHT - 45
        cv2.rectangle(canvas, (0, bar_y), (DASHBOARD_WIDTH, DASHBOARD_HEIGHT), (16, 18, 22), -1)
        cv2.line(canvas, (0, bar_y), (DASHBOARD_WIDTH, bar_y), (45, 50, 60), 1)

        # Hotkeys
        hotkeys = "[1] Checkout TV 1   [2] Checkout TV 2   [G] Add Verified Game   [S] Toggle Sim   [Q] Quit"
        cv2.putText(canvas, hotkeys, (25, DASHBOARD_HEIGHT - 17), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 200), 1, cv2.LINE_AA)

        # Notification / Status message
        if time.time() - self.notification_time < 5.0:
            cv2.putText(canvas, f">> {self.notification_msg}", (720, DASHBOARD_HEIGHT - 17), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 200, 50), 1, cv2.LINE_AA)

        return canvas

    def _render_tv_card(
        self,
        canvas: np.ndarray,
        ch: TVChannel,
        x: int,
        y: int,
        w: int,
        h: int
    ):
        """Render a modular status and video card for a single TV station."""
        # Card Background & Border
        cv2.rectangle(canvas, (x, y), (x + w, y + h), (32, 35, 42), -1)
        cv2.rectangle(canvas, (x, y), (x + w, y + h), (55, 60, 72), 1)

        # Header Strip of Card
        card_header_h = 44
        cv2.rectangle(canvas, (x, y), (x + w, y + card_header_h), (40, 44, 54), -1)
        cv2.putText(canvas, f"STATION {ch.tv_id}: {ch.tv_name.upper()}", (x + 15, y + 28), cv2.FONT_HERSHEY_DUPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA)

        # Status Badge
        session = ch.get_session()
        is_active = session is not None
        status_label = "ACTIVE" if is_active else "IDLE"
        status_color = (0, 220, 100) if is_active else (130, 130, 130)
        cv2.circle(canvas, (x + w - 85, y + 22), 6, status_color, -1)
        cv2.putText(canvas, status_label, (x + w - 70, y + 27), cv2.FONT_HERSHEY_SIMPLEX, 0.45, status_color, 1, cv2.LINE_AA)

        # Video Viewport
        feed_h = 290
        feed_w = w - 30
        feed_x = x + 15
        feed_y = y + card_header_h + 15

        if ch.last_frame is not None and ch.last_frame.size > 0:
            thumb = cv2.resize(ch.last_frame, (feed_w, feed_h), interpolation=cv2.INTER_LINEAR)

            # Draw scoreboard box overlay if detected
            if ch.scoreboard_bbox is not None and ch.last_frame.shape[1] > 0:
                scale_x = feed_w / float(ch.last_frame.shape[1])
                scale_y = feed_h / float(ch.last_frame.shape[0])
                bx, by, bw, bh = ch.scoreboard_bbox
                cv2.rectangle(
                    thumb,
                    (int(bx * scale_x), int(by * scale_y)),
                    (int((bx + bw) * scale_x), int((by + bh) * scale_y)),
                    (0, 255, 0),
                    2
                )

            canvas[feed_y:feed_y + feed_h, feed_x:feed_x + feed_w] = thumb
        else:
            # Standby screen
            cv2.rectangle(canvas, (feed_x, feed_y), (feed_x + feed_w, feed_y + feed_h), (15, 17, 20), -1)
            cv2.putText(canvas, "NO VIDEO FEED", (feed_x + feed_w // 2 - 60, feed_y + feed_h // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (80, 85, 95), 1, cv2.LINE_AA)

        cv2.rectangle(canvas, (feed_x, feed_y), (feed_x + feed_w, feed_y + feed_h), (60, 65, 75), 1)

        # Telemetry & Billing Grid below video
        grid_y = feed_y + feed_h + 15

        # Row 1: Match Clock & Score
        reading = ch.last_reading
        clock_disp = reading.clock_str if (reading and reading.valid and reading.clock_str) else "--:--"
        score_disp = f"{reading.score_home} - {reading.score_away}" if (reading and reading.valid and reading.score_home is not None) else "- - -"
        state_disp = ch.current_state

        cv2.putText(canvas, "MATCH CLOCK:", (feed_x, grid_y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 170, 180), 1)
        cv2.putText(canvas, clock_disp, (feed_x + 110, grid_y + 20), cv2.FONT_HERSHEY_DUPLEX, 0.55, (0, 255, 200), 1)

        cv2.putText(canvas, "SCORE:", (feed_x + 220, grid_y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 170, 180), 1)
        cv2.putText(canvas, score_disp, (feed_x + 280, grid_y + 20), cv2.FONT_HERSHEY_DUPLEX, 0.55, (255, 255, 255), 1)

        # Row 2: Match Brain State & Confidence
        conf_val = reading.overall_confidence if reading else 0.0
        cv2.putText(canvas, "STATE:", (feed_x, grid_y + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 170, 180), 1)
        state_col = (0, 255, 0) if "MATCH" in state_disp else (255, 200, 50)
        cv2.putText(canvas, state_disp, (feed_x + 110, grid_y + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.48, state_col, 1)

        cv2.putText(canvas, f"CONF: {conf_val:.0%}", (feed_x + 360, grid_y + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 170, 180), 1)

        # Divider Line
        cv2.line(canvas, (feed_x, grid_y + 68), (feed_x + feed_w, grid_y + 68), (45, 50, 60), 1)

        # Row 3: Session Games & Running Bill
        games_count = session["completed_games"] if session else 0
        bill_amount = games_count * PRICE_PER_GAME

        cv2.putText(canvas, "VERIFIED GAMES:", (feed_x, grid_y + 98), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (180, 190, 200), 1)
        cv2.putText(canvas, f"{games_count} MATCHES", (feed_x + 145, grid_y + 98), cv2.FONT_HERSHEY_DUPLEX, 0.65, (0, 255, 255), 2)

        cv2.putText(canvas, "CURRENT BILL:", (feed_x + 320, grid_y + 98), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (180, 190, 200), 1)
        cv2.putText(canvas, f"{bill_amount} ETB", (feed_x + 440, grid_y + 98), cv2.FONT_HERSHEY_DUPLEX, 0.70, (0, 255, 120), 2)

        # Row 4: Session Duration & Actions
        start_time_str = session["start_time"] if session else "N/A"
        cv2.putText(canvas, f"Session Started: {start_time_str}", (feed_x, grid_y + 130), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (130, 140, 155), 1)

    def process_all_channels(self, frame_tv1: np.ndarray, frame_tv2: Optional[np.ndarray] = None):
        """Run parallel vision channels for all active TVs."""
        # Process TV 1
        if 1 in self.channels:
            self.channels[1].process_frame(frame_tv1)

        # Process TV 2 (uses frame_tv2 or simulated secondary view)
        if 2 in self.channels:
            f2 = frame_tv2 if frame_tv2 is not None else frame_tv1
            self.channels[2].process_frame(f2)

    def run(self, max_frames: Optional[int] = None):
        """Main real-time dashboard execution loop."""
        print("\n============================================================")
        print("GAMEWATCH MULTI-TV COMMAND CENTER ACTIVE")
        print("============================================================")
        print(f"Monitoring {len(self.channels)} TV Stations simultaneously.")
        print("Hotkeys:")
        print("  [1] Checkout TV 1 Session")
        print("  [2] Checkout TV 2 Session")
        print("  [G] Trigger +1 Verified Game on TV 1")
        print("  [S] Toggle Simulation vs Live Feed")
        print("  [Q] Quit Dashboard")
        print("============================================================\n")

        cap = None
        if not self.simulate:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                print("[!] Webcam not available. Defaulting to multi-TV simulation mode.")
                self.simulate = True
                cap = None
            else:
                print("[+] Live Camera 0 connected.")

        frames_run = 0

        try:
            while True:
                now = time.time()

                # Get frame for TV 1
                if self.simulate or cap is None:
                    if now - self.sim_last_switch > 3.0:
                        self.sim_index = (self.sim_index + 1) % len(self.sim_frames)
                        self.sim_last_switch = now
                    frame1 = self.sim_frames[self.sim_index]
                else:
                    success, frame1 = cap.read()
                    if not success or frame1 is None:
                        break

                # Process all channels
                self.process_all_channels(frame1)
                frames_run += 1

                # Render Command Center Dashboard
                dashboard_canvas = self.render_dashboard()

                if max_frames and frames_run >= max_frames:
                    print(f"[OK] Reached target limit of {max_frames} frames. Stopping.")
                    break

                if not self.headless:
                    cv2.imshow("GameWatch - Lounge Command Center", dashboard_canvas)
                    key = cv2.waitKey(20) & 0xFF

                    if key == ord("q"):
                        print("[DASHBOARD] Quit command received.")
                        break
                    elif key == ord("1"):
                        res = self.channels[1].checkout(payment_method="CASH")
                        self.set_notification(f"TV 1 Checked Out: {res.get('message', 'Completed')}")
                    elif key == ord("2"):
                        res = self.channels[2].checkout(payment_method="CASH")
                        self.set_notification(f"TV 2 Checked Out: {res.get('message', 'Completed')}")
                    elif key == ord("g"):
                        res = self.channels[1].record_completed_game("Operator Confirmation")
                        self.set_notification(f"TV 1 +1 Game Verified! Total: {res.get('completed_games')}")
                    elif key == ord("s"):
                        self.simulate = not self.simulate
                        mode = "SIMULATION" if self.simulate else "LIVE CAMERA"
                        self.set_notification(f"Switched source mode: {mode}")

        finally:
            if cap is not None:
                cap.release()
            if not self.headless:
                cv2.destroyAllWindows()

        print("\n[OK] Multi-TV Command Center shutdown cleanly.")


# ========================================
# ENTRY POINT
# ========================================

def main():
    parser = argparse.ArgumentParser(description="GameWatch Multi-TV Command Center Dashboard")
    parser.add_argument("--simulate", action="store_true", help="Run with simulation test image feed")
    parser.add_argument("--headless", action="store_true", help="Run in headless testing mode")
    parser.add_argument("--max-frames", type=int, default=None, help="Stop after N frames for automated test")

    args = parser.parse_args()

    dashboard = MultiTVMonitor(simulate=args.simulate, headless=args.headless)
    dashboard.run(max_frames=args.max_frames)


if __name__ == "__main__":
    main()
