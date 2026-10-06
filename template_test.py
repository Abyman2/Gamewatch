import cv2
import os


# ----------------------------------------
# TEMPLATE FOLDER
# ----------------------------------------

TEMPLATE_FOLDER = "scoreboard_templates"


# ----------------------------------------
# LOAD IMAGES
# ----------------------------------------

images = {

    "KICKOFF": "kickoff_scoreboard.jpg",

    "ONE MINUTE": "one_minute_scoreboard.jpg",

    "THREE MINUTES": "three_minutes_scoreboard.jpg"

}


loaded_images = {}


for name, filename in images.items():

    path = os.path.join(
        TEMPLATE_FOLDER,
        filename
    )


    image = cv2.imread(
        path,
        cv2.IMREAD_GRAYSCALE
    )


    if image is None:

        print(
            f"❌ Could not load: {filename}"
        )

        continue


    loaded_images[name] = image


    print(
        f"✓ Loaded: {name}"
    )


# ----------------------------------------
# COMPARE FUNCTION
# ----------------------------------------

def compare_images(
    image1,
    image2
):

    # Resize both images to the same size

    image2 = cv2.resize(

        image2,

        (
            image1.shape[1],
            image1.shape[0]
        )

    )


    # Calculate absolute difference

    difference = cv2.absdiff(
        image1,
        image2
    )


    # Calculate average difference

    score = difference.mean()


    return score


# ----------------------------------------
# COMPARE STAGES
# ----------------------------------------

print(
    "\n========================================"
)

print(
    "GAMEWATCH TEMPLATE COMPARISON TEST"
)

print(
    "========================================"
)


template_names = list(
    loaded_images.keys()
)


for i in range(
    len(template_names)
):

    for j in range(
        i + 1,
        len(template_names)
    ):

        name1 = template_names[i]

        name2 = template_names[j]


        image1 = loaded_images[
            name1
        ]

        image2 = loaded_images[
            name2
        ]


        score = compare_images(

            image1,

            image2

        )


        print()

        print(
            f"{name1} vs {name2}"
        )

        print(
            f"Difference Score: "
            f"{score:.2f}"
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