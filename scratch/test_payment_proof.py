import urllib.request
import json
import base64
import time
import os

BASE = "http://127.0.0.1:5000"

def post(path, payload=None, cookie=None):
    data = json.dumps(payload or {}).encode("utf-8")
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers={"Content-Type": "application/json"})
    if cookie:
        req.add_header("Cookie", cookie)
    with urllib.request.urlopen(req) as resp:
        cookie_header = resp.headers.get("Set-Cookie")
        return resp.status, json.loads(resp.read().decode("utf-8")), cookie_header

def get(path, cookie=None):
    req = urllib.request.Request(f"{BASE}{path}")
    if cookie:
        req.add_header("Cookie", cookie)
    with urllib.request.urlopen(req) as resp:
        cookie_header = resp.headers.get("Set-Cookie")
        return resp.status, resp.read(), cookie_header

def test_proof_flow():
    print("--- 1. Authenticating as Owner (abyman) ---")
    st, auth_data, cookie = post("/api/auth/login", {
        "email": "abyman24680@gmail.com",
        "password": "password123"
    })
    assert st == 200
    print("PASS: Logged in")

    # Add 1 game to TV 1 so there is an active bill
    post("/api/tv/1/add_game", cookie=cookie)

    # 2. Test Checkout with a sample payment proof photo (base64) and NO SMS ref
    # Small 1x1 green png base64 for test
    sample_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    
    print("\n--- 2. Checking out with Payment Proof Photo (No SMS code required) ---")
    st, chk_res, _ = post("/api/tv/1/checkout", {
        "payment_method": "TELEBIRR",
        "payment_reference": "PHOTO_VERIFIED",
        "payment_proof_base64": sample_b64,
        "notes": "Verified by taking client phone screen photo"
    }, cookie=cookie)

    assert st == 200, f"Expected 200, got {st}: {chk_res}"
    assert chk_res["success"] is True
    tx_id = chk_res.get("transaction_id") or chk_res.get("transaction", {}).get("id")
    proof_url = chk_res.get("payment_proof")
    print(f"PASS: Checkout succeeded for Transaction #{tx_id}! Proof URL: {proof_url}")
    assert proof_url is not None and proof_url.startswith("/api/payment_proof/")

    print("\n--- 3. Verifying Saved Payment Proof Image is accessible ---")
    st, img_bytes, _ = get(proof_url, cookie=cookie)
    assert st == 200
    assert len(img_bytes) > 0
    print(f"PASS: Payment proof file served successfully ({len(img_bytes)} bytes)")

    print("\n--- 4. Verifying Transaction Details includes the photo proof ---")
    st, raw_tx, _ = get(f"/api/transaction/{tx_id}", cookie=cookie)
    tx_json = json.loads(raw_tx.decode("utf-8"))
    assert st == 200
    tx = tx_json["transaction"]
    assert tx["payment_proof"] == proof_url
    print(f"PASS: Transaction record verified with payment_proof: {tx['payment_proof']}")

    print("\n========================================================")
    print("PAYMENT PROOF PHOTO CAPTURE & CHECKOUT TESTS PASSED 100%!")
    print("========================================================")

if __name__ == "__main__":
    time.sleep(1)
    test_proof_flow()
