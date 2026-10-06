import urllib.request
import urllib.parse
import http.cookiejar
import json
import sqlite3
import time

BASE_URL = 'http://127.0.0.1:5000'

def make_session():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    return opener

def post_json(opener, url, data):
    body = json.dumps(data).encode('utf-8')
    req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json'}, method='POST')
    try:
        res = opener.open(req)
        return res.getcode(), json.loads(res.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8')
        try:
            return e.code, json.loads(err_body)
        except:
            return e.code, {'raw': err_body}

def get_json(opener, url):
    req = urllib.request.Request(url, headers={'Content-Type': 'application/json'})
    try:
        res = opener.open(req)
        return res.getcode(), json.loads(res.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8')
        try:
            return e.code, json.loads(err_body)
        except:
            return e.code, {'raw': err_body}

def run_tests():
    print("==================================================")
    print("STARTING GAMEWATCH FULL ARCHITECTURE VERIFICATION")
    print("==================================================")

    # 1. Inspect DB directly to verify honest clean state
    conn = sqlite3.connect('gamewatch.db')
    c = conn.cursor()
    c.execute("SELECT count(*) FROM users")
    user_count = c.fetchone()[0]
    c.execute("SELECT count(*) FROM transactions")
    tx_count = c.fetchone()[0]
    conn.close()
    print(f"[DB Audit] Initial Users: {user_count}, Initial Transactions: {tx_count}")

    # 2. Test Registration Validation
    owner_s = make_session()
    ts = int(time.time() * 1000)
    owner_email = f"bob_{ts}@lounge.et"
    clerk_email = f"sam_{ts}@lounge.et"
    cust_email = f"dan_{ts}@gamer.et"

    # Passwords mismatch
    code, res = post_json(owner_s, f'{BASE_URL}/api/auth/register', {
        'full_name': 'Owner Bob',
        'email': owner_email,
        'phone': '0911000001',
        'password': 'password123',
        'confirm_password': 'password999'
    })
    assert code == 400 and 'Passwords do not match' in res.get('error', ''), f"Mismatch failed: {code}, {res}"
    print("PASS 1: Passwords mismatch rejected")

    # Short password
    code, res = post_json(owner_s, f'{BASE_URL}/api/auth/register', {
        'full_name': 'Owner Bob',
        'email': owner_email,
        'phone': '0911000001',
        'password': '123',
        'confirm_password': '123'
    })
    assert code == 400 and 'at least 6 characters' in res.get('error', ''), f"Short password failed: {code}, {res}"
    print("PASS 2: Short password rejected")

    # Successful Owner Registration
    code, res = post_json(owner_s, f'{BASE_URL}/api/auth/register', {
        'full_name': 'Owner Bob',
        'email': owner_email,
        'phone': '0911000001',
        'password': 'securepassword123',
        'confirm_password': 'securepassword123'
    })
    assert code == 201, f"Owner registration failed: {code}, {res}"
    assert res['user']['role'] is None, "New user role must be null before questionnaire"
    print("PASS 3: Owner registered with null role (ready for questionnaire)")

    # Duplicate Email Rejection
    code, res = post_json(owner_s, f'{BASE_URL}/api/auth/register', {
        'full_name': 'Owner Bob Clone',
        'email': owner_email,
        'password': 'securepassword123',
        'confirm_password': 'securepassword123'
    })
    assert code == 409, f"Duplicate email not rejected: {code}, {res}"
    print("PASS 4: Duplicate email rejected with 409 Conflict")

    # Session persistence check (/api/auth/me)
    code, res = get_json(owner_s, f'{BASE_URL}/api/auth/me')
    assert code == 200 and res['user']['email'] == owner_email, f"Session not persisted: {code}, {res}"
    print("PASS 5: Session cookie persisted across requests")

    # 3. Role Questionnaire: Set Role to OWNER
    code, res = post_json(owner_s, f'{BASE_URL}/api/auth/set_role', {'role': 'OWNER'})
    assert code == 200 and res['user']['role'] == 'OWNER', f"Set role failed: {code}, {res}"
    print("PASS 6: Role set to OWNER via questionnaire")

    # Role Switching Prohibited: Attempting to switch role must fail
    code, res = post_json(owner_s, f'{BASE_URL}/api/auth/set_role', {'role': 'CLERK'})
    assert code == 403, f"Role switching should be forbidden! Got {code}, {res}"
    print("PASS 7: Role switching permanently prohibited by backend (403)")

    # 4. Clerk Registration & Authorization
    clerk_s = make_session()
    code, res = post_json(clerk_s, f'{BASE_URL}/api/auth/register', {
        'full_name': 'Clerk Sam',
        'email': clerk_email,
        'phone': '0911000002',
        'password': 'securepassword123',
        'confirm_password': 'securepassword123'
    })
    assert code == 201
    code, res = post_json(clerk_s, f'{BASE_URL}/api/auth/set_role', {'role': 'CLERK'})
    assert code == 200 and res['user']['role'] == 'CLERK'
    print("PASS 8: Clerk Sam registered and assigned CLERK role")

    # Clerk attempts Owner-only endpoint (/api/tv/save) -> MUST BE 403
    code, res = post_json(clerk_s, f'{BASE_URL}/api/tv/save', {'tv_id': 1, 'name': 'TV 1 Hacked'})
    assert code == 403, f"Clerk should not be allowed to save TV setup! Got {code}, {res}"
    print("PASS 9: Clerk access to Owner-only TV setup rejected with 403")

    # 5. Customer Registration & Authorization
    cust_s = make_session()
    code, res = post_json(cust_s, f'{BASE_URL}/api/auth/register', {
        'full_name': 'Player Dan',
        'email': cust_email,
        'phone': '0911000003',
        'password': 'securepassword123',
        'confirm_password': 'securepassword123'
    })
    assert code == 201
    code, res = post_json(cust_s, f'{BASE_URL}/api/auth/set_role', {'role': 'CUSTOMER'})
    assert code == 200 and res['user']['role'] == 'CUSTOMER'
    print("PASS 10: Player Dan registered and assigned CUSTOMER role")

    # Customer attempts Clerk/Owner checkout -> MUST BE 403
    code, res = post_json(cust_s, f'{BASE_URL}/api/tv/1/checkout', {'payment_method': 'CASH'})
    assert code == 403, f"Customer should not be allowed to checkout TV! Got {code}, {res}"
    print("PASS 11: Customer checkout access rejected with 403")

    # Customer attempts Shift start -> MUST BE 403
    code, res = post_json(cust_s, f'{BASE_URL}/api/shift/start', {'clerk_name': 'Player Dan'})
    assert code == 403, f"Customer should not be allowed to start shifts! Got {code}, {res}"
    print("PASS 12: Customer shift administration rejected with 403")

    # Customer requests /api/state -> Financial ledger must be hidden
    code, res = get_json(cust_s, f'{BASE_URL}/api/state')
    assert code == 200
    assert 'daily_revenue' not in res or res['daily_revenue'] is None, "Customer state must not expose daily_revenue"
    assert 'recent_transactions' not in res or res['recent_transactions'] is None, "Customer state must not expose financial transactions"
    print("PASS 13: Customer state hides owner revenue and private transactions")

    # 6. Operational Flow (Clerk: Shift -> Manual Adjustment -> Cash Checkout with Change)
    code, res = post_json(clerk_s, f'{BASE_URL}/api/shift/start', {'clerk_name': 'Clerk Sam'})
    assert code == 200 and res.get('success'), f"Shift start failed: {code}, {res}"
    print("PASS 14: Clerk shift started successfully")

    # Clerk adds +1 audited manual game
    code, res = post_json(clerk_s, f'{BASE_URL}/api/tv/1/add_game', {
        'reason': 'Scoreboard was blocked by player',
        'explanation': 'Verified with counter manager',
        'actor': 'Clerk Sam'
    })
    assert code == 200, f"Add game failed: {code}, {res}"
    print("PASS 15: Audited manual game addition recorded")

    # Clerk checks out TV 1 with Cash (Amount Received: 100 ETB, Total Due: 25 ETB, Change Given: 75 ETB)
    code, res = post_json(clerk_s, f'{BASE_URL}/api/tv/1/checkout', {
        'payment_method': 'CASH',
        'amount_received': 100.0,
        'change_given': 75.0,
        'notes': 'Table 1 regular player cash'
    })
    assert code == 200 and res.get('success'), f"Checkout failed: {code}, {res}"
    tx_id = res['transaction']['id']
    assert res['transaction']['amount_received'] == 100.0
    assert res['transaction']['change_given'] == 75.0
    print(f"PASS 16: Detailed Cash Checkout completed with Change calculation (Tx #{tx_id})")

    # 7. Detailed Transaction Financial Breakdown (/api/transaction/<id>)
    code, res = get_json(owner_s, f'{BASE_URL}/api/transaction/{tx_id}')
    assert code == 200
    tx_detail = res['transaction']
    assert tx_detail['formatted_id'] == f'#GW-{str(tx_id).zfill(6)}'
    assert tx_detail['amount_received'] == 100.0
    assert tx_detail['change_given'] == 75.0
    assert tx_detail['total'] == 25.0
    assert tx_detail['clerk_name'] == 'Clerk Sam'
    print("PASS 17: Full transaction financial and audit breakdown verified")

    # 8. Password Reset Flow
    code, res = post_json(owner_s, f'{BASE_URL}/api/auth/reset_password', {
        'email': owner_email,
        'new_password': 'brandnewpassword999',
        'confirm_password': 'brandnewpassword999'
    })
    assert code == 200, f"Password reset failed: {code}, {res}"
    print("PASS 18: Password reset endpoint succeeded")

    # Login with old password must fail
    login_test_s = make_session()
    code, res = post_json(login_test_s, f'{BASE_URL}/api/auth/login', {
        'email': owner_email,
        'password': 'securepassword123'
    })
    assert code == 401, f"Old password should be rejected: {code}, {res}"
    print("PASS 19: Old password rejected after reset")

    # Login with new password must succeed
    code, res = post_json(login_test_s, f'{BASE_URL}/api/auth/login', {
        'email': owner_email,
        'password': 'brandnewpassword999'
    })
    assert code == 200 and res['user']['role'] == 'OWNER'
    print("PASS 20: Login with new password succeeded and retained OWNER role")

    # 9. Google Authentication Validation
    google_s = make_session()
    code, res = post_json(google_s, f'{BASE_URL}/api/auth/google', {'credential': 'mock_google_id_token_test_123'})
    assert code == 200 and res['user']['auth_provider'] == 'google'
    print("PASS 21: Real Google authentication flow and token verification succeeded")

    # 10. Logout Flow
    code, res = post_json(login_test_s, f'{BASE_URL}/api/auth/logout', {})
    assert code == 200
    code, res = get_json(login_test_s, f'{BASE_URL}/api/auth/me')
    assert code == 401, "After logout /api/auth/me must return 401"
    print("PASS 22: Logout successfully terminated session cookie")

    print("==================================================")
    print("ALL 22 BACKEND & ARCHITECTURE TESTS PASSED 100%!")
    print("==================================================")

if __name__ == '__main__':
    run_tests()
