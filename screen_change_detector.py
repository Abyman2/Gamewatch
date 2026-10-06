import cv2
import json
import numpy as np


# --------------------------------
# LOAD TV REGIONS
# --------------------------------

with open("tv_regions.json", "r") as file:
    tv_regions = json.load(file)


# --------------------------------
# OPEN CAMERA
# --------------------------------

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("ERROR: Could not open camera")
    exit()


print("GameWatch Screen Change Detector Started")
print("Press Q to quit.")


# Store the previous frame for each TV
previous_frames = {}


while True:

    success, frame = camera.read()

    if not success:
        print("ERROR: Could not read camera")
        break


    # Process every TV
    for tv in tv_regions:

        tv_id = tv["tv_id"]

        x = tv["x"]
        y = tv["y"]
        width = tv["width"]
        height = tv["height"]


        # Crop the TV
        tv_frame = frame[
            y:y + height,
            x:x + width
        ]


        # Convert to grayscale
        gray = cv2.cvtColor(
            tv_frame,
            cv2.COLOR_BGR2GRAY
        )


        # Resize to make comparison faster
        gray = cv2.resize(
            gray,
            (160, 90)
        )


        # First frame for this TV
        if tv_id not in previous_frames:

            previous_frames[tv_id] = gray

            continue


        # Compare current frame with previous frame
        difference = cv2.absdiff(
            previous_frames[tv_id],
            gray
        )


        # Calculate average difference
        change_score = np.mean(difference)


        # Save current frame
        previous_frames[tv_id] = gray


        # Decide whether there was a major change
        if change_score > 20:

            status = "BIG CHANGE!"

        else:

            status = "Normal"


        # Display score on the TV crop
        display_frame = tv_frame.copy()

        cv2.putText(
            display_frame,
            f"Change: {change_score:.1f}",
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        cv2.putText(
            display_frame,
            status,
            (10, 55),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255) if change_score > 20 else (0, 255, 0),
            2
        )


        # Show TV
        cv2.imshow(
            f"GameWatch - TV {tv_id}",
            display_frame
        )


    # Show full camera
    cv2.imshow(
        "GameWatch - Full Camera",
        frame
    )


    # Quit
    if cv2.waitKey(1) & 0xFF == ord("q"):

        break


camera.release()
cv2.destroyAllWindows()