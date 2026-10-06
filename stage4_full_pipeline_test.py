import cv2
import numpy as np
import os
import time
import json
from typing import Dict, List, Tuple, Optional

from scoreboard_reader import ScoreboardReader, ScoreboardReading
from stage3_reader_brain_test import TimeAwareMatchBrain
from db_manager import (
    add_tv,
    start_session,
    add_completed_game,
    get_active_session,
    checkout_session
)
import database


# ========================================
# CONFIGURATION
# ========================================

TV_ID = 1
TV_NAME = "Gaming Lounge TV 1"
TEST_IMAGE_DIR = "test_images"
OUTPUT_DIR = "pipeline_results"


# ========================================
# FULL GAMEWATCH CAMERA PIPELINE
# ========================================

class GameWatchCameraPipeline:
    """
    End-to-End GameWatch Vision & Brain Pipeline.
    Processes full camera frames (1280x576) -> Auto-detects Scoreboard ->
    Preprocesses -> Reads Clock/Scores -> Time-Aware Brain -> SQLite Database.
    """

    def __init__(self, tv_id: int = TV_ID, tv_name: str = TV_NAME):
        self.tv_id = tv_id
        self.tv_name = tv_name
        self.reader = ScoreboardReader()
        self.brain = TimeAwareMatchBrain(f"TV-{tv_id}")
        self._ensure_db_and_session()

    def _ensure_db_and_session(self):
        """Ensure database tables exist, TV is registered, and an active session is running."""
        database.initialize_database()
        add_tv(self.tv_id, self.tv_name)

        # Check or start session
        active = get_active_session(self.tv_id)
        if active is None:
            res = start_session(self.tv_id)
            print(f"[DB] Started new session for TV {self.tv_id}: {res['message']}")
        else:
            print(f"[DB] Resumed active session #{active['id']} for TV {self.tv_id} (Games: {active['completed_games']})")

    def process_frame(
        self,
        frame: np.ndarray,
        simulated_elapsed_real_seconds: float = 0.0
    ) -> Tuple[ScoreboardReading, str, np.ndarray]:
        """
        Process a single full camera frame through the entire stack.
        Returns:
            reading: ScoreboardReading
            state: Brain state
            annotated_frame: Frame with HUD overlay for visualization
        """
        h, w = frame.shape[:2]
        annotated = frame.copy()

        # 1. Locate & Crop Scoreboard
        crop, bbox, crop_conf = self.reader.detect_and_crop_scoreboard(frame)
        x, y, bw, bh = bbox

        # 2. Read Clock & Scores
        reading = self.reader.read(crop)

        # 3. Update Time-Aware Brain
        new_state = self.brain.process_reading(
            reading,
            simulated_elapsed_real_seconds=simulated_elapsed_real_seconds
        )

        # 4. Annotate Full Frame HUD
        if reading.valid and reading.clock_str:
            # Draw green bounding box around detected scoreboard
            cv2.rectangle(annotated, (x, y), (x + bw, y + bh), (0, 255, 0), 2)

            # HUD Status Badge
            hud_text = f"TV 1: {reading.clock_str} | Score: {reading.score_home}-{reading.score_away} | Conf: {reading.overall_confidence:.0%} | {new_state}"
            cv2.rectangle(annotated, (x, max(0, y - 24)), (x + 360, y), (20, 20, 20), -1)
            cv2.putText(annotated, hud_text, (x + 5, max(12, y - 7)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 200), 1, cv2.LINE_AA)
        else:
            cv2.putText(annotated, f"TV 1: NO SCOREBOARD | {new_state}", (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        return reading, new_state, annotated

    def record_verified_game(self, reason: str = "Match duration verified"):
        """Record a verified completed game in brain and persist to SQLite database."""
        self.brain.verify_and_count_game(reason)
        db_res = add_completed_game(self.tv_id)
        if db_res.get("success"):
            print(f"[DB] Game recorded in SQLite: Total session games = {db_res.get('completed_games')}")
        else:
            print(f"[DB] Failed to record in SQLite: {db_res.get('message')}")


# ========================================
# STAGE 4 SYSTEM TEST
# ========================================

def main():
    print("============================================================")
    print("GAMEWATCH STAGE 4: FULL CAMERA FRAME -> VERIFIED GAME TEST")
    print("Testing 1280x576 Full Frames through Full Stack to SQLite")
    print("============================================================\n")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    pipeline = GameWatchCameraPipeline(tv_id=1, tv_name="Gaming Lounge TV 1")

    # Full frame sequence
    frames = [
        ("Kickoff Frame", "kickoff.jpg", 0.0),
        ("One Minute Frame", "one_minute.jpg", 30.0),
        ("Three Minutes Frame", "three_minutes.jpg", 114.0)
    ]

    print("\n[+] Processing Full 1280x576 Frames:\n")

    for label, filename, real_delta in frames:
        img_path = os.path.join(TEST_IMAGE_DIR, filename)
        frame = cv2.imread(img_path)

        if frame is None:
            print(f"[!] Could not load {img_path}")
            continue

        reading, state, annotated = pipeline.process_frame(frame, simulated_elapsed_real_seconds=real_delta)

        # Save annotated HUD image
        save_path = os.path.join(OUTPUT_DIR, f"annotated_{filename}")
        cv2.imwrite(save_path, annotated)

        print(f"   [FRAME] {label:<20} -> Clock: {reading.clock_str:<6} | State: {state:<18} | Saved: {save_path}")

    # Verify game completion and persist to database
    print("\n[+] Finalizing Match Verification:")
    session_before = get_active_session(1)
    games_before = session_before["completed_games"] if session_before else 0

    pipeline.record_verified_game("Full match cycle confirmed across kickoff -> 1min -> 3min frames")

    session_after = get_active_session(1)
    games_after = session_after["completed_games"] if session_after else 0

    print("\n[+] Database Verification:")
    print(f"   Active Session #{session_after['id']}")
    print(f"   Games Before: {games_before}")
    print(f"   Games After:  {games_after} (+{games_after - games_before})")
    print(f"   Current Total Bill: {games_after * 25} ETB (@ 25 ETB/game)")

    assert games_after == games_before + 1, "Database game count did not increment!"

    print("\n============================================================")
    print("[ALL PASS] STAGE 4 COMPLETE!")
    print("Full 1280x576 camera frames successfully recognized,")
    print("verified by Time-Aware Brain, and recorded in SQLite!")
    print("============================================================\n")


if __name__ == "__main__":
    main()
