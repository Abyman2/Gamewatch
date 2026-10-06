# ----------------------------------------
# GAMEWATCH MATCH TIME BRAIN TEST
# ----------------------------------------


# ----------------------------------------
# SETTINGS
# ----------------------------------------

state = "WAITING"

game_count = 0

last_match_time = None


# ----------------------------------------
# PROCESS MATCH TIME
# ----------------------------------------

def process_match_time(match_time):

    global state
    global game_count
    global last_match_time


    print("\n----------------------------------------")

    print(
        f"Current State: {state}"
    )

    print(
        f"Incoming Match Time: {match_time}"
    )


    # ------------------------------------
    # UNKNOWN
    # ------------------------------------

    if match_time == "UNKNOWN":

        print(
            "❓ Match time could not be detected."
        )

        return


    # ------------------------------------
    # MATCH START
    # ------------------------------------

    if match_time <= 1:


        # A new match may have started

        if state == "MATCH_IN_PROGRESS":

            print(
                "🔄 Match clock returned to the beginning."
            )

            print(
                "Possible new match detected."
            )


        state = "EARLY_MATCH"

        last_match_time = match_time


        print(
            "🟢 Early match detected."
        )

        return


    # ------------------------------------
    # EARLY MATCH
    # ------------------------------------

    if state == "EARLY_MATCH":


        if match_time > last_match_time:

            state = "MATCH_IN_PROGRESS"

            last_match_time = match_time


            print(
                "🟡 Match progression confirmed."
            )

            print(
                "Match is now being tracked."
            )

        else:

            print(
                "⚠ Match time did not progress correctly."
            )


        return


    # ------------------------------------
    # MATCH IN PROGRESS
    # ------------------------------------

    if state == "MATCH_IN_PROGRESS":


        if match_time > last_match_time:

            print(
                "⚽ Match continuing normally."
            )

            last_match_time = match_time


        elif match_time <= 1:

            print(
                "🔄 Possible restart detected."
            )

            state = "EARLY_MATCH"

            last_match_time = match_time


        else:

            print(
                "⚠ Time moved backwards."
            )

            print(
                "Possible restart or detection error."
            )


        return


    # ------------------------------------
    # WAITING
    # ------------------------------------

    if state == "WAITING":


        if match_time <= 1:

            state = "EARLY_MATCH"

            last_match_time = match_time


            print(
                "🟢 New match beginning detected."
            )


        else:

            state = "MATCH_IN_PROGRESS"

            last_match_time = match_time


            print(
                "👀 Match already in progress."
            )

            print(
                "This match will NOT be counted."
            )


# ----------------------------------------
# RUN TEST
# ----------------------------------------

def run_test(test_name, times):

    global state
    global game_count
    global last_match_time


    # Reset before each test

    state = "WAITING"

    game_count = 0

    last_match_time = None


    print(
        "\n========================================"
    )

    print(
        f"TEST: {test_name}"
    )

    print(
        "========================================"
    )


    for match_time in times:

        process_match_time(
            match_time
        )


    print(
        "\n========================================"
    )

    print(
        f"FINAL STATE: {state}"
    )

    print(
        f"LAST MATCH TIME: {last_match_time}"
    )

    print(
        "========================================"
    )


# ----------------------------------------
# TEST CASES
# ----------------------------------------

tests = {


    # Normal progression

    "1. Normal Match":

        [
            0,
            1,
            3,
            10,
            45,
            89
        ],


    # Camera misses part of the match

    "2. Camera Blocked":

        [
            0,
            1,
            "UNKNOWN",
            "UNKNOWN",
            5,
            20
        ],


    # Camera starts watching late

    "3. Camera Sees 40 Minutes":

        [
            40,
            41,
            60
        ],


    # Match restart

    "4. Match Restart":

        [
            0,
            1,
            5,
            20,
            0,
            1,
            3
        ],


    # Extra time

    "5. Extra Time":

        [
            0,
            1,
            45,
            90,
            105,
            120
        ]

}


# ----------------------------------------
# START
# ----------------------------------------

print(
    "\n🎮 GAMEWATCH MATCH TIME BRAIN"
)


for test_name, times in tests.items():

    run_test(
        test_name,
        times
    )


print(
    "\n========================================"
)

print(
    "✓ ALL MATCH TIME TESTS COMPLETE"
)

print(
    "========================================"
)