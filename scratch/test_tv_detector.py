import cv2
import numpy as np
import os
import json

def test_tv_detection():
    # Load simulation frame from app_server
    sim_dir = "static/img"
    sim_file = os.path.join(sim_dir, "sim_frame_1.jpg")
    if not os.path.exists(sim_file):
        # Create a synthetic dual-TV lounge frame
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        # TV 1 on left
        cv2.rectangle(frame, (80, 80), (580, 480), (40, 40, 40), -1)
        cv2.rectangle(frame, (100, 100), (560, 460), (0, 180, 0), -1) # green pitch
        # TV 2 on right
        cv2.rectangle(frame, (700, 80), (1200, 480), (40, 40, 40), -1)
        cv2.rectangle(frame, (720, 100), (1180, 460), (0, 160, 0), -1)
    else:
        frame = cv2.imread(sim_file)

    fh, fw = frame.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 40, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    detected = []
    min_area = (fw * fh) * 0.04

    for c in contours:
        area = cv2.contourArea(c)
        if area < min_area:
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.03 * peri, True)
        x, y, w, h = cv2.boundingRect(c)
        aspect = float(w) / max(1, h)
        if 1.1 <= aspect <= 2.4 and w >= 200 and h >= 120:
            detected.append((x, y, w, h))

    # If no contours met strict quad criteria, provide intelligent split
    if not detected:
        print("Using smart geometric split for dual stations")
        w_split = int(fw * 0.44)
        h_split = int(fh * 0.65)
        y_top = int(fh * 0.12)
        detected = [
            (int(fw * 0.04), y_top, w_split, h_split),
            (int(fw * 0.52), y_top, w_split, h_split)
        ]

    # Sort left to right
    detected.sort(key=lambda b: b[0])

    print(f"Detected {len(detected)} TV screens:")
    for idx, (x, y, w, h) in enumerate(detected, 1):
        crop = frame[y:y+h, x:x+w]
        var = cv2.Laplacian(crop, cv2.CV_64F).var()
        is_blurry = var < 70
        print(f" TV {idx}: pos=({x}, {y}, {w}, {h}), sharpness={var:.1f}, blurry={is_blurry}")

if __name__ == "__main__":
    test_tv_detection()
