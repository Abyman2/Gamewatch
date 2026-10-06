import urllib.request
import json
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = "http://127.0.0.1:5000"

def get(path, cookie=None):
    req = urllib.request.Request(f"{BASE}{path}")
    if cookie:
        req.add_header("Cookie", cookie)
    with urllib.request.urlopen(req) as resp:
        cookie_header = resp.headers.get("Set-Cookie")
        return resp.status, json.loads(resp.read().decode("utf-8")), cookie_header

def post(path, payload=None, cookie=None):
    data = json.dumps(payload or {}).encode("utf-8")
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers={"Content-Type": "application/json"})
    if cookie:
        req.add_header("Cookie", cookie)
    with urllib.request.urlopen(req) as resp:
        cookie_header = resp.headers.get("Set-Cookie")
        return resp.status, json.loads(resp.read().decode("utf-8")), cookie_header

def test_all():
    print("--- 1. Testing Lounge Code Verification for Clerk & Customer ---")
    st, data, _ = get("/api/auth/verify_lounge_code?code=GW-OWNER-050")
    assert st == 200, f"Expected 200, got {st}"
    assert data["valid"] is True, "Expected valid == True"
    assert data["lounge"]["name"] == "Abyman GameZone", f"Unexpected name: {data['lounge']['name']}"
    print(f"PASS: Verified GW-OWNER-050 -> {data['lounge']['name']} in {data['lounge']['area']}")

    print("\n--- 2. Testing Area Search Normalization ('4kilo' vs '4 Kilo') ---")
    st, data, _ = get("/api/lounges?search=4kilo")
    assert st == 200
    lounges = data.get("lounges", [])
    assert len(lounges) >= 2, f"Expected at least 2 lounges in 4 Kilo, found {len(lounges)}"
    names = [l["name"] for l in lounges]
    print(f"PASS: Search '4kilo' returned {len(lounges)} lounges: {names}")

    print("\n--- 3. Testing Geolocation Distance Sorting ---")
    # Coordinates near 4 Kilo (9.035, 38.762)
    st, data, _ = get("/api/lounges?lat=9.035&lng=38.762")
    assert st == 200
    lounges = data.get("lounges", [])
    assert len(lounges) > 0
    assert lounges[0]["distance_km"] is not None
    assert lounges[0]["distance_km"] < 1.0, f"Expected nearest lounge < 1km, got {lounges[0]['distance_km']}km"
    print(f"PASS: Nearest lounge is '{lounges[0]['name']}' at {lounges[0]['distance_km']:.2f} km")

    print("\n--- 4. Testing State API (cbe_enabled, promotions, events, area) ---")
    st, state, _ = get("/api/state")
    assert st == 200
    assert "cbe_enabled" in state, "Missing cbe_enabled in state"
    assert "lounge_area" in state, "Missing lounge_area in state"
    assert "events" in state, "Missing events in state"
    print(f"PASS: State contains area '{state.get('lounge_area')}', cbe_enabled={state.get('cbe_enabled')}, active_promo={bool(state.get('active_promotion'))}")

    print("\n--- 5. Testing Tournament & Events API ---")
    st, ev_data, _ = get("/api/events")
    assert st == 200
    events = ev_data.get("events", [])
    assert len(events) > 0, "No events returned"
    ev = events[0]
    print(f"PASS: Active tournament found: '{ev['title']}' ({ev['current_participants']}/{ev['max_participants']} registered, entry: {ev['entry_fee']} ETB)")

    # Test registering for event
    if ev['current_participants'] >= ev['max_participants']:
        import db_manager
        c = db_manager.get_connection()
        c.cursor().execute("UPDATE events SET current_participants = 14 WHERE id = ?", (ev['id'],))
        c.commit()
        c.close()

    st, reg_data, _ = post(f"/api/events/{ev['id']}/register", {
        "customer_name": "Test Gamer Yonas",
        "customer_phone": "0911998877",
        "payment_method": "TELEBIRR"
    })
    assert st == 200
    assert reg_data["success"] is True
    print(f"PASS: Successfully registered gamer in event (id: {reg_data.get('registration_id')})")

    # Authenticate as Owner (abyman) using login
    st, auth_data, cookie = post("/api/auth/login", {
        "email": "abyman24680@gmail.com",
        "password": "password123"
    })
    assert st == 200, f"Expected 200, got {st}: {auth_data}"
    print("PASS: Authenticated as Owner (abyman)")

    # Test attendees list with authenticated owner session
    st, part_data, _ = get(f"/api/events/{ev['id']}/participants", cookie=cookie)
    assert st == 200
    parts = part_data.get("participants", [])
    assert any(p["customer_name"] == "Test Gamer Yonas" for p in parts), "Registered participant missing from list"
    print(f"PASS: Participant list verified with {len(parts)} total attendees")

    print("\n--- 6. Testing -1 Deduct Game Endpoint & Audit Logging ---")
    # First add a game to ensure there's a game to deduct
    st, add_res, _ = post("/api/tv/1/add_game", cookie=cookie)
    prev_games = add_res.get("completed_games", 1)

    st, deduct_res, _ = post("/api/tv/1/deduct_game", {
        "reason": "Customer cancellation / accidental increment",
        "actor": "Station Clerk"
    }, cookie=cookie)
    assert st == 200
    assert deduct_res["success"] is True
    new_games = deduct_res.get("completed_games", 0)
    assert new_games == max(0, prev_games - 1), f"Expected {prev_games - 1}, got {new_games}"
    print(f"PASS: Deducted game on TV 1. Completed games: {prev_games} -> {new_games}")

    # Check audit log
    st, audit_data, _ = get("/api/audit_logs", cookie=cookie)
    assert st == 200
    logs = audit_data.get("logs", [])
    assert len(logs) > 0
    assert logs[0]["action"] == "MANUAL_GAME_DEDUCT", f"Expected MANUAL_GAME_DEDUCT, got {logs[0]['action']}"
    print(f"PASS: Audit log verified: {logs[0]['action']} by {logs[0]['actor']} (reason: {logs[0]['reason']})")

    print("\n--- 7. Testing Business Analytics Engine ---")
    st, ana_data, _ = get("/api/analytics/business", cookie=cookie)
    assert st == 200
    assert ana_data["success"] is True
    ana = ana_data["analytics"]
    assert "weekly_revenue" in ana
    assert "days" in ana and len(ana["days"]) == 7
    assert "peak_hours" in ana
    assert "station_performance" in ana
    assert "ai_insights" in ana
    print(f"PASS: Analytics report generated. Weekly rev: {ana['weekly_revenue']} ETB, Peak hours: {ana['peak_hours']}, AI insights: {len(ana['ai_insights'])}")

    print("\n========================================================")
    print("ALL 7 END-TO-END VERIFICATION CHECKS PASSED WITH 100% SUCCESS!")
    print("========================================================")

if __name__ == "__main__":
    time.sleep(1)
    test_all()
