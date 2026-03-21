# kalshi_api.py
import requests
import json
import time
import hashlib
import hmac
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import config

class KalshiAPI:
    def __init__(self):
        self.base_url = "https://demo-api.kalshi.co/trade-api/v2"
        self.api_key = config.KALSHI_API_KEY
        self.private_key_pem = config.KALSHI_PRIVATE_KEY
        
        try:
            self.private_key = serialization.load_pem_private_key(
                self.private_key_pem.encode(),
                password=None,
            )
        except:
            self.private_key = None
    
    def _generate_signature(self, method: str, path: str, body: str = "") -> Tuple[str, int]:
        if not self.private_key:
            return "", 0
        timestamp = int(time.time() * 1000)
        message = f"{method}{path}{timestamp}{body}"
        try:
            signature = self.private_key.sign(
                message.encode(),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            return base64.b64encode(signature).decode(), timestamp
        except:
            return "", 0
    
    def _make_request(self, method: str, path: str, body: Dict = None) -> Dict:
        if not self.private_key:
            return {}
        url = f"{self.base_url}{path}"
        body_str = json.dumps(body) if body else ""
        signature, timestamp = self._generate_signature(method, path, body_str)
        if not signature:
            return {}
        headers = {
            "Content-Type": "application/json",
            "API-KEY": self.api_key,
            "API-SIGNATURE": signature,
            "API-TIMESTAMP": str(timestamp)
        }
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            else:
                response = requests.post(url, headers=headers, json=body, timeout=10)
            if response.status_code == 200:
                return response.json()
            return {}
        except:
            return {}
    
    def get_market_price(self, market_id: str) -> Optional[Dict]:
        result = self._make_request("GET", f"/markets/{market_id}")
        if result and 'yes_bid' in result:
            return {
                'market_id': market_id,
                'yes_bid': result.get('yes_bid', 0),
                'yes_ask': result.get('yes_ask', 0)
            }
        return None
    
    def get_current_btc_odds(self) -> Dict:
        now = datetime.now()
        results = {}
        hour_market_id = f"BTC-{now.strftime('%Y%m%d')}-{now.hour:02d}-00"
        hour_market = self.get_market_price(hour_market_id)
        if hour_market:
            results['hourly'] = {'type': 'hourly', 'price': hour_market}
        minute_floor = (now.minute // 15) * 15
        min_market_id = f"BTC-{now.strftime('%Y%m%d')}-{now.hour:02d}-{minute_floor:02d}"
        min_market = self.get_market_price(min_market_id)
        if min_market:
            results['15min'] = {'type': '15min', 'price': min_market}
        return results
    
    def get_kalshi_signal(self, prediction_direction: str, confidence: float) -> Dict:
        kalshi_odds = self.get_current_btc_odds()
        signals = []
        for timeframe, market in kalshi_odds.items():
            if market and 'price' in market:
                market_prob = market['price'].get('yes_ask', 50)
                if market_prob > 0:
                    if confidence > market_prob + 10:
                        signals.append({
                            'timeframe': timeframe,
                            'action': 'BUY',
                            'reason': f"Our confidence {confidence}% > market {market_prob}%"
                        })
                    elif confidence < market_prob - 10:
                        signals.append({
                            'timeframe': timeframe,
                            'action': 'SELL',
                            'reason': f"Our confidence {confidence}% < market {market_prob}%"
                        })
        return {'signals': signals, 'kalshi_odds': kalshi_odds, 'arbitrage_opportunity': len(signals) > 0}