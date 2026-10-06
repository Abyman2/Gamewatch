import cv2


# ----------------------------------------
# CAMERA
# ----------------------------------------

CAMERA_INDEX = 0


# ----------------------------------------
# START CAMERA
# ----------------------------------------

camera = cv2.VideoCapture(
    CAMERA_INDEX
)


if not camera.isOpened():

    print("❌ Could not open camera.")

    exit()


print(
    "\n========================================"
)

print(
    "GAMEWATCH LIVE TV VISIBILITY TEST"
)

print(
    "========================================"
)

print(
    "\nPoint the camera at the TV."
)

print(
    "You should see the TV in the window."
)

print(
    "\nPress Q to quit."
)


# ----------------------------------------
# CAMERA LOOP
# ----------------------------------------

while True:

    success, frame = camera.read()


    if not success:

        print(
            "❌ Could not read camera."
        )

        break


    # ------------------------------------
    # SHOW FULL CAMERA
    # ------------------------------------

    cv2.imshow(
        "GameWatch - TV Camera View",
        frame
    )


    # ------------------------------------
    # QUIT
    # ------------------------------------

    key = cv2.waitKey(1) & 0xFF


    if key == ord("q"):

        break


# ----------------------------------------
# CLEANUP
# ----------------------------------------

camera.release()

cv2.destroyAllWindows()