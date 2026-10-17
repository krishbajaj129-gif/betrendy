"""
Generate clean, vibrant fashion visual cards in static/images/ for all BeTrendy clothing items.
Uses Pillow to generate high-contrast, modern streetwear graphics for each clothing item.
"""
import os
from PIL import Image, ImageDraw, ImageFont

IMAGES_DIR = os.path.join(os.path.dirname(__file__), 'static', 'images')
os.makedirs(IMAGES_DIR, exist_ok=True)

ITEMS_THEMES = {
    # Item name: (slug, gradient_color_1, gradient_color_2, icon_symbol, accent_tag)
    "cargo pants": ("cargo-pants", (255, 46, 147), (255, 138, 0), "👖", "STREETWEAR"),
    "oversized t shirt": ("oversized-t-shirt", (139, 92, 246), (59, 130, 246), "👕", "OVERSIZED"),
    "linen shirt": ("linen-shirt", (16, 185, 129), (6, 182, 212), "👔", "SUMMER LINEN"),
    "polo t shirt": ("polo-t-shirt", (59, 130, 246), (99, 102, 241), "👕", "CLASSIC FIT"),
    "bomber jacket": ("bomber-jacket", (236, 72, 153), (244, 63, 94), "🧥", "OUTERWEAR"),
    "kurta": ("kurta", (245, 158, 11), (239, 68, 68), "✨", "ETHNIC CASUAL"),
    "denim jacket": ("denim-jacket", (37, 99, 235), (30, 58, 138), "🧥", "VINTAGE DENIM"),
    "joggers": ("joggers", (107, 114, 128), (55, 65, 81), "👖", "ATHLEISURE"),
    "formal shirt": ("formal-shirt", (79, 70, 229), (124, 58, 237), "👔", "SMART CASUAL"),
    "hoodie": ("hoodie", (168, 85, 247), (236, 72, 153), "🧥", "WINTER HEAVY"),
    "track pants": ("track-pants", (20, 184, 166), (15, 118, 110), "👖", "SPORTSWEAR"),
    "baggy jeans": ("baggy-jeans", (14, 165, 233), (2, 132, 199), "👖", "90S WIDE LEG"),
    
    # Women
    "co ord set": ("co-ord-set", (255, 46, 147), (168, 85, 247), "✨", "TRENDING MATCH"),
    "kurti": ("kurti", (249, 115, 22), (236, 72, 153), "👗", "FUSION ETHNIC"),
    "palazzo pants": ("palazzo-pants", (139, 92, 246), (217, 70, 239), "👖", "FLOWY WIDE"),
    "crop top": ("crop-top", (244, 63, 94), (251, 146, 60), "👚", "Y2K CHIC"),
    "maxi dress": ("maxi-dress", (16, 185, 129), (52, 211, 153), "👗", "SUMMER FLOW"),
    "saree": ("saree", (217, 70, 239), (244, 63, 94), "✨", "HERITAGE DRAPE"),
    "blazer": ("blazer", (51, 65, 85), (30, 41, 59), "🧥", "TAILORED CHIC"),
    "wide leg jeans": ("wide-leg-jeans", (2, 132, 199), (59, 130, 246), "👖", "RELAXED FIT"),
    "oversized shirt": ("oversized-shirt", (99, 102, 241), (168, 85, 247), "👔", "BOYFRIEND FIT"),
    "jumpsuit": ("jumpsuit", (245, 158, 11), (217, 119, 6), "👗", "ONE-PIECE"),
    "anarkali": ("anarkali", (236, 72, 153), (180, 83, 9), "✨", "ROYAL FLARE"),
    "t shirt": ("t-shirt", (100, 116, 139), (71, 85, 105), "👕", "CORE ESSENTIAL")
}

def create_item_image(slug, color1, color2, symbol, tag_text, title):
    width, height = 480, 360
    img = Image.new("RGB", (width, height), color=color1)
    draw = ImageDraw.Draw(img)

    # Draw vibrant diagonal gradient background
    for y in range(height):
        ratio = y / height
        r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
        g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
        b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Add geometric streetwear grid overlay / decorative shapes
    draw.rectangle([20, 20, width - 20, height - 20], outline=(255, 255, 255, 60), width=2)
    draw.line([30, 30, 60, 30], fill=(255, 255, 255), width=4)
    draw.line([30, 30, 30, 60], fill=(255, 255, 255), width=4)
    draw.line([width - 30, height - 30, width - 60, height - 30], fill=(255, 255, 255), width=4)
    draw.line([width - 30, height - 30, width - 30, height - 60], fill=(255, 255, 255), width=4)

    # Stylized center circle
    center_x, center_y = width // 2, height // 2 - 20
    draw.ellipse([center_x - 70, center_y - 70, center_x + 70, center_y + 70], fill=(0, 0, 0, 70), outline=(255, 255, 255), width=3)

    # Add tag pill
    pill_w = len(tag_text) * 11 + 24
    draw.rectangle([center_x - pill_w // 2, 45, center_x + pill_w // 2, 75], fill=(0, 0, 0), outline=(255, 255, 255), width=1)
    draw.text((center_x - (len(tag_text) * 4), 52), tag_text, fill=(255, 255, 255))

    # Center title and initial
    initials = "".join([w[0].upper() for w in title.split()[:2]])
    draw.text((center_x - 22, center_y - 20), initials, fill=(255, 255, 255))
    
    # Bottom banner with item title
    title_display = title.upper()
    draw.rectangle([40, height - 85, width - 40, height - 35], fill=(15, 17, 23))
    draw.text((60, height - 68), title_display, fill=(255, 255, 255))
    draw.text((width - 110, height - 68), "BETRENDY", fill=(255, 138, 0))

    # Save as JPG
    jpg_path = os.path.join(IMAGES_DIR, f"{slug}.jpg")
    img.save(jpg_path, "JPEG", quality=92)
    
    # Also save with underscore for safety (cargo_pants.jpg)
    alt_slug = slug.replace("-", "_")
    if alt_slug != slug:
        img.save(os.path.join(IMAGES_DIR, f"{alt_slug}.jpg"), "JPEG", quality=92)

def generate_all():
    for name, (slug, c1, c2, symbol, tag) in ITEMS_THEMES.items():
        create_item_image(slug, c1, c2, symbol, tag, name)
    print(f"Generated {len(ITEMS_THEMES)} fashion images in {IMAGES_DIR}")

if __name__ == "__main__":
    generate_all()
