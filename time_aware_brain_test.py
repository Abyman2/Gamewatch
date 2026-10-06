import time


# ========================================
# GAMEWATCH TIME-AWARE BRAIN
# ========================================

state = "WAITING"

last_game_time = None
restart_candidate_time = None

last_real_time = None

suspicious_events = 0


# ========================================
# CLOCK FUNCTIONS
# ========================================

def clock_to_seconds(clock):

    minutes, seconds = clock.split(":")

    return (
        int(minutes) * 60
        + int(seconds)
    )


def seconds_to_clock(seconds):

    minutes = seconds // 60
    seconds = seconds % 60

    return f"{minutes:02d}:{seconds:02d}"


# ========================================
# PROCESS OBSERVATION
# ========================================

def process_observation(
    game_clock,
    real_elapsed_seconds
):

    global state
    global last_game_time
    global restart_candidate_time
    global last_real_time
    global suspicious_events

    print()
    print("----------------------------------------")

    print(
        f"State: {state}"
    )

    print(
        f"Game Clock: {game_clock}"
    )

    print(
        f"Real Time Since Last Reading: "
        f"{real_elapsed_seconds} seconds"
    )

    # ====================================
    # UNKNOWN / CAMERA BLOCKED
    # ====================================

    if game_clock == "UNKNOWN":

        print(
            "❓ Clock unavailable."
        )

        print(
            "Keeping the last trusted state."
        )

        return


    # ====================================
    # CONVERT CLOCK
    # ====================================

    current_game_time = (
        clock_to_seconds(game_clock)
    )


    # ====================================
    # FIRST OBSERVATION
    # ====================================

    if last_game_time is None:

        last_game_time = (
            current_game_time
        )

        last_real_time = (
            real_elapsed_seconds
        )

        if current_game_time <= 10:

            state = "EARLY_MATCH"

            print(
                "🟢 Early match observed."
            )

        else:

            state = "MATCH_IN_PROGRESS"

            print(
                "👀 Match already in progress."
            )

            print(
                "⚠ Kickoff was not observed."
            )

        return


    # ====================================
    # CLOCK MOVED BACKWARD
    # ====================================

    if current_game_time < last_game_time:

        backwards = (
            last_game_time
            - current_game_time
        )


        # --------------------------------
        # POSSIBLE NEW MATCH / RESTART
        # --------------------------------

        if current_game_time <= 60:

            print(
                "🔄 CLOCK RESET CANDIDATE"
            )

            print(
                f"Previous trusted time: "
                f"{seconds_to_clock(last_game_time)}"
            )

            print(
                f"New time: {game_clock}"
            )

            print(
                "Possible new match/restart."
            )

            # Remember the new clock.
            restart_candidate_time = (
                current_game_time
            )

            # IMPORTANT:
            # From this point forward,
            # compare the next reading
            # against the NEW match clock,
            # not the old match clock.

            last_game_time = (
                current_game_time
            )

            last_real_time = (
                real_elapsed_seconds
            )

            state = "POSSIBLE_RESTART"

            return


        # --------------------------------
        # REAL BACKWARD JUMP / OCR ERROR
        # --------------------------------

        suspicious_events += 1

        print(
            "🚨 BACKWARD CLOCK JUMP"
        )

        print(
            f"Moved backward "
            f"{backwards} seconds."
        )

        print(
            "Reading rejected."
        )

        return


    # ====================================
    # CLOCK MOVED FORWARD
    # ====================================

    game_difference = (
        current_game_time
        - last_game_time
    )


    # ====================================
    # REAL-TIME COMPARISON
    # ====================================

    real_difference = (
        real_elapsed_seconds
    )


    if real_difference > 0:

        ratio = (
            game_difference
            / real_difference
        )

    else:

        ratio = 1


    print(
        f"Game clock advanced: "
        f"{game_difference} seconds."
    )

    print(
        f"Game/Real Time Ratio: "
        f"{ratio:.2f}"
    )


    # ====================================
    # IMPOSSIBLE CLOCK SPEED
    # ====================================

    # A FIFA match clock should move
    # approximately as fast as real time.
    #
    # We allow some tolerance because:
    #
    # - camera readings are not continuous
    # - OCR may be delayed
    # - screenshots may be taken at
    #   slightly different moments
    #
    # A huge ratio is almost certainly
    # an OCR/detection mistake.

    if (
        real_difference > 0
        and ratio > 3
    ):

        suspicious_events += 1

        print(
            "🚨 GAME CLOCK MOVED TOO FAST."
        )

        print(
            "Reading rejected."
        )

        print(
            "Possible OCR error or bad detection."
        )

        return


    # ====================================
    # LARGE FORWARD JUMP
    # ====================================

    # If the camera was blocked for a while,
    # a larger jump can be legitimate.
    #
    # Therefore we primarily use the
    # real-time ratio above rather than
    # automatically rejecting every large
    # clock difference.

    if game_difference > 120:

        print(
            "⚠ Large clock jump observed."
        )

        print(
            "Checking against real elapsed time."
        )


    # ====================================
    # POSSIBLE RESTART
    # ====================================

    if state == "POSSIBLE_RESTART":

        # We already moved the trusted clock
        # to the new starting point.
        #
        # Therefore a forward movement here
        # means the suspected restart is
        # actually progressing.

        if (
            current_game_time
            > restart_candidate_time
        ):

            state = "EARLY_MATCH"

            restart_candidate_time = None

            print(
                "🟢 New match progression "
                "confirmed."
            )

        else:

            print(
                "⏳ Still waiting for "
                "restart confirmation."
            )

            return


    # ====================================
    # EARLY MATCH
    # ====================================

    if state == "EARLY_MATCH":

        if game_difference >= 20:

            state = "MATCH_IN_PROGRESS"

            print(
                "🟢 Match progression "
                "confirmed."
            )

        else:

            print(
                "⏳ Early match continues."
            )


    # ====================================
    # MATCH IN PROGRESS
    # ====================================

    elif state == "MATCH_IN_PROGRESS":

        print(
            "⚽ Normal progression."
        )


    # ====================================
    # EXTRA TIME
    # ====================================

    if current_game_time >= 90 * 60:

        if state != "EXTRA_TIME":

            state = "EXTRA_TIME"

            print(
                "⏱ Extra-time range."
            )

        else:

            print(
                "⏱ Extra-time range."
            )


    # ====================================
    # SAVE TRUSTED TIME
    # ====================================

    last_game_time = (
        current_game_time
    )

    last_real_time = (
        real_elapsed_seconds
    )


