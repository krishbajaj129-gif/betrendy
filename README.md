# 🔥 BeTrendy - Modern Fashion Trend Analyzer & Predictor

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask%203.x-red.svg)](https://flask.palletsprojects.com/)
[![scikit-learn](https://img.shields.io/badge/ML-scikit--learn-orange.svg)](https://scikit-learn.org/)
[![Status](https://img.shields.io/badge/Status-Complete%20%26%20Tested-brightgreen.svg)]()

> **College Project Edition**  
> A bold, colorful, Gen Z streetwear-inspired fashion trend analysis and forecasting platform. Tracks search interest velocity across Google Trends, normalizes multi-batch queries with anchor baseline terms, predicts upcoming 8-week fashion adoption using scikit-learn Linear Regression, and lets users curate their personal watchlists.

---

## ⚡ Quick Start (Run in 3 Steps)

### Step 1: Install Dependencies
Open your terminal inside the project directory:
```bash
pip install -r requirements.txt
```

### Step 2: Run the Application Server
```bash
python app.py
```
*(Or double-click `run_server.bat` on Windows)*

### Step 3: Open in Browser
Visit:
```
http://127.0.0.1:5000
```

To run the automated test suite:
```bash
python -m unittest test_app.py -v
```

---

## 🚀 Key Features

1. **Live Google Trends & Multi-Batch Anchor Rescaling**:
   - Google Trends limits queries to 5 keywords per request.
   - `trend_logic.py` batches keywords into groups of 4 and adds the universal anchor keyword **`"t shirt"`** to every batch.
   - Calculates the relative scaling ratio against the reference anchor mean to normalize all batches onto a single unified **0 to 100** relative search interest scale.
   - Built-in 1-hour in-memory cache and exponential backoff retry for HTTP 429 rate limits.
   - Automatic graceful fallback to `data/sample_trends.json` with a clear notice banner.
   - "Sample data" toggle switch directly in the navbar.

2. **Trend Velocity Rule (Rising / Stable / Declining)**:
   - Mathematically compares the **Recent Window** (last 25% of points, min 4 weeks) against the identical **Baseline Window** preceding it.
   - $\text{Growth Rate (\%)} = \frac{\mu_{recent} - \mu_{baseline}}{\max(\mu_{baseline}, 1.0)} \times 100\%$
   - $\ge +15\%$ &rarr; **Rising** (High adoption momentum)
   - $\le -15\%$ &rarr; **Declining** (Fading trend)
   - Otherwise &rarr; **Stable** (Classic wardrobe staple)

3. **Explainable 8-Week Predictive Forecasting (`forecast.py`)**:
   - Trained on the recent 26 weeks using **scikit-learn Ordinary Least Squares Linear Regression** ($y = mx + c$).
   - Generates 8 weekly forward predictions, clamped to $[0, 100]$.
   - Visualized on Chart.js as a **dashed line** continuing seamlessly from the solid historical line.
   - Plain-language trajectory label: **"Expected to rise"**, **"Expected to hold"**, or **"Expected to fall"**.
   - Mandatory plain-language note: *"Scores are relative (0 to 100), not search counts. Predictions are estimates based on past interest, not guarantees."*

4. **Signature Gen Z Streetwear Design ("Hang Tags")**:
   - Top 3 rising items rendered as physical apparel hang tags with:
     - 45-degree angled clipped corners.
     - Punched metallic hole at top center.
     - Dashed stitched border.
     - Big bold growth percentage badge (e.g. `+96%`).
     - Real-time 2D canvas sparkline.
     - One-click heart save button.
   - Vibrant color palette: Hot Pink (`#FF2E93`), Electric Orange (`#FF6B00`), Electric Purple (`#7928CA`), Neon Lime (`#10B981`).
   - High contrast readability with clean dark base text on crisp white card surfaces.
   - Respects `prefers-reduced-motion` and includes visible keyboard focus outlines.

5. **Authentication, Database & Security**:
   - SQLite relational database with Flask-SQLAlchemy (`betrendy.db`).
   - User registration and login managed via Flask-Login.
   - Passwords securely hashed with Werkzeug's modern scrypt/pbkdf2 salts; never stored in plaintext.
   - CSRF protection across all forms and AJAX endpoints with `X-CSRFToken` verification.
   - Logged-out users can browse all trends, but are prompted to authenticate when saving items.

---

## 📁 Project Structure

```
betrendy/
├── app.py                     # Main Flask application and JSON API routes
├── models.py                  # SQLAlchemy models (User, Favourite) & password hashing
├── trend_logic.py             # Google Trends fetching, anchor rescaling, caching & analysis
├── forecast.py                # Scikit-learn Linear Regression 8-week forecasting
├── requirements.txt           # Python package requirements
├── test_app.py                # Unit test suite (9 test cases)
├── check_live_server.py       # Live server health check script
├── create_sample_data.py      # Generator script for curated fallback dataset
├── create_images.py           # Generator script for local fashion visual assets
├── README.md                  # Project documentation & teacher evaluator guide
├── data/
│   └── sample_trends.json     # Curated 52-week time series for 24 keywords + anchor
├── static/
│   ├── css/
│   │   └── style.css          # Custom bold streetwear CSS (no heavy frameworks)
│   ├── js/
│   │   └── app.js             # Vanilla JS, Chart.js integrations & AJAX favourites
│   └── images/                # Local fashion images for all 24 clothing items
└── templates/
    ├── base.html              # Layout skeleton, navbar, sample toggle, flash container
    ├── index.html             # Dashboard (Hero, Hang Tags, Filters, Movers, Forecast, Table)
    ├── about.html             # About page (Features, Metrics, Project info, FAQ, Contact)
    ├── login.html             # User login form with CSRF protection
    ├── register.html          # User registration form with security notice
    └── favourites.html        # Saved favourites watchlist with mini sparklines
```

---

## 🎓 Technical Architecture & Teacher Evaluation Guide

This section contains the comprehensive technical breakdown for faculty evaluators, detailing the system architecture, mathematical formulations, machine learning methodologies, and security implementations.

### 1. System Architecture & End-to-End Data Pipeline

BeTrendy follows a clean, decoupled MVC architecture with Python Flask on the backend and lightweight vanilla JavaScript and Chart.js on the client layer:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        1. Client Layer (Browser)                       │
│  - Vanilla JavaScript & Chart.js rendering (zero hydration delay)      │
│  - Asynchronous AJAX requests (/api/trends, /api/forecast, /api/favs)  │
│  - Cryptographic CSRF token transmission via X-CSRFToken header        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP AJAX (JSON)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   2. Flask Application Server (app.py)                 │
│  - Session management & authentication (Flask-Login)                   │
│  - CSRF protection middleware & route authorization                   │
│  - Jinja2 template rendering for server-delivered views                │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
                    ▼                                ▼
┌──────────────────────────────────┐ ┌──────────────────────────────────┐
│  Trend Pipeline (trend_logic.py) │ │     ML Engine (forecast.py)      │
│  - Pytrends extraction           │ │  - Scikit-learn OLS Regression   │
│  - Multi-batch anchor rescaling  │ │  - 26-week training window       │
│  - 1-hour in-memory cache        │ │  - 8-week forward projection     │
│  - Automatic sample data fallback│ │  - Directional trajectory labels │
└───────────────────┬──────────────┘ └──────────────────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   3. Relational Persistence (models.py)                │
│  - SQLite database (betrendy.db) managed via Flask-SQLAlchemy          │
│  - User entities with salted scrypt/pbkdf2 password hashing            │
│  - Relational Favourites table with unique constraints & foreign keys  │
└────────────────────────────────────────────────────────────────────────┘
```

---

### 2. Google Trends Ingestion & Multi-Batch Anchor Rescaling

Google Trends provides consumer search interest scores on a relative scale of **0 to 100**, where 100 indicates peak popularity for the requested query group and region, not raw search counts.

#### The Multi-Batch Normalization Problem
Google Trends limits any single query to at most **5 keywords**. If Batch A contains `["cargo pants", "hoodie"]` and Batch B contains `["kurta", "denim jacket"]`, Google independently normalizes each batch so that each has its own internal 100 peak. Therefore, an interest score of 80 in Batch A cannot be compared directly to 80 in Batch B.

#### Mathematical Anchor Term Rescaling
In `trend_logic.py`, BeTrendy reserves the 5th keyword slot in every batch for the universal anchor keyword: **`"t shirt"`**.

1. **Reference Anchor Mean ($A_{ref}$)**: Computed from the first batch as the benchmark baseline.
2. **Batch $k$ Anchor Mean ($A_k$)**: Computed from the anchor time series in batch $k$.
3. **Rescaling Ratio ($S_k$)**:
   $$S_k = \frac{A_{ref}}{\max(A_k, 0.001)}$$
4. **Rescaled Item Series**:
   $$\text{Series}_{k, \text{item}}(t) = \text{Raw}_{k, \text{item}}(t) \times S_k$$
5. **Global Normalization (0–100 Scale)**:
   $$\text{Normalized}(t) = \frac{\text{Value}(t)}{\text{Global Max Across All Items}} \times 100$$

#### Rate Limit Resilience & Offline Fallback
Google Trends frequently issues HTTP 429 rate limits. `trend_logic.py` implements:
- Exponential backoff retry logic.
- 1-hour in-memory caching (`_MEMORY_CACHE`).
- Automatic, graceful fallback to `data/sample_trends.json` with a prominent UI notice: *"Showing sample data"*.
- Instant client toggle in the navbar to switch between live queries and sample data.

---

### 3. Mathematical Velocity Rule & Trend Classification

To prevent short-term fluctuations from distorting trend momentum, `analyze_trends()` compares a **Recent Window** against an identical **Baseline Window** directly preceding it:

$$N = \text{Total weekly data points (e.g., 52 weeks)}$$
$$W = \max(4, \text{round}(N \times 0.25)) \quad (\text{e.g., 13 weeks})$$

$$\text{Recent Window: } R = [y_{N-W}, \dots, y_{N-1}], \quad \mu_{recent} = \frac{1}{W} \sum R$$
$$\text{Baseline Window: } B = [y_{N-2W}, \dots, y_{N-W-1}], \quad \mu_{baseline} = \frac{1}{W} \sum B$$

$$\text{Growth Rate (\%)} = \frac{\mu_{recent} - \mu_{baseline}}{\max(\mu_{baseline}, 1.0)} \times 100\%$$

#### Classification Thresholds
- **Rising**: $\text{Growth Rate} \ge +15.0\%$ *(Accelerating consumer interest and adoption)*
- **Declining**: $\text{Growth Rate} \le -15.0\%$ *(Significant loss of momentum / fading trend)*
- **Stable**: $-15.0\% < \text{Growth Rate} < +15.0\%$ *(Evergreen wardrobe staple)*

---

### 4. Machine Learning Predictive Forecasting Engine (`forecast.py`)

We utilize **scikit-learn Linear Regression (Ordinary Least Squares)** trained on the recent 26 weeks of historical consumer interest. Linear regression was chosen over complex black-box neural networks because it is **fully explainable, deterministic, and mathematically transparent** for academic defense and evaluation.

#### Mathematical Model
$$y = m \cdot x + c$$

Where:
- $x = [0, 1, \dots, 25]$ (Time step in weeks).
- $y \in [0, 100]$ (Historical search interest).
- $m$ = Slope (Velocity of interest change per week).
- $c$ = Intercept.

#### 8-Week Forward Horizon Projection
For future weeks $x_f \in [26, 27, \dots, 33]$ (Next 8 Weeks):
$$y_{\text{pred}}(x_f) = \text{clamp}(m \cdot x_f + c, 0, 100)$$

#### Trajectory Decision Boundary
Let $\Delta$ be the percentage change between the projected 8th week and the most recent actual week:
$$\Delta = \frac{y_{\text{pred}}[8] - y_{\text{actual}}[\text{last}]}{\max(y_{\text{actual}}[\text{last}], 1.0)} \times 100\%$$

- **"Expected to rise"**: If $m > 0.25$ AND $\Delta \ge +5.0\%$
- **"Expected to fall"**: If $m < -0.25$ AND $\Delta \le -5.0\%$
- **"Expected to hold"**: Otherwise (slope is near flat or delta is within $\pm 5\%$)

*Mandatory Plain-Language Note*: Every prediction card and chart includes: *"Scores are relative (0 to 100), not search counts. Predictions are estimates based on past interest, not guarantees."*

---

### 5. SQLite Relational Schema & Security Architecture

The application uses an SQLite relational database managed through Flask-SQLAlchemy with modern security safeguards.

#### Table: `users`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | Primary Key, Auto-increment | Unique user identifier |
| `username` | `VARCHAR(80)` | Unique, Not Null | Chosen handle / login name |
| `password_hash` | `VARCHAR(255)` | Not Null | Cryptographic salted password hash |
| `created_at` | `DATETIME` | UTC timestamp | Account creation date |

#### Table: `favourites`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | Primary Key, Auto-increment | Favourite record ID |
| `user_id` | `INTEGER` | Foreign Key (`users.id`) | Owner user reference |
| `item_name` | `VARCHAR(100)` | Not Null | Clothing item name |
| `category` | `VARCHAR(50)` | Default `'general'` | Category slug (`men` / `women`) |
| `created_at` | `DATETIME` | UTC timestamp | Bookmark timestamp |
| *Constraint* | `UniqueConstraint(user_id, item_name)` | Prevents duplicate saves per user |

#### Security Implementation Highlights
1. **Password Hashing**: Passwords are never stored in plain text. Passwords are salted and hashed using Werkzeug's modern `generate_password_hash()` (scrypt/pbkdf2:sha256).
2. **CSRF Protection**: All state-modifying requests (POST/PUT/DELETE) validate a cryptographic session-bound token passed via form inputs or the `X-CSRFToken` request header.
3. **Session Security**: Handled by Flask-Login with signed, HttpOnly session cookies to mitigate session hijacking and XSS leakage.
4. **Legacy Link Resilience**: Permanent 301 redirection routes legacy `/how-it-works` traffic to `/about` without breaking bookmarks or evaluator URLs.

---

### 6. Academic Evaluation Code Map & Rubric

Quick reference table for grading and code verification:

| Academic Requirement | File Location | Key Functions / Classes |
| :--- | :--- | :--- |
| **Pytrends batching & anchor rescaling** | `trend_logic.py` | `_fetch_from_pytrends()`, `ANCHOR_KEYWORD = "t shirt"` |
| **1-hour caching & fallback resilience** | `trend_logic.py` | `fetch_trends()`, `_MEMORY_CACHE`, `data/sample_trends.json` |
| **Trend velocity classification rule** | `trend_logic.py` | `analyze_trends()` ($\ge +15\%$ Rising, $\le -15\%$ Declining) |
| **Scikit-learn 8-week Linear Regression** | `forecast.py` | `forecast_item()`, `LinearRegression().fit()` |
| **Directional trajectory labels** | `forecast.py` | `forecast_item()` (slope & delta decision logic) |
| **User authentication & password hashing** | `models.py`, `app.py` | `User.set_password()`, `User.check_password()`, `register()` |
| **Relational SQLite ORM & Favourites** | `models.py`, `app.py` | `Favourite` model, `/api/favourites/toggle` |
| **RESTful JSON API Endpoints** | `app.py` | `/api/trends`, `/api/forecast`, `/api/export-csv` |
| **CSRF Defense Middleware** | `app.py` | `csrf_protect()`, `get_csrf_token()` |
| **Signature Hang Tags & Chart.js** | `static/js/app.js` | `renderHangTags()`, `renderMoversChart()`, `renderForecastChart()` |
| **Comprehensive Unit Test Suite** | `test_app.py` | `BeTrendyTestCase` (9 automated tests) |

---

## 🖼️ Image Handling & Where to Put Custom Images

Every clothing item displays a clean visual card on its hang tag and table row:
- Local images are saved in `static/images/` and named by lowercasing the item name and replacing spaces with hyphens (e.g. `cargo-pants.jpg`, `baggy-jeans.jpg`, `co-ord-set.jpg`).
- **Missing Image Fallback**: If an image file is missing or fails to load, an automatic `onerror` handler displays a vibrant gradient tile showing the item's initial and name. The page never shows broken image icons!
- **Adding Your Own Photos**:
  To replace or add an image for any clothing item:
  1. Save your JPEG/PNG image inside `static/images/`.
  2. Name it using the item's slug format: `<item-name>.jpg` (for example, `bucket-hat.jpg` or `linen-shirt.jpg`).
  3. Reload the page — BeTrendy will automatically display your custom image.

---

## 📊 Core Curated Keywords Tracked

- **Men**: `cargo pants`, `oversized t shirt`, `linen shirt`, `polo t shirt`, `bomber jacket`, `kurta`, `denim jacket`, `joggers`, `formal shirt`, `hoodie`, `track pants`, `baggy jeans`.
- **Women**: `co ord set`, `kurti`, `palazzo pants`, `crop top`, `maxi dress`, `denim jacket`, `saree`, `blazer`, `wide leg jeans`, `oversized shirt`, `jumpsuit`, `anarkali`.
- **Anchor Term**: `t shirt` (used across all batches for mathematical rescaling).
- **Custom Keywords**: Users can dynamically enter any fashion keyword (e.g. *"corset top"*, *"leather jacket"*) via the `+ Add item` control.

---

## 🧪 Automated Testing

Run the test suite to verify all logic components:
```bash
python -m unittest test_app.py -v
```

Tests included:
1. `test_trend_classification_rules`: Verifies $+15\%$ Rising, $-15\%$ Declining, and Stable classification thresholds.
2. `test_sample_trends_loading`: Checks that sample dataset loads 24 fashion items and anchor correctly.
3. `test_forecast_values_and_labels`: Verifies 8-step scikit-learn forecasting, [0, 100] clamping, and trajectory labels.
4. `test_password_hashing_security`: Validates Werkzeug scrypt hashing and prevents plaintext leakage.
5. `test_favourites_model_uniqueness`: Tests SQLite foreign key relationships and unique user-item constraints.
6. `test_public_pages_status_codes`: Verifies HTTP 200 on public views (`/`, `/about`, `/login`) and 301 redirect on `/how-it-works`.
7. `test_api_trends_json_response`: Checks `/api/trends` JSON contract.
8. `test_api_forecast_json_response`: Checks `/api/forecast` JSON contract.
9. `test_unauthorized_favourite_toggle`: Verifies anonymous 401 unauthorized security check.

---

&copy; 2026 BeTrendy Team. Built for College Academic Evaluation.
