import cv2
import numpy as np


# ----------------------------------------
# SETTINGS
# ----------------------------------------

CAMERA_INDEX = 0


# ----------------------------------------
# START CAMERA
# ----------------------------------------

camera = cv2.VideoCapture(
    CAMERA_INDEX
)


if not camera.isOpened():

    print(
        "❌ Could not open camera."
    )

    exit()


print(
    "\n========================================"
)

print(
    "GAMEWATCH LIVE DIFFERENCE TEST"
)

print(
    "========================================"
)

print(
    "\nPoint the camera at the TV."
)

print(
    "Press Q to quit."
)

print(
    "Press S to select the scoreboard area."
)


# ----------------------------------------
# VARIABLES
# ----------------------------------------

previous_crop = None

scoreboard_region = None

difference_value = 0


# ----------------------------------------
# MAIN LOOP
# ----------------------------------------

while True:

    success, frame = camera.read()


    if not success:

        print(
            "❌ Could not read camera."
        )

        break


    display = frame.copy()


    # ------------------------------------
    # SELECT SCOREBOARD
    # ------------------------------------

    if scoreboard_region is not None:

        x, y, width, height = (
            scoreboard_region
        )


        cv2.rectangle(

            display,

            (x, y),

            (
                x + width,
                y + height
            ),

            (0, 255, 0),

            2

        )


        # Crop scoreboard

        crop = frame[

            y:y + height,

            x:x + width

        ]


        if crop.size != 0:

            # Resize to make comparison stable

            crop = cv2.resize(

                crop,

                (160, 90)

            )


            # Convert to grayscale

            gray = cv2.cvtColor(

                crop,

                cv2.COLOR_BGR2GRAY

            )


            # --------------------------------
            # COMPARE WITH PREVIOUS FRAME
            # --------------------------------

            if previous_crop is not None:

                difference = cv2.absdiff(

                    previous_crop,

                    gray

                )


                difference_value = (

                    np.mean(difference)

                )


            previous_crop = gray.copy()


    # ------------------------------------
    # DISPLAY DIFFERENCE
    # ------------------------------------

    cv2.putText(

        display,

        f"Difference: {difference_value:.2f}",

        (20, 40),

        cv2.FONT_HERSHEY_SIMPLEX,

        0.9,

        (0, 255, 0),

        2

    )


    if scoreboard_region is None:

        cv2.putText(

            display,

            "Press S to select scoreboard",

            (20, 75),

            cv2.FONT_HERSHEY_SIMPLEX,

            0.7,

            (0, 255, 0),

            2

        )


    # ------------------------------------
    # SHOW CAMERA
    # ------------------------------------

    cv2.imshow(

        "GameWatch Live Difference",

        display

    )


    # ------------------------------------
    # KEYBOARD
    # ------------------------------------

    key = cv2.waitKey(1) & 0xFF


    # Select scoreboard

    if key == ord("s"):

        print(
            "\nSelect the scoreboard area."
        )

        print(
            "Press ENTER or SPACE when finished."
        )


        region = cv2.selectROI(

            "Select Scoreboard",

            frame,

            False,

            False

        )


        x, y, width, height = region


        if width > 0 and height > 0:

            scoreboard_region = (

                x,
                y,
                width,
                height

            )


            previous_crop = None

            print(
                "✓ Scoreboard region selected."
            )

        else:

            print(
                "❌ No region selected."
            )


        cv2.destroyWindow(
            "Select Scoreboard"
        )


    # Quit

    if key == ord("q"):

        break


# ----------------------------------------
# CLEANUP
# ----------------------------------------

camera.release()

cv2.destroyAllWindows()