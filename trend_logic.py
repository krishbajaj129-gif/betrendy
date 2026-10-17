"""
Trend Logic Module for BeTrendy.
Handles:
1. Google Trends data fetching via pytrends with multi-batch anchor normalization.
2. In-memory 1-hour caching and exponential backoff retry for rate limits.
3. Fallback to curated local dataset (data/sample_trends.json).
4. Trend analysis comparing Recent Window vs Baseline Window (+/- 15% threshold).
"""
import os
import json
import time
import logging
from typing import List, Dict, Tuple, Optional, Any
import numpy as np
import pandas as pd

# Setup logger for transparency
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BeTrendy.TrendLogic")

# Core curated fashion keywords required by BeTrendy
MEN_KEYWORDS = [
    "cargo pants", "oversized t shirt", "linen shirt", "polo t shirt",
    "bomber jacket", "kurta", "denim jacket", "joggers",
    "formal shirt", "hoodie", "track pants", "baggy jeans"
]

WOMEN_KEYWORDS = [
    "co ord set", "kurti", "palazzo pants", "crop top",
    "maxi dress", "denim jacket", "saree", "blazer",
    "wide leg jeans", "oversized shirt", "jumpsuit", "anarkali"
]

# Anchor term present in every batch to allow relative rescaling across queries
ANCHOR_KEYWORD = "t shirt"

# Cache TTL: 1 hour (3600 seconds)
CACHE_TTL = 3600
_MEMORY_CACHE: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

# Path to the sample data file
SAMPLE_DATA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'sample_trends.json')


def get_default_keywords(category: str = "both") -> List[str]:
    """
    Return unique list of fashion keywords based on category.
    Category can be 'men', 'women', or 'both'.
    """
    category = (category or "both").lower()
    if category == "men":
        return list(dict.fromkeys(MEN_KEYWORDS))
    elif category == "women":
        return list(dict.fromkeys(WOMEN_KEYWORDS))
    else:
        # Preserve order while eliminating duplicates (e.g. 'denim jacket')
        combined = MEN_KEYWORDS + [w for w in WOMEN_KEYWORDS if w not in MEN_KEYWORDS]
        return list(dict.fromkeys(combined))


def get_item_category(item_name: str) -> str:
    """Classify an item name as 'men', 'women', or 'unisex'."""
    item = item_name.strip().lower()
    in_men = item in [k.lower() for k in MEN_KEYWORDS]
    in_women = item in [k.lower() for k in WOMEN_KEYWORDS]
    if in_men and in_women:
        return "unisex"
    elif in_men:
        return "men"
    elif in_women:
        return "women"
    return "custom"


