# ----------------------------------------
# GAMEWATCH MATCH VERIFIER STRESS TEST
# ----------------------------------------


# ----------------------------------------
# MATCH BRAIN
# ----------------------------------------

state = "WAITING"

game_count = 0


def process_stage(detected_stage):

    global state
    global game_count


    print(
        f"\nCurrent State: {state}"
    )

    print(
        f"Incoming Event: {detected_stage}"
    )


    # ------------------------------------
    # UNKNOWN
    # ------------------------------------

    if detected_stage == "UNKNOWN":

        state = "UNKNOWN"

        print(
            "❓ Detection lost."
        )

        print(
            "GameWatch is waiting for "
            "new reliable evidence."
        )

        return


    # ------------------------------------
    # WAITING
    # ------------------------------------

    if state == "WAITING":

        if detected_stage == "KICKOFF":

            state = "KICKOFF_SEEN"

            print(
                "🟢 Kickoff confirmed."
            )

        else:

            print(
                "⏳ Waiting for a valid kickoff."
            )


    # ------------------------------------
    # KICKOFF SEEN
    # ------------------------------------

    elif state == "KICKOFF_SEEN":

        if detected_stage == "ONE_MINUTE":

            state = "ONE_MINUTE_SEEN"

            print(
                "🟡 One-minute confirmed."
            )

        elif detected_stage == "KICKOFF":

            print(
                "ℹ Still seeing kickoff."
            )

        else:

            state = "UNKNOWN"

            print(
                "⚠ Sequence interrupted."
            )

            print(
                "State changed to UNKNOWN."
            )


    # ------------------------------------
    # ONE MINUTE SEEN
    # ------------------------------------

    elif state == "ONE_MINUTE_SEEN":

        if detected_stage == "THREE_MINUTES":

            game_count += 1

            print(
                "\n🎮🔥 MATCH VERIFIED!"
            )

            print(
                f"Games Counted: {game_count}"
            )

            state = "WAITING"

        elif detected_stage == "ONE_MINUTE":

            print(
                "ℹ Still seeing one-minute stage."
            )

        else:

            state = "UNKNOWN"

            print(
                "⚠ Sequence interrupted."
            )

            print(
                "State changed to UNKNOWN."
            )


    # ------------------------------------
    # UNKNOWN
    # ------------------------------------

    elif state == "UNKNOWN":

        if detected_stage == "KICKOFF":

            state = "KICKOFF_SEEN"

            print(
                "🟢 Recovery: new kickoff detected."
            )

        elif detected_stage == "ONE_MINUTE":

            state = "ONE_MINUTE_SEEN"

            print(
                "🟡 Recovery: one-minute detected."
            )

        else:

            print(
                "❓ Still waiting for reliable evidence."
            )


# ----------------------------------------
# TEST RUNNER
# ----------------------------------------

def run_test(test_name, events):

    global state
    global game_count


    # Reset system before every test

    state = "WAITING"

    game_count = 0


    print(
        "\n========================================"
    )

    print(
        f"TEST: {test_name}"
    )

    print(
        "========================================"
    )


    for event in events:

        process_stage(event)


    print(
        "\n----------------------------------------"
    )

    print(
        f"FINAL STATE: {state}"
    )

    print(
        f"GAMES COUNTED: {game_count}"
    )

    print(
        "========================================"
    )


# ----------------------------------------
# TEST CASES
# ----------------------------------------

tests = {


    # Normal match

    "1. Normal Match":

        [
            "KICKOFF",
            "ONE_MINUTE",
            "THREE_MINUTES"
        ],


    # Missed kickoff

    "2. Missed Kickoff":

        [
            "ONE_MINUTE",
            "THREE_MINUTES"
        ],


    # Camera blocked

    "3. Camera Blocked":

        [
            "KICKOFF",
            "UNKNOWN",
            "THREE_MINUTES"
        ],


    # Recovery

    "4. Camera Recovery":

        [
            "KICKOFF",
            "UNKNOWN",
            "KICKOFF",
            "ONE_MINUTE",
            "THREE_MINUTES"
        ],


    # Wrong order

    "5. Wrong Order":

        [
            "KICKOFF",
            "THREE_MINUTES"
        ],


    # Match already in progress

    "6. Camera Sees 40 Minutes":

        [
            "UNKNOWN",
            "UNKNOWN",
            "THREE_MINUTES"
        ]

}


# ----------------------------------------
# RUN ALL TESTS
# ----------------------------------------

print(
    "\n🎮 GAMEWATCH MATCH BRAIN STRESS TEST"
)


for test_name, events in tests.items():

    run_test(
        test_name,
        events
    )


print(
    "\n========================================"
)

print(
    "✓ ALL STRESS TESTS COMPLETE"
)

print(
    "========================================"
)