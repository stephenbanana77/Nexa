"""Nexa V0 End-to-End Test with Kaggle Superstore dataset."""
import subprocess
import sys
import time
import json
import requests

BACKEND_URL = "http://localhost:8000"
TEST_EMAIL = "test@nexa.ai"
TEST_PASSWORD = "test123456"

def check_health():
    for i in range(20):
        try:
            r = requests.get(f"{BACKEND_URL}/api/health", timeout=2)
            if r.status_code == 200:
                print(f"  ✓ Backend is ready: {r.json()}")
                return True
        except:
            time.sleep(1)
    print("  ✗ Backend failed to start")
    return False

def register():
    print("\n[1] Register user...")
    r = requests.post(f"{BACKEND_URL}/api/auth/register", json={
        "email": TEST_EMAIL, "password": TEST_PASSWORD
    })
    if r.status_code == 400:
        print("  (User exists, skipping)")
    elif r.status_code == 200:
        print(f"  ✓ Registered: {r.json().get('email')}")
    else:
        print(f"  ! Unexpected: {r.status_code}")

def login():
    print("\n[2] Login...")
    r = requests.post(f"{BACKEND_URL}/api/auth/login", json={
        "email": TEST_EMAIL, "password": TEST_PASSWORD
    })
    if r.status_code == 200:
        token = r.json()["token"]
        print(f"  ✓ Token: {token[:30]}...")
        return token
    print(f"  ✗ Login failed: {r.status_code} {r.text[:200]}")
    return None

def create_project(token):
    print("\n[3] Create project...")
    r = requests.post(f"{BACKEND_URL}/api/projects", json={
        "name": "Superstore Analysis"
    }, headers={"Authorization": f"Bearer {token}"})
    if r.status_code == 200:
        pid = r.json()["id"]
        print(f"  ✓ Project: {pid}")
        return pid
    print(f"  ✗ Failed: {r.status_code} {r.text[:200]}")
    return None

def upload_csv(token, project_id):
    print("\n[4] Upload Superstore CSV...")
    csv_path = "storage/Sample - Superstore.csv"
    with open(csv_path, "rb") as f:
        r = requests.post(
            f"{BACKEND_URL}/api/datasets/upload?project_id={project_id}",
            files={"file": ("Sample - Superstore.csv", f, "text/csv")},
            headers={"Authorization": f"Bearer {token}"}
        )
    if r.status_code == 200:
        data = r.json()
        print(f"  ✓ Uploaded: {data['name']}")
        print(f"    Rows: {data['row_count']}, Cols: {data['column_count']}")
        print(f"    Schema sample: {[c['name'] for c in data['schema_info'][:5]]}")
        print(f"    Preview rows: {len(data['preview']['rows'])}")
        return data
    print(f"  ✗ Failed: {r.status_code} {r.text[:200]}")
    return None

def chat_analysis(token, project_id):
    print("\n[5] Chat: 'What are the top 5 product categories by total sales?'")
    r = requests.post(
        f"{BACKEND_URL}/api/chat/stream",
        json={"project_id": project_id, "message": "What are the top 5 product categories by total sales?"},
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "text/event-stream"
        },
        stream=True
    )
    if r.status_code != 200:
        print(f"  ✗ Chat failed: {r.status_code} {r.text[:200]}")
        return None

    events = []
    print("  Events:", end=" ", flush=True)
    for line in r.iter_lines(decode_unicode=True):
        if not line:
            continue
        if line.startswith("event:"):
            continue
        if line.startswith("data:"):
            try:
                event = json.loads(line[6:])
                events.append(event)
                print(f"[{event.get('event')}]", end=" ", flush=True)
            except:
                pass

    print()
    if events:
        last = events[-1]
        print(f"  ✓ Got {len(events)} events")
        if "summary" in last:
            print(f"\n  === AI Analysis ===")
            print(f"  {last['summary'][:500]}")
        if "sql" in last:
            print(f"\n  === Generated SQL ===")
            print(f"  {last['sql'][:300]}")
        if "row_count" in last:
            print(f"\n  === Results ===")
            print(f"  {last['row_count']} rows returned")
        return last
    return None

def main():
    print("=" * 60)
    print("  Nexa V0 — End-to-End Test")
    print("  Dataset: Kaggle Superstore (9,994 rows)")
    print("=" * 60)

    if not check_health():
        sys.exit(1)

    register()
    token = login()
    if not token:
        sys.exit(1)

    project_id = create_project(token)
    if not project_id:
        sys.exit(1)

    upload = upload_csv(token, project_id)
    if not upload:
        sys.exit(1)

    result = chat_analysis(token, project_id)

    print("\n" + "=" * 60)
    if result:
        print("  ✓ ALL STEPS PASSED — Nexa V0 is functional!")
    else:
        print("  ✗ Chat analysis failed — check LLM config")
    print("=" * 60)

if __name__ == "__main__":
    main()
