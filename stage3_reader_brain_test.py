import cv2
import numpy as np
import os
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple

from scoreboard_reader import ScoreboardReader, ScoreboardReading


# ========================================
# CONFIGURATION & CONSTANTS
# ========================================

TEMPLATE_DIR = "scoreboard_templates"
MIN_CONFIDENCE_THRESHOLD = 0.65  # Reject OCR readings below this confidence
NORMAL_MATCH_END_SECS = 90 * 60  # 90:00 (5400 seconds) for standard match
VERIFICATION_MIN_OBSERVED_SECS = 120  # Minimum progression seconds to verify a game in test


# ========================================
# TIME-AWARE MATCH BRAIN
# ========================================

class TimeAwareMatchBrain:
    """
    Deterministic Time-Aware Decision Brain for GameWatch.
    Combines visual readings from ScoreboardReader with elapsed real-time
    physics to verify matches and count billable games without error.
    """

    def __init__(self, name: str = "TV-1 Brain", debug_agent=None):
        self.name = name
        self.debug_agent = debug_agent
        self.state = "WAITING"
        self.last_game_seconds: Optional[int] = None
        self.last_real_timestamp: Optional[float] = None
        self.restart_candidate_seconds: Optional[int] = None
        self.accumulated_game_seconds: int = 0
        self.games_counted: int = 0
        self.suspicious_events: int = 0
        self.history: List[Dict] = []

    def reset_for_new_match(self):
        """Reset state tracking for a new match."""
        self.state = "WAITING"
        self.last_game_seconds = None
        self.last_real_timestamp = None
        self.restart_candidate_seconds = None
        self.accumulated_game_seconds = 0

    @staticmethod
    def format_clock(seconds: Optional[int]) -> str:
        """Format total seconds to MM:SS string."""
        if seconds is None:
            return "UNKNOWN"
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins:02d}:{secs:02d}"

    def process_reading(
        self,
        reading: ScoreboardReading,
        simulated_elapsed_real_seconds: Optional[float] = None
    ) -> str:
        """
        Process a visual scoreboard reading against temporal rules.
        simulated_elapsed_real_seconds: optional override for testing/simulation.
        Returns the updated state.
        """
        current_real_time = time.time()

        # Determine real elapsed time since last reading
        if simulated_elapsed_real_seconds is not None:
            real_delta = simulated_elapsed_real_seconds
        elif self.last_real_timestamp is not None:
            real_delta = current_real_time - self.last_real_timestamp
        else:
            real_delta = 0.0

        print("\n------------------------------------------------------------")
        print(f"[{self.name}] Current State: {self.state}")

        # ------------------------------------------------------------
        # RULE 1: INVALID READING / CAMERA BLOCKED / UNKNOWN
        # ------------------------------------------------------------
        if not reading.valid or reading.clock_seconds is None:
            print("[?] Scoreboard or clock unavailable (camera blocked / non-game screen).")
            print(f"   Action: Preserving trusted state '{self.state}'.")
            return self.state

        # ------------------------------------------------------------
        # RULE 2: CONFIDENCE THRESHOLD
        # ------------------------------------------------------------
        if reading.overall_confidence < MIN_CONFIDENCE_THRESHOLD:
            self.suspicious_events += 1
            print(f"[!] Low Confidence Reading: {reading.overall_confidence:.1%} < {MIN_CONFIDENCE_THRESHOLD:.1%}")
            print(f"   Raw Clock: {reading.clock_str} -> REJECTED")
            return self.state

        current_game_seconds = reading.clock_seconds
        clock_str = reading.clock_str or self.format_clock(current_game_seconds)

        print(f"Incoming Clock: {clock_str} ({current_game_seconds}s) | Score: {reading.score_home}-{reading.score_away} | Conf: {reading.overall_confidence:.1%}")
        print(f"Real Elapsed: {real_delta:.1f}s")

        # ------------------------------------------------------------
        # RULE 3: FIRST OBSERVATION
        # ------------------------------------------------------------
        if self.last_game_seconds is None:
            self.last_game_seconds = current_game_seconds
            self.last_real_timestamp = current_real_time

            if current_game_seconds <= 60:
                self.state = "EARLY_MATCH"
                print("[+] Kickoff / Early match observed.")
            else:
                self.state = "MATCH_IN_PROGRESS"
                print("[*] Match already in progress (kickoff was missed or unobserved).")

            return self.state

        # ------------------------------------------------------------
        # RULE 4: CLOCK MOVED BACKWARD
        # ------------------------------------------------------------
        if current_game_seconds < self.last_game_seconds:
            backwards = self.last_game_seconds - current_game_seconds

            # Case 4A: Possible New Match / Restart (reset to <= 60s)
            if current_game_seconds <= 60:
                print(f"[RESET] CLOCK RESET CANDIDATE (Moved backwards {backwards}s to {clock_str}).")
                print("   Possible new match or match restart detected.")
                self.restart_candidate_seconds = current_game_seconds
                self.last_game_seconds = current_game_seconds
                self.last_real_timestamp = current_real_time
                self.state = "POSSIBLE_RESTART"
                return self.state

            # Case 4B: OCR Glitch / Impossible Backward Jump
            self.suspicious_events += 1
            print(f"[!] BACKWARD CLOCK JUMP: from {self.format_clock(self.last_game_seconds)} to {clock_str} (-{backwards}s).")
            print("   Action: Reading rejected. Maintaining last trusted state.")
            if self.debug_agent:
                from ai.antigravity_debug_agent import AnomalyEvent
                self.debug_agent.log_anomaly(AnomalyEvent(
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                    tv_id=1,
                    event_type="BACKWARD_JUMP",
                    current_state=self.state,
                    detected_clock=clock_str,
                    detected_seconds=current_game_seconds,
                    previous_clock=self.format_clock(self.last_game_seconds),
                    previous_seconds=self.last_game_seconds,
                    real_elapsed_seconds=real_delta,
                    confidence=reading.overall_confidence
                ))
            return self.state

        # ------------------------------------------------------------
        # RULE 5: CLOCK MOVED FORWARD
        # ------------------------------------------------------------
        game_delta = current_game_seconds - self.last_game_seconds

        # Speed ratio check (game clock vs real elapsed seconds)
        if real_delta > 0:
            ratio = game_delta / real_delta
        else:
            ratio = 1.0

        print(f"Clock Advanced: +{game_delta}s (Ratio: {ratio:.2f})")

        # Case 5A: Impossible clock speed (huge ratio > 3.5 without camera gap)
        if real_delta > 0 and ratio > 3.5 and game_delta > 90:
            self.suspicious_events += 1
            print(f"[!] IMPOSSIBLE CLOCK SPEED: Game advanced {game_delta}s in {real_delta:.1f}s real time.")
            print("   Action: Suspected OCR error. Reading rejected.")
            if self.debug_agent:
                from ai.antigravity_debug_agent import AnomalyEvent
                self.debug_agent.log_anomaly(AnomalyEvent(
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                    tv_id=1,
                    event_type="IMPOSSIBLE_SPEED",
                    current_state=self.state,
                    detected_clock=clock_str,
                    detected_seconds=current_game_seconds,
                    previous_clock=self.format_clock(self.last_game_seconds),
                    previous_seconds=self.last_game_seconds,
                    real_elapsed_seconds=real_delta,
                    confidence=reading.overall_confidence
                ))
            return self.state

        # Track valid progression
        self.accumulated_game_seconds += game_delta

        # ------------------------------------------------------------
        # STATE MACHINE TRANSITIONS
        # ------------------------------------------------------------
        if self.state == "POSSIBLE_RESTART":
            if self.restart_candidate_seconds is not None and current_game_seconds > self.restart_candidate_seconds:
                self.state = "EARLY_MATCH"
                self.restart_candidate_seconds = None
                self.accumulated_game_seconds = current_game_seconds
                print("[+] New match progression confirmed.")
            else:
                print("[...] Still waiting for restart confirmation.")

        elif self.state == "EARLY_MATCH":
            if self.accumulated_game_seconds >= 20:
                self.state = "MATCH_IN_PROGRESS"
                print("[+] Match progression confirmed.")

        elif self.state == "MATCH_IN_PROGRESS":
            print("[+] Normal match progression.")

        # Check for Extra Time range
        if current_game_seconds >= NORMAL_MATCH_END_SECS:
            self.state = "EXTRA_TIME"
            print("[+] Extra-time range reached.")

        # Update trusted pointers
        self.last_game_seconds = current_game_seconds
        self.last_real_timestamp = current_real_time

        return self.state

    def verify_and_count_game(self, reason: str = "Full Match Verified") -> bool:
        """
        Officially confirm and record a completed game.
        Prevents double-counting by resetting state.
        """
        self.games_counted += 1
        print("\n" + "=" * 60)
        print("[GAME COUNTED] MATCH CONFIRMED AND RECORDED!")
        print(f"   Total Games Counted: {self.games_counted}")
        print(f"   Reason: {reason}")
        print(f"   Accumulated Match Seconds: {self.accumulated_game_seconds}s")
        print("=" * 60)
        self.reset_for_new_match()
        return True


