import cv2
import os
import numpy as np


# ----------------------------------------
# SETTINGS
# ----------------------------------------

IMAGE_FOLDER = "test_images"

IMAGES = {
    "KICKOFF": "kickoff.jpg",
    "ONE MINUTE": "one_minute.jpg",
    "THREE MINUTES": "three_minutes.jpg"
}


# ----------------------------------------
# SIMULATE SLIGHT CAMERA VARIATION
# ----------------------------------------

def simulate_camera_variation(image):

    # Make a copy

    simulated = image.copy()


    # ------------------------------------
    # SLIGHT BLUR
    # ------------------------------------

    simulated = cv2.GaussianBlur(

        simulated,

        (3, 3),

        0

    )


    # ------------------------------------
    # SLIGHT BRIGHTNESS VARIATION
    # ------------------------------------

    alpha = np.random.uniform(

        0.95,

        1.05

    )

    beta = np.random.randint(

        -5,

        6

    )


    simulated = cv2.convertScaleAbs(

        simulated,

        alpha=alpha,

        beta=beta

    )


    # ------------------------------------
    # SMALL CAMERA NOISE
    # ------------------------------------

    noise = np.random.normal(

        0,

        2,

        simulated.shape

    ).astype(np.int16)


    simulated = np.clip(

        simulated.astype(np.int16)
        + noise,

        0,

        255

    ).astype(np.uint8)


    return simulated


# ----------------------------------------
# CALCULATE DIFFERENCE
# ----------------------------------------

def calculate_difference(image1, image2):

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
# LOAD IMAGES
# ----------------------------------------

loaded_images = {}


for name, filename in IMAGES.items():

    path = os.path.join(

        IMAGE_FOLDER,

        filename

    )


    image = cv2.imread(path)


    if image is None:

        print(

            f"❌ Could not load {filename}"

        )

        exit()


    loaded_images[name] = image


# ----------------------------------------
# START TEST
# ----------------------------------------

print(

    "\n========================================"

)

print(

    "GAMEWATCH STABILITY VS CHANGE TEST"

)

print(

    "========================================"

)


# ----------------------------------------
# TEST SAME IMAGE VARIATIONS
# ----------------------------------------

print(

    "\nSAME STAGE — CAMERA VARIATION"
)

print(

    "----------------------------------------"
)


same_stage_scores = []


for name, image in loaded_images.items():

    print(

        f"\n{name}:"
    )


    # Create 5 slightly different
    # camera versions

    versions = []


    for i in range(5):

        version = simulate_camera_variation(

            image

        )

        versions.append(

            version

        )


    # Compare consecutive versions

    for i in range(

        len(versions) - 1

    ):

        score = calculate_difference(

            versions[i],

            versions[i + 1]

        )


        same_stage_scores.append(

            score

        )


        print(

            f"Variation {i + 1} "
            f"vs {i + 2}: "
            f"{score:.2f}"

        )


# ----------------------------------------
# DIFFERENT GAME STAGES
# ----------------------------------------

print(

    "\n========================================"

)

print(

    "DIFFERENT GAME STAGES"
)

print(

    "----------------------------------------"
)


kickoff = loaded_images["KICKOFF"]

one_minute = loaded_images["ONE MINUTE"]

three_minutes = loaded_images["THREE MINUTES"]


change_scores = []


comparisons = [

    (
        "KICKOFF vs ONE MINUTE",
        kickoff,
        one_minute
    ),

    (
        "KICKOFF vs THREE MINUTES",
        kickoff,
        three_minutes
    ),

    (
        "ONE MINUTE vs THREE MINUTES",
        one_minute,
        three_minutes
    )

]


for label, image1, image2 in comparisons:

    score = calculate_difference(

        image1,

        image2

    )


    change_scores.append(

        score

    )


    print(

        f"\n{label}: "
        f"{score:.2f}"

    )


# ----------------------------------------
# FINAL ANALYSIS
# ----------------------------------------

print(

    "\n========================================"

)

print(

    "FINAL RESULTS"
)

print(

    "========================================"
)


print(

    f"\nHighest SAME-STAGE variation: "
    f"{max(same_stage_scores):.2f}"
)


print(

    f"Lowest REAL stage change: "
    f"{min(change_scores):.2f}"
)


gap = (

    min(change_scores)
    -
    max(same_stage_scores)

)


print(

    f"\nDetection gap: "
    f"{gap:.2f}"
)


print(

    "\n----------------------------------------"
)


if gap > 5:

    print(

        "✓ STRONG SEPARATION"
    )

    print(

        "Camera variation and real "
        "stage changes are clearly different."
    )


elif gap > 0:

    print(

        "⚠ SOME SEPARATION"
    )

    print(

        "The method may work, but needs "
        "careful thresholds."
    )


else:

    print(

        "❌ OVERLAP DETECTED"
    )

    print(

        "Simple image difference is not "
        "reliable enough by itself."
    )


print(

    "\n========================================"

)

print(

    "TEST COMPLETE"
)

print(

    "========================================"
)