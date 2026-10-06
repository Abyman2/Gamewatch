import urllib.request
import urllib.parse
import http.cookiejar
import json
import time

BASE_URL = "http://127.0.0.1:5000"

class Client:
    def __init__(self):
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))

    def request(self, method, path, data=None):
        url = f"{BASE_URL}{path}"
        headers = {"Content-Type": "application/json", "User-Agent": "TestClient/1.0"}
        body = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with self.opener.open(req) as resp:
                status = resp.status
                raw = resp.read().decode("utf-8")
                try:
                    res_json = json.loads(raw)
                except Exception:
                    res_json = raw
                return status, res_json
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8")
            try:
                res_json = json.loads(raw)
            except Exception:
                res_json = raw
            return e.code, res_json

    def get(self, path):
        return self.request("GET", path)

    def post(self, path, data=None):
        return self.request("POST", path, data)

def run_tests():
    s = Client()
    print("--- 1. Testing Unauthenticated Access ---")
    status, d = s.get("/api/auth/me")
    assert status == 401, f"Expected 401, got {status}"
    print("PASS: /api/auth/me is 401 when unauthenticated")

    status, d = s.post("/api/tv/save", {"tv_id": 1, "name": "TV 1"})
    assert status == 401, f"Expected 401, got {status}"
    print("PASS: /api/tv/save is 401 when unauthenticated")

    print("\n--- 2. Testing Registration Validations ---")
    # Missing fields
    status, d = s.post("/api/auth/register", {"email": "bad"})
    assert status == 400
    print("PASS: Missing fields rejected")

    # Invalid email
    status, d = s.post("/api/auth/register", {
        "full_name": "Test User", "email": "notanemail", "password": "password123", "confirm_password": "password123"
    })
    assert status == 400
    print("PASS: Invalid email format rejected")

    # Short password
    status, d = s.post("/api/auth/register", {
        "full_name": "Test User", "email": "test@gamewatch.et", "password": "123", "confirm_password": "123"
    })
    assert status == 400
    print("PASS: Short password rejected")

    # Password mismatch
    status, d = s.post("/api/auth/register", {
        "full_name": "Test User", "email": "test@gamewatch.et", "password": "password123", "confirm_password": "mismatch"
    })
    assert status == 400
    print("PASS: Password mismatch rejected")

    print("\n--- 3. Testing Real Registration ---")
    ts = int(time.time())
    owner_email = f"owner_{ts}@gamewatch.et"
    status, reg_data = s.post("/api/auth/register", {
        "full_name": "Lounge Owner",
        "email": owner_email,
        "phone": "+251911223344",
        "password": "production_password_2026",
        "confirm_password": "production_password_2026"
    })
    assert status == 200, f"Registration failed: {reg_data}"
    assert reg_data["needs_role"] is True
    assert "password_hash" not in reg_data["user"]
    print(f"PASS: User registered successfully: {owner_email}")

    # Duplicate email check
    status, d = s.post("/api/auth/register", {
        "full_name": "Duplicate User",
        "email": owner_email,
        "password": "production_password_2026",
        "confirm_password": "production_password_2026"
    })
    assert status == 400, "Duplicate email should be rejected"
    print("PASS: Duplicate email rejected")

    print("\n--- 4. Testing Role Enforcement Before Role Selection ---")
    status, me_data = s.get("/api/auth/me")
    assert status == 200
    assert me_data["needs_role"] is True
    print("PASS: Session active, needs_role is True")

    # Cannot access owner endpoints before selecting role
    status, d = s.post("/api/tv/save", {"tv_id": 99, "name": "Test TV"})
    assert status == 403, f"Expected 403, got {status}"
    print("PASS: Endpoint protected from user without role (403)")

    print("\n--- 5. Testing Role Questionnaire (Rule 5 & 6) ---")
    status, d = s.post("/api/auth/set_role", {"role": "HACKER"})
    assert status == 400, "Invalid role should be rejected"

    status, d = s.post("/api/auth/set_role", {"role": "OWNER"})
    assert status == 200
    assert d["user"]["role"] == "OWNER"
    print("PASS: Assigned role 'OWNER'")

    # Prohibit Role Switching (Rule 5 & 22)
    status, d = s.post("/api/auth/set_role", {"role": "CLERK"})
    assert status == 400, "Role switching must be prohibited!"
    print("PASS: Role switching attempt rejected (400)")

    print("\n--- 6. Testing Owner Privileges ---")
    status, d = s.post("/api/tv/save", {"tv_id": 1, "name": "TV 1 (Executive Lounge)"})
    assert status == 200
    print("PASS: Owner can configure TVs")

    print("\n--- 7. Testing Clerk Privileges & Isolation (Rule 8) ---")
    clerk_s = Client()
    clerk_email = f"clerk_{ts}@gamewatch.et"
    status, d = clerk_s.post("/api/auth/register", {
        "full_name": "Hana Clerk",
        "email": clerk_email,
        "password": "clerk_password_2026",
        "confirm_password": "clerk_password_2026"
    })
    assert status == 200
    clerk_s.post("/api/auth/set_role", {"role": "CLERK"})

    # Clerk CANNOT save TV (Owner only)
    status, d = clerk_s.post("/api/tv/save", {"tv_id": 2, "name": "Hacked TV"})
    assert status == 403, f"Expected 403 for Clerk on TV Save, got {status}"
    print("PASS: Clerk forbidden from TV administration (403)")

    # Clerk CAN start shift
    status, d = clerk_s.post("/api/shift/start", {})
    assert status == 200
    print("PASS: Clerk can start operational shift")

    print("\n--- 8. Testing Customer Privileges & Isolation (Rule 9 & 21) ---")
    cust_s = Client()
    cust_email = f"cust_{ts}@gamewatch.et"
    status, d = cust_s.post("/api/auth/register", {
        "full_name": "Dawit Gamer",
        "email": cust_email,
        "password": "gamer_password_2026",
        "confirm_password": "gamer_password_2026"
    })
    assert status == 200
    cust_s.post("/api/auth/set_role", {"role": "CUSTOMER"})

    # Customer CANNOT access TV save
    status, d = cust_s.post("/api/tv/save", {"tv_id": 1, "name": "Bad"})
    assert status == 403
    print("PASS: Customer forbidden from TV administration (403)")

    # Customer CANNOT access checkout
    status, d = cust_s.post("/api/tv/1/checkout", {})
    assert status == 403
    print("PASS: Customer forbidden from Checkout (403)")

    # Customer CANNOT access transactions
    status, d = cust_s.get("/api/transaction/1")
    assert status == 403
    print("PASS: Customer forbidden from Transaction details (403)")

    # Customer CAN join queue
    status, d = cust_s.post("/api/waiting_list", {"name": "Dawit Gamer", "phone": "0911223344", "station": "TV 1"})
    assert status == 200
    print("PASS: Customer can join waiting queue")

    print("\n--- 9. Testing Checkout & Detailed Financials (Rule 13, 14, 15, 16) ---")
    # Add a game to TV 1
    clerk_s.post("/api/tv/1/add_game", {"reason": "Test match verification", "explanation": "Player finished PES game"})
    
    # Execute Cash Checkout with amount received and change
    status, tx_res = clerk_s.post("/api/tv/1/checkout", {
        "payment_method": "CASH",
        "amount_received": 100.0,
        "discount": 0.0,
        "notes": "Cash in counter"
    })
    assert status == 200, f"Checkout failed: {tx_res}"
    assert tx_res["success"] is True
    tx_id = tx_res["transaction_id"]
    print(f"PASS: Checkout created transaction {tx_res['formatted_id']} (Total: {tx_res['total']} ETB, Recv: {tx_res['amount_received']} ETB, Change: {tx_res['change_given']} ETB)")

    # Inspect transaction details endpoint
    status, tx_json = clerk_s.get(f"/api/transaction/{tx_id}")
    assert status == 200
    tx_detail = tx_json["transaction"]
    assert tx_detail["amount_received"] == 100.0
    assert tx_detail["change_given"] == (100.0 - tx_res["total"])
    assert tx_detail["clerk_name"] == "Hana Clerk"
    print(f"PASS: Transaction details modal API verified with full financial breakdown")

    print("\n--- 10. Testing Password Reset (Rule 3) ---")
    status, d = s.post("/api/auth/reset_password", {
        "email": owner_email,
        "password": "new_super_secure_pwd_2026",
        "confirm_password": "new_super_secure_pwd_2026"
    })
    assert status == 200, f"Password reset failed: {d}"
    print("PASS: Password reset succeeded")

    # Logout and login with new password
    s.post("/api/auth/logout")
    status, d = s.post("/api/auth/login", {
        "email": owner_email,
        "password": "new_super_secure_pwd_2026"
    })
    assert status == 200, f"Login with new password failed: {d}"
    assert d["user"]["role"] == "OWNER"
    print("PASS: Logged in with new password; role persists as OWNER")

    print("\n==========================================")
    print("ALL 10 BACKEND ARCHITECTURE TESTS PASSED 100%")
    print("==========================================")

if __name__ == "__main__":
    run_tests()
