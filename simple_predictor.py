# simple_predictor.py
# 15-Minute Binary Predictor

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import ccxt
import ta
from sklearn.preprocessing import RobustScaler
import xgboost as xgb
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
import joblib
import os
import warnings
import config

warnings.filterwarnings('ignore')

class Simple15MinPredictor:
    def __init__(self):
        self.exchange = ccxt.kraken({'enableRateLimit': True})
        self.scaler = RobustScaler()
        self.models = {}
        self.init_models()
        
    def init_models(self):
        self.models['xgboost'] = xgb.XGBClassifier(
            n_estimators=400, max_depth=8, learning_rate=0.03, random_state=42
        )
        self.models['random_forest'] = RandomForestClassifier(
            n_estimators=300, max_depth=10, random_state=42
        )
        self.models['gradient_boosting'] = GradientBoostingClassifier(
            n_estimators=300, max_depth=8, learning_rate=0.05, random_state=42
        )
        self.load_models()
    
    def load_models(self):
        if os.path.exists('models/simple_15min'):
            for name in self.models:
                path = f'models/simple_15min/{name}.joblib'
                if os.path.exists(path):
                    self.models[name] = joblib.load(path)
            if os.path.exists('models/simple_scaler.joblib'):
                self.scaler = joblib.load('models/simple_scaler.joblib')
    
    def save_models(self):
        os.makedirs('models/simple_15min', exist_ok=True)
        for name, model in self.models.items():
            joblib.dump(model, f'models/simple_15min/{name}.joblib')
        joblib.dump(self.scaler, 'models/simple_scaler.joblib')
    
    def fetch_data(self, limit=5000):
        ohlcv = self.exchange.fetch_ohlcv('BTC/USD', '1m', limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        return df
    
    def round_down(self, price):
        return int(np.floor(price / 100) * 100)
    
    def add_features(self, df):
        df = df.copy()
        
        for p in [1, 3, 5, 10, 15]:
            df[f'ret_{p}'] = df['close'].pct_change(p) * 100
        
        for p in [5, 10, 15, 20, 30]:
            df[f'sma_{p}'] = ta.trend.sma_indicator(df['close'], window=p)
            df[f'ema_{p}'] = ta.trend.ema_indicator(df['close'], window=p)
        
        df['rsi_14'] = ta.momentum.rsi(df['close'], window=14)
        
        df['macd'] = ta.trend.macd(df['close'])
        df['macd_signal'] = ta.trend.macd_signal(df['close'])
        df['macd_hist'] = ta.trend.macd_diff(df['close'])
        
        upper = ta.volatility.bollinger_hband(df['close'], window=20, window_dev=2)
        lower = ta.volatility.bollinger_lband(df['close'], window=20, window_dev=2)
        df['bb_position'] = (df['close'] - lower) / (upper - lower + 0.001)
        
        df['vol_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        
        df = df.fillna(method='ffill').fillna(0)
        df = df.replace([np.inf, -np.inf], 0)
        
        return df
    
    def create_labels(self, df):
        future_price = df['close'].shift(-15)
        current_price = df['close']
        price_change = (future_price - current_price) / current_price * 100
        
        labels = np.where(price_change > 0.05, 1, 
                         np.where(price_change < -0.05, 0, np.nan))
        
        return pd.Series(labels, index=df.index)
    
    def prepare_features(self, df):
        exclude = ['open', 'high', 'low', 'close', 'volume']
        cols = [c for c in df.columns if c not in exclude]
        features = df[cols].values
        features = np.nan_to_num(features)
        return features, cols
    
    def train(self, df):
        print("=" * 50)
        print("TRAINING 15-MIN BINARY PREDICTOR")
        print("=" * 50)
        
        df = self.add_features(df)
        y = self.create_labels(df)
        
        mask = ~y.isna()
        df = df[mask]
        y = y[mask]
        
        X, _ = self.prepare_features(df)
        split = int(len(X) * 0.8)
        
        X_train, X_test = X[:split], X[split:]
        y_train, y_test = y[:split], y[split:]
        
        print(f"Training samples: {len(X_train)}")
        
        X_train = self.scaler.fit_transform(X_train)
        X_test = self.scaler.transform(X_test)
        
        results = {}
        for name, model in self.models.items():
            print(f"Training {name}...")
            model.fit(X_train, y_train)
            score = model.score(X_test, y_test)
            results[name] = score
            print(f"  {name}: {score:.2%}")
        
        self.save_models()
        
        print(f"Ensemble Accuracy: {np.mean(list(results.values())):.2%}")
        return results
    
    def get_next_prediction_time(self):
        now = datetime.now()
        minute = now.minute
        next_min = ((minute // 15) + 1) * 15
        if next_min >= 60:
            next_hour = now.hour + 1
            next_min = 0
        else:
            next_hour = now.hour
        return now.replace(hour=next_hour % 24, minute=next_min, second=0, microsecond=0)
    
    def predict(self, df):
        df = self.add_features(df)
        X, _ = self.prepare_features(df)
        X_latest = X[-1:].reshape(1, -1)
        X_scaled = self.scaler.transform(X_latest)
        
        probs = {}
        for name, model in self.models.items():
            try:
                proba = model.predict_proba(X_scaled)[0]
                probs[name] = proba[1] * 100
            except:
                probs[name] = 50
        
        weights = {'xgboost': 0.35, 'random_forest': 0.35, 'gradient_boosting': 0.30}
        up_probability = sum(probs.get(n, 50) * w for n, w in weights.items() if n in probs)
        up_probability = up_probability / sum(weights.values())
        
        direction = "UP" if up_probability > 50 else "DOWN"
        confidence = abs(up_probability - 50) * 2
        confidence = min(100, max(0, confidence))
        
        current_price = df['close'].iloc[-1]
        current_rounded = self.round_down(current_price)
        
        next_time = self.get_next_prediction_time()
        
        return {
            'direction': direction,
            'confidence': round(confidence, 1),
            'up_probability': round(up_probability, 1),
            'current_price': round(current_price, 2),
            'current_rounded': current_rounded,
            'prediction_time': next_time.isoformat()
        }
    
    def get_accuracy(self):
        import sqlite3
        if not os.path.exists('data/15min.db'):
            return {'overall': 50, 'recent': 50, 'total': 0, 'edge': 0}
        
        conn = sqlite3.connect('data/15min.db')
        df = pd.read_sql_query("SELECT * FROM predictions WHERE actual IS NOT NULL", conn)
        conn.close()
        
        if len(df) < 10:
            return {'overall': 50, 'recent': 50, 'total': len(df), 'edge': 0}
        
        correct = (df['predicted'] == df['actual']).sum()
        overall = correct / len(df) * 100
        recent = df.head(100)
        recent_correct = (recent['predicted'] == recent['actual']).sum()
        recent_acc = recent_correct / len(recent) * 100 if len(recent) > 0 else 0
        
        return {
            'overall': round(overall, 1),
            'recent': round(recent_acc, 1),
            'total': len(df),
            'edge': round(overall - 50, 1)
        }