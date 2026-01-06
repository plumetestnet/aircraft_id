"""
Pre-flight Check - Run this before starting the bot
"""

import os
from dotenv import load_dotenv

print("=" * 60)
print("🔍 Pre-Flight Checklist")
print("=" * 60)

# Load .env
load_dotenv()

checks_passed = 0
checks_failed = 0

# Check 1: MONGODB_URI
print("\n1️⃣  Checking MongoDB URI...")
mongodb_uri = os.getenv('MONGODB_URI')
if mongodb_uri and mongodb_uri.startswith('mongodb+srv://'):
    print("   ✅ MongoDB URI configured correctly")
    print(f"   📝 URI: {mongodb_uri[:50]}...")
    checks_passed += 1
else:
    print("   ❌ MongoDB URI missing or incorrect")
    print(f"   Current value: {mongodb_uri}")
    checks_failed += 1

# Check 2: BOT_TOKEN
print("\n2️⃣  Checking Bot Token...")
bot_token = os.getenv('BOT_TOKEN')
if bot_token and ':' in bot_token:
    print("   ✅ Bot token configured")
    print(f"   📝 Token: {bot_token[:20]}...")
    checks_passed += 1
else:
    print("   ❌ Bot token missing or invalid")
    checks_failed += 1

# Check 3: API credentials
print("\n3️⃣  Checking Telegram API credentials...")
api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')
if api_id and api_hash:
    print("   ✅ API credentials configured")
    print(f"   📝 API ID: {api_id}")
    checks_passed += 1
else:
    print("   ❌ API credentials missing")
    checks_failed += 1

# Check 4: OWNER_ID
print("\n4️⃣  Checking Owner ID...")
owner_id = os.getenv('OWNER_ID')
if owner_id and owner_id != '123456789':
    print("   ✅ Owner ID configured")
    print(f"   📝 Owner ID: {owner_id}")
    checks_passed += 1
else:
    print("   ⚠️  Owner ID not updated (still default)")
    print("   Get your ID from @userinfobot and update OWNER_ID in .env")
    checks_failed += 1

# Check 5: Dependencies
print("\n5️⃣  Checking dependencies...")
deps_ok = True
required = [
    'telegram',
    'pymongo',
    'dotenv',
    'aiohttp',
    'telethon'
]

for dep in required:
    try:
        __import__(dep if dep != 'dotenv' else 'dotenv')
        print(f"   ✅ {dep}")
    except ImportError:
        print(f"   ❌ {dep} not installed")
        deps_ok = False

if deps_ok:
    checks_passed += 1
else:
    checks_failed += 1
    print("   Run: pip install -r requirements.txt")

# Check 6: MongoDB Connection
print("\n6️⃣  Testing MongoDB connection...")
try:
    from pymongo import MongoClient
    if mongodb_uri:
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        client.server_info()
        print("   ✅ MongoDB connection successful")
        checks_passed += 1
    else:
        print("   ❌ No MongoDB URI to test")
        checks_failed += 1
except Exception as e:
    print(f"   ❌ MongoDB connection failed: {e}")
    checks_failed += 1

# Summary
print("\n" + "=" * 60)
print("📊 Summary")
print("=" * 60)
print(f"✅ Passed: {checks_passed}/6")
print(f"❌ Failed: {checks_failed}/6")

if checks_failed == 0:
    print("\n🎉 All checks passed! You can run the bot:")
    print("   python bot.py")
elif checks_failed == 1 and owner_id == '123456789':
    print("\n⚠️  Almost ready! Just update OWNER_ID:")
    print("   1. Message @userinfobot on Telegram")
    print("   2. Copy your user ID")
    print("   3. Update OWNER_ID in .env")
    print("   4. Run: python bot.py")
else:
    print("\n❌ Please fix the issues above before running the bot")
    print("\nQuick fixes:")
    if checks_failed > 2:
        print("   1. Make sure .env file is in the same directory")
        print("   2. Check .env has correct format (no extra spaces)")
        print("   3. Run: pip install -r requirements.txt")
    print("   4. Run this script again to verify")

print("=" * 60)