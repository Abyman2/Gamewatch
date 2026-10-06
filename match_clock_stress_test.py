# ----------------------------------------
# GAMEWATCH MATCH CLOCK STRESS TEST
# ----------------------------------------

state = "WAITING"
last_clock = None
suspicious_events = 0


# ----------------------------------------
# SETTINGS
# ----------------------------------------

MAX_NORMAL_GAP = 90       # temporary testing rule
NORMAL_MATCH_END = 90
EXTRA_TIME_END = 120


# ----------------------------------------
# CONVERT CLOCK
# ----------------------------------------

def clock_to_seconds(clock):

    minutes, seconds = map(
        int,
        clock.split(":")
    )

    return minutes * 60 + seconds


def seconds_to_clock(total_seconds):

    minutes = total_seconds // 60
    seconds = total_seconds % 60

    return f"{minutes:02d}:{seconds:02d}"


# ----------------------------------------
# PROCESS CLOCK
# ----------------------------------------

def process_clock(clock):

    global state
    global last_clock
    global suspicious_events


    print("\n----------------------------------------")
    print(f"State: {state}")
    print(f"Incoming Clock: {clock}")


    # ------------------------------------
    # UNKNOWN
    # ------------------------------------

    if clock == "UNKNOWN":

        print(
            "❓ Clock cannot currently be read."
        )

        return


    current_seconds = clock_to_seconds(clock)


    # ------------------------------------
    # FIRST OBSERVATION
    # ------------------------------------

    if last_clock is None:

        last_clock = current_seconds


        if current_seconds <= 60:

            state = "EARLY_MATCH"

            print(
                "🟢 Early match detected."
            )

        else:

            state = "MATCH_IN_PROGRESS"

            print(
                f"👀 Match already in progress "
                f"at {clock}."
            )

            print(
                "⚠ This match was not observed "
                "from kickoff."
            )

        return


    # ------------------------------------
    # CLOCK RESET
    # ------------------------------------

    if current_seconds < last_clock:

        if current_seconds <= 60:

            print(
                "🔄 CLOCK RESET DETECTED"
            )

            print(
                f"Previous: "
                f"{seconds_to_clock(last_clock)}"
            )

            print(
                f"Current: {clock}"
            )

            print(
                "Possible new match/restart."
            )

            state = "EARLY_MATCH"

            last_clock = current_seconds

        else:

            suspicious_events += 1

            print(
                "🚨 Suspicious backward jump."
            )

        return


    # ------------------------------------
    # SAME CLOCK
    # ------------------------------------

    if current_seconds == last_clock:

        print(
            "ℹ Same clock reading."
        )

        return


    # ------------------------------------
    # FORWARD MOVEMENT
    # ------------------------------------

    jump = current_seconds - last_clock


    print(
        f"Clock advanced by {jump} seconds."
    )


    # ------------------------------------
    # NORMAL PROGRESSION
    # ------------------------------------

    if jump <= MAX_NORMAL_GAP:

        last_clock = current_seconds


        if current_seconds <= NORMAL_MATCH_END * 60:

            if state == "EARLY_MATCH":

                state = "MATCH_IN_PROGRESS"

                print(
                    "🟡 Match progression confirmed."
                )

            else:

                print(
                    "⚽ Normal match progression."
                )


        elif current_seconds <= EXTRA_TIME_END * 60:

            state = "EXTRA_TIME"

            print(
                "⏱ Extra-time range detected."
            )


        else:

            print(
                "🚨 Clock is beyond expected "
                "extra-time range."
            )


        return


    # ------------------------------------
    # LARGE JUMP
    # ------------------------------------

    suspicious_events += 1


    print(
        "🚨 LARGE CLOCK JUMP!"
    )

    print(
        "GameWatch will NOT immediately "
        "trust this reading."
    )

    print(
        "Previous trusted clock: "
        f"{seconds_to_clock(last_clock)}"
    )

    print(
        "Current reading: "
        f"{clock}"
    )

    print(
        "Waiting for another reliable reading."
    )


# ----------------------------------------
# TEST RUNNER
# ----------------------------------------

def run_test(name, clocks):

    global state
    global last_clock
    global suspicious_events


    state = "WAITING"
    last_clock = None
    suspicious_events = 0


    print(
        "\n========================================"
    )

    print(
        f"TEST: {name}"
    )

    print(
        "========================================"
    )


    for clock in clocks:

        process_clock(clock)


    print(
        "\n----------------------------------------"
    )

    print(
        f"FINAL STATE: {state}"
    )

    if last_clock is not None:

        print(
            "LAST TRUSTED CLOCK:",
            seconds_to_clock(last_clock)
        )

    print(
        f"SUSPICIOUS EVENTS: "
        f"{suspicious_events}"
    )

    print(
        "========================================"
    )


# ----------------------------------------
# TEST CASES
# ----------------------------------------

tests = {

    "1. Normal Match":
        [
            "00:05",
            "00:32",
            "01:14",
            "02:05",
            "03:42",
            "05:10"
        ],


    "2. Camera Blocked":
        [
            "00:05",
            "00:35",
            "UNKNOWN",
            "UNKNOWN",
            "03:20",
            "04:15"
        ],


    "3. OCR Mistake":
        [
            "10:12",
            "10:45",
            "81:20",
            "11:17",
            "12:05"
        ],


    "4. Impossible Jump":
        [
            "00:05",
            "00:45",
            "45:00"
        ],


    "5. Match Restart":
        [
            "00:05",
            "00:40",
            "03:15",
            "20:10",
            "00:05",
            "00:42",
            "02:10"
        ],


    "6. Camera Starts Late":
        [
            "40:15",
            "40:48",
            "41:22",
            "42:10"
        ],


    "7. End Of Normal Match":
        [
            "88:40",
            "89:15",
            "89:52",
            "90:00"
        ],


    "8. Extra Time":
        [
            "90:00",
            "95:20",
            "105:15",
            "110:40",
            "119:30",
            "120:00"
        ],


    "9. Beyond Expected Time":
        [
            "119:30",
            "120:00",
            "125:00"
        ]

}


# ----------------------------------------
# START
# ----------------------------------------

print(
    "\n🎮 GAMEWATCH MATCH CLOCK STRESS TEST"
)

print(
    "Using MM:SS match-clock format."
)


for name, clocks in tests.items():

    run_test(
        name,
        clocks
    )


print(
    "\n========================================"
)

print(
    "✓ ALL MATCH CLOCK TESTS COMPLETE"
)

print(
    "========================================"
)