def load_sample_dataset() -> Dict[str, Any]:
    """Load the fallback curated sample dataset from disk."""
    if not os.path.exists(SAMPLE_DATA_PATH):
        raise FileNotFoundError(f"Sample data file not found at {SAMPLE_DATA_PATH}")
    with open(SAMPLE_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _fetch_from_pytrends(keywords: List[str], timeframe: str, geo: str) -> Optional[pd.DataFrame]:
    """
    Execute live batch fetching from Google Trends with pytrends.
    Batches keywords into groups of 4 + anchor keyword ("t shirt"),
    then rescales each batch against the anchor keyword to allow cross-batch comparison.
    """
    try:
        from pytrends.request import TrendReq
    except ImportError:
        logger.warning("pytrends is not installed.")
        return None

    # Google Trends allows max 5 keywords per request
    batch_size = 4
    batches = [keywords[i:i + batch_size] for i in range(0, len(keywords), batch_size)]
    
    # Format geo for pytrends ('ALL' means worldwide -> empty string)
    pytrends_geo = "" if geo.upper() in ["ALL", "WORLDWIDE", ""] else geo.upper()
    
    # Initialize TrendReq with timeout and retry configuration
    pytrends = TrendReq(hl='en-US', tz=330, timeout=(10, 25), retries=2, backoff_factor=0.5)

    all_batch_dfs = []
    
    for idx, batch in enumerate(batches):
        query_terms = list(dict.fromkeys(batch + [ANCHOR_KEYWORD]))
        success = False
        
        # Exponential backoff retry for Google Trends rate limit (HTTP 429)
        for attempt in range(3):
            try:
                logger.info(f"Pytrends querying batch {idx + 1}/{len(batches)} (attempt {attempt + 1}): {query_terms}")
                pytrends.build_payload(kw_list=query_terms, cat=0, timeframe=timeframe, geo=pytrends_geo, gprop='')
                df = pytrends.interest_over_time()
                if df is not None and not df.empty:
                    # Drop 'isPartial' column added by pytrends
                    if 'isPartial' in df.columns:
                        df = df.drop(columns=['isPartial'])
                    all_batch_dfs.append(df)
                    success = True
                    break
                else:
                    time.sleep(1.0)
            except Exception as ex:
                logger.warning(f"Batch {idx + 1} attempt {attempt + 1} failed: {ex}")
                time.sleep(1.5 * (attempt + 1))
        
        if not success:
            logger.error(f"Failed to fetch batch {idx + 1} after 3 attempts.")
            return None
            
        # Avoid hitting Google rate limits too quickly between batches
        time.sleep(1.0)

    if not all_batch_dfs:
        return None

    # --- ANCHOR RESCALING ALGORITHM ---
    # Batch 1 is used as our reference baseline.
    ref_df = all_batch_dfs[0]
    if ANCHOR_KEYWORD not in ref_df.columns:
        return None
        
    ref_anchor_mean = ref_df[ANCHOR_KEYWORD].mean()
    if ref_anchor_mean <= 0:
        ref_anchor_mean = 1.0

    unified_columns = {}
    dates_index = ref_df.index

    # Add items from reference batch
    for col in ref_df.columns:
        unified_columns[col] = ref_df[col].astype(float).values

    # Rescale subsequent batches
    for batch_df in all_batch_dfs[1:]:
        if ANCHOR_KEYWORD in batch_df.columns:
            batch_anchor_mean = batch_df[ANCHOR_KEYWORD].mean()
            # Scaling ratio to match reference batch anchor
            scale_ratio = ref_anchor_mean / max(batch_anchor_mean, 0.001)
        else:
            scale_ratio = 1.0

        for col in batch_df.columns:
            if col != ANCHOR_KEYWORD and col not in unified_columns:
                # Apply rescale multiplier
                unified_columns[col] = (batch_df[col].astype(float) * scale_ratio).values

    combined_df = pd.DataFrame(unified_columns, index=dates_index)

    # Normalize entire combined dataset to a 0-100 relative index
    global_max = combined_df.max().max()
    if global_max > 0:
        combined_df = (combined_df / global_max) * 100.0

    return combined_df.round(1)


def fetch_trends(
    keywords: Optional[List[str]] = None,
    timeframe: str = "today 12-m",
    geo: str = "IN",
    force_sample: bool = False
) -> Dict[str, Any]:
    """
    Fetch fashion search trends for given parameters.
    1. Checks in-memory 1-hour cache.
    2. If force_sample is False, tries live pytrends with anchor rescaling.
    3. If pytrends fails or is rate limited, falls back to sample_trends.json.
    
    Returns:
        dict containing:
        - dates: list of date strings (YYYY-MM-DD)
        - series: dict of keyword -> list of floats (0 to 100)
        - is_sample: boolean flag
        - sample_notice: explanation string if sample data was used
    """
    if keywords is None:
        keywords = get_default_keywords("both")
        
    cache_key = (",".join(sorted(keywords)), timeframe, geo.upper())
    now = time.time()

    # Check cache unless force_sample is explicitly requested
    if not force_sample and cache_key in _MEMORY_CACHE:
        cache_entry = _MEMORY_CACHE[cache_key]
        if now - cache_entry['timestamp'] < CACHE_TTL:
            logger.info("Serving trends data from 1-hour memory cache.")
            return cache_entry['data']

    # If force_sample is requested, directly return curated sample data
    if force_sample:
        logger.info("Force sample requested. Loading sample_trends.json.")
        sample_data = load_sample_dataset()
        result = _filter_sample_data(sample_data, keywords, geo)
        result['is_sample'] = True
        result['sample_notice'] = "Showing sample data (sample mode enabled)."
        return result

    # Try live Google Trends via pytrends
    live_df = _fetch_from_pytrends(keywords, timeframe, geo)
    if live_df is not None and not live_df.empty:
        dates = [d.strftime("%Y-%m-%d") for d in live_df.index]
        series = {}
        for kw in keywords:
            if kw in live_df.columns:
                series[kw] = [float(v) for v in live_df[kw].tolist()]
            elif kw.lower() in [c.lower() for c in live_df.columns]:
                matching_col = next(c for c in live_df.columns if c.lower() == kw.lower())
                series[kw] = [float(v) for v in live_df[matching_col].tolist()]
                
        result = {
            'dates': dates,
            'series': series,
            'is_sample': False,
            'sample_notice': ""
        }
        # Save to memory cache
        _MEMORY_CACHE[cache_key] = {'timestamp': now, 'data': result}
        return result

    # Fallback to sample data when live fetch fails
    logger.warning("Pytrends live fetch returned no data or hit rate limits. Falling back to sample data.")
    sample_data = load_sample_dataset()
    result = _filter_sample_data(sample_data, keywords, geo)
    result['is_sample'] = True
    result['sample_notice'] = "Showing sample data (Google Trends rate limited or offline)."
    return result


def _filter_sample_data(sample_data: Dict[str, Any], keywords: List[str], geo: str) -> Dict[str, Any]:
    """Filter and adjust sample trends by requested keywords and geo."""
    dates = sample_data.get("dates", [])
    raw_series = sample_data.get("series", {})
    multipliers = sample_data.get("regional_multipliers", {}).get(geo.upper(), {})
    
    filtered_series = {}
    for kw in keywords:
        kw_lower = kw.strip().lower()
        if kw_lower in raw_series:
            vals = raw_series[kw_lower]
        else:
            # For custom added items not in sample data, generate synthetic baseline
            # using hash-based seed for consistent and explainable visualization
            seed_val = abs(hash(kw_lower)) % 40 + 35
            vals = [max(10, min(100, round(seed_val + np.sin(i * 0.4) * 8 + (i * 0.2), 1))) for i in range(len(dates))]

        # Apply regional multiplier if available
        if kw_lower in multipliers:
            factor = multipliers[kw_lower]
            vals = [max(5, min(100, round(v * factor, 1))) for v in vals]
            
        filtered_series[kw] = vals

    return {
        'dates': dates,
        'series': filtered_series
    }


def analyze_trends(trend_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze search interest time series.
    Compares the Recent Window with the Baseline Window:
    - Recent window: last 25% of points (minimum 4 weeks).
    - Baseline window: preceding window of equal duration.
    - Growth % = ((Recent_Mean - Baseline_Mean) / max(Baseline_Mean, 1.0)) * 100
    - Status:
        - Growth >= +15%: 'Rising'
        - Growth <= -15%: 'Declining'
        - Otherwise: 'Stable'
        
    Returns:
        Structured dictionary containing analyzed items, top 3 rising,
        summary statistics, and dynamic hero headline.
    """
    dates = trend_data.get('dates', [])
    series = trend_data.get('series', {})
    is_sample = trend_data.get('is_sample', False)
    sample_notice = trend_data.get('sample_notice', '')

    n_points = len(dates)
    if n_points < 4:
        raise ValueError("Insufficient data points for trend analysis (requires >= 4).")

    # Define window sizes
    window_size = max(4, int(n_points * 0.25))
    recent_slice = slice(n_points - window_size, n_points)
    baseline_slice = slice(max(0, n_points - (2 * window_size)), n_points - window_size)

    analyzed_items = []

    for item_name, values in series.items():
        if not values or len(values) < 4:
            continue

        arr = np.array(values, dtype=float)
        recent_vals = arr[recent_slice]
        baseline_vals = arr[baseline_slice]

        recent_mean = float(np.mean(recent_vals))
        baseline_mean = float(np.mean(baseline_vals)) if len(baseline_vals) > 0 else 1.0
        
        # Calculate growth rate
        if baseline_mean > 0:
            growth_rate = ((recent_mean - baseline_mean) / baseline_mean) * 100.0
        else:
            growth_rate = 0.0

        growth_rate = round(growth_rate, 1)

        # Categorize trend status
        if growth_rate >= 15.0:
            status = "Rising"
        elif growth_rate <= -15.0:
            status = "Declining"
        else:
            status = "Stable"

        current_score = round(float(arr[-1]), 1)
        peak_score = round(float(np.max(arr)), 1)
        min_score = round(float(np.min(arr)), 1)
        sparkline = [round(float(v), 1) for v in arr[-12:].tolist()]

        analyzed_items.append({
            'name': item_name,
            'category': get_item_category(item_name),
            'current_score': current_score,
            'baseline_score': round(baseline_mean, 1),
            'recent_score': round(recent_mean, 1),
            'growth_rate': growth_rate,
            'status': status,
            'peak_score': peak_score,
            'min_score': min_score,
            'sparkline': sparkline,
            'full_series': [round(float(v), 1) for v in values]
        })

    # Sort items by growth rate descending (highest movers at the top)
    analyzed_items.sort(key=lambda x: x['growth_rate'], reverse=True)

    # Top 3 rising items (must be 'Rising' status if available)
    rising_candidates = [i for i in analyzed_items if i['status'] == 'Rising']
    if len(rising_candidates) >= 3:
        top_rising = rising_candidates[:3]
    else:
        top_rising = analyzed_items[:3]

    # Generate dynamic hero headline built from real data
    if top_rising:
        leader = top_rising[0]
        leader_name = leader['name'].title()
        leader_growth = abs(leader['growth_rate'])
        hero_headline = f"{leader_name} searches are up {int(leader_growth)}%!"
    else:
        hero_headline = "Streetwear Trends in Real Time"

    return {
        'items': analyzed_items,
        'dates': dates,
        'top_rising': top_rising,
        'hero_headline': hero_headline,
        'is_sample': is_sample,
        'sample_notice': sample_notice,
        'total_items': len(analyzed_items),
        'rising_count': sum(1 for i in analyzed_items if i['status'] == 'Rising'),
        'declining_count': sum(1 for i in analyzed_items if i['status'] == 'Declining'),
        'stable_count': sum(1 for i in analyzed_items if i['status'] == 'Stable')
    }
