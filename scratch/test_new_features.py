import urllib.request
import json

BASE_URL = "http://127.0.0.1:5000"

def get(path):
    req = urllib.request.Request(f"{BASE_URL}{path}")
    with urllib.request.urlopen(req) as resp:
        return resp.status, resp.read().decode('utf-8')

def post(path, payload=None):
    data = json.dumps(payload or {}).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode('utf-8'))

def delete(path):
    req = urllib.request.Request(f"{BASE_URL}{path}", method="DELETE")
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode('utf-8'))

def test_features():
    print("Testing new hardening features...")

    # 1. Test Camera Connectors API
    status, raw = get("/api/camera_sources")
    assert status == 200, f"Expected 200, got {status}"
    data = json.loads(raw)
    assert data["success"] is True, "Failed to get camera sources"
    sources = data["sources"]
    print(f"PASS 1: Camera sources listed ({len(sources)} connectors found)")

    # 2. Add a new phone camera connector
    status, add_data = post("/api/camera_sources", {
        "name": "TV 3 Station Phone (DroidCam)",
        "source_type": "PHONE",
        "address": "http://192.168.1.120:4747/video",
        "tv_id": 3
    })
    assert status == 201, f"Expected 201, got {status}"
    new_id = add_data["id"]
    print(f"PASS 2: New camera connector registered with id={new_id}")

    # 3. Test camera connection ping (non-blocking)
    status, test_res = post(f"/api/camera_sources/{new_id}/test")
    assert status == 200, f"Expected 200, got {status}"
    assert "status" in test_res, "Expected status in test response"
    print(f"PASS 3: Camera source ping test responded: status={test_res['status']}")

    # 4. Delete camera connector
    status, del_res = delete(f"/api/camera_sources/{new_id}")
    assert status == 200, f"Expected 200, got {status}"
    print("PASS 4: Camera connector deleted cleanly")

    # 5. Verify HTML markup
    status, html = get("/")
    assert status == 200
    assert "flair-joystick" in html, "Missing flair-joystick in HTML"
    assert "flair-gamepad" in html, "Missing flair-gamepad in HTML"
    assert "flair-puzzle" in html, "Missing flair-puzzle in HTML"
    assert "camera-hub-panel" in html, "Missing camera-hub-panel in HTML"
    assert "add-camera-modal" in html, "Missing add-camera-modal in HTML"
    assert "lounge-hub-footer" in html, "Missing lounge-hub-footer in HTML"
    assert "settings-actions-bar" in html, "Missing settings-actions-bar in HTML"
    print("PASS 5: All required HTML elements and components present in index.html")

    # 6. Verify CSS definitions
    status, css = get("/static/css/style.css?v=10")
    assert status == 200
    assert "joystickWobble" in css, "Missing joystick animation in CSS"
    assert "gamepadFloat" in css, "Missing gamepad animation in CSS"
    assert "puzzleFloat" in css, "Missing puzzle animation in CSS"
    assert ".lounge-hub-footer" in css, "Missing lounge-hub-footer in CSS"
    assert ".camera-hub-panel" in css, "Missing camera-hub-panel in CSS"
    assert "#view-settings" in css, "Missing #view-settings in CSS"
    print("PASS 6: All animations, lounge hub, and settings clearance rules present in style.css")

    # 7. Verify JS definitions
    status, js = get("/static/js/app.js?v=10")
    assert status == 200
    assert "fetchCameraSources" in js, "Missing fetchCameraSources in app.js"
    assert "testCameraSource" in js, "Missing testCameraSource in app.js"
    assert "quickFillCamPreset" in js, "Missing quickFillCamPreset in app.js"
    print("PASS 7: All camera source connector handlers present in app.js")

    print("\nALL 7 FEATURE CHECKS PASSED PERFECTLY!")

if __name__ == "__main__":
    test_features()
