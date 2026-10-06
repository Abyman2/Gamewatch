import cv2
import os


# ----------------------------------------
# IMAGE FOLDER
# ----------------------------------------

IMAGE_FOLDER = "test_images"


# ----------------------------------------
# MATCH STAGES
# ----------------------------------------

images = {

    "STAGE 1 - MATCH STARTED":
        "kickoff.jpg",

    "STAGE 2 - ONE MINUTE":
        "one_minute.jpg",

    "STAGE 3 - THREE MINUTES":
        "three_minutes.jpg"

}


# ----------------------------------------
# LOAD AND DISPLAY IMAGES
# ----------------------------------------

print(
    "\n========================================"
)

print(
    "GAMEWATCH MATCH STAGE TEST"
)

print(
    "========================================"
)


for stage, filename in images.items():

    image_path = os.path.join(
        IMAGE_FOLDER,
        filename
    )


    # Check if image exists

    if not os.path.exists(
        image_path
    ):

        print(
            f"\n❌ IMAGE NOT FOUND:"
        )

        print(
            image_path
        )

        continue


    # Load image

    image = cv2.imread(
        image_path
    )


    # Check image loaded correctly

    if image is None:

        print(
            f"\n❌ COULD NOT LOAD:"
        )

        print(
            filename
        )

        continue


    # ------------------------------------
    # SHOW IMAGE
    # ------------------------------------

    print(
        f"\n✓ Loaded: {stage}"
    )

    print(
        f"File: {filename}"
    )

    print(
        f"Size: "
        f"{image.shape[1]} x "
        f"{image.shape[0]}"
    )


    # Resize large images

    height, width = image.shape[:2]

    max_width = 1000


    if width > max_width:

        scale = (
            max_width / width
        )


        new_width = int(
            width * scale
        )


        new_height = int(
            height * scale
        )


        image = cv2.resize(

            image,

            (
                new_width,
                new_height
            )

        )


    cv2.imshow(

        stage,

        image

    )


# ----------------------------------------
# WAIT FOR USER
# ----------------------------------------

print(
    "\n========================================"
)

print(
    "All available images loaded."
)

print(
    "Press any key in an image window "
    "to close."
)

print(
    "========================================"
)


cv2.waitKey(0)

cv2.destroyAllWindows()