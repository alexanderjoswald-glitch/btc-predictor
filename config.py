# config.py
# Kalshi BTC Predictor - Configuration for Render.com

import os

# ============ PRIVATE ACCESS ============
# You will set this as an Environment Variable on Render.com
# DO NOT hardcode your password here for security!
ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH', 'Replace Me')
SECRET_KEY = os.environ.get('SECRET_KEY', 'kalshi-btc-predictor-2024')

# ============ KALSHI API ============
KALSHI_API_KEY = "e82e3161-5fca-4218-a101-081436a42cd9"
KALSHI_PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA5tUMA6xLsCRArXfzFer6IIUiYxn99KmEGbm6IuD8gIAyV0lR
7kaZu3W4VdkkqLD/SnadHWvVoroMp8OwV7vOrYZlRCXwHqocZYkzfJMkyc/bpiTn
vHcSEaeCTZmIu03Y6GAcEVAhns1LyyODEkdGdohOWKSvZ8XEj7hFNQ/8Q/a8+4O4
WLqhxQeivkVGF0oLpl+F3FhLbPiQLEgGQE2/KJ3xz/FxTJjZSYetQ8xMhlrJ61q7
fHVXh2Et0qRaadE5ODkYIeZkSfii0CvyyrZRWFYTppm4NJLPg6xK/NcYrkwZ9BvQ
UU4zYnbdzLI93W9Isd+wsOF9BkhrgETwGz1IMwIDAQABAoIBABOm5LB1XTZAR99c
3G2rxSK6ouxT/Kp1OiFkjgPFKsoX3/FNdTO3gAQVKB3q8DOKahmhUov8L8J8W3J2
9w7pFtXwILP2FOTPb753OVJsRpAF6bnR34bMjlXBcJcBsMHdhU93SzxwGYSnDsJb
IiAOwGF8BkuGrcZEcJEZy46Sb1QrxpF03sRgSYjINwEQiPKnIdTOD7nTgxuctpAl
9JzpM67AlXCr+T0KFN1+1qsIF0aw63YfR9HqJbbsKalUPvusRxJW52VMLc1lBqAD
LPVMinZkaFdRy3+q95n0hfeGHAU+FeWm7dlbRQCIr5Uqm0bKC0dsAyBeTbQPuMGt
dkdcpKUCgYEA+EIRhVTjr5oxZewQ5+LRkrNCbzK/E4awAmrxLlbttM7jv1Jrt1dy
QrLlI6yxS1VilpLzOvqtB1tEuo51kpzwDfqzEvyWRqBLbLp82t4tkp8ljWaRYA13
f4HOrd9030aoyU0WTsgDDSPzM5CGjuEHrXK8o8f6aSYTYn/4dTVIe5UCgYEA7gfc
lwbpR7BMARHRiXx6pxBv81C8ktr7TYykgpOnFbVdahxe5CVP+nh1PoKJ0bCyXFy0
xTTohD7WM2As1s650Evc4ykkBLjwueE0LR9q6NirtSGhHh0Jf3P99tu5Aitd44iW
LDSFSedaNHwq7dlzX0HUoqzG9O82z1rQfDyngqcCgYA1W830QGinp5aSd4iyrneo
9kqDJ/8VrU9LVbz83sY8pHMi/g4U3AC9AUJqxoVc0b9c6bzJonNqL124U0JF/uFB
v+6ZWBzclTtg5TxMtpBJAVfK6o64fGyAxV+s02iFTOSeT6lJyYeOXXm6TYf+UbOa
vhx5f1P9Iafs9eBrIMaxeQKBgQDQpsOO/9ftp3R4W4453owFdjssJlGmyZ4QVIDA
lX2ZYeoI4eWsR6jb/kuICBWXYjR3EizD0aUgh5RsZJnpkjz/ggCWf7G7EgKybd62
zxuAEK4zkM8S/pEc0CiHBAQhCrK6iThad49/QPWpnE5lQIAJuEMUdi/Q9QAus4Sd
4u1TcQKBgHxQmb87rNue3RvJGTKdKD6AP8okiKj+xaTI+F8LfSFB8kMRJvxTz3sD
jFRm29jFWj6e6OJcLUCv8J1a7O+6re2xTpHitu8P3/wMMH3lF2qXLlEnosFAav+4
G+jtvKZq1DwKlcjjvnbvVj88yd10aKkc2Z0Hwd3uwYSevSkx8+5Z
-----END RSA PRIVATE KEY-----"""

KALSHI_ENV = "demo"

# ============ PREDICTION SETTINGS ============
SYMBOL = "BTC/USDT"
TIMEFRAME = "1m"
ROUND_TO = 100

BINARY_HORIZON = 15
HOURLY_HORIZON = 60

KALSHI_TIER_DIFF = {
    'aggressive': 0,
    'modest': 300,
    'safe': 800
}

# ============ MODEL SETTINGS ============
MODEL_WEIGHTS = {
    'xgboost': 0.35,
    'random_forest': 0.35,
    'gradient_boosting': 0.30
}

# ============ WHALE TRACKING ============
WHALE_THRESHOLD_USDT = 500000
WHALE_ACCUMULATION_THRESHOLD = 0.7

# ============ AUTO-KEEP-ALIVE ============
KEEP_ALIVE_ENABLED = True
KEEP_ALIVE_INTERVAL_MINUTES = 5