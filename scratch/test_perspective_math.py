import cv2
import numpy as np

def order_quad_points(pts):
    """
    Orders 4 points as: [Top-Left, Top-Right, Bottom-Right, Bottom-Left].
    """
    pts = np.array(pts, dtype="float32")
    rect = np.zeros((4, 2), dtype="float32")
    
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]  # TL
    rect[2] = pts[np.argmax(s)]  # BR
    
    diff = np.diff(pts, axis=1)  # y - x
    rect[1] = pts[np.argmin(diff)]  # TR
    rect[3] = pts[np.argmax(diff)]  # BL
    
    return rect

def rectify_perspective(image, corners, target_size=(960, 540)):
    """
    Warps an angled quadrilateral TV screen into a canonical 16:9 rectangle.
    """
    ordered = order_quad_points(corners)
    tw, th = target_size
    dst = np.array([
        [0, 0],
        [tw - 1, 0],
        [tw - 1, th - 1],
        [0, th - 1]
    ], dtype="float32")
    
    M = cv2.getPerspectiveTransform(ordered, dst)
    rectified = cv2.warpPerspective(image, M, (tw, th), flags=cv2.INTER_LINEAR)
    return rectified, M

def suppress_glare(image, clip_limit=2.8, tile_grid=(8, 8)):
    """
    Suppresses specular reflection and glare hotspots from overhead lights.
    """
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid)
    l_norm = clahe.apply(l)
    merged = cv2.merge((l_norm, a, b))
    return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

def estimate_keystone_angles(corners):
    """
    Calculates perspective keystone distortion angles.
    """
    ordered = order_quad_points(corners)
    tl, tr, br, bl = ordered
    
    # Top and bottom widths
    top_w = np.linalg.norm(tr - tl)
    bot_w = np.linalg.norm(br - bl)
    
    # Left and right heights
    left_h = np.linalg.norm(bl - tl)
    right_h = np.linalg.norm(br - tr)
    
    # Trapezoid convergence ratios
    horizontal_skew = abs(top_w - bot_w) / max(1.0, max(top_w, bot_w))
    vertical_skew = abs(left_h - right_h) / max(1.0, max(left_h, right_h))
    
    # Angles in degrees (approximate pitch and yaw)
    pitch_angle = np.degrees(np.arctan(vertical_skew * 1.5))
    yaw_angle = np.degrees(np.arctan(horizontal_skew * 1.5))
    
    return {
        "pitch_angle": round(float(pitch_angle), 1),
        "yaw_angle": round(float(yaw_angle), 1),
        "is_angled": bool(pitch_angle > 3.0 or yaw_angle > 3.0),
        "width_ratio": round(float(top_w / max(1.0, bot_w)), 2),
        "height_ratio": round(float(left_h / max(1.0, right_h)), 2)
    }

# Test ordering & angles
test_corners = [[100, 50], [500, 30], [530, 340], [80, 360]]
ordered = order_quad_points(test_corners)
angles = estimate_keystone_angles(test_corners)
print("Ordered:", ordered.tolist())
print("Angles:", angles)
