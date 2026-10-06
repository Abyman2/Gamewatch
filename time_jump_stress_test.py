# ----------------------------------------
# GAMEWATCH TIME JUMP STRESS TEST
# ----------------------------------------

state = "WAITING"

last_match_time = None

suspicious_events = 0


# ----------------------------------------
# SETTINGS
# ----------------------------------------

MAX_NORMAL_JUMP = 10


# ----------------------------------------
# PROCESS TIME
# ----------------------------------------

def process_time(match_time):

    global state
    global last_match_time
    global suspicious_events


    print("\n----------------------------------------")

    print(f"State: {state}")
    print(f"Incoming Time: {match_time}")


    # ------------------------------------
    # UNKNOWN
    # ------------------------------------

    if match_time == "UNKNOWN":

        print("❓ Camera/OCR could not read the clock.")

        return


    # ------------------------------------
    # FIRST OBSERVATION
    # ------------------------------------

    if last_match_time is None:

        last_match_time = match_time

        if match_time <= 1:

            state = "EARLY_MATCH"

            print(
                "🟢 Early match detected."
            )

        else:

            state = "MATCH_IN_PROGRESS"

            print(
                f"👀 Match already in progress at "
                f"{match_time} minutes."
            )

            print(
                "⚠ This match was not observed from kickoff."
            )

        return


    # ------------------------------------
    # CLOCK RESET
    # ------------------------------------

    if match_time < last_match_time:

        if match_time <= 1:

            print(
                "🔄 CLOCK RESET DETECTED"
            )

            print(
                f"Previous: {last_match_time}"
            )

            print(
                f"Current: {match_time}"
            )

            print(
                "Possible new match/restart."
            )

            state = "EARLY_MATCH"

            last_match_time = match_time

        else:

            suspicious_events += 1

            print(
                "🚨 SUSPICIOUS BACKWARD JUMP"
            )

        return


    # ------------------------------------
    # NO CHANGE
    # ------------------------------------

    if match_time == last_match_time:

        print(
            "ℹ Same time detected."
        )

        return


    # ------------------------------------
    # FORWARD JUMP
    # ------------------------------------

    jump = match_time - last_match_time


    print(
        f"Time jumped forward by {jump} minute(s)."
    )


    # ------------------------------------
    # SMALL NORMAL JUMP
    # ------------------------------------

    if jump <= MAX_NORMAL_JUMP:

        print(
            "🟢 Normal progression."
        )

        last_match_time = match_time

        if state == "EARLY_MATCH":

            state = "MATCH_IN_PROGRESS"

            print(
                "🟡 Match progression confirmed."
            )

        return


    # ------------------------------------
    # LARGE JUMP
    # ------------------------------------

    suspicious_events += 1

    print(
        "🚨 LARGE TIME JUMP!"
    )

    print(
        "GameWatch will NOT trust this reading yet."
    )

    print(
        "Waiting for another observation."
    )


# ----------------------------------------
# TEST RUNNER
# ----------------------------------------

def run_test(name, times):

    global state
    global last_match_time
    global suspicious_events


    state = "WAITING"

    last_match_time = None

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


    for value in times:

        process_time(value)


    print(
        "\n----------------------------------------"
    )

    print(
        f"FINAL STATE: {state}"
    )

    print(
        f"LAST TRUSTED TIME: {last_match_time}"
    )

    print(
        f"SUSPICIOUS EVENTS: {suspicious_events}"
    )

    print(
        "========================================"
    )


# ----------------------------------------
# TEST CASES
# ----------------------------------------

tests = {


    # ------------------------------------
    # 1. NORMAL
    # ------------------------------------

    "1. Normal Progression":

        [
            0,
            1,
            3,
            5,
            8,
            10
        ],


    # ------------------------------------
    # 2. CAMERA BLOCKED
    # ------------------------------------

    "2. Camera Temporarily Blocked":

        [
            0,
            1,
            "UNKNOWN",
            "UNKNOWN",
            5,
            8,
            12
        ],


    # ------------------------------------
    # 3. IMPOSSIBLE JUMP
    # ------------------------------------

    "3. Impossible Jump":

        [
            0,
            1,
            45
        ],


    # ------------------------------------
    # 4. OCR MISTAKE
    # ------------------------------------

    "4. OCR Mistake":

        [
            10,
            11,
            81,
            12,
            14
        ],


    # ------------------------------------
    # 5. MATCH RESTART
    # ------------------------------------

    "5. Match Restart":

        [
            0,
            1,
            5,
            20,
            0,
            1,
            3,
            5
        ],


    # ------------------------------------
    # 6. CAMERA STARTS LATE
    # ------------------------------------

    "6. Camera Starts at 40 Minutes":

        [
            40,
            41,
            42,
            45
        ],


    # ------------------------------------
    # 7. EXTRA TIME
    # ------------------------------------

    "7. Extra Time":

        [
            85,
            89,
            90,
            95,
            105,
            120
        ]


}


# ----------------------------------------
# RUN TESTS
# ----------------------------------------

print(
    "\n🎮 GAMEWATCH TIME JUMP STRESS TEST"
)


for name, times in tests.items():

    run_test(
        name,
        times
    )


print(
    "\n========================================"
)

print(
    "✓ ALL TIME JUMP TESTS COMPLETE"
)

print(
    "========================================"
)