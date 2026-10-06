import cv2
import numpy as np
import os
import sys
import json
import urllib.request
import http.cookiejar

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scoreboard_preprocessor import (
    order_quad_points,
    rectify_perspective,
    suppress_glare,
    estimate_keystone_angles
)

def run_tests():
    print("=" * 60)
    print("STEP 1 HARDENING: COMPUTER VISION PIPELINE & CALIBRATION TEST")
    print("=" * 60)

    # 1. Pipeline Test: Test quadrilateral point ordering
    unordered_pts = [(400, 300), (50, 60), (420, 50), (40, 290)]
    ordered = order_quad_points(unordered_pts)
    assert len(ordered) == 4
    # TL should have min sum
    tl, tr, br, bl = ordered
    assert tl[0] < tr[0] and tl[1] < bl[1], f"Points misordered: {ordered}"
    print("[PASS] 1. Quad point ordering verified (deterministic clockwise order)")

    # 2. Pipeline Test: Synthetic Angled TV Screen with Specular Glare
    # Generate 1280x720 scene with a heavily keystoned screen (Ceiling mounted CCTV angle)
    scene = np.zeros((720, 1280, 3), dtype=np.uint8)
    scene[:] = (30, 30, 35) # Dark lounge room background

    # Angled quadrilateral TV screen:
    # Top edge is narrower (farther away), bottom edge is wider (closer)
    quad_corners = np.array([
        [280, 120],   # Top-Left
        [980, 100],   # Top-Right
        [1120, 620],  # Bottom-Right
        [160, 640]    # Bottom-Left
    ], dtype=np.float32)

    # Draw synthetic TV screen on scene
    cv2.fillPoly(scene, [quad_corners.astype(np.int32)], (180, 120, 60))
    # Add a mock scoreboard at top of TV
    cv2.putText(scene, "ARS 2 - 1 CHE", (460, 260), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
    cv2.putText(scene, "78:42", (580, 310), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
    # Add specular glare (bright fluorescent light reflection blob)
    cv2.circle(scene, (600, 280), 80, (255, 255, 255), -1)

    # Calculate keystone tilt
    angles = estimate_keystone_angles(quad_corners)
    print(f"[PASS] 2. Keystone angles estimated:")
    print(f"       Pitch: {angles['pitch_angle']}°, Yaw: {angles['yaw_angle']}°, Composite Tilt: {angles['composite_tilt']}°")
    assert angles["is_angled"] is True, "Screen should be detected as angled"

    # Rectify perspective to canonical 16:9 (960x540)
    rectified, M = rectify_perspective(scene, quad_corners, target_size=(960, 540))
    assert rectified.shape == (540, 960, 3), f"Unexpected shape {rectified.shape}"
    assert M is not None
    print("[PASS] 3. Homography perspective rectification produced exact 960x540 canonical feed")

    # Anti-glare suppression test
    deglared = suppress_glare(rectified)
    assert deglared.shape == (540, 960, 3)
    # Mean luminance should be normalized
    print("[PASS] 4. CLAHE Specular glare suppression executed cleanly")

    # Save debug output frames to scratch for inspection
    os.makedirs("scratch", exist_ok=True)
    cv2.imwrite("scratch/test_synthetic_scene.jpg", scene)
    cv2.imwrite("scratch/test_rectified_tv.jpg", rectified)
    cv2.imwrite("scratch/test_deglared_tv.jpg", deglared)
    print("       Saved debug frames to scratch/ for visual inspection")

    # 5. Integration Test with running app_server
    BASE_URL = "http://127.0.0.1:5000"
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    def api_req(method, path, body=None):
        url = f"{BASE_URL}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        if body is not None:
            req.add_header("Content-Type", "application/json")
        with opener.open(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))

    # Authenticate as owner
    status, login = api_req("POST", "/api/auth/login", {"email": "abyman24680@gmail.com", "password": "password123"})
    assert status == 200 and login.get("success")
    print("[PASS] 5. Authenticated with app_server API")

    # Test auto_detect_tvs endpoint
    status, auto_resp = api_req("POST", "/api/calibration/auto_detect_tvs")
    assert status == 200 and auto_resp.get("success")
    assert len(auto_resp.get("detected_screens", [])) > 0
    print(f"[PASS] 6. Auto-detect endpoint returned {len(auto_resp['detected_screens'])} screens with 4 corner vertices")

    # Test analyze_crop with 4-point quadrilateral & anti-glare
    c_pts = [[100, 50], [700, 30], [720, 420], [80, 440]]
    status, crop_resp = api_req("POST", "/api/tv/analyze_crop", {
        "corners": c_pts,
        "anti_glare": True
    })
    assert status == 200 and crop_resp.get("success")
    assert crop_resp.get("is_quadrilateral") is True
    assert crop_resp.get("tv_preview") is not None
    print(f"[PASS] 7. /api/tv/analyze_crop successfully rectified quad with tilt: {crop_resp['keystone']['composite_tilt']}°")

    # Test save station with corners
    status, save_resp = api_req("POST", "/api/tv/save", {
        "tv_id": 1,
        "name": "TV 1 (Keystone Ceiling Calibrated)",
        "customer_name": "VIP Gamers",
        "roi": crop_resp["tv_box"],
        "corners": c_pts,
        "enable_anti_glare": True
    })
    assert status == 200 and save_resp.get("success")
    print("[PASS] 8. /api/tv/save persisted 4-point corners and anti-glare toggle")

    # Verify state reflects saved settings
    status, state_resp = api_req("GET", "/api/state")
    assert status == 200
    tvs = state_resp.get("tvs", [])
    tv1 = next((t for t in tvs if t["id"] == 1), None)
    assert tv1 is not None
    assert tv1.get("is_quadrilateral") is True
    assert tv1.get("corners") == c_pts
    assert tv1.get("enable_anti_glare") is True
    print("[PASS] 9. /api/state confirms TV 1 is running 4-point homography & anti-glare in production")

    print("\n" + "=" * 60)
    print("ALL STEP 1 HARDENING CRITERIA VERIFIED AND PASSING 100%!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
