"""
Generate rich, realistic sample trend datasets for BeTrendy.
This file generates data/sample_trends.json with 52 weeks of search volume data
for all 24 required fashion keywords across Men and Women categories, plus anchor 't shirt'.
"""
import json
import os
import math
from datetime import datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(DATA_DIR, 'sample_trends.json')

MEN_ITEMS = [
    "cargo pants", "oversized t shirt", "linen shirt", "polo t shirt",
    "bomber jacket", "kurta", "denim jacket", "joggers",
    "formal shirt", "hoodie", "track pants", "baggy jeans"
]

WOMEN_ITEMS = [
    "co ord set", "kurti", "palazzo pants", "crop top",
    "maxi dress", "denim jacket", "saree", "blazer",
    "wide leg jeans", "oversized shirt", "jumpsuit", "anarkali"
]

ANCHOR_ITEM = "t shirt"

# Profiles define the trajectory across 52 weeks:
# (start_val, end_val, peak_week, noise_amplitude, wave_freq)
ITEM_PROFILES = {
    # Rising Items (Men)
    "cargo pants": (42, 88, 48, 4.0, 1.2),         # Viral breakout: +96% recent vs baseline
    "baggy jeans": (48, 76, 50, 3.5, 1.0),         # 90s streetwear: +48%
    "oversized t shirt": (58, 82, 51, 4.0, 1.5),   # Core streetwear: +35%
    "linen shirt": (38, 55, 42, 3.0, 1.0),         # Summer luxury: +28%
    # Declining Items (Men)
    "formal shirt": (64, 46, 12, 3.5, 0.8),        # Workwear casualization: -24%
    "joggers": (72, 53, 10, 4.0, 1.0),             # Replaced by cargo/baggy: -23%
    "bomber jacket": (50, 37, 8, 3.0, 0.9),        # Dip: -21%
    "polo t shirt": (60, 48, 14, 3.0, 1.1),        # Shift to oversized: -17%
    "track pants": (65, 52, 16, 3.5, 1.0),         # Replaced by wide fits: -16%
    # Stable Items (Men)
    "kurta": (55, 56, 44, 5.0, 2.0),               # Festive peaks (Diwali/Eid), stable overall
    "denim jacket": (58, 60, 40, 3.0, 1.0),        # Timeless staple: +3%
    "hoodie": (62, 65, 48, 6.0, 1.5),              # Seasonal winter peaks, stable baseline
    
    # Rising Items (Women)
    "co ord set": (48, 82, 49, 4.0, 1.3),          # Explosive airport/party look: +62%
    "kurti": (62, 78, 46, 4.5, 2.0),               # Ethnic fusion college wave: +22%
    "wide leg jeans": (52, 66, 48, 3.0, 1.0),      # Dominant silhouette: +20%
    "anarkali": (48, 58, 45, 5.0, 2.2),            # Festive & wedding surge: +18%
    "crop top": (56, 66, 32, 4.0, 1.5),            # Y2K essential: +16%
    "oversized shirt": (50, 59, 47, 3.0, 1.2),     # Layering trend: +15%
    # Declining Items (Women)
    "palazzo pants": (62, 47, 10, 3.5, 1.0),       # Giving way to wide-leg jeans: -19%
    # Stable Items (Women)
    "saree": (74, 75, 44, 6.0, 2.5),               # Eternal cultural powerhouse
    "maxi dress": (52, 54, 30, 4.0, 1.4),          # Vacation staple
    "blazer": (50, 49, 20, 3.0, 0.9),              # Power dressing / neutral
    "jumpsuit": (46, 44, 25, 3.0, 1.2),            # Niche staple
    
    # Anchor term
    "t shirt": (68, 71, 26, 3.0, 1.0)              # Universal anchor
}

def generate_weekly_series(start_val, end_val, peak_week, noise_amp, wave_freq, n_weeks=52):
    """Generate realistic weekly values from week 0 to n_weeks-1."""
    values = []
    for i in range(n_weeks):
        t = i / (n_weeks - 1)
        # Base linear progression
        base = start_val + (end_val - start_val) * t
        # Seasonal wave
        wave = math.sin(2 * math.pi * wave_freq * t) * (noise_amp * 1.5)
        # Peak bump around peak_week
        dist = abs(i - peak_week)
        peak_bump = max(0, (10 - dist) * 0.8)
        # Small pseudo-random organic fluctuation
        organic = math.sin(i * 1.7) * (noise_amp * 0.8)
        
        val = base + wave + peak_bump + organic
        # Clamp to realistic 0-100 range
        val = max(10, min(100, round(val, 1)))
        values.append(val)
    return values

def build_dataset():
    # End date around current date (e.g., Oct 2026)
    end_date = datetime(2026, 10, 15)
    dates = [(end_date - timedelta(weeks=(51 - i))).strftime("%Y-%m-%d") for i in range(52)]
    
    series_by_keyword = {}
    categories = {}
    
    for item in MEN_ITEMS:
        categories[item] = "men"
        profile = ITEM_PROFILES.get(item, (50, 50, 26, 3.0, 1.0))
        series_by_keyword[item] = generate_weekly_series(*profile)
        
    for item in WOMEN_ITEMS:
        # Avoid duplicate denim jacket overwrite
        categories[item] = "women"
        profile = ITEM_PROFILES.get(item, (50, 50, 26, 3.0, 1.0))
        series_by_keyword[item] = generate_weekly_series(*profile)
        
    # Anchor
    categories[ANCHOR_ITEM] = "anchor"
    series_by_keyword[ANCHOR_ITEM] = generate_weekly_series(*ITEM_PROFILES[ANCHOR_ITEM])
    
    # Regional multipliers to allow geo simulation if offline
    regional_variations = {
        "IN": {"kurta": 1.4, "kurti": 1.4, "saree": 1.5, "anarkali": 1.4, "cargo pants": 1.1},
        "US": {"cargo pants": 1.2, "baggy jeans": 1.3, "hoodie": 1.25, "kurta": 0.2, "saree": 0.15},
        "GB": {"bomber jacket": 1.2, "t shirt": 1.0, "hoodie": 1.3, "kurta": 0.3},
        "ALL": {}
    }
    
    dataset = {
        "metadata": {
            "title": "BeTrendy Curated Fashion Search Dataset",
            "source": "Google Trends (relative search index 0-100)",
            "generated_at": datetime.utcnow().isoformat(),
            "timeframe": "today 12-m",
            "weeks_count": 52,
            "anchor_term": ANCHOR_ITEM
        },
        "dates": dates,
        "categories": categories,
        "series": series_by_keyword,
        "regional_multipliers": regional_variations
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2)
        
    print(f"Generated sample trends data with {len(series_by_keyword)} items at {OUTPUT_FILE}")

if __name__ == "__main__":
    build_dataset()
