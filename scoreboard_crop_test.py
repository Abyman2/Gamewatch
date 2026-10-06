import cv2


# ----------------------------------------
# CAMERA SETTINGS
# ----------------------------------------

CAMERA_INDEX = 0


# ----------------------------------------
# OPEN CAMERA
# ----------------------------------------

camera = cv2.VideoCapture(
    CAMERA_INDEX
)


if not camera.isOpened():

    print(
        "ERROR: Could not open camera."
    )

    exit()


print(
    "\n========================================"
)

print(
    "GAMEWATCH SCOREBOARD CROP TEST"
)

print(
    "========================================"
)

print(
    "\nPoint the camera at the TV."
)

print(
    "Drag a box around the FULL TV."
)

print(
    "Then press ENTER."
)


# ----------------------------------------
# GET ONE FRAME
# ----------------------------------------

while True:

    success, frame = camera.read()


    if not success:

        print(
            "ERROR: Could not read camera."
        )

        camera.release()

        exit()


    cv2.imshow(
        "GameWatch - Camera",
        frame
    )


    key = cv2.waitKey(1) & 0xFF


    if key == ord("s"):

        break


    elif key == ord("q"):

        camera.release()

        cv2.destroyAllWindows()

        exit()


print(
    "\nFrame captured."
)

print(
    "Now select the FULL TV."
)


# ----------------------------------------
# SELECT FULL TV
# ----------------------------------------

tv_region = cv2.selectROI(

    "Select FULL TV",

    frame,

    False,

    False
)


x, y, width, height = tv_region


# Crop the full TV

tv_frame = frame[
    y:y + height,
    x:x + width
]


cv2.destroyWindow(
    "Select FULL TV"
)


# ----------------------------------------
# SELECT SCOREBOARD
# ----------------------------------------

print(
    "\nNow select ONLY the scoreboard."
)

print(
    "Select the TOP-LEFT area containing:"
)

print(
    "• Match time"
)

print(
    "• Score"
)

print(
    "• Team names if visible"
)


scoreboard_region = cv2.selectROI(

    "Select SCOREBOARD",

    tv_frame,

    False,

    False
)


sx, sy, sw, sh = scoreboard_region


scoreboard = tv_frame[
    sy:sy + sh,
    sx:sx + sw
]


cv2.destroyWindow(
    "Select SCOREBOARD"
)


# ----------------------------------------
# ZOOM SCOREBOARD
# ----------------------------------------

zoomed_scoreboard = cv2.resize(

    scoreboard,

    None,

    fx=5,

    fy=5,

    interpolation=cv2.INTER_CUBIC
)


# ----------------------------------------
# SHOW RESULTS
# ----------------------------------------

print(
    "\n========================================"
)

print(
    "CROP COMPLETE"
)

print(
    "========================================"
)

print(
    "\nYou should now see:"
)

print(
    "1. Full TV"
)

print(
    "2. Original scoreboard crop"
)

print(
    "3. Zoomed scoreboard"
)

print(
    "\nPress any key to close."
)


cv2.imshow(
    "1 - FULL TV",

    tv_frame
)


cv2.imshow(
    "2 - SCOREBOARD",

    scoreboard
)


cv2.imshow(
    "3 - ZOOMED SCOREBOARD",

    zoomed_scoreboard
)


cv2.waitKey(0)


camera.release()

cv2.destroyAllWindows()