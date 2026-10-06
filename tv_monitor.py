import cv2
import json


# -----------------------------
# LOAD SAVED TV REGIONS
# -----------------------------

with open("tv_regions.json", "r") as file:
    tv_regions = json.load(file)


print("Loaded TV regions:")

for tv in tv_regions:
    print(f"TV {tv['tv_id']} loaded")


# -----------------------------
# OPEN CAMERA
# -----------------------------

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("ERROR: Could not open camera")
    exit()


print("\nGameWatch monitoring started!")
print("Press Q to quit.")


# -----------------------------
# LIVE MONITORING LOOP
# -----------------------------

while True:

    success, frame = camera.read()

    if not success:
        print("ERROR: Could not read camera")
        break


    # Go through every saved TV

    for tv in tv_regions:

        tv_id = tv["tv_id"]

        x = tv["x"]
        y = tv["y"]
        width = tv["width"]
        height = tv["height"]


        # Crop the TV from the full camera frame

        tv_frame = frame[
            y:y + height,
            x:x + width
        ]


        # Show each TV separately

        cv2.imshow(
            f"GameWatch - TV {tv_id}",
            tv_frame
        )


    # Show the full room too

    cv2.imshow(
        "GameWatch - Full Camera",
        frame
    )


    # Press Q to quit

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


camera.release()

cv2.destroyAllWindows()