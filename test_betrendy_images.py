import urllib.request

BASE_URL = "http://127.0.0.1:5000/static/images"

items = [
    "cargo-pants.jpg",
    "oversized-t-shirt.jpg",
    "linen-shirt.jpg",
    "polo-t-shirt.jpg",
    "bomber-jacket.jpg",
    "kurta.jpg",
    "denim-jacket.jpg",
    "joggers.jpg",
    "formal-shirt.jpg",
    "hoodie.jpg",
    "track-pants.jpg",
    "baggy-jeans.jpg",
    "co-ord-set.jpg",
    "kurti.jpg",
    "palazzo-pants.jpg",
    "crop-top.jpg",
    "maxi-dress.jpg",
    "saree.jpg",
    "blazer.jpg",
    "wide-leg-jeans.jpg",
    "oversized-shirt.jpg",
    "jumpsuit.jpg",
    "anarkali.jpg",
    "t-shirt.jpg"
]

print("=== CHECKING ALL 24 IMAGES ON BETRENDY SERVER ===")
all_pass = True
for filename in items:
    url = f"{BASE_URL}/{filename}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            content_length = resp.headers.get('Content-Length')
            content_type = resp.headers.get('Content-Type')
            print(f"[OK 200] {filename:25} | {content_type} | {content_length} bytes")
    except Exception as e:
        print(f"[FAIL] {filename:25} | {e}")
        all_pass = False

if all_pass:
    print("\nALL 24 REAL FASHION PRODUCT PHOTOS ARE LIVE ON BETRENDY!")
