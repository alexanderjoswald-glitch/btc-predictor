# tiered_predictor.py
# 1-Hour Tiered Predictor - Kalshi Format

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

class TieredHourlyPredictor:
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
        if os.path.exists('models/tiered_hourly'):
            for name in self.models:
                path = f'models/tiered_hourly/{name}.joblib'
                if os.path.exists(path):
                    self.models[name] = joblib.load(path)
            if os.path.exists('models/tiered_scaler.joblib'):
                self.scaler = joblib.load('models/tiered_scaler.joblib')
    
    def save_models(self):
        os.makedirs('models/tiered_hourly', exist_ok=True)
        for name, model in self.models.items():
            joblib.dump(model, f'models/tiered_hourly/{name}.joblib')
        joblib.dump(self.scaler, 'models/tiered_scaler.joblib')
    
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
        
        for p in [5, 10, 15, 30, 60]:
            df[f'ret_{p}'] = df['close'].pct_change(p) * 100
        
        for p in [10, 20, 30, 50]:
            df[f'sma_{p}'] = ta.trend.sma_indicator(df['close'], window=p)
            df[f'ema_{p}'] = ta.trend.ema_indicator(df['close'], window=p)
        
        df['rsi_14'] = ta.momentum.rsi(df['close'], window=14)
        
        df['macd'] = ta.trend.macd(df['close'])
        df['macd_signal'] = ta.trend.macd_signal(df['close'])
        
        upper = ta.volatility.bollinger_hband(df['close'], window=20, window_dev=2)
        lower = ta.volatility.bollinger_lband(df['close'], window=20, window_dev=2)
        df['bb_position'] = (df['close'] - lower) / (upper - lower + 0.001)
        
        df['vol_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        
        df = df.fillna(method='ffill').fillna(0)
        df = df.replace([np.inf, -np.inf], 0)
        
        return df
    
    def create_labels(self, df):
        future_price = df['close'].shift(-60)
        current_price = df['close']
        price_change_pct = (future_price - current_price) / current_price * 100
        
        labels = np.where(price_change_pct > 0.1, 1, 
                         np.where(price_change_pct < -0.1, 0, np.nan))
        
        return pd.Series(labels, index=df.index)
    
    def prepare_features(self, df):
        exclude = ['open', 'high', 'low', 'close', 'volume']
        cols = [c for c in df.columns if c not in exclude]
        features = df[cols].values
        features = np.nan_to_num(features)
        return features, cols
    
    def train(self, df):
        print("=" * 50)
        print("TRAINING HOURLY PREDICTOR")
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
    
    def calculate_kalshi_tiers(self, projected_rounded):
        return {
            'aggressive': projected_rounded,
            'modest': projected_rounded - 300,
            'safe': projected_rounded - 800
        }
    
    def get_next_hour_time(self):
        return datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    
    def predict(self, df):
        try:
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
            
            if direction == "UP":
                expected_move_pct = (up_probability - 50) / 50 * 1.5
                projected_price = current_price * (1 + expected_move_pct / 100)
            else:
                expected_move_pct = (50 - up_probability) / 50 * 1.5
                projected_price = current_price * (1 - expected_move_pct / 100)
            
            projected_rounded = self.round_down(projected_price)
            tiers = self.calculate_kalshi_tiers(projected_rounded)
            
            next_time = self.get_next_hour_time()
            
            return {
                'direction': direction,
                'confidence': round(confidence, 1),
                'up_probability': round(up_probability, 1),
                'expected_move_pct': round(expected_move_pct, 2),
                'current_price': round(current_price, 2),
                'current_rounded': current_rounded,
                'projected_price': round(projected_price, 2),
                'projected_rounded': projected_rounded,
                'prediction_time': next_time.isoformat(),
                'tiers': {
                    'aggressive': {
                        'price': tiers['aggressive'],
                        'formatted': f"${tiers['aggressive']:,}",
                        'description': 'Projected rounded price'
                    },
                    'modest': {
                        'price': tiers['modest'],
                        'formatted': f"${tiers['modest']:,}",
                        'description': 'Projected - $300'
                    },
                    'safe': {
                        'price': tiers['safe'],
                        'formatted': f"${tiers['safe']:,}",
                        'description': 'Projected - $800 (Safest)'
                    }
                }
            }
            
        except Exception as e:
            print(f"Error: {e}")
            return {
                'direction': 'ERROR',
                'confidence': 0,
                'up_probability': 50,
                'expected_move_pct': 0,
                'current_price': 0,
                'current_rounded': 0,
                'projected_price': 0,
                'projected_rounded': 0,
                'prediction_time': datetime.now().isoformat(),
                'tiers': {
                    'aggressive': {'price': 0, 'formatted': '$0', 'description': ''},
                    'modest': {'price': 0, 'formatted': '$0', 'description': ''},
                    'safe': {'price': 0, 'formatted': '$0', 'description': ''}
                }
            }
    
    def get_accuracy(self):
        import sqlite3
        if not os.path.exists('data/hourly.db'):
            return {'overall': 50, 'recent': 50, 'total': 0}
        
        try:
            conn = sqlite3.connect('data/hourly.db')
            df = pd.read_sql_query("SELECT * FROM predictions WHERE actual IS NOT NULL", conn)
            conn.close()
            
            if len(df) < 10:
                return {'overall': 50, 'recent': 50, 'total': len(df)}
            
            correct = (df['predicted'] == df['actual']).sum()
            overall = correct / len(df) * 100
            recent = df.head(100)
            recent_correct = (recent['predicted'] == recent['actual']).sum()
            recent_acc = recent_correct / len(recent) * 100 if len(recent) > 0 else 0
            
            return {
                'overall': round(overall, 1),
                'recent': round(recent_acc, 1),
                'total': len(df)
            }
        except:
            return {'overall': 50, 'recent': 50, 'total': 0}