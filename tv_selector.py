import cv2
import json

# Open default camera
camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("ERROR: Could not open camera")
    exit()

print("Camera opened!")
print("Press SPACE to capture the current frame.")
print("Press Q to quit.")

captured_frame = None

while True:
    success, frame = camera.read()

    if not success:
        print("ERROR: Could not read camera")
        break

    cv2.imshow("GameWatch - Press SPACE to Capture", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord(" "):
        captured_frame = frame.copy()
        break

    elif key == ord("q"):
        camera.release()
        cv2.destroyAllWindows()
        exit()

camera.release()
cv2.destroyAllWindows()

# Select multiple TV regions
print("\nDraw boxes around each TV.")
print("Press ENTER or SPACE after selecting each TV.")
print("When finished, press ESC.")

boxes = cv2.selectROIs(
    "Select TVs - Draw boxes around each TV",
    captured_frame,
    showCrosshair=True,
    fromCenter=False
)

cv2.destroyAllWindows()

tv_data = []

for index, box in enumerate(boxes):
    x, y, width, height = box

    tv = {
        "tv_id": index + 1,
        "x": int(x),
        "y": int(y),
        "width": int(width),
        "height": int(height)
    }

    tv_data.append(tv)

# Save TV positions
with open("tv_regions.json", "w") as file:
    json.dump(tv_data, file, indent=4)

print("\nTV regions saved successfully!")

for tv in tv_data:
    print(tv)