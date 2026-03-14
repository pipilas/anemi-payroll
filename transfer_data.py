"""
Transfer all restaurant data from old UID to new UID in Firebase.
"""
import json
import urllib.request

DB_URL = "https://payroll-be52a-default-rtdb.firebaseio.com"

OLD_UID = "NC61woDSYbRmdlCcJxktMsYwrad2"
NEW_UID = "6vnGqaKTPXTQXMfWKYWpbCPKDa72"

def fb_get(path):
    url = f"{DB_URL}/{path}.json"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def fb_put(path, data):
    url = f"{DB_URL}/{path}.json"
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="PUT",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

# Step 1: Read all data from old UID
print(f"Reading all data from restaurant_data/{OLD_UID}...")
src_data = fb_get(f"restaurant_data/{OLD_UID}")

if not src_data:
    print("ERROR: No data found for old UID.")
    exit(1)

keys = list(src_data.keys()) if isinstance(src_data, dict) else []
print(f"  Found: {keys}")
for k in keys:
    if isinstance(src_data[k], dict):
        print(f"    {k}: {len(src_data[k])} entries")

# Step 2: Write to new UID
print(f"\nWriting all data to restaurant_data/{NEW_UID}...")
fb_put(f"restaurant_data/{NEW_UID}", src_data)
print("  Done!")

# Step 3: Verify
print("\nVerifying...")
dst_data = fb_get(f"restaurant_data/{NEW_UID}")
dst_keys = list(dst_data.keys()) if isinstance(dst_data, dict) else []

if set(keys) == set(dst_keys):
    print("\nTransfer complete! All data moved successfully.")
    print("Log out and back in on the app to see it.")
else:
    print("\nWarning: Keys don't match. Check manually.")
