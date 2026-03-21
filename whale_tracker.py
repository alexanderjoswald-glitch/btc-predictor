# whale_tracker.py
import pandas as pd
import numpy as np
from collections import deque
from datetime import datetime
import ccxt

class WhaleTracker:
    def __init__(self):
        self.exchange = ccxt.kraken({'enableRateLimit': True})
        self.trades = deque(maxlen=1000)
    
    def track(self):
        try:
            order_book = self.exchange.fetch_order_book('BTC/USD', 100)
            
            bids = pd.DataFrame(order_book['bids'], columns=['price', 'volume'])
            bids['value'] = bids['price'] * bids['volume']
            bids['type'] = 'buy'
            
            asks = pd.DataFrame(order_book['asks'], columns=['price', 'volume'])
            asks['value'] = asks['price'] * asks['volume']
            asks['type'] = 'sell'
            
            orders = pd.concat([bids, asks])
            whale_orders = orders[orders['value'] >= 500000]
            
            for _, row in whale_orders.iterrows():
                self.trades.append({
                    'timestamp': datetime.now(),
                    'type': row['type'],
                    'value': row['value']
                })
            
            if len(whale_orders) == 0:
                return {'active': False, 'sentiment': 0}
            
            buy_vol = whale_orders[whale_orders['type'] == 'buy']['value'].sum()
            sell_vol = whale_orders[whale_orders['type'] == 'sell']['value'].sum()
            total = buy_vol + sell_vol
            
            if total == 0:
                return {'active': False, 'sentiment': 0}
            
            sentiment = ((buy_vol - sell_vol) / total) * 100
            
            return {
                'active': True,
                'sentiment': round(sentiment, 1),
                'buy_volume': round(buy_vol / 1000000, 1),
                'sell_volume': round(sell_vol / 1000000, 1),
                'is_accumulating': sentiment > 30
            }
            
        except Exception as e:
            return {'active': False, 'sentiment': 0}
    
    def get_signal(self):
        if len(self.trades) == 0:
            return 0
        
        recent = list(self.trades)[-50:]
        buy_sum = sum(t['value'] for t in recent if t['type'] == 'buy')
        sell_sum = sum(t['value'] for t in recent if t['type'] == 'sell')
        
        if buy_sum + sell_sum == 0:
            return 0
        
        return ((buy_sum - sell_sum) / (buy_sum + sell_sum)) * 100