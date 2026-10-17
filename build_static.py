"""
build_static.py - Pre-renders Flask templates into static HTML for Netlify / static web hosting.
Generates index.html, about.html, favourites.html, login.html, register.html,
and pre-calculated JSON API files in data/.
"""
import os
import json
import re

def build():
    from app import app
    print("Building static export for Netlify...")

    routes = [
        ('/', 'index.html'),
        ('/about', 'about.html'),
        ('/favourites', 'favourites.html'),
        ('/login', 'login.html'),
        ('/register', 'register.html'),
    ]

    with app.test_client() as client:
        for route, fname in routes:
            resp = client.get(route)
            if resp.status_code != 200:
                print(f"Warning: {route} returned status {resp.status_code}")
                continue
            html = resp.data.decode('utf-8')
            # Normalize links for pure static hosting fallback
            html = re.sub(r'href="/"', 'href="index.html"', html)
            html = re.sub(r'href="/about"', 'href="about.html"', html)
            html = re.sub(r'href="/favourites"', 'href="favourites.html"', html)
            html = re.sub(r'href="/login"', 'href="login.html"', html)
            html = re.sub(r'href="/register"', 'href="register.html"', html)
            html = re.sub(r'href="/logout"', 'href="index.html"', html)
            
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"Generated {fname} ({len(html)} bytes)")

        # Generate pre-calculated trends and forecast JSON
        os.makedirs('data', exist_ok=True)
        trends_resp = client.get('/api/trends?category=both&geo=IN&timeframe=today+12-m&sample=1')
        if trends_resp.status_code == 200:
            with open('data/trends.json', 'w', encoding='utf-8') as f:
                f.write(trends_resp.data.decode('utf-8'))
            print("Generated data/trends.json")

        forecast_resp = client.get('/api/forecast?items=cargo+pants,co+ord+set,baggy+jeans,oversized+t+shirt,linen+shirt,crop+top,denim+jacket&geo=IN&timeframe=today+12-m&sample=1')
        if forecast_resp.status_code == 200:
            with open('data/forecast.json', 'w', encoding='utf-8') as f:
                f.write(forecast_resp.data.decode('utf-8'))
            print("Generated data/forecast.json")

    print("Static build complete!")

if __name__ == '__main__':
    build()
