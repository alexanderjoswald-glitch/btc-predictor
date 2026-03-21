# app.py
# Main Flask Application - For Render.com Deployment

from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import bcrypt
from datetime import datetime, timedelta
import os
import sqlite3
import pandas as pd
import threading
import time
import requests
import json
import config

from simple_predictor import Simple15MinPredictor
from tiered_predictor import TieredHourlyPredictor
from whale_tracker import WhaleTracker
from kalshi_api import KalshiAPI

app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY

# Initialize predictors
predictor_15min = Simple15MinPredictor()
predictor_hourly = TieredHourlyPredictor()
whale = WhaleTracker()
kalshi = KalshiAPI()

# Setup login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id) if user_id == '1' else None

def verify_password(password):
    stored_hash = config.ADMIN_PASSWORD_HASH
    if stored_hash == "REPLACE_ME" or not stored_hash:
        return False
    return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))

# ============ AUTO-KEEP-ALIVE ============
last_ping_time = datetime.now()
ping_count = 0

def keep_alive():
    """Ping the site every 5 minutes to prevent sleeping"""
    global last_ping_time, ping_count
    
    # Get the site URL from environment or use default
    site_url = os.environ.get('RENDER_EXTERNAL_URL', 'https://btc-predictor.onrender.com')
    print(f"🔄 Auto-keep-alive started - pinging {site_url} every 5 minutes")
    
    while True:
        time.sleep(300)
        try:
            response = requests.get(site_url, timeout=10)
            if response.status_code == 200:
                last_ping_time = datetime.now()
                ping_count += 1
                print(f"✅ Keep-alive ping #{ping_count} at {datetime.now()}")
        except Exception as e:
            print(f"⚠️ Keep-alive error: {e}")

if config.KEEP_ALIVE_ENABLED:
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    print("✅ Auto-keep-alive thread started")

# ============ ROUTES ============

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if verify_password(password):
            login_user(User('1'))
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid password', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/15min')
@login_required
def predict_15min():
    try:
        df = predictor_15min.fetch_data(200)
        if df.empty:
            return jsonify({'error': 'No data'})
        pred = predictor_15min.predict(df)
        kalshi_data = kalshi.get_kalshi_signal(pred['direction'], pred['confidence'])
        
        # Store prediction
        conn = sqlite3.connect('data/15min.db')
        conn.execute('''CREATE TABLE IF NOT EXISTS predictions
                        (id INTEGER PRIMARY KEY, timestamp TEXT, 
                         predicted TEXT, confidence REAL, price REAL, 
                         pred_time TEXT, actual TEXT, correct INTEGER)''')
        conn.execute("INSERT INTO predictions (timestamp, predicted, confidence, price, pred_time) VALUES (?, ?, ?, ?, ?)",
                     (datetime.now().isoformat(), pred['direction'], pred['confidence'], 
                      pred['current_price'], pred['prediction_time']))
        conn.commit()
        conn.close()
        
        pred['kalshi'] = kalshi_data
        return jsonify(pred)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/hourly')
@login_required
def predict_hourly():
    try:
        df = predictor_hourly.fetch_data(200)
        if df.empty:
            return jsonify({'error': 'No data'})
        pred = predictor_hourly.predict(df)
        kalshi_data = kalshi.get_kalshi_signal(pred['direction'], pred['confidence'])
        
        # Store prediction
        conn = sqlite3.connect('data/hourly.db')
        conn.execute('''CREATE TABLE IF NOT EXISTS predictions
                        (id INTEGER PRIMARY KEY, timestamp TEXT,
                         predicted TEXT, confidence REAL, price REAL,
                         rounded INTEGER, pred_time TEXT,
                         aggressive INTEGER, modest INTEGER, safe INTEGER,
                         aggressive_reached INTEGER, modest_reached INTEGER, 
                         safe_reached INTEGER, actual TEXT, correct INTEGER,
                         actual_price REAL)''')
        conn.execute("INSERT INTO predictions (timestamp, predicted, confidence, price, rounded, pred_time, aggressive, modest, safe) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (datetime.now().isoformat(), pred['direction'], pred['confidence'], 
                      pred['current_price'], pred['current_rounded'], pred['prediction_time'],
                      pred['tiers']['aggressive']['price'], pred['tiers']['modest']['price'],
                      pred['tiers']['safe']['price']))
        conn.commit()
        conn.close()
        
        pred['kalshi'] = kalshi_data
        return jsonify(pred)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/whale')
@login_required
def get_whale():
    try:
        metrics = whale.track()
        signal = whale.get_signal()
        return jsonify({'metrics': metrics, 'signal': round(signal, 1)})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/15min_accuracy')
@login_required
def acc_15min():
    return jsonify(predictor_15min.get_accuracy())

@app.route('/api/hourly_accuracy')
@login_required
def acc_hourly():
    return jsonify(predictor_hourly.get_accuracy())

@app.route('/api/15min_history')
@login_required
def history_15min():
    try:
        conn = sqlite3.connect('data/15min.db')
        df = pd.read_sql_query("SELECT timestamp, predicted, confidence, actual FROM predictions ORDER BY timestamp DESC LIMIT 50", conn)
        conn.close()
        return jsonify(df.to_dict('records'))
    except:
        return jsonify([])

@app.route('/api/hourly_history')
@login_required
def history_hourly():
    try:
        conn = sqlite3.connect('data/hourly.db')
        df = pd.read_sql_query("SELECT timestamp, predicted, confidence, aggressive, modest, safe, actual FROM predictions ORDER BY timestamp DESC LIMIT 50", conn)
        conn.close()
        return jsonify(df.to_dict('records'))
    except:
        return jsonify([])

@app.route('/keep-alive')
def keep_alive_endpoint():
    return jsonify({
        'status': 'alive',
        'timestamp': datetime.now().isoformat(),
        'ping_count': ping_count
    })

@app.route('/status')
def status_endpoint():
    return jsonify({
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'uptime_days': (datetime.now() - last_ping_time).days if last_ping_time else 0
    })

# ============ INITIAL TRAINING ============
if __name__ == '__main__':
    # Create directories
    os.makedirs('data', exist_ok=True)
    os.makedirs('models/simple_15min', exist_ok=True)
    os.makedirs('models/tiered_hourly', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    
    print("=" * 60)
    print("KALSHI BTC PREDICTOR - STARTING")
    print("=" * 60)
    
    # Train models if needed
    if not os.path.exists('models/simple_15min/xgboost.joblib'):
        print("\nTraining 15-min predictor...")
        df = predictor_15min.fetch_data(3000)
        if not df.empty:
            predictor_15min.train(df)
    
    if not os.path.exists('models/tiered_hourly/xgboost.joblib'):
        print("\nTraining hourly predictor...")
        df = predictor_hourly.fetch_data(3000)
        if not df.empty:
            predictor_hourly.train(df)
    
    # Get port from environment variable (Render sets this)
    port = int(os.environ.get('PORT', 5000))
    
    print("\n" + "=" * 60)
    print("✅ SYSTEM READY!")
    print(f"📍 Running on port {port}")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=False)