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
# SIMULATE DIFFERENT CAMERA QUALITIES
# ----------------------------------------

def simulate_camera_quality(image, level):

    height, width = image.shape[:2]


    # ------------------------------------
    # LEVEL 1 — GOOD CAMERA
    # ------------------------------------

    if level == 1:

        scale = 2
        blur = 3
        noise_strength = 1


    # ------------------------------------
    # LEVEL 2 — MEDIUM CAMERA
    # ------------------------------------

    elif level == 2:

        scale = 3
        blur = 5
        noise_strength = 3


    # ------------------------------------
    # LEVEL 3 — POOR CAMERA
    # ------------------------------------

    elif level == 3:

        scale = 5
        blur = 7
        noise_strength = 5


    # ------------------------------------
    # LEVEL 4 — VERY POOR CAMERA
    # ------------------------------------

    else:

        scale = 8
        blur = 9
        noise_strength = 8


    # ------------------------------------
    # REDUCE RESOLUTION
    # ------------------------------------

    small = cv2.resize(

        image,

        (
            max(1, width // scale),
            max(1, height // scale)
        )

    )


    # ------------------------------------
    # SCALE BACK UP
    # ------------------------------------

    simulated = cv2.resize(

        small,

        (
            width,
            height
        ),

        interpolation=cv2.INTER_LINEAR

    )


    # ------------------------------------
    # ADD BLUR
    # ------------------------------------

    simulated = cv2.GaussianBlur(

        simulated,

        (blur, blur),

        0

    )


    # ------------------------------------
    # ADD NOISE
    # ------------------------------------

    noise = np.random.normal(

        0,
        noise_strength,
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
# LOAD ORIGINAL IMAGES
# ----------------------------------------

original_images = {}


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

    original_images[name] = image


# ----------------------------------------
# START TEST
# ----------------------------------------

print(
    "\n========================================"
)

print(
    "GAMEWATCH CAMERA QUALITY LEVEL TEST"
)

print(
    "========================================"
)


# ----------------------------------------
# TEST EACH QUALITY LEVEL
# ----------------------------------------

for level in range(1, 5):

    print(
        f"\n######## CAMERA QUALITY LEVEL {level} ########"
    )


    simulated_images = {}


    for name, image in original_images.items():

        simulated_images[name] = (
            simulate_camera_quality(
                image,
                level
            )
        )


    kickoff = simulated_images["KICKOFF"]

    one_minute = simulated_images["ONE MINUTE"]

    three_minutes = simulated_images["THREE MINUTES"]


    score_1 = calculate_difference(
        kickoff,
        one_minute
    )


    score_2 = calculate_difference(
        kickoff,
        three_minutes
    )


    score_3 = calculate_difference(
        one_minute,
        three_minutes
    )


    print(
        f"\nKICKOFF vs ONE MINUTE: "
        f"{score_1:.2f}"
    )

    print(
        f"KICKOFF vs THREE MINUTES: "
        f"{score_2:.2f}"
    )

    print(
        f"ONE MINUTE vs THREE MINUTES: "
        f"{score_3:.2f}"
    )


    # Show one example image

    cv2.imshow(

        f"Camera Quality Level {level}",

        simulated_images["KICKOFF"]

    )

    print(
        "\nPress any key to continue "
        "to the next quality level."
    )

    cv2.waitKey(0)

    cv2.destroyAllWindows()


print(
    "\n========================================"
)

print(
    "✓ ALL CAMERA QUALITY LEVELS TESTED"
)

print(
    "========================================"
)