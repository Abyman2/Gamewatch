print()
print("========================================")
print("🎮 GAMEWATCH SYSTEM TEST")
print("========================================")


# ----------------------------------------
# SIMULATED FULL GAMEWATCH PIPELINE
# ----------------------------------------

class GameWatchSystem:

    def __init__(self):
        self.state = "WAITING"
        self.games_counted = 0

    def process_event(self, event):

        print()
        print("----------------------------------------")
        print("Current State:", self.state)
        print("Incoming Event:", event)

        # --------------------------------
        # WAITING FOR MATCH
        # --------------------------------

        if self.state == "WAITING":

            if event == "KICKOFF":
                self.state = "KICKOFF_SEEN"
                print("🟢 Kickoff detected.")

            elif event == "UNKNOWN":
                self.state = "UNKNOWN"
                print("❓ Camera/detection unavailable.")

            else:
                print("⏳ Waiting for a valid kickoff.")

        # --------------------------------
        # KICKOFF SEEN
        # --------------------------------

        elif self.state == "KICKOFF_SEEN":

            if event == "ONE_MINUTE":
                self.state = "ONE_MINUTE_SEEN"
                print("🟡 One-minute stage confirmed.")

            elif event == "UNKNOWN":
                self.state = "UNKNOWN"
                print("❓ Detection lost.")

            elif event == "KICKOFF":
                print("ℹ Duplicate kickoff ignored.")

            else:
                self.state = "UNKNOWN"
                print("⚠ Sequence interrupted.")

        # --------------------------------
        # ONE MINUTE SEEN
        # --------------------------------

        elif self.state == "ONE_MINUTE_SEEN":

            if event == "THREE_MINUTES":

                self.games_counted += 1

                print()
                print("🎮🔥 MATCH VERIFIED!")
                print("Games Counted:", self.games_counted)

                self.state = "WAITING"

            elif event == "UNKNOWN":
                self.state = "UNKNOWN"
                print("❓ Detection lost.")

            else:
                print("⚠ Unexpected event.")

        # --------------------------------
        # UNKNOWN / CAMERA RECOVERY
        # --------------------------------

        elif self.state == "UNKNOWN":

            if event == "KICKOFF":
                self.state = "KICKOFF_SEEN"
                print("🟢 Recovery: kickoff detected.")

            elif event == "UNKNOWN":
                print("❓ Still waiting for reliable evidence.")

            else:
                print("⏳ Waiting for reliable evidence.")


# ----------------------------------------
# TEST 1
# NORMAL COMPLETE MATCH
# ----------------------------------------

print()
print("========================================")
print("TEST 1: NORMAL COMPLETE MATCH")
print("========================================")

system = GameWatchSystem()

events = [
    "KICKOFF",
    "ONE_MINUTE",
    "THREE_MINUTES"
]

for event in events:
    system.process_event(event)

print()
print("FINAL STATE:", system.state)
print("GAMES COUNTED:", system.games_counted)


# ----------------------------------------
# TEST 2
# CAMERA BLOCKED
# ----------------------------------------

print()
print("========================================")
print("TEST 2: CAMERA BLOCKED")
print("========================================")

system = GameWatchSystem()

events = [
    "KICKOFF",
    "UNKNOWN",
    "UNKNOWN",
    "KICKOFF",
    "ONE_MINUTE",
    "THREE_MINUTES"
]

for event in events:
    system.process_event(event)

print()
print("FINAL STATE:", system.state)
print("GAMES COUNTED:", system.games_counted)


# ----------------------------------------
# TEST 3
# MISSED KICKOFF
# ----------------------------------------

print()
print("========================================")
print("TEST 3: MISSED KICKOFF")
print("========================================")

system = GameWatchSystem()

events = [
    "ONE_MINUTE",
    "THREE_MINUTES"
]

for event in events:
    system.process_event(event)

print()
print("FINAL STATE:", system.state)
print("GAMES COUNTED:", system.games_counted)


# ----------------------------------------
# TEST 4
# WRONG ORDER
# ----------------------------------------

print()
print("========================================")
print("TEST 4: WRONG ORDER")
print("========================================")

system = GameWatchSystem()

events = [
    "KICKOFF",
    "THREE_MINUTES"
]

for event in events:
    system.process_event(event)

print()
print("FINAL STATE:", system.state)
print("GAMES COUNTED:", system.games_counted)


# ----------------------------------------
# FINAL
# ----------------------------------------

print()
print("========================================")
print("✓ SYSTEM TEST COMPLETE")
print("========================================")