# ========================================
# TEST RUNNER
# ========================================

def run_test(
    test_name,
    observations
):

    global state
    global last_game_time
    global restart_candidate_time
    global last_real_time
    global suspicious_events


    state = "WAITING"

    last_game_time = None

    restart_candidate_time = None

    last_real_time = None

    suspicious_events = 0


    print()
    print("========================================")
    print(
        f"TEST: {test_name}"
    )
    print("========================================")


    for game_clock, real_time in observations:

        process_observation(
            game_clock,
            real_time
        )


    print()
    print(
        f"FINAL STATE: {state}"
    )


    if last_game_time is not None:

        print(
            "LAST TRUSTED GAME TIME: "
            f"{seconds_to_clock(last_game_time)}"
        )

    else:

        print(
            "LAST TRUSTED GAME TIME: NONE"
        )


    print(
        f"SUSPICIOUS EVENTS: "
        f"{suspicious_events}"
    )

    print(
        "========================================"
    )


# ========================================
# TESTS
# ========================================


# ----------------------------------------
# TEST 1
# NORMAL MATCH
# ----------------------------------------

run_test(

    "1. Normal Match",

    [

        ("00:05", 5),

        ("00:32", 27),

        ("01:14", 42),

        ("02:05", 51),

        ("03:42", 97),

    ]

)


# ----------------------------------------
# TEST 2
# CAMERA BLOCKED
# ----------------------------------------

run_test(

    "2. Camera Blocked",

    [

        ("00:05", 5),

        ("00:35", 30),

        ("UNKNOWN", 20),

        ("UNKNOWN", 30),

        ("03:20", 165),

        ("04:15", 55),

    ]

)


# ----------------------------------------
# TEST 3
# OCR ERROR
# ----------------------------------------

run_test(

    "3. OCR Error",

    [

        ("10:12", 10),

        ("10:45", 33),

        ("81:20", 1),

        ("11:17", 32),

        ("12:05", 48),

    ]

)


# ----------------------------------------
# TEST 4
# DELAYED CAMERA READING
# ----------------------------------------

run_test(

    "4. Delayed Camera Reading",

    [

        ("05:10", 10),

        ("06:30", 80),

        ("08:45", 135),

        ("10:20", 95),

    ]

)


# ----------------------------------------
# TEST 5
# MATCH RESTART
# ----------------------------------------

run_test(

    "5. Match Restart",

    [

        ("00:05", 5),

        ("00:40", 35),

        ("03:15", 155),

        ("20:10", 1015),

        # MATCH RESTART
        ("00:05", 3),

        # NEW MATCH PROGRESS
        ("00:42", 37),

        ("02:10", 88),

    ]

)


# ----------------------------------------
# TEST 6
# CAMERA STARTS AT 40 MINUTES
# ----------------------------------------

run_test(

    "6. Camera Starts at 40 Minutes",

    [

        ("40:15", 5),

        ("40:48", 33),

        ("41:22", 34),

        ("42:10", 48),

    ]

)


# ----------------------------------------
# TEST 7
# EXTRA TIME
# ----------------------------------------

run_test(

    "7. Extra Time",

    [

        ("89:40", 40),

        ("90:00", 20),

        ("95:20", 320),

        ("105:15", 595),

        ("110:40", 325),

        ("120:00", 560),

    ]

)


# ----------------------------------------
# TEST 8
# IMPOSSIBLE CLOCK
# ----------------------------------------

run_test(

    "8. Impossible Clock",

    [

        ("20:00", 10),

        ("20:20", 20),

        ("75:00", 1),

        ("20:50", 30),

    ]

)


print()
print("========================================")
print("✓ ALL TIME-AWARE TESTS COMPLETE")
print("========================================")
