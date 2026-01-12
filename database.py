"""
MongoDB Database Module - BULK SESSION SYSTEM
Complete version with all functionality
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging
import config
from bson.objectid import ObjectId

logger = logging.getLogger(__name__)

# MongoDB Client
client = None
db = None

def init_db():
    """Initialize MongoDB connection with pooling"""
    global client, db
    
    try:
        mongodb_url = config.MONGODB_URL
        
        logger.info(f"🔗 Connecting to MongoDB...")
        
        client = MongoClient(
            mongodb_url,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=10000,
            maxPoolSize=50,
            minPoolSize=10,
            retryWrites=True,
            retryReads=True
        )
        
        client.admin.command('ping')
        db = client.telegram_bot
        
        logger.info("✅ MongoDB connected successfully")
        create_indexes()
        create_default_settings()
        return True
        
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        raise Exception(f"Cannot connect to MongoDB: {e}")

def get_db():
    """Get database instance"""
    global db
    if db is None:
        init_db()
    return db

def create_indexes():
    """Create database indexes for performance"""
    database = get_db()
    
    # Users indexes
    database.users.create_index([("telegram_id", ASCENDING)], unique=True)
    database.users.create_index([("username", ASCENDING)])
    database.users.create_index([("is_banned", ASCENDING)])
    
    # Bulk Sessions indexes
    database.bulk_sessions.create_index([("country_code", ASCENDING)])
    database.bulk_sessions.create_index([("session_type", ASCENDING)])
    database.bulk_sessions.create_index([("remaining_count", ASCENDING)])
    database.bulk_sessions.create_index([("created_at", DESCENDING)])
    
    # Purchases indexes
    database.purchases.create_index([("user_id", ASCENDING)])
    database.purchases.create_index([("purchased_at", DESCENDING)])
    database.purchases.create_index([("country_code", ASCENDING)])
    
    # Transactions indexes
    database.transactions.create_index([("user_id", ASCENDING)])
    database.transactions.create_index([("created_at", DESCENDING)])
    database.transactions.create_index([("status", ASCENDING)])
    database.transactions.create_index([("transaction_type", ASCENDING)])
    
    logger.info("✅ Database indexes created")

def create_default_settings():
    """Create default system settings"""
    database = get_db()
    
    if database.settings.count_documents({}) == 0:
        default_settings = {
            "min_deposit": 1.0,
            "maintenance_mode": False,
            "created_at": datetime.utcnow()
        }
        database.settings.insert_one(default_settings)
        logger.info("✅ Default settings created")

# ============================================
# USER MODEL
# ============================================

class User:
    """User operations - MongoDB compatible"""
    
    @staticmethod
    def create(telegram_id, username=None, first_name=None, last_name=None):
        """Create new user"""
        database = get_db()
        user_data = {
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "balance": 0.0,
            "language": "en",
            "is_banned": False,
            "is_admin": False,
            "created_at": datetime.utcnow(),
            "last_active": datetime.utcnow()
        }
        result = database.users.insert_one(user_data)
        logger.info(f"✅ User created: {telegram_id}")
        return result.inserted_id
    
    @staticmethod
    def get_by_telegram_id(telegram_id):
        """Get user by telegram ID"""
        database = get_db()
        return database.users.find_one({"telegram_id": telegram_id})
    
    @staticmethod
    def get_by_id(user_id):
        """Get user by ObjectId"""
        database = get_db()
        return database.users.find_one({"_id": ObjectId(user_id)})
    
    @staticmethod
    def get_by_username(username):
        """Get user by username"""
        database = get_db()
        return database.users.find_one({"username": username})
    
    @staticmethod
    def update_balance(telegram_id, amount, operation='add'):
        """Update user balance"""
        database = get_db()
        if operation == 'add':
            result = database.users.update_one(
                {"telegram_id": telegram_id},
                {"$inc": {"balance": amount}}
            )
        elif operation == 'subtract':
            result = database.users.update_one(
                {"telegram_id": telegram_id},
                {"$inc": {"balance": -amount}}
            )
        return result.modified_count > 0
    
    @staticmethod
    def set_balance(telegram_id, amount):
        """Set balance to specific amount"""
        database = get_db()
        result = database.users.update_one(
            {"telegram_id": telegram_id},
            {"$set": {"balance": amount}}
        )
        return result.modified_count > 0
    
    @staticmethod
    def update_language(telegram_id, language):
        """Update user language"""
        database = get_db()
        result = database.users.update_one(
            {"telegram_id": telegram_id},
            {"$set": {"language": language}}
        )
        return result.modified_count > 0
    
    @staticmethod
    def update_last_active(telegram_id):
        """Update last active timestamp"""
        database = get_db()
        result = database.users.update_one(
            {"telegram_id": telegram_id},
            {"$set": {"last_active": datetime.utcnow()}}
        )
        return result.modified_count > 0
    
    @staticmethod
    def ban_user(telegram_id):
        """Ban user"""
        database = get_db()
        result = database.users.update_one(
            {"telegram_id": telegram_id},
            {"$set": {"is_banned": True}}
        )
        logger.info(f"🚫 User banned: {telegram_id}")
        return result.modified_count > 0
    
    @staticmethod
    def unban_user(telegram_id):
        """Unban user"""
        database = get_db()
        result = database.users.update_one(
            {"telegram_id": telegram_id},
            {"$set": {"is_banned": False}}
        )
        logger.info(f"✅ User unbanned: {telegram_id}")
        return result.modified_count > 0
    
    @staticmethod
    def is_banned(telegram_id):
        """Check if user is banned"""
        user = User.get_by_telegram_id(telegram_id)
        return user.get('is_banned', False) if user else False
    
    @staticmethod
    def get_all_users(limit=100, skip=0):
        """Get all users with pagination"""
        database = get_db()
        return list(database.users.find().skip(skip).limit(limit).sort("created_at", DESCENDING))
    
    @staticmethod
    def count_users():
        """Count total users"""
        database = get_db()
        return database.users.count_documents({})
    
    @staticmethod
    def count_active_users():
        """Count active (non-banned) users"""
        database = get_db()
        return database.users.count_documents({"is_banned": False})
    
    @staticmethod
    def count_banned_users():
        """Count banned users"""
        database = get_db()
        return database.users.count_documents({"is_banned": True})
    
    @staticmethod
    def get_top_users_by_balance(limit=10):
        """Get top users by balance"""
        database = get_db()
        return list(database.users.find().sort("balance", DESCENDING).limit(limit))

# ============================================
# BULK SESSION MODEL - NEW SYSTEM
# ============================================

class BulkSession:
    """
    Bulk Session System
    One ZIP = Multiple sessions
    No phone numbers stored
    """
    
    @staticmethod
    def create(country_code, session_type, file_id, total_count, 
               price_per_session, uploader_id, info=None, has_2fa=False, two_fa_password=None):
        """
        Create bulk session
        
        Args:
            country_code: '+880', '+91', etc
            session_type: 'session' or 'tdata'
            file_id: Telegram file_id of ZIP
            total_count: Total sessions in ZIP (e.g., 50)
            price_per_session: Price per session
            uploader_id: Admin ID
            info: Optional description
            has_2fa: Whether sessions have 2FA
            two_fa_password: 2FA password if applicable
        """
        database = get_db()
        
        bulk_data = {
            "country_code": country_code,
            "session_type": session_type,
            "file_id": file_id,
            "total_count": total_count,
            "remaining_count": total_count,
            "price_per_session": price_per_session,
            "has_2fa": has_2fa,
            "two_fa_password": two_fa_password,
            "info": info,
            "uploader_id": uploader_id,
            "sold_indices": [],  # Track sold session indices
            "created_at": datetime.utcnow()
        }
        
        result = database.bulk_sessions.insert_one(bulk_data)
        logger.info(f"✅ Bulk created: {country_code} - {total_count} sessions - ${price_per_session}/each - 2FA: {has_2fa}")
        return result.inserted_id
    
    @staticmethod
    def get_by_country(country_code):
        """Get available bulks for country"""
        database = get_db()
        return list(database.bulk_sessions.find({
            "country_code": country_code,
            "remaining_count": {"$gt": 0}
        }).sort("price_per_session", ASCENDING))
    
    @staticmethod
    def get_available_countries():
        """Get all countries with available sessions"""
        database = get_db()
        pipeline = [
            {"$match": {"remaining_count": {"$gt": 0}}},
            {"$group": {
                "_id": "$country_code",
                "total_available": {"$sum": "$remaining_count"},
                "min_price": {"$min": "$price_per_session"},
                "session_types": {"$addToSet": "$session_type"}
            }},
            {"$sort": {"_id": 1}}
        ]
        return list(database.bulk_sessions.aggregate(pipeline))
    
    @staticmethod
    def purchase_sessions(bulk_id, quantity):
        """
        Purchase N sessions from bulk
        Returns indices of purchased sessions
        """
        database = get_db()
        
        bulk = database.bulk_sessions.find_one({"_id": ObjectId(bulk_id)})
        if not bulk:
            return None, "Bulk session not found"
        
        if bulk['remaining_count'] < quantity:
            return None, f"Only {bulk['remaining_count']} available"
        
        # Get next available indices
        sold = bulk['sold_indices']
        total = bulk['total_count']
        available = [i for i in range(total) if i not in sold]
        
        if len(available) < quantity:
            return None, "Index error"
        
        # Take first N
        purchased = available[:quantity]
        new_sold = sold + purchased
        new_remaining = total - len(new_sold)
        
        result = database.bulk_sessions.update_one(
            {"_id": ObjectId(bulk_id)},
            {
                "$set": {
                    "sold_indices": new_sold,
                    "remaining_count": new_remaining
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"✅ Purchased {quantity} sessions from bulk {bulk_id}")
            return purchased, None
        return None, "Update failed"
    
    @staticmethod
    def get_by_id(bulk_id):
        """Get bulk by ID"""
        database = get_db()
        return database.bulk_sessions.find_one({"_id": ObjectId(bulk_id)})
    
    @staticmethod
    def delete_bulk(bulk_id):
        """Delete bulk"""
        database = get_db()
        result = database.bulk_sessions.delete_one({"_id": ObjectId(bulk_id)})
        if result.deleted_count > 0:
            logger.info(f"🗑️ Bulk deleted: {bulk_id}")
        return result.deleted_count > 0
    
    @staticmethod
    def get_all_bulks(limit=50):
        """Get all bulks for admin"""
        database = get_db()
        return list(database.bulk_sessions.find().limit(limit).sort("created_at", DESCENDING))
    
    @staticmethod
    def count_by_country(country_code):
        """Count available sessions in country"""
        database = get_db()
        pipeline = [
            {
                "$match": {
                    "country_code": country_code,
                    "remaining_count": {"$gt": 0}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": "$remaining_count"}
                }
            }
        ]
        result = list(database.bulk_sessions.aggregate(pipeline))
        return result[0]['total'] if result else 0
    
    @staticmethod
    def get_min_price_by_country(country_code):
        """Get minimum price in country"""
        database = get_db()
        bulk = database.bulk_sessions.find_one(
            {"country_code": country_code, "remaining_count": {"$gt": 0}},
            sort=[("price_per_session", ASCENDING)]
        )
        return bulk['price_per_session'] if bulk else 0.0
    
    @staticmethod
    def count_total_sessions():
        """Count total available sessions across all bulks"""
        database = get_db()
        pipeline = [
            {"$match": {"remaining_count": {"$gt": 0}}},
            {"$group": {"_id": None, "total": {"$sum": "$remaining_count"}}}
        ]
        result = list(database.bulk_sessions.aggregate(pipeline))
        return result[0]['total'] if result else 0
    
    @staticmethod
    def count_sold_sessions():
        """Count total sold sessions"""
        database = get_db()
        pipeline = [
            {"$project": {"sold_count": {"$size": "$sold_indices"}}},
            {"$group": {"_id": None, "total": {"$sum": "$sold_count"}}}
        ]
        result = list(database.bulk_sessions.aggregate(pipeline))
        return result[0]['total'] if result else 0

# ============================================
# PURCHASE MODEL
# ============================================

class Purchase:
    """Purchase records"""
    
    @staticmethod
    def create(user_id, bulk_id, country_code, quantity, price_paid, 
               session_type, purchased_indices, zip_file_id=None):
        """
        Create purchase
        
        Args:
            user_id: Buyer telegram ID
            bulk_id: Source bulk ID
            country_code: Country
            quantity: Number purchased
            price_paid: Total paid
            session_type: 'session' or 'tdata'
            purchased_indices: List of indices
            zip_file_id: Generated ZIP file_id
        """
        database = get_db()
        
        purchase_data = {
            "user_id": user_id,
            "bulk_id": str(bulk_id),
            "country_code": country_code,
            "quantity": quantity,
            "price_paid": price_paid,
            "session_type": session_type,
            "purchased_indices": purchased_indices,
            "zip_file_id": zip_file_id,
            "purchased_at": datetime.utcnow()
        }
        
        result = database.purchases.insert_one(purchase_data)
        logger.info(f"✅ Purchase: User {user_id} bought {quantity}x {country_code}")
        return result.inserted_id
    
    @staticmethod
    def get_by_user(user_id, limit=20):
        """Get user purchases"""
        database = get_db()
        return list(database.purchases.find({"user_id": user_id}).limit(limit).sort("purchased_at", DESCENDING))
    
    @staticmethod
    def count_by_user(user_id):
        """Count user purchases"""
        database = get_db()
        return database.purchases.count_documents({"user_id": user_id})
    
    @staticmethod
    def get_by_id(purchase_id):
        """Get purchase by ID"""
        database = get_db()
        return database.purchases.find_one({"_id": ObjectId(purchase_id)})
    
    @staticmethod
    def get_all_purchases(limit=50):
        """Get all purchases for admin"""
        database = get_db()
        return list(database.purchases.find().limit(limit).sort("purchased_at", DESCENDING))
    
    @staticmethod
    def count_total_purchases():
        """Count total purchases"""
        database = get_db()
        return database.purchases.count_documents({})
    
    @staticmethod
    def get_total_revenue():
        """Calculate total revenue"""
        database = get_db()
        pipeline = [
            {"$group": {"_id": None, "total": {"$sum": "$price_paid"}}}
        ]
        result = list(database.purchases.aggregate(pipeline))
        return result[0]['total'] if result else 0.0

# ============================================
# TRANSACTION MODEL
# ============================================

class Transaction:
    """Transaction operations"""
    
    @staticmethod
    def create(user_id, amount, payment_method, transaction_type='deposit'):
        """Create transaction"""
        database = get_db()
        transaction_data = {
            "user_id": user_id,
            "amount": amount,
            "payment_method": payment_method,
            "transaction_type": transaction_type,
            "status": "pending",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        result = database.transactions.insert_one(transaction_data)
        logger.info(f"💳 Transaction created: {transaction_type} - ${amount:.2f} - User {user_id}")
        return result.inserted_id
    
    @staticmethod
    def update_status(transaction_id, status):
        """Update status"""
        database = get_db()
        result = database.transactions.update_one(
            {"_id": ObjectId(transaction_id)},
            {
                "$set": {
                    "status": status,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        if result.modified_count > 0:
            logger.info(f"✅ Transaction {transaction_id} status: {status}")
        return result.modified_count > 0
    
    @staticmethod
    def get_by_id(transaction_id):
        """Get transaction"""
        database = get_db()
        return database.transactions.find_one({"_id": ObjectId(transaction_id)})
    
    @staticmethod
    def get_by_user(user_id, limit=20):
        """Get user transactions"""
        database = get_db()
        return list(database.transactions.find({"user_id": user_id}).limit(limit).sort("created_at", DESCENDING))
    
    @staticmethod
    def get_all_transactions(limit=50):
        """Get all transactions"""
        database = get_db()
        return list(database.transactions.find().limit(limit).sort("created_at", DESCENDING))
    
    @staticmethod
    def count_by_status(status):
        """Count transactions by status"""
        database = get_db()
        return database.transactions.count_documents({"status": status})
    
    @staticmethod
    def count_pending():
        """Count pending transactions"""
        return Transaction.count_by_status("pending")
    
    @staticmethod
    def count_completed():
        """Count completed transactions"""
        return Transaction.count_by_status("completed")
    
    @staticmethod
    def get_total_deposits():
        """Get total completed deposits"""
        database = get_db()
        pipeline = [
            {
                "$match": {
                    "transaction_type": "deposit",
                    "status": "completed"
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total": {"$sum": "$amount"}
                }
            }
        ]
        result = list(database.transactions.aggregate(pipeline))
        return result[0]['total'] if result else 0.0

# ============================================
# SYSTEM SETTINGS
# ============================================

class SystemSettings:
    """System settings"""
    
    @staticmethod
    def get():
        """Get settings"""
        database = get_db()
        settings = database.settings.find_one()
        if not settings:
            create_default_settings()
            settings = database.settings.find_one()
        return settings
    
    @staticmethod
    def update_min_deposit(amount):
        """Update min deposit"""
        database = get_db()
        result = database.settings.update_one(
            {},
            {"$set": {"min_deposit": amount}},
            upsert=True
        )
        logger.info(f"⚙️ Min deposit updated: ${amount:.2f}")
        return result.modified_count > 0 or result.upserted_id is not None
    
    @staticmethod
    def set_maintenance(enabled):
        """Set maintenance"""
        database = get_db()
        result = database.settings.update_one(
            {},
            {"$set": {"maintenance_mode": enabled}},
            upsert=True
        )
        logger.info(f"⚙️ Maintenance mode: {'ON' if enabled else 'OFF'}")
        return result.modified_count > 0 or result.upserted_id is not None
    
    @staticmethod
    def is_maintenance():
        """Check if in maintenance mode"""
        settings = SystemSettings.get()
        return settings.get('maintenance_mode', False)
    
    @staticmethod
    def get_min_deposit():
        """Get minimum deposit amount"""
        settings = SystemSettings.get()
        return settings.get('min_deposit', 1.0)