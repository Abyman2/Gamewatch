import cv2
import os
import numpy as np


# ----------------------------------------
# SETTINGS
# ----------------------------------------

TEMPLATE_FOLDER = "scoreboard_templates"


# ----------------------------------------
# LOAD TEMPLATE
# ----------------------------------------

def load_template(filename):

    path = os.path.join(
        TEMPLATE_FOLDER,
        filename
    )

    image = cv2.imread(path)

    if image is None:

        print(
            f"❌ Could not load {filename}"
        )

        return None

    return image


# ----------------------------------------
# CALCULATE DIFFERENCE
# ----------------------------------------

def calculate_difference(
    image1,
    image2
):

    target_width = 160
    target_height = 90


    image1 = cv2.resize(
        image1,
        (
            target_width,
            target_height
        )
    )


    image2 = cv2.resize(
        image2,
        (
            target_width,
            target_height
        )
    )


    difference = cv2.absdiff(
        image1,
        image2
    )


    gray = cv2.cvtColor(
        difference,
        cv2.COLOR_BGR2GRAY
    )


    return np.mean(gray)


# ----------------------------------------
# LOAD TEMPLATES
# ----------------------------------------

templates = {

    "KICKOFF":
        load_template(
            "kickoff_scoreboard.jpg"
        ),

    "ONE_MINUTE":
        load_template(
            "one_minute_scoreboard.jpg"
        ),

    "THREE_MINUTES":
        load_template(
            "three_minutes_scoreboard.jpg"
        )

}


if any(
    template is None
    for template in templates.values()
):

    print(
        "❌ Template loading failed."
    )

    exit()


print(
    "\n✓ All templates loaded."
)


# ----------------------------------------
# DETECT STAGE
# ----------------------------------------

def detect_stage(scoreboard):

    scores = {}


    for stage, template in templates.items():

        scores[stage] = calculate_difference(
            scoreboard,
            template
        )


    best_stage = min(
        scores,
        key=scores.get
    )


    best_score = scores[
        best_stage
    ]


    return (
        best_stage,
        best_score,
        scores
    )


# ----------------------------------------
# MATCH BRAIN
# ----------------------------------------

state = "WAITING"

game_count = 0


# ----------------------------------------
# PROCESS DETECTION
# ----------------------------------------

def process_stage(
    detected_stage
):

    global state
    global game_count


    print(
        f"\nCurrent State: {state}"
    )

    print(
        f"Detected: {detected_stage}"
    )


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
                "⏳ Waiting for kickoff."
            )


    # ------------------------------------
    # KICKOFF SEEN
    # ------------------------------------

    elif state == "KICKOFF_SEEN":

        if detected_stage == "ONE_MINUTE":

            state = "ONE_MINUTE_SEEN"

            print(
                "🟡 One-minute stage confirmed."
            )

        elif detected_stage == "KICKOFF":

            print(
                "ℹ Still seeing kickoff."
            )

        else:

            print(
                "⚠ Unexpected stage."
            )

            state = "UNKNOWN"

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
                f"Games Counted: "
                f"{game_count}"
            )


            state = "WAITING"

        elif detected_stage == "ONE_MINUTE":

            print(
                "ℹ Still seeing one-minute stage."
            )

        else:

            print(
                "⚠ Unexpected stage."
            )

            state = "UNKNOWN"

            print(
                "State changed to UNKNOWN."
            )


    # ------------------------------------
    # UNKNOWN
    # ------------------------------------

    elif state == "UNKNOWN":

        print(
            "❓ Camera state is UNKNOWN."
        )


        if detected_stage == "KICKOFF":

            state = "KICKOFF_SEEN"

            print(
                "🟢 Recovery successful."
            )

            print(
                "New kickoff detected."
            )


        elif detected_stage == "ONE_MINUTE":

            state = "ONE_MINUTE_SEEN"

            print(
                "🟡 Recovery successful."
            )

            print(
                "One-minute stage detected."
            )


        elif detected_stage == "THREE_MINUTES":

            print(
                "⚠ Three-minute stage seen,"
            )

            print(
                "but previous evidence was lost."
            )

            print(
                "No game will be counted."
            )


# ----------------------------------------
# LOAD TEST SCOREBOARDS
# ----------------------------------------

test_sequence = [

    (
        "scoreboard_templates/kickoff_scoreboard.jpg",
        "Normal Kickoff"
    ),

    (
        "scoreboard_templates/one_minute_scoreboard.jpg",
        "Normal One Minute"
    ),

    (
        "scoreboard_templates/three_minutes_scoreboard.jpg",
        "Normal Three Minutes"
    )

]


# ----------------------------------------
# START
# ----------------------------------------

print(
    "\n========================================"
)

print(
    "GAMEWATCH MATCH VERIFIER V2"
)

print(
    "========================================"
)


for path, description in test_sequence:

    print(
        "\n----------------------------------------"
    )

    print(
        description
    )


    image = cv2.imread(
        path
    )


    if image is None:

        print(
            f"❌ Could not load {path}"
        )

        continue


    detected_stage, score, scores = (
        detect_stage(
            image
        )
    )


    print(
        f"\nBest Match: "
        f"{detected_stage}"
    )

    print(
        f"Difference: "
        f"{score:.2f}"
    )


    process_stage(
        detected_stage
    )


# ----------------------------------------
# FINAL RESULT
# ----------------------------------------

print(
    "\n========================================"
)

print(
    "FINAL RESULT"
)

print(
    "========================================"
)


print(
    f"\nFinal State: "
    f"{state}"
)


print(
    f"Games Verified: "
    f"{game_count}"
)


print(
    "\n========================================"
)