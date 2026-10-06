import cv2
import os
import numpy as np


# ----------------------------------------
# SETTINGS
# ----------------------------------------

TEMPLATE_FOLDER = "scoreboard_templates"

MATCH_THRESHOLD = 13


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

    # Make both images the same size

    height = 90
    width = 160


    image1 = cv2.resize(
        image1,
        (width, height)
    )


    image2 = cv2.resize(
        image2,
        (width, height)
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
# LOAD STAGES
# ----------------------------------------

kickoff_template = load_template(
    "kickoff_scoreboard.jpg"
)

one_minute_template = load_template(
    "one_minute_scoreboard.jpg"
)

three_minutes_template = load_template(
    "three_minutes_scoreboard.jpg"
)


if (

    kickoff_template is None

    or

    one_minute_template is None

    or

    three_minutes_template is None

):

    print(
        "❌ Templates missing."
    )

    exit()


print(
    "\n✓ Kickoff template loaded"
)

print(
    "✓ One-minute template loaded"
)

print(
    "✓ Three-minute template loaded"
)


# ----------------------------------------
# MATCH STATE
# ----------------------------------------

current_stage = 0

game_count = 0


# ----------------------------------------
# DETECT BEST STAGE
# ----------------------------------------

def detect_stage(image):

    kickoff_score = calculate_difference(
        image,
        kickoff_template
    )


    one_minute_score = calculate_difference(
        image,
        one_minute_template
    )


    three_minutes_score = calculate_difference(
        image,
        three_minutes_template
    )


    scores = {

        "KICKOFF":
            kickoff_score,

        "ONE_MINUTE":
            one_minute_score,

        "THREE_MINUTES":
            three_minutes_score

    }


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
# TEST IMAGES
# ----------------------------------------

TEST_FOLDER = "test_images"


test_stages = [

    (
        "kickoff.jpg",
        "KICKOFF"
    ),

    (
        "one_minute.jpg",
        "ONE_MINUTE"
    ),

    (
        "three_minutes.jpg",
        "THREE_MINUTES"
    )

]


# ----------------------------------------
# START TEST
# ----------------------------------------

print(
    "\n========================================"
)

print(
    "GAMEWATCH MATCH VERIFICATION ENGINE"
)

print(
    "========================================"
)


for filename, expected_stage in test_stages:

    path = os.path.join(
        TEST_FOLDER,
        filename
    )


    image = cv2.imread(
        path
    )


    if image is None:

        print(
            f"\n❌ Could not load {filename}"
        )

        continue


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
        f"Best Difference: {score:.2f}"
    )


    print(
        "\nAll Scores:"
    )


    for stage, stage_score in all_scores.items():

        print(
            f"{stage}: "
            f"{stage_score:.2f}"
        )


    # ------------------------------------
    # MATCH VERIFICATION LOGIC
    # ------------------------------------

    if detected_stage == "KICKOFF":

        if current_stage == 0:

            current_stage = 1

            print(
                "\n🟢 STAGE 1 CONFIRMED"
            )

            print(
                "Kickoff detected."
            )

        else:

            print(
                "\nℹ Kickoff ignored."
            )


    elif detected_stage == "ONE_MINUTE":

        if current_stage == 1:

            current_stage = 2

            print(
                "\n🟡 STAGE 2 CONFIRMED"
            )

            print(
                "One-minute stage detected."
            )

        else:

            print(
                "\n⚠ One-minute stage ignored."
            )

            print(
                "Waiting for kickoff first."
            )


    elif detected_stage == "THREE_MINUTES":

        if current_stage == 2:

            current_stage = 0

            game_count += 1


            print(
                "\n🔴 STAGE 3 CONFIRMED"
            )

            print(
                "Three-minute stage detected."
            )


            print(
                "\n🎮🔥 MATCH VERIFIED!"
            )


            print(
                f"TOTAL GAMES: "
                f"{game_count}"
            )


        else:

            print(
                "\n⚠ Three-minute stage ignored."
            )

            print(
                "Previous stages not complete."
            )


# ----------------------------------------
# FINAL RESULT
# ----------------------------------------

print(
    "\n========================================"
)

print(
    "FINAL MATCH RESULT"
)

print(
    "========================================"
)


print(
    f"\nGames Verified: "
    f"{game_count}"
)


if game_count > 0:

    print(
        "\n🎮 SUCCESS!"
    )

    print(
        "GameWatch successfully verified "
        "the full match sequence."
    )

else:

    print(
        "\n❌ No complete match sequence detected."
    )


print(
    "\n========================================"
)