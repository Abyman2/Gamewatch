import cv2
import numpy as np
import os
import time
import json
import argparse
from typing import Optional, Tuple, Dict, List

from scoreboard_reader import ScoreboardReader, ScoreboardReading
from stage3_reader_brain_test import TimeAwareMatchBrain
import db_manager
import database


# ========================================
# CONFIGURATION & SETTINGS
# ========================================

TV_ID = 1
TV_REGIONS_FILE = "tv_regions.json"
TEST_IMAGES_DIR = "test_images"
PRICE_PER_GAME = 25  # ETB
INFERENCE_INTERVAL_SECONDS = 0.5  # Process reader every 0.5s to preserve CPU


# ========================================
# LIVE PIPELINE ENGINE
# ========================================

class LiveGameWatchPipeline:
    """
    Production-Ready Live Camera Pipeline for GameWatch.
    Captures live frames -> Detects TV / Scoreboard -> Preprocesses ->
    Decodes Match Clock & Scores -> Drives Time-Aware Brain -> Records in SQLite.
    """

    def __init__(
        self,
        camera_index: int = 0,
        tv_id: int = TV_ID,
        simulate: bool = False,
        headless: bool = False
    ):
        self.camera_index = camera_index
        self.tv_id = tv_id
        self.simulate = simulate
        self.headless = headless

        # Components
        self.reader = ScoreboardReader()
        self.brain = TimeAwareMatchBrain(f"Live TV-{tv_id}")
        self.tv_roi = self._load_calibrated_tv_roi()

        # Database session
        self._setup_db_session()

        # State tracking
        self.last_inference_time = time.time()
        self.last_reading: Optional[ScoreboardReading] = None
        self.current_state = "WAITING"
        self.fps = 0.0
        self.frame_count = 0
        self.start_time = time.time()

        # Simulation feed files
        self.simulation_images = [
            "kickoff.jpg",
            "one_minute.jpg",
            "three_minutes.jpg"
        ]
        self.sim_index = 0
        self.sim_last_switch = time.time()

    def _load_calibrated_tv_roi(self) -> Optional[Tuple[int, int, int, int]]:
        """Load TV ROI from tv_regions.json if available."""
        if not os.path.exists(TV_REGIONS_FILE):
            return None
        try:
            with open(TV_REGIONS_FILE, "r") as f:
                data = json.load(f)
                for item in data:
                    if item.get("tv_id") == self.tv_id:
                        return (item["x"], item["y"], item["width"], item["height"])
        except Exception as e:
            print(f"[!] Warning reading {TV_REGIONS_FILE}: {e}")
        return None

    def _setup_db_session(self):
        """Ensure database is ready and TV has an active session."""
        database.initialize_database()
        db_manager.add_tv(self.tv_id, f"TV {self.tv_id}")
        session = db_manager.get_active_session(self.tv_id)
        if session is None:
            res = db_manager.start_session(self.tv_id)
            print(f"[DB] Session started for TV {self.tv_id}: {res['message']}")
        else:
            print(f"[DB] Active session #{session['id']} loaded. Current games: {session['completed_games']}")

    def get_frame(self, cap: Optional[cv2.VideoCapture]) -> Tuple[bool, Optional[np.ndarray]]:
        """Fetch frame from live camera or simulation feed."""
        if self.simulate or cap is None:
            # Cycle through test images every 3 seconds in simulation
            now = time.time()
            if now - self.sim_last_switch > 3.0:
                self.sim_index = (self.sim_index + 1) % len(self.simulation_images)
                self.sim_last_switch = now

            filename = self.simulation_images[self.sim_index]
            path = os.path.join(TEST_IMAGES_DIR, filename)
            frame = cv2.imread(path)
            if frame is None:
                # Return dummy frame if file missing
                frame = np.zeros((576, 1280, 3), dtype=np.uint8)
            return True, frame

        success, frame = cap.read()
        return success, frame

    def process_live_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Process single video frame through reader and brain.
        Renders rich HUD annotations directly onto the frame.
        """
        self.frame_count += 1
        now = time.time()
        annotated = frame.copy()
        h, w = frame.shape[:2]

        # Calculate FPS
        elapsed = now - self.start_time
        if elapsed > 0:
            self.fps = self.frame_count / elapsed

        # Step 1: Run inference at throttle interval (e.g. twice a second)
        time_since_last_inference = now - self.last_inference_time
        if time_since_last_inference >= INFERENCE_INTERVAL_SECONDS:
            self.last_inference_time = now

            # Locate scoreboard
            crop, bbox, crop_conf = self.reader.detect_and_crop_scoreboard(frame)

            if crop is not None and crop.size > 0 and crop_conf >= 0.50:
                self.last_reading = self.reader.read(crop)
                self.current_state = self.brain.process_reading(
                    self.last_reading,
                    simulated_elapsed_real_seconds=time_since_last_inference
                )

                # Check if brain verified a game completion
                if self.brain.accumulated_game_seconds >= 120 and self.current_state in ("MATCH_IN_PROGRESS", "EXTRA_TIME"):
                    # Check for match completion trigger in live flow
                    pass
            else:
                blank = ScoreboardReading(valid=False, overall_confidence=0.0)
                self.current_state = self.brain.process_reading(
                    blank,
                    simulated_elapsed_real_seconds=time_since_last_inference
                )

        # Step 2: Draw HUD Overlay on Display Frame
        self._render_hud(annotated)
        return annotated

    def _render_hud(self, frame: np.ndarray):
        """Draw production status dashboard over the camera frame."""
        h, w = frame.shape[:2]

        # Top Banner Background
        banner_h = 42
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, banner_h), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        # Get active session info
        session = db_manager.get_active_session(self.tv_id)
        games = session["completed_games"] if session else self.brain.games_counted
        total_bill = games * PRICE_PER_GAME

        # Status text elements
        state_color = (0, 255, 0) if "MATCH" in self.current_state else (0, 200, 255)
        if self.last_reading and self.last_reading.valid and self.last_reading.clock_str:
            clock_text = f"Clock: {self.last_reading.clock_str}"
            score_text = f"Score: {self.last_reading.score_home}-{self.last_reading.score_away}"
            conf_text = f"Conf: {self.last_reading.overall_confidence:.0%}"
        else:
            clock_text = "Clock: --:--"
            score_text = "Score: -:-"
            conf_text = "Conf: 0%"

        # Draw Header Elements
        cv2.putText(frame, f"GAMEWATCH LIVE | TV {self.tv_id}", (15, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, f"State: {self.current_state}", (270, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.55, state_color, 2, cv2.LINE_AA)
        cv2.putText(frame, f"{clock_text} | {score_text} | {conf_text}", (540, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1, cv2.LINE_AA)
        cv2.putText(frame, f"Games: {games} ({total_bill} ETB)", (w - 230, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 255, 255), 2, cv2.LINE_AA)

        # FPS counter in bottom corner
        cv2.putText(frame, f"FPS: {self.fps:.1f}", (15, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1, cv2.LINE_AA)

    def trigger_game_confirmation(self, reason: str = "Operator or Vision Confirmation"):
        """Manually or automatically confirm a completed game and persist to SQLite."""
        self.brain.verify_and_count_game(reason)
        res = db_manager.add_completed_game(self.tv_id)
        if res.get("success"):
            print(f"[LIVE] Game officially recorded in SQLite! Total: {res.get('completed_games')}")
        else:
            print(f"[LIVE] Database notice: {res.get('message')}")

    def run(self, max_frames: Optional[int] = None):
        """Main camera execution loop."""
        print("\n========================================")
        print("   GAMEWATCH LIVE PIPELINE ACTIVE       ")
        print("========================================")
        print("Controls:")
        print("  Q = Quit pipeline")
        print("  G = Manually trigger +1 Game confirmation")
        print("  R = Reset match brain state")
        print("  S = Toggle Simulation Feed (test images vs camera)")
        print("========================================\n")

        cap = None
        if not self.simulate:
            cap = cv2.VideoCapture(self.camera_index)
            if not cap.isOpened():
                print(f"[!] Could not open camera {self.camera_index}. Falling back to simulation feed.")
                self.simulate = True
                cap = None
            else:
                print(f"[+] Connected to live camera {self.camera_index}.")

        frames_run = 0

        try:
            while True:
                success, frame = self.get_frame(cap)
                if not success or frame is None:
                    print("[!] Failed to grab frame. Exiting loop.")
                    break

                processed_frame = self.process_live_frame(frame)
                frames_run += 1

                if max_frames and frames_run >= max_frames:
                    print(f"[OK] Reached target limit of {max_frames} frames. Stopping.")
                    break

                if not self.headless:
                    cv2.imshow("GameWatch - Live Production Pipeline", processed_frame)
                    key = cv2.waitKey(1) & 0xFF

                    if key == ord("q"):
                        print("[LIVE] Quit command received.")
                        break
                    elif key == ord("g"):
                        self.trigger_game_confirmation("Operator confirmed match")
                    elif key == ord("r"):
                        self.brain.reset_for_new_match()
                        print("[LIVE] Brain reset to WAITING state.")
                    elif key == ord("s"):
                        self.simulate = not self.simulate
                        mode = "SIMULATION" if self.simulate else "LIVE CAMERA"
                        print(f"[LIVE] Switched source mode to: {mode}")

        finally:
            if cap is not None:
                cap.release()
            if not self.headless:
                cv2.destroyAllWindows()

        print("\n[OK] Live pipeline shut down cleanly.")


# ========================================
# COMMAND LINE ENTRY POINT
# ========================================

def main():
    parser = argparse.ArgumentParser(description="GameWatch Live Camera Pipeline")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (default: 0)")
    parser.add_argument("--simulate", action="store_true", help="Run with simulated test image feed")
    parser.add_argument("--headless", action="store_true", help="Run without graphical cv2.imshow windows")
    parser.add_argument("--max-frames", type=int, default=None, help="Stop after N frames (for automated testing)")

    args = parser.parse_args()

    pipeline = LiveGameWatchPipeline(
        camera_index=args.camera,
        tv_id=TV_ID,
        simulate=args.simulate,
        headless=args.headless
    )

    pipeline.run(max_frames=args.max_frames)


if __name__ == "__main__":
    main()
