# generate_hash.py
# Run this on your Windows computer to generate your password hash

import bcrypt

print("=" * 60)
print("KALSHI BTC PREDICTOR - PASSWORD HASH GENERATOR")
print("=" * 60)

password = input("\nEnter your password: ")

# Generate hash
salt = bcrypt.gensalt()
password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
hash_string = password_hash.decode('utf-8')

print("\n" + "=" * 60)
print("COPY THIS HASH - You'll add it to Render.com environment variables")
print("=" * 60)
print(hash_string)
print("=" * 60)

# Save to file
with open('my_password_hash.txt', 'w') as f:
    f.write(hash_string)

print("\n✅ Saved to my_password_hash.txt")
print("📋 Keep this file safe!")