import urllib.request
import json

routes = [
    '/',
    '/about',
    '/how-it-works',
    '/favourites',
    '/login',
    '/register',
    '/api/trends?sample=1',
    '/api/forecast?items=cargo%20pants,baggy%20jeans&sample=1'
]

print("=== CHECKING BE-TRENDY LIVE SERVER ===")
for r in routes:
    url = f"http://127.0.0.1:5000{r}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        code = resp.getcode()
        final_url = resp.geturl()
        content = resp.read()
        print(f"{r:60} => HTTP {code} ({len(content)} bytes) [URL: {final_url}]")
        if 'api' in r:
            parsed = json.loads(content)
            keys = list(parsed.keys())
            print(f"    JSON keys: {keys}")
print("=== ALL ROUTES RESPONDING HEALTHY ===")
