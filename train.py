# train.py
from simple_predictor import Simple15MinPredictor
from tiered_predictor import TieredHourlyPredictor

print("=" * 50)
print("TRAINING BTC PREDICTOR")
print("=" * 50)

print("\n1. Training 15-min predictor...")
p15 = Simple15MinPredictor()
df = p15.fetch_data(3000)
p15.train(df)

print("\n2. Training hourly predictor...")
ph = TieredHourlyPredictor()
df2 = ph.fetch_data(3000)
ph.train(df2)

print("\n" + "=" * 50)
print("TRAINING COMPLETE!")
print("=" * 50)
