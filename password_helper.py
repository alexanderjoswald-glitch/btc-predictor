# password_helper.py
import bcrypt

print("=" * 50)
print("KALSHI BTC PREDICTOR - PASSWORD GENERATOR")
print("=" * 50)

password = input("\nEnter your password: ")

salt = bcrypt.gensalt()
password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
hash_string = password_hash.decode('utf-8')

print("\n" + "=" * 50)
print("COPY THIS LINE TO config.py:")
print("=" * 50)
print(f'ADMIN_PASSWORD_HASH = "{hash_string}"')
print("=" * 50)

with open('password_hash.txt', 'w') as f:
    f.write(hash_string)

print("\n✅ Saved to password_hash.txt")