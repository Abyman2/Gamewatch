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
# SIMULATE CAMERA QUALITY
# ----------------------------------------

def simulate_camera_quality(image):

    # ------------------------------------
    # 1. REDUCE RESOLUTION
    # ------------------------------------

    height, width = image.shape[:2]

    small = cv2.resize(

        image,

        (
            max(1, width // 4),
            max(1, height // 4)
        )

    )


    # ------------------------------------
    # 2. SCALE BACK UP
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
    # 3. ADD BLUR
    # ------------------------------------

    simulated = cv2.GaussianBlur(

        simulated,

        (5, 5),

        0

    )


    # ------------------------------------
    # 4. SLIGHT BRIGHTNESS CHANGE
    # ------------------------------------

    simulated = cv2.convertScaleAbs(

        simulated,

        alpha=0.85,

        beta=-10

    )


    # ------------------------------------
    # 5. ADD SMALL CAMERA NOISE
    # ------------------------------------

    noise = np.random.normal(

        0,

        4,

        simulated.shape

    ).astype(np.int16)


    simulated = np.clip(

        simulated.astype(np.int16) + noise,

        0,

        255

    ).astype(np.uint8)


    return simulated


# ----------------------------------------
# CALCULATE DIFFERENCE
# ----------------------------------------

def calculate_difference(

    image1,

    image2

):

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
# LOAD AND SIMULATE IMAGES
# ----------------------------------------

print(

    "\n========================================"

)

print(

    "GAMEWATCH CAMERA QUALITY SIMULATION"

)

print(

    "========================================\n"

)


simulated_images = {}


for name, filename in IMAGES.items():

    image_path = os.path.join(

        IMAGE_FOLDER,

        filename

    )


    image = cv2.imread(

        image_path

    )


    if image is None:

        print(

            f"❌ Could not load {filename}"

        )

        continue


    simulated = simulate_camera_quality(

        image

    )


    simulated_images[name] = simulated


    print(

        f"✓ Simulated camera view: {name}"

    )


# ----------------------------------------
# COMPARE GAME STAGES
# ----------------------------------------

print(

    "\n========================================"

)

print(

    "SIMULATED CAMERA COMPARISON"

)

print(

    "========================================\n"

)


stages = list(

    simulated_images.keys()

)


for i in range(

    len(stages)

):

    for j in range(

        i + 1,

        len(stages)

    ):

        stage1 = stages[i]

        stage2 = stages[j]


        score = calculate_difference(

            simulated_images[stage1],

            simulated_images[stage2]

        )


        print(

            f"{stage1} vs {stage2}"

        )

        print(

            f"Difference Score: {score:.2f}\n"

        )


# ----------------------------------------
# SHOW RESULTS
# ----------------------------------------

for name, image in simulated_images.items():

    cv2.imshow(

        f"SIMULATED CAMERA - {name}",

        image

    )


print(

    "Press any key to close."

)


cv2.waitKey(0)

cv2.destroyAllWindows()