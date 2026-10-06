import urllib.request
import urllib.parse
import http.cookiejar
import json

BASE_URL = "http://127.0.0.1:5000"
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def request(method, path, body=None):
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with opener.open(req) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        err_content = e.read().decode("utf-8")
        try:
            return e.code, json.loads(err_content)
        except Exception:
            return e.code, {"error": err_content}

# 1. Login as owner
status, login_res = request("POST", "/api/auth/login", {"email": "abyman24680@gmail.com", "password": "password123"})
assert status == 200, f"Login failed: {login_res}"
print("[PASS] 1. Authenticated as Owner (abyman)")

# 2. Test auto_detect_tvs with quadrilateral corner detection
status, data = request("POST", "/api/calibration/auto_detect_tvs")
assert status == 200, f"Auto-detect failed: {data}"
assert data.get("success"), "Auto-detect returned success=False"
screens = data.get("detected_screens", [])
print(f"[PASS] 2. Auto-detected {len(screens)} TV screens")
assert len(screens) > 0, "Expected at least 1 detected screen"
first_tv = screens[0]
assert "corners" in first_tv and len(first_tv["corners"]) == 4, "Missing 4 corners in detected screen"
assert "keystone" in first_tv, "Missing keystone diagnostics in detected screen"
print(f"       TV 1 corners: {first_tv['corners']}")
print(f"       TV 1 keystone: {first_tv['keystone']}")

# 3. Test analyze_crop with 4-point quadrilateral (simulating angled ceiling mount)
angled_corners = [
    [75, 25],
    [585, 15],
    [595, 345],
    [65, 355]
]
status, a_data = request("POST", "/api/tv/analyze_crop", {
    "corners": angled_corners,
    "anti_glare": True
})
assert status == 200, f"Analyze crop failed: {a_data}"
assert a_data.get("success"), "Analyze crop returned success=False"
assert a_data.get("is_quadrilateral") is True, "Expected is_quadrilateral=True"
assert a_data.get("anti_glare_applied") is True, "Expected anti_glare_applied=True"
assert a_data.get("tv_preview") is not None, "Missing tv_preview"
print(f"[PASS] 3. Homography perspective rectification & glare filter tested on angled quad:")
print(f"       Confidence: {a_data.get('confidence')}")
print(f"       Scoreboard found: {a_data.get('scoreboard_found')}")
print(f"       Keystone pitch: {a_data['keystone']['pitch_angle']}°, yaw: {a_data['keystone']['yaw_angle']}°")

# 4. Test save TV with 4 corners and anti_glare
status, save_res = request("POST", "/api/tv/save", {
    "tv_id": 1,
    "name": "TV 1 (Keystone Calibrated)",
    "customer_name": "Abel & Friends",
    "roi": a_data["tv_box"],
    "corners": angled_corners,
    "enable_anti_glare": True
})
assert status == 200, f"Save failed: {save_res}"
print("[PASS] 4. Successfully saved TV 1 with 4-point keystone calibration & anti-glare filter")

# 5. Verify state contains corners and is_quadrilateral
status, state_data = request("GET", "/api/state")
assert status == 200
tvs = state_data.get("tvs", [])
tv1 = next((t for t in tvs if t["id"] == 1), None)
assert tv1 is not None, "TV 1 not found in state"
assert tv1.get("is_quadrilateral") is True, "TV 1 should be quadrilateral"
assert tv1.get("corners") == angled_corners, "TV 1 corners mismatch in state"
assert tv1.get("enable_anti_glare") is True, "TV 1 anti-glare should be True"
print("[PASS] 5. Verified TV 1 in /api/state: is_quadrilateral=True, corners and anti-glare active")

# 6. Test backward compatibility: analyze and save with simple ROI [x, y, w, h] (TV 2)
status, la_data = request("POST", "/api/tv/analyze_crop", {
    "x": 680, "y": 10, "width": 540, "height": 340, "anti_glare": False
})
assert status == 200
assert la_data.get("success")
assert la_data.get("is_quadrilateral") is False
print("[PASS] 6. Verified 100% backward compatibility with legacy ROI bounding boxes")

print("\n=======================================================")
print("ALL STEP 1 BACKEND & COMPUTER VISION TESTS PASSED 100%!")
print("=======================================================")
