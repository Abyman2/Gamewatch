import urllib.request
import json

def get(url):
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode())

def post(url, data):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())

print("1. Active shift status:", get("http://127.0.0.1:5000/api/shift/active"))
print("2. Starting shift:", post("http://127.0.0.1:5000/api/shift/start", {"clerk_name": "Hana"}))
print("3. Add audited game:", post("http://127.0.0.1:5000/api/tv/1/add_game", {
    "reason": "Camera missed detection",
    "explanation": "Celebration blocked clock",
    "actor": "Hana"
}))
logs = get("http://127.0.0.1:5000/api/audit_logs")
print("4. Audit logs count:", len(logs["logs"]))
print("5. Latest audit record:", logs["logs"][0])
shift_now = get("http://127.0.0.1:5000/api/shift/active")
print("6. Shift status after adjustment:", shift_now)
