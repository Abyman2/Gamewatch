import cv2
import json
import numpy as np
import time


with open("tv_regions.json", "r") as file:
    tv_regions = json.load(file)


camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("ERROR: Could not open camera")
    exit()


print("GameWatch Stable Change Detector Started")
print("Press Q to quit.")


previous_frames = {}

# Stores whether each TV is currently
# in a "possible screen change" state
change_detected = {}

# Time when the change started
change_time = {}

# Prevent repeated triggers
cooldown_until = {}


CHANGE_THRESHOLD = 20
WAIT_SECONDS = 2
COOLDOWN_SECONDS = 5


while True:

    success, frame = camera.read()

    if not success:
        break


    current_time = time.time()


    for tv in tv_regions:

        tv_id = tv["tv_id"]

        x = tv["x"]
        y = tv["y"]
        width = tv["width"]
        height = tv["height"]


        tv_frame = frame[
            y:y + height,
            x:x + width
        ]


        gray = cv2.cvtColor(
            tv_frame,
            cv2.COLOR_BGR2GRAY
        )


        gray = cv2.resize(
            gray,
            (160, 90)
        )


        # First frame setup
        if tv_id not in previous_frames:

            previous_frames[tv_id] = gray
            change_detected[tv_id] = False
            change_time[tv_id] = 0
            cooldown_until[tv_id] = 0

            continue


        difference = cv2.absdiff(
            previous_frames[tv_id],
            gray
        )

        change_score = np.mean(
            difference
        )


        previous_frames[tv_id] = gray


        status = "NORMAL"


        # Only detect if not in cooldown
        if current_time > cooldown_until[tv_id]:

            # Big change detected
            if (
                change_score > CHANGE_THRESHOLD
                and not change_detected[tv_id]
            ):

                change_detected[tv_id] = True

                change_time[tv_id] = current_time

                print(
                    f"TV {tv_id}: "
                    f"SCREEN CHANGE DETECTED"
                )


            # Wait before confirming
            if change_detected[tv_id]:

                elapsed = (
                    current_time
                    - change_time[tv_id]
                )

                status = (
                    f"ANALYZING... "
                    f"{elapsed:.1f}s"
                )


                if elapsed >= WAIT_SECONDS:

                    print(
                        f"TV {tv_id}: "
                        f"NEW SCREEN CONFIRMED"
                    )

                    # Save screenshot
                    filename = (
                        f"tv_{tv_id}_"
                        f"changed_screen.jpg"
                    )

                    cv2.imwrite(
                        filename,
                        tv_frame
                    )

                    print(
                        f"Saved: {filename}"
                    )


                    # Reset
                    change_detected[tv_id] = False

                    cooldown_until[tv_id] = (
                        current_time
                        + COOLDOWN_SECONDS
                    )

                    status = (
                        "SCREEN CAPTURED"
                    )


        else:

            remaining = (
                cooldown_until[tv_id]
                - current_time
            )

            status = (
                f"COOLDOWN {remaining:.1f}s"
            )


        display_frame = tv_frame.copy()


        cv2.putText(
            display_frame,
            f"Change: {change_score:.1f}",
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2
        )


        cv2.putText(
            display_frame,
            status,
            (10, 55),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 255),
            2
        )


        cv2.imshow(
            f"GameWatch - TV {tv_id}",
            display_frame
        )


    cv2.imshow(
        "GameWatch - Full Camera",
        frame
    )


    if cv2.waitKey(1) & 0xFF == ord("q"):

        break


camera.release()

cv2.destroyAllWindows()