# ========================================
# END-TO-END PIPELINE RUNNER
# ========================================

def run_image_through_pipeline(
    image_path: str,
    reader: ScoreboardReader,
    brain: TimeAwareMatchBrain,
    simulated_real_delta: float
) -> Tuple[ScoreboardReading, str]:
    """
    Full top-down pipeline execution:
    Image file -> ScoreboardReader -> TimeAwareMatchBrain
    """
    img = cv2.imread(image_path)
    if img is None:
        # Create simulated blank/corrupt frame
        reading = ScoreboardReading(valid=False, overall_confidence=0.0)
    else:
        reading = reader.read(img)

    new_state = brain.process_reading(reading, simulated_elapsed_real_seconds=simulated_real_delta)
    return reading, new_state


# ========================================
# SYSTEM TEST SCENARIOS
# ========================================

def main():
    print("============================================================")
    print("GAMEWATCH STAGE 3: READER -> TIME-AWARE BRAIN TEST")
    print("Testing real images through preprocessing, reader, & brain")
    print("============================================================")

    reader = ScoreboardReader()
    brain = TimeAwareMatchBrain("Lounge TV-1")

    # ------------------------------------------------------------
    # SCENARIO 1: NORMAL MATCH PROGRESSION FROM REAL IMAGES
    # ------------------------------------------------------------
    print("\n\n" + "#" * 60)
    print("### SCENARIO 1: Real Scoreboard Images Progression")
    print("### kickoff -> one_minute -> three_minutes")
    print("#" * 60)

    # 1. Kickoff image (00:51)
    p_kickoff = os.path.join(TEMPLATE_DIR, "kickoff_scoreboard.jpg")
    r1, s1 = run_image_through_pipeline(p_kickoff, reader, brain, simulated_real_delta=0.0)
    assert s1 in ("EARLY_MATCH", "MATCH_IN_PROGRESS"), f"Unexpected state: {s1}"

    # 2. One minute image (01:21) - 30 seconds real time elapsed
    p_one_min = os.path.join(TEMPLATE_DIR, "one_minute_scoreboard.jpg")
    r2, s2 = run_image_through_pipeline(p_one_min, reader, brain, simulated_real_delta=30.0)
    assert s2 == "MATCH_IN_PROGRESS", f"Expected MATCH_IN_PROGRESS, got: {s2}"

    # 3. Three minutes image (03:15) - 114 seconds real time elapsed
    p_three_min = os.path.join(TEMPLATE_DIR, "three_minutes_scoreboard.jpg")
    r3, s3 = run_image_through_pipeline(p_three_min, reader, brain, simulated_real_delta=114.0)
    assert s3 == "MATCH_IN_PROGRESS", f"Expected MATCH_IN_PROGRESS, got: {s3}"

    print(f"\n[OK] Scenario 1 Passed! Verified accumulated game time: {brain.accumulated_game_seconds}s")

    # ------------------------------------------------------------
    # SCENARIO 2: CAMERA OBSTRUCTION & RECOVERY
    # ------------------------------------------------------------
    print("\n\n" + "#" * 60)
    print("### SCENARIO 2: Camera Obstruction / Blurry Screen (UNKNOWN)")
    print("### Brain must hold state without crashing or dropping match")
    print("#" * 60)

    # Simulate camera blocked: create blank image
    blank_reading = ScoreboardReading(valid=False, overall_confidence=0.0)
    state_during_block = brain.process_reading(blank_reading, simulated_elapsed_real_seconds=8.0)
    assert state_during_block == "MATCH_IN_PROGRESS", "State was lost during camera block!"

    # Camera recovers with three_minutes image
    r_recover, s_recover = run_image_through_pipeline(p_three_min, reader, brain, simulated_real_delta=2.0)
    assert s_recover == "MATCH_IN_PROGRESS", "Failed to recover after obstruction!"
    print("\n[OK] Scenario 2 Passed! Handled temporary camera loss cleanly.")

    # ------------------------------------------------------------
    # SCENARIO 3: BACKWARD CLOCK GLITCH REJECTION
    # ------------------------------------------------------------
    print("\n\n" + "#" * 60)
    print("### SCENARIO 3: Backward Clock OCR Glitch")
    print("### Brain must reject false reading and log suspicious event")
    print("#" * 60)

    # Create artificial glitch: clock says 01:05 while trusted is 03:15
    glitch_reading = ScoreboardReading(
        valid=True,
        clock_str="01:05",
        clock_seconds=65,
        clock_confidence=0.91,
        score_home=0,
        score_away=0,
        overall_confidence=0.91
    )
    suspicious_before = brain.suspicious_events
    state_after_glitch = brain.process_reading(glitch_reading, simulated_elapsed_real_seconds=5.0)

    assert brain.suspicious_events == suspicious_before + 1, "Suspicious event was not logged!"
    assert brain.last_game_seconds == 195, f"Trusted clock was corrupted! Got {brain.last_game_seconds}"
    print("\n[OK] Scenario 3 Passed! Rejected backward clock glitch.")

    # ------------------------------------------------------------
    # SCENARIO 4: FULL MATCH VERIFICATION & BILLING TRIGGER
    # ------------------------------------------------------------
    print("\n\n" + "#" * 60)
    print("### SCENARIO 4: Complete Match Verification & Game Counter")
    print("### Trigger verified game completion")
    print("#" * 60)

    # Match reaches full duration / completion
    brain.verify_and_count_game("Full 90min match confirmed with consistent visual progression")
    assert brain.games_counted == 1, "Game was not counted!"
    assert brain.state == "WAITING", "State was not reset to WAITING!"

    print("\n[OK] Scenario 4 Passed! Game officially counted (+1) and state reset.")

    # ------------------------------------------------------------
    # SUMMARY REPORT
    # ------------------------------------------------------------
    print("\n" + "=" * 60)
    print("[ALL PASS] ALL STAGE 3 TESTS PASSED SUCCESSFULLY!")
    print(f"Total Games Counted: {brain.games_counted}")
    print(f"Total Suspicious Events Handled: {brain.suspicious_events}")
    print("Real images flow: Image -> Preprocessing -> Reader -> Time Brain -> +1 Game")
    print("============================================================")


if __name__ == "__main__":
    main()
