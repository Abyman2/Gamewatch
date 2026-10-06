import cv2
import os


# ----------------------------------------
# IMAGE FOLDER
# ----------------------------------------

IMAGE_FOLDER = "test_images"

OUTPUT_FOLDER = "scoreboard_templates"


# ----------------------------------------
# CREATE OUTPUT FOLDER
# ----------------------------------------

os.makedirs(
    OUTPUT_FOLDER,
    exist_ok=True
)


# ----------------------------------------
# TEST IMAGES
# ----------------------------------------

images = {

    "STAGE 1 - MATCH STARTED": (
        "kickoff.jpg",
        "kickoff_scoreboard.jpg"
    ),

    "STAGE 2 - ONE MINUTE": (
        "one_minute.jpg",
        "one_minute_scoreboard.jpg"
    ),

    "STAGE 3 - THREE MINUTES": (
        "three_minutes.jpg",
        "three_minutes_scoreboard.jpg"
    )

}


# ----------------------------------------
# START
# ----------------------------------------

print(
    "\n========================================"
)

print(
    "GAMEWATCH SCOREBOARD TEMPLATE CREATOR"
)

print(
    "========================================"
)


# ----------------------------------------
# PROCESS EACH IMAGE
# ----------------------------------------

for stage, files in images.items():

    filename = files[0]

    output_filename = files[1]


    image_path = os.path.join(

        IMAGE_FOLDER,

        filename

    )


    image = cv2.imread(

        image_path

    )


    if image is None:

        print(

            f"\n❌ Could not load: {filename}"

        )

        continue


    print(

        "\n----------------------------------------"

    )

    print(

        f"Select the scoreboard for:"

    )

    print(

        stage

    )

    print(

        "Drag a box around the scoreboard."

    )

    print(

        "Then press ENTER or SPACE."

    )


    # ------------------------------------
    # SELECT SCOREBOARD
    # ------------------------------------

    scoreboard_region = cv2.selectROI(

        f"Select Scoreboard - {stage}",

        image,

        False,

        False

    )


    x, y, width, height = (

        scoreboard_region

    )


    # ------------------------------------
    # CHECK SELECTION
    # ------------------------------------

    if width == 0 or height == 0:

        print(

            "❌ No scoreboard selected."

        )

        cv2.destroyAllWindows()

        continue


    # ------------------------------------
    # CROP SCOREBOARD
    # ------------------------------------

    scoreboard = image[

        y:y + height,

        x:x + width

    ]


    # ------------------------------------
    # SAVE SCOREBOARD
    # ------------------------------------

    output_path = os.path.join(

        OUTPUT_FOLDER,

        output_filename

    )


    cv2.imwrite(

        output_path,

        scoreboard

    )


    # ------------------------------------
    # ZOOM SCOREBOARD
    # ------------------------------------

    zoomed_scoreboard = cv2.resize(

        scoreboard,

        None,

        fx=6,

        fy=6,

        interpolation=cv2.INTER_CUBIC

    )


    # ------------------------------------
    # SHOW RESULT
    # ------------------------------------

    cv2.imshow(

        f"SAVED - {stage}",

        zoomed_scoreboard

    )


    print(

        f"✓ Saved: {output_path}"

    )

    print(

        "Press any key to continue."

    )


    cv2.waitKey(0)


    cv2.destroyAllWindows()


print(

    "\n========================================"

)

print(

    "✓ ALL 3 SCOREBOARD TEMPLATES SAVED"

)

print(

    "========================================"
)