import requests
import re

session = requests.Session()
BASE_URL = "http://127.0.0.1:5000"

print("--- 1. Testing Registration ---")
# Get registration page and extract CSRF token
resp_reg_page = session.get(f"{BASE_URL}/register")
match = re.search(r'name="csrf_token"\s+value="([^"]+)"', resp_reg_page.text)
if not match:
    # Try meta tag
    match = re.search(r'<meta name="csrf-token" content="([^"]+)"', resp_reg_page.text)

csrf_token = match.group(1) if match else None
print("Found CSRF Token:", csrf_token[:8] + "...")

# Register user
reg_payload = {
    'username': 'evaluator_demo',
    'password': 'CollegeProjectPassword2026',
    'confirm_password': 'CollegeProjectPassword2026',
    'csrf_token': csrf_token
}
resp_reg = session.post(f"{BASE_URL}/register", data=reg_payload, allow_redirects=True)
print("Registration Response Status:", resp_reg.status_code)
assert "@evaluator_demo" in resp_reg.text
print("Registered and logged in as @evaluator_demo successfully!")

print("\n--- 2. Testing Favourite Toggle (AJAX) ---")
# Toggle favourite for "cargo pants"
fav_payload = {
    'item_name': 'cargo pants',
    'category': 'men'
}
headers = {
    'X-CSRFToken': csrf_token,
    'Content-Type': 'application/json'
}
resp_fav = session.post(f"{BASE_URL}/api/favourites/toggle", json=fav_payload, headers=headers)
print("Toggle Favourite Status:", resp_fav.status_code, resp_fav.json())
assert resp_fav.json()['saved'] is True

print("\n--- 3. Testing Favourites View ---")
resp_fav_page = session.get(f"{BASE_URL}/favourites")
print("Favourites Page Status:", resp_fav_page.status_code)
assert "cargo pants" in resp_fav_page.text.lower()
print("Saved item 'cargo pants' confirmed on Favourites page!")

print("\n--- 4. Testing CSV Export ---")
resp_csv = session.get(f"{BASE_URL}/api/export-csv?category=both&geo=IN&sample=1")
print("CSV Export Status:", resp_csv.status_code, f"Length: {len(resp_csv.text)} bytes")
assert "Cargo Pants" in resp_csv.text
print("CSV generation confirmed!")

print("\n=== ALL END-TO-END INTEGRATION TESTS PASSED ===")
