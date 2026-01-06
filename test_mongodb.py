"""
MongoDB Connection Test Script - Enhanced Version
"""

import os
import sys

print("=" * 60)
print("🔍 MongoDB Connection Diagnostic Tool")
print("=" * 60)

# Check if .env file exists
if not os.path.exists('.env'):
    print("\n❌ ERROR: .env file not found in current directory!")
    print(f"Current directory: {os.getcwd()}")
    print("\nPlease make sure .env file is in the same directory as this script.")
    sys.exit(1)

print(f"\n✅ Found .env file in: {os.getcwd()}")

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ python-dotenv loaded")
except ImportError:
    print("❌ python-dotenv not installed")
    print("Run: pip install python-dotenv")
    sys.exit(1)

# Get and validate connection string
uri = os.getenv('MONGODB_URI')

if not uri:
    print("\n❌ ERROR: MONGODB_URI not found in .env file")
    print("\nYour .env file should contain:")
    print("MONGODB_URI=mongodb+srv://bot:botuser08@cluster0.xd144zw.mongodb.net/telegram_bot?retryWrites=true&w=majority")
    sys.exit(1)

# Check URI format
print(f"\n📝 Connection String Found")
print(f"   Length: {len(uri)} characters")
print(f"   Starts with: {uri[:20]}...")
print(f"   Ends with: ...{uri[-30:]}")

# Validate scheme
if not uri.startswith('mongodb://') and not uri.startswith('mongodb+srv://'):
    print("\n❌ ERROR: Invalid URI scheme")
    print(f"   Your URI starts with: {uri.split(':')[0]}")
    print("   Should start with: mongodb:// or mongodb+srv://")
    print("\n🔧 Fix:")
    print("   Make sure your .env has no extra spaces or characters before 'mongodb+srv://'")
    sys.exit(1)

print("   ✅ URI scheme is valid")

# Check for database name
if '/telegram_bot' not in uri and '?retryWrites' in uri:
    print("\n⚠️  WARNING: Database name might be missing")
    print("   URI should include: /telegram_bot before the ?")
else:
    print("   ✅ Database name included")

# Test pymongo
print("\n📦 Checking dependencies...")
try:
    import pymongo
    print(f"   ✅ pymongo version: {pymongo.__version__}")
except ImportError:
    print("   ❌ pymongo not installed")
    print("   Run: pip install 'pymongo[srv]'")
    sys.exit(1)

# Test dnspython
try:
    import dns.resolver
    print(f"   ✅ dnspython installed")
except ImportError:
    print("   ❌ dnspython not installed (REQUIRED for mongodb+srv://)")
    print("   Run: pip install dnspython")
    sys.exit(1)

# Test connection
print("\n🔌 Testing connection...")
print("   (This may take 5-10 seconds...)")

try:
    from pymongo import MongoClient
    from pymongo.errors import ServerSelectionTimeoutError, ConfigurationError, OperationFailure
    
    # Create client with timeout
    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    
    # Force connection
    info = client.server_info()
    
    print("\n✅ CONNECTION SUCCESSFUL!")
    print(f"   MongoDB version: {info.get('version', 'unknown')}")
    
    # List databases
    databases = client.list_database_names()
    print(f"\n📁 Available databases:")
    for db in databases:
        print(f"   - {db}")
    
    # Test telegram_bot database
    db = client['telegram_bot']
    print(f"\n💾 Testing 'telegram_bot' database...")
    
    # Test collections
    collections = db.list_collection_names()
    if collections:
        print(f"   Existing collections: {', '.join(collections)}")
    else:
        print(f"   No collections yet (will be created on first use)")
    
    # Test write operation
    print(f"\n📝 Testing write operation...")
    test_collection = db['_connection_test']
    from datetime import datetime
    result = test_collection.insert_one({
        'test': 'connection',
        'timestamp': datetime.now(),
        'version': 'v1.0'
    })
    print(f"   ✅ Write successful! (Document ID: {result.inserted_id})")
    
    # Test read operation
    doc = test_collection.find_one({'_id': result.inserted_id})
    if doc:
        print(f"   ✅ Read successful!")
    
    # Clean up
    test_collection.delete_one({'_id': result.inserted_id})
    print(f"   ✅ Cleanup successful!")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print("\n🚀 Your MongoDB connection is working perfectly!")
    print("\nYou can now run: python bot.py")
    print("=" * 60)
    
except ConfigurationError as e:
    print("\n❌ CONFIGURATION ERROR")
    print(f"   Error: {e}")
    print("\n🔧 Possible solutions:")
    print("   1. Check if dnspython is installed: pip install dnspython")
    print("   2. Verify URI format (must start with mongodb+srv:// for Atlas)")
    print("   3. Check for typos in connection string")
    sys.exit(1)
    
except ServerSelectionTimeoutError as e:
    print("\n❌ CONNECTION TIMEOUT")
    print("   Could not connect to MongoDB server")
    print("\n🔧 Troubleshooting steps:")
    print("   1. Check internet connection")
    print("   2. Verify MongoDB Atlas Network Access:")
    print("      → Go to https://cloud.mongodb.com")
    print("      → Network Access → Add IP Address")
    print("      → Select 'Allow Access from Anywhere' (0.0.0.0/0)")
    print("   3. Verify cluster is running (not paused)")
    print("   4. Check if firewall/VPN is blocking connection")
    print(f"\n   Error details: {str(e)[:200]}")
    sys.exit(1)
    
except OperationFailure as e:
    print("\n❌ AUTHENTICATION FAILED")
    print(f"   Error: {e}")
    print("\n🔧 Check:")
    print("   1. Username is correct: 'bot'")
    print("   2. Password is correct: 'botuser08'")
    print("   3. User exists in Database Access (MongoDB Atlas)")
    print("   4. User has proper permissions (Read and write to any database)")
    print("\n   To fix in MongoDB Atlas:")
    print("   → Database Access → Add New Database User")
    print("   → Username: bot")
    print("   → Password: botuser08")
    print("   → Database User Privileges: Atlas admin")
    sys.exit(1)
    
except Exception as e:
    print(f"\n❌ UNEXPECTED ERROR")
    print(f"   Error type: {type(e).__name__}")
    print(f"   Error message: {e}")
    print("\n🔧 Please check:")
    print("   1. Connection string format")
    print("   2. All dependencies installed")
    print("   3. Internet connection")
    print("   4. MongoDB Atlas status: https://status.mongodb.com/")
    sys.exit(1)