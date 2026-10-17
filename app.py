"""
BeTrendy - Modern Fashion Trend Analyzer
Main Flask Application Server.

Features:
- Flask web routes with Jinja2 templates
- User authentication with Flask-Login and Werkzeug password hashing
- SQLite database with Flask-SQLAlchemy
- JSON API endpoints for real-time trends, scikit-learn forecasting, and user favourites
- CSRF protection across forms and AJAX requests
- Fallback system with sample dataset toggle
"""
import os
import io
import csv
import secrets
from typing import Dict, Any, List
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, session, Response
)
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)
from models import db, User, Favourite
from trend_logic import (
    fetch_trends, analyze_trends, get_default_keywords,
    get_item_category, MEN_KEYWORDS, WOMEN_KEYWORDS
)
from forecast import forecast_multiple_items, DISCLAIMER_NOTE

# Base paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'betrendy.db')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'betrendy-streetwear-college-secret-key-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH.replace(os.sep, '/')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to save and manage your favourite fashion trends.'
login_manager.login_message_category = 'info'


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login user loader callback."""
    return db.session.get(User, int(user_id))


# Create database tables automatically
with app.app_context():
    db.create_all()


# --- CSRF PROTECTION SYSTEM ---
def get_csrf_token() -> str:
    """Generate or retrieve per-session CSRF token."""
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(24)
    return session['_csrf_token']


@app.context_processor
def inject_globals():
    """Inject CSRF token and helper constants into all Jinja2 templates."""
    return {
        'csrf_token': get_csrf_token,
        'app_name': 'BeTrendy',
        'year': 2026
    }


@app.before_request
def csrf_protect():
    """Validate CSRF token on modifying HTTP requests (POST, PUT, DELETE)."""
    if request.method in ('POST', 'PUT', 'DELETE'):
        token = request.form.get('csrf_token') or request.headers.get('X-CSRFToken')
        session_token = session.get('_csrf_token')

        if not session_token or token != session_token:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'Invalid or expired CSRF security token.'}), 403
            flash('Security token invalid or expired. Please submit the form again.', 'danger')
            return redirect(request.referrer or url_for('index'))


# --- PAGE ROUTES ---
@app.route('/')
def index():
    """
    Main Trend Analyzer Dashboard.
    Renders filter bar, top 3 hang tags, charts, and all items table.
    """
    category = request.args.get('category', 'both')
    geo = request.args.get('geo', 'IN')
    timeframe = request.args.get('timeframe', 'today 12-m')
    force_sample = request.args.get('sample', '0') == '1'

    return render_template(
        'index.html',
        current_category=category,
        current_geo=geo,
        current_timeframe=timeframe,
        force_sample=force_sample
    )


@app.route('/favourites')
def favourites_page():
    """
    Saved Favourites View.
    Displays all saved items for the logged-in user with live trend metrics.
    """
    if not current_user.is_authenticated:
        return render_template('favourites.html', favourites=[])

    user_favs = current_user.favourites.all()
    fav_names = [f.item_name for f in user_favs]

    # Fetch trend metrics for favourite items
    trend_data = fetch_trends(
        keywords=fav_names if fav_names else None,
        force_sample=True  # Fast local render for user collection
    )
    analysis = analyze_trends(trend_data)
    
    # Map metrics back to favourites
    metrics_map = {item['name'].lower(): item for item in analysis['items']}
    
    enriched_favs = []
    for f in user_favs:
        m = metrics_map.get(f.item_name.lower(), {})
        enriched_favs.append({
            'id': f.id,
            'item_name': f.item_name,
            'category': f.category,
            'created_at': f.created_at,
            'current_score': m.get('current_score', 50),
            'growth_rate': m.get('growth_rate', 0.0),
            'status': m.get('status', 'Stable'),
            'sparkline': m.get('sparkline', [50] * 12)
        })

    return render_template('favourites.html', favourites=enriched_favs)


@app.route('/about')
def about():
    """About page introducing BeTrendy, features, metrics, project details, FAQ, and contact."""
    return render_template('about.html')


@app.route('/how-it-works')
def how_it_works():
    """Permanent 301 redirect to /about so legacy links do not break."""
    return redirect(url_for('about'), code=301)



# --- AUTHENTICATION ROUTES ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route with secure password hashing."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm = request.form.get('confirm_password', '').strip()

        if len(username) < 3 or len(username) > 30:
            flash('Username must be between 3 and 30 characters.', 'warning')
            return render_template('register.html', username=username)

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'warning')
            return render_template('register.html', username=username)

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html', username=username)

        existing = User.query.filter(db.func.lower(User.username) == username.lower()).first()
        if existing:
            flash('Username already registered. Please choose another or log in.', 'warning')
            return render_template('register.html', username=username)

        # Create new user with hashed password
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        flash(f'Welcome to BeTrendy, @{username}! Your account has been created.', 'success')
        return redirect(url_for('index'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login route verifying hashed credentials."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        remember = request.form.get('remember') == 'on'

        user = User.query.filter(db.func.lower(User.username) == username.lower()).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f'Welcome back, @{user.username}!', 'success')
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')
            return render_template('login.html', username=username)

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """Log out current user."""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))


# --- JSON API ROUTES ---
@app.route('/api/trends', methods=['GET'])
def api_trends():
    """
    JSON API for fashion trends analysis.
    Query parameters:
    - category: 'both' | 'men' | 'women'
    - geo: 'IN' | 'US' | 'GB' | 'ALL'
    - timeframe: 'today 3-m' | 'today 12-m' | 'today 5-y'
    - sample: '1' to force local dataset
    """
    category = request.args.get('category', 'both')
    geo = request.args.get('geo', 'IN')
    timeframe = request.args.get('timeframe', 'today 12-m')
    force_sample = request.args.get('sample', '0') == '1'

    # Get keywords for selected category
    keywords = get_default_keywords(category)

    # Include any custom keywords added in this user's session
    custom_items = session.get('custom_items', [])
    for c in custom_items:
        if c not in keywords:
            keywords.append(c)

    trend_data = fetch_trends(keywords=keywords, timeframe=timeframe, geo=geo, force_sample=force_sample)
    analysis = analyze_trends(trend_data)

    # Annotate items with user's saved status if logged in
    user_fav_names = set()
    if current_user.is_authenticated:
        user_fav_names = {f.item_name.lower() for f in current_user.favourites.all()}

    for item in analysis['items']:
        item['is_favourite'] = item['name'].lower() in user_fav_names

    return jsonify(analysis)


@app.route('/api/forecast', methods=['GET'])
def api_forecast():
    """
    JSON API for scikit-learn 8-week fashion trend forecasting.
    Query parameters:
    - items: comma-separated list of items (e.g. 'cargo pants,baggy jeans')
    - geo: region code
    - timeframe: timeframe string
    - sample: '1' or '0'
    """
    items_raw = request.args.get('items', 'cargo pants,baggy jeans,co ord set')
    requested_items = [i.strip() for i in items_raw.split(',') if i.strip()][:5]
    
    geo = request.args.get('geo', 'IN')
    timeframe = request.args.get('timeframe', 'today 12-m')
    force_sample = request.args.get('sample', '0') == '1'

    trend_data = fetch_trends(keywords=requested_items, timeframe=timeframe, geo=geo, force_sample=force_sample)
    dates = trend_data.get('dates', [])
    series = trend_data.get('series', {})

    # Generate 8-week predictive forecasts using Linear Regression
    forecast_results = forecast_multiple_items(series, dates, forecast_steps=8)
    forecast_results['historical_series'] = series
    forecast_results['is_sample'] = trend_data.get('is_sample', False)
    forecast_results['sample_notice'] = trend_data.get('sample_notice', '')

    return jsonify(forecast_results)


@app.route('/api/favourites', methods=['GET'])
def api_favourites():
    """List saved items for authenticated user."""
    if not current_user.is_authenticated:
        return jsonify({'error': 'Authentication required', 'favourites': []}), 401

    favs = [f.to_dict() for f in current_user.favourites.all()]
    return jsonify({'favourites': favs, 'count': len(favs)})


@app.route('/api/favourites/toggle', methods=['POST'])
def api_toggle_favourite():
    """
    Toggle saving/removing an item from user favourites.
    Payload: { "item_name": "cargo pants", "category": "men" }
    """
    if not current_user.is_authenticated:
        return jsonify({
            'error': 'Please log in to save items to your favourites.',
            'requires_login': True,
            'login_url': url_for('login')
        }), 401

    data = request.get_json(silent=True) or {}
    item_name = data.get('item_name', '').strip()
    category = data.get('category') or get_item_category(item_name)

    if not item_name:
        return jsonify({'error': 'item_name is required'}), 400

    existing = Favourite.query.filter(
        Favourite.user_id == current_user.id,
        db.func.lower(Favourite.item_name) == item_name.lower()
    ).first()

    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({
            'saved': False,
            'item_name': item_name,
            'message': f"Removed '{item_name}' from favourites."
        })
    else:
        new_fav = Favourite(user_id=current_user.id, item_name=item_name, category=category)
        db.session.add(new_fav)
        db.session.commit()
        return jsonify({
            'saved': True,
            'item_name': item_name,
            'message': f"Saved '{item_name}' to favourites!"
        })


@app.route('/api/custom-item', methods=['POST'])
def api_add_custom_item():
    """
    Add a custom clothing keyword to track dynamically.
    Payload: { "keyword": "corset top" }
    """
    data = request.get_json(silent=True) or {}
    keyword = data.get('keyword', '').strip().lower()

    if not keyword or len(keyword) < 2 or len(keyword) > 40:
        return jsonify({'error': 'Keyword must be between 2 and 40 characters.'}), 400

    if 'custom_items' not in session:
        session['custom_items'] = []

    custom_items = session['custom_items']
    if keyword not in custom_items:
        custom_items.append(keyword)
        session['custom_items'] = custom_items
        session.modified = True

    return jsonify({
        'success': True,
        'keyword': keyword,
        'message': f"Added '{keyword}' to your trend dashboard."
    })


@app.route('/api/export-csv')
def export_csv():
    """Export current trends view as downloadable CSV."""
    category = request.args.get('category', 'both')
    geo = request.args.get('geo', 'IN')
    timeframe = request.args.get('timeframe', 'today 12-m')
    force_sample = request.args.get('sample', '0') == '1'

    keywords = get_default_keywords(category)
    trend_data = fetch_trends(keywords=keywords, timeframe=timeframe, geo=geo, force_sample=force_sample)
    analysis = analyze_trends(trend_data)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Item Name", "Category", "Current Search Interest (0-100)",
        "Baseline Score", "Recent Score", "Growth Rate (%)", "Status"
    ])

    for item in analysis['items']:
        writer.writerow([
            item['name'].title(),
            item['category'].title(),
            item['current_score'],
            item['baseline_score'],
            item['recent_score'],
            f"{item['growth_rate']}%",
            item['status']
        ])

    csv_data = output.getvalue()
    filename = f"betrendy_trends_{category}_{geo}.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1')
    print(f">> Starting BeTrendy server on port {port} (debug={debug})")
    app.run(debug=debug, host='0.0.0.0', port=port)
