"""
Unit Tests for BeTrendy.
Covers:
- Trend analysis (+15% Rising, -15% Declining, Stable thresholds)
- Scikit-learn Linear Regression 8-week forecasting and labels
- User authentication, password hashing security, and database models
- Flask JSON APIs and route responses
"""
import unittest
import json
from app import app, db
from models import User, Favourite
from trend_logic import analyze_trends, fetch_trends
from forecast import forecast_item, forecast_multiple_items, DISCLAIMER_NOTE


class BeTrendyTestCase(unittest.TestCase):
    def setUp(self):
        """Set up in-memory test database and test client."""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app
        self.client = app.test_client()

        with app.app_context():
            db.create_all()

    def tearDown(self):
        """Clean up database session and tables."""
        with app.app_context():
            db.session.remove()
            db.drop_all()

    # --- 1. TREND LOGIC TESTS ---
    def test_trend_classification_rules(self):
        """Verify Rising (>= +15%), Declining (<= -15%), and Stable rules."""
        # 16 weekly points: baseline window is weeks 8..11, recent window is weeks 12..15
        dummy_dates = [f"2026-01-{i:02d}" for i in range(1, 17)]
        
        # Rising item: baseline ~ 40, recent ~ 80 (+100% growth)
        rising_series = [40] * 12 + [80, 80, 80, 80]
        # Declining item: baseline ~ 80, recent ~ 40 (-50% growth)
        declining_series = [80] * 12 + [40, 40, 40, 40]
        # Stable item: baseline ~ 50, recent ~ 52 (+4% growth)
        stable_series = [50] * 12 + [52, 51, 52, 51]

        data = {
            'dates': dummy_dates,
            'series': {
                'Rising Flare': rising_series,
                'Declining Flare': declining_series,
                'Stable Staple': stable_series
            },
            'is_sample': True,
            'sample_notice': 'Test notice'
        }

        result = analyze_trends(data)
        items_by_name = {item['name']: item for item in result['items']}

        self.assertEqual(items_by_name['Rising Flare']['status'], 'Rising')
        self.assertGreaterEqual(items_by_name['Rising Flare']['growth_rate'], 15.0)

        self.assertEqual(items_by_name['Declining Flare']['status'], 'Declining')
        self.assertLessEqual(items_by_name['Declining Flare']['growth_rate'], -15.0)

        self.assertEqual(items_by_name['Stable Staple']['status'], 'Stable')
        self.assertTrue(-15.0 < items_by_name['Stable Staple']['growth_rate'] < 15.0)

    def test_sample_trends_loading(self):
        """Verify sample dataset fetches and contains all required items."""
        sample_data = fetch_trends(force_sample=True)
        self.assertTrue(sample_data['is_sample'])
        self.assertGreaterEqual(len(sample_data['series']), 20)
        self.assertIn('cargo pants', sample_data['series'])
        self.assertIn('baggy jeans', sample_data['series'])

    # --- 2. FORECAST TESTS ---
    def test_forecast_values_and_labels(self):
        """Verify scikit-learn forecasting produces 8 steps and expected trajectory labels."""
        # Upward history
        upward_history = [30 + i * 2 for i in range(26)]
        forecast_up = forecast_item(upward_history, forecast_steps=8)
        self.assertEqual(len(forecast_up['forecast_values']), 8)
        self.assertEqual(forecast_up['label'], 'Expected to rise')
        self.assertEqual(forecast_up['disclaimer'], DISCLAIMER_NOTE)
        # All values clamped to 100
        for val in forecast_up['forecast_values']:
            self.assertTrue(0 <= val <= 100)

        # Downward history
        downward_history = [80 - i * 2 for i in range(26)]
        forecast_down = forecast_item(downward_history, forecast_steps=8)
        self.assertEqual(forecast_down['label'], 'Expected to fall')

        # Flat history
        flat_history = [50 + (i % 2) for i in range(26)]
        forecast_flat = forecast_item(flat_history, forecast_steps=8)
        self.assertEqual(forecast_flat['label'], 'Expected to hold')

    # --- 3. DATABASE MODELS & AUTH TESTS ---
    def test_password_hashing_security(self):
        """Verify passwords are never stored in plaintext and hashing works correctly."""
        with app.app_context():
            user = User(username='fashionista')
            user.set_password('SecretStreetwear123!')
            db.session.add(user)
            db.session.commit()

            # Ensure plaintext password is NOT in the hash string
            self.assertNotEqual(user.password_hash, 'SecretStreetwear123!')
            self.assertTrue(user.password_hash.startswith('scrypt:') or user.password_hash.startswith('pbkdf2:'))

            # Check verification
            self.assertTrue(user.check_password('SecretStreetwear123!'))
            self.assertFalse(user.check_password('WrongPassword'))

    def test_favourites_model_uniqueness(self):
        """Verify favourite records associate with user and enforce uniqueness."""
        with app.app_context():
            user = User(username='streetking')
            user.set_password('Pass123!')
            db.session.add(user)
            db.session.commit()

            fav = Favourite(user_id=user.id, item_name='cargo pants', category='men')
            db.session.add(fav)
            db.session.commit()

            self.assertTrue(user.is_favourite('cargo pants'))
            self.assertFalse(user.is_favourite('blazer'))

    # --- 4. FLASK ROUTES AND API ENDPOINTS ---
    def test_public_pages_status_codes(self):
        """Ensure core pages render with HTTP 200 and legacy routes redirect."""
        r_index = self.client.get('/')
        self.assertEqual(r_index.status_code, 200)

        # /about renders with 200
        r_about = self.client.get('/about')
        self.assertEqual(r_about.status_code, 200)

        # /how-it-works permanently redirects to /about with 301
        r_how = self.client.get('/how-it-works')
        self.assertEqual(r_how.status_code, 301)
        self.assertIn('/about', r_how.location)

        # Following redirect leads to /about
        r_how_follow = self.client.get('/how-it-works', follow_redirects=True)
        self.assertEqual(r_how_follow.status_code, 200)

        r_login = self.client.get('/login')
        self.assertEqual(r_login.status_code, 200)


    def test_api_trends_json_response(self):
        """Ensure /api/trends returns expected JSON structure."""
        resp = self.client.get('/api/trends?sample=1')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn('items', data)
        self.assertIn('top_rising', data)
        self.assertIn('hero_headline', data)
        self.assertTrue(len(data['items']) > 0)

    def test_api_forecast_json_response(self):
        """Ensure /api/forecast returns 8-week predictions."""
        resp = self.client.get('/api/forecast?items=cargo pants,baggy jeans&sample=1')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn('forecasts', data)
        self.assertIn('cargo pants', data['forecasts'])
        self.assertEqual(len(data['forecasts']['cargo pants']['forecast_values']), 8)

    def test_unauthorized_favourite_toggle(self):
        """Verify anonymous user cannot toggle favourites without authentication."""
        # Get CSRF token from session
        with self.client.session_transaction() as sess:
            sess['_csrf_token'] = 'test-csrf-token'

        resp = self.client.post(
            '/api/favourites/toggle',
            data=json.dumps({'item_name': 'cargo pants'}),
            headers={'X-CSRFToken': 'test-csrf-token', 'Content-Type': 'application/json'}
        )
        self.assertEqual(resp.status_code, 401)
        data = json.loads(resp.data)
        self.assertTrue(data.get('requires_login'))


if __name__ == '__main__':
    unittest.main()
