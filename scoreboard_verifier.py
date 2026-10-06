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

    # Both images must have
    # exactly the same size

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


# Check all loaded

if any(
    template is None
    for template in templates.values()
):

    print(
        "❌ Template loading failed."
    )

    exit()


print(
    "\n✓ All scoreboard templates loaded."
)


# ----------------------------------------
# DETECT STAGE
# ----------------------------------------

def detect_stage(scoreboard):

    scores = {}


    for stage, template in templates.items():

        score = calculate_difference(
            scoreboard,
            template
        )


        scores[stage] = score


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
# TEST EACH TEMPLATE
# ----------------------------------------

print(
    "\n========================================"
)

print(
    "GAMEWATCH SCOREBOARD VERIFIER"
)

print(
    "========================================"
)


for expected_stage, image in templates.items():

    detected_stage, score, all_scores = (
        detect_stage(
            image
        )
    )


    print(
        "\n----------------------------------------"
    )


    print(
        f"Expected: {expected_stage}"
    )


    print(
        f"Detected: {detected_stage}"
    )


    print(
        f"Best Score: {score:.2f}"
    )


    print(
        "\nAll Scores:"
    )


    for stage, stage_score in all_scores.items():

        print(
            f"{stage}: "
            f"{stage_score:.2f}"
        )


# ----------------------------------------
# COMPLETE
# ----------------------------------------

print(
    "\n========================================"
)

print(
    "✓ VERIFICATION TEST COMPLETE"
)

print(
    "========================================"
)