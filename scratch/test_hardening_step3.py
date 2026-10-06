import urllib.request
import urllib.parse
import http.cookiejar
import json
import time

BASE_URL = "http://127.0.0.1:5000"

def run_tests():
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

    def request(method, path, data=None):
        url = BASE_URL + path
        headers = {"Content-Type": "application/json"}
        req_data = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
        try:
            with opener.open(req) as resp:
                body = resp.read().decode("utf-8")
                return resp.status, json.loads(body) if body else {}
        except urllib.error.HTTPError as err:
            body = err.read().decode("utf-8")
            try:
                parsed = json.loads(body)
            except Exception:
                parsed = {"raw": body}
            return err.code, parsed

    print("--- 1. Health Check ---")
    status, data = request("GET", "/api/health")
    assert status == 200, f"Health check failed: {status}"
    print("Health check: PASS")

    print("\n--- 2. Auth: Strict Email & Password Complexity Validation ---")
    # Weak email
    status, data = request("POST", "/api/auth/register", {
        "full_name": "Test User",
        "email": "notanemail",
        "password": "Password123!",
        "confirm_password": "Password123!"
    })
    assert status == 400, f"Failed to reject invalid email, got {status}"
    print("Invalid email rejected: PASS")

    # Weak password (missing special char or uppercase)
    status, data = request("POST", "/api/auth/register", {
        "full_name": "Test User",
        "email": "valid.user@gamewatch.et",
        "password": "simplepassword",
        "confirm_password": "simplepassword"
    })
    assert status == 400, f"Failed to reject weak password, got {status}"
    print("Weak password rejected: PASS")

    # Valid registration
    unique_email = f"clerk.test.{int(time.time())}@gamewatch.et"
    status, data = request("POST", "/api/auth/register", {
        "full_name": "Clerk Test",
        "email": unique_email,
        "password": "StrongPassword123!",
        "confirm_password": "StrongPassword123!"
    })
    assert status in (200, 201), f"Registration failed: {status} {data}"
    user_data = data["user"]
    print(f"Valid registration accepted for {unique_email}: PASS")

    print("\n--- 3. Clerk Lounge Code Requirement & Scoping ---")
    # Invalid code
    status, data = request("POST", "/api/auth/set_role", {
        "role": "CLERK",
        "lounge_code": "INVALID-CODE-999"
    })
    assert status == 400, f"Failed to reject invalid clerk code, got {status}"
    print("Invalid clerk code rejected: PASS")

    # Valid code: GW-BOLE-101 (Bole Medhanialem, 2 TVs)
    status, data = request("POST", "/api/auth/set_role", {
        "role": "CLERK",
        "lounge_code": "GW-BOLE-101"
    })
    assert status == 200, f"Valid code failed: {status} {data}"
    print("Valid clerk code GW-BOLE-101 bound: PASS")

    print("\n--- 4. Verify Clerk TV Station Scoping (2 TVs, not 4) ---")
    status, state = request("GET", "/api/state")
    assert status == 200
    tv_count = len(state["tvs"])
    print(f"Clerk state TV count: {tv_count} (Lounge: {state.get('lounge_name')}, Code: {state.get('lounge_code')})")
    assert tv_count == 2, f"Expected 2 TVs for Bole lounge, got {tv_count}"
    print("Clerk station count correctly scoped to 2 TVs: PASS")

    print("\n--- 5. Simulation Toggle (Clerk & Owner Allowed) ---")
    status, sim_data = request("POST", "/api/simulation/toggle")
    assert status == 200, f"Simulation toggle failed: {status} {sim_data}"
    assert "mode" in sim_data, f"Mode missing from response: {sim_data}"
    print(f"Simulation toggle succeeded: mode is '{sim_data['mode']}': PASS")

    print("\n--- 6. TV Auto-Detection & Laplacian Sharpness Quality Diagnostics (as Owner) ---")
    owner_email = f"owner.test.{int(time.time())}@gamewatch.et"
    status, o_reg = request("POST", "/api/auth/register", {
        "full_name": "Owner Test",
        "email": owner_email,
        "password": "StrongPassword123!",
        "confirm_password": "StrongPassword123!"
    })
    assert status in (200, 201)
    status, o_role = request("POST", "/api/auth/set_role", {"role": "OWNER"})
    assert status == 200

    status, ad_data = request("POST", "/api/calibration/auto_detect_tvs")
    assert status == 200, f"Auto-detect TVs failed: {status} {ad_data}"
    assert ad_data["success"] is True
    screens = ad_data["detected_screens"]
    print(f"Auto-detected {len(screens)} TV station(s):")
    for s in screens:
        print(f"  - TV {s['tv_id']} '{s['label']}': bbox={s['bounding_box']}, sharpness={s['sharpness_score']}, blurry={s['is_blurry']}, scoreboard={s['scoreboard_detected']}")
    print("TV auto-detection with edge & sharpness analysis: PASS")

    print("\n--- 7. Lounge Explorer Search & Join ---")
    status, l_data = request("GET", "/api/lounges?search=CMC")
    assert status == 200
    lounges = l_data["lounges"]
    assert any("CMC" in l["lounge_code"] or "CMC" in l["name"] for l in lounges)
    print(f"Lounge Explorer found CMC lounge: PASS")

    print("\n--- 8. Dynamic Camera Source Activation ---")
    status, cam_data = request("POST", "/api/camera_sources", {
        "name": "Phone Cam IP Webcam Test",
        "source_type": "PHONE",
        "address": "http://192.168.1.105:8080/video",
        "tv_id": 1
    })
    assert status in (200, 201), f"Add camera source failed: {status} {cam_data}"
    source_id = cam_data["source"]["id"]
    status, act_data = request("POST", f"/api/camera_sources/{source_id}/activate")
    assert status == 200
    print(f"Camera source #{source_id} successfully activated live: PASS")

    print("\n==========================================")
    print("ALL 8 HARDENING STEP 3 TESTS PASSED!")
    print("==========================================")

if __name__ == "__main__":
    run_tests()
