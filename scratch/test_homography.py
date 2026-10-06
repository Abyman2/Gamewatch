import cv2
import numpy as np
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scoreboard_reader import ScoreboardReader
from scoreboard_preprocessor import ScoreboardPreprocessor

img = cv2.imread("test_images/kickoff.jpg")
h, w = img.shape[:2]

# Let's say TV 1 is in region [60, 10, 540, 340]
# But because of camera tilt, it's angled:
# Top-left is at (80, 20), Top-right is at (580, 15),
# Bottom-right is at (600, 345), Bottom-left is at (70, 335)
quad_corners = np.float32([
    [80, 20],
    [580, 15],
    [600, 345],
    [70, 335]
])

canon_w, canon_h = 960, 540
dst_canon = np.float32([
    [0, 0],
    [canon_w - 1, 0],
    [canon_w - 1, canon_h - 1],
    [0, canon_h - 1]
])

M = cv2.getPerspectiveTransform(quad_corners, dst_canon)
rectified_tv = cv2.warpPerspective(img, M, (canon_w, canon_h))

reader = ScoreboardReader()
sb_crop, bbox, conf = reader.detect_and_crop_scoreboard(rectified_tv)
print(f"Scoreboard on rectified TV: conf={conf}, bbox={bbox}")
if sb_crop is not None and conf >= 0.40:
    reading = reader.read(sb_crop)
    print(f"Reading: clock={reading.clock_str}, score={reading.score_home}-{reading.score_away}, conf={reading.overall_confidence}")

# Test glare simulation and suppression
glare_img = rectified_tv.copy()
# Add a bright ceiling light glare hotspot
cv2.circle(glare_img, (200, 50), 70, (255, 255, 255), -1)

# Now apply illumination / glare suppression:
lab = cv2.cvtColor(glare_img, cv2.COLOR_BGR2LAB)
l, a, b = cv2.split(lab)
clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
l_norm = clahe.apply(l)
lab_norm = cv2.merge((l_norm, a, b))
suppressed = cv2.cvtColor(lab_norm, cv2.COLOR_LAB2BGR)
print("Glare suppression pipeline ran smoothly!")
