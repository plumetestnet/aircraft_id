import logging
import os
import random
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler, CallbackQueryHandler, MessageHandler,
    filters, ConversationHandler, ContextTypes
)
from database import User, BulkSession, Transaction, SystemSettings, Purchase
from zip_utils import validate_bulk_zip
import config

logger = logging.getLogger(__name__)

# Conversation states - FIXED: Added DELETE_SESSION_ID
(UPLOAD_BULK, BULK_COUNTRY, BULK_PRICE, BULK_2FA, BULK_INFO,
 ADD_BALANCE_USER, ADD_BALANCE_AMOUNT, REMOVE_BALANCE_USER, REMOVE_BALANCE_AMOUNT,
 BAN_USER_ID, UNBAN_USER_ID, DELETE_BULK_ID, DELETE_SESSION_ID, BROADCAST_MESSAGE,
 SET_MIN_DEPOSIT) = range(15)  # ✅ Changed from 14 to 15

# ============================================
# PAGINATION HELPER
# ============================================

def paginate_list(items, page=0, per_page=10):
    """Paginate a list"""
    total = len(items)
    total_pages = max(1, (total + per_page - 1) // per_page)
    current_page = max(0, min(page, total_pages - 1))
    start = current_page * per_page
    end = start + per_page
    return items[start:end], total_pages, current_page

def admin_only(func):
    """Decorator to restrict commands to admins only (supports multiple admins)"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        # Check if user is owner or in admin list
        if user_id not in config.ALL_ADMINS:
            await update.message.reply_text("❌ You don't have permission to use this command.")
            logger.warning(f"⚠️ Unauthorized admin access attempt by user {user_id}")
            return
        
        logger.info(f"✅ Admin command executed by user {user_id}")
        return await func(update, context)
    return wrapper

# ✅ NEW: Helper function to check if user is admin
def is_admin(user_id: int) -> bool:
    """Check if user is an admin"""
    return user_id in config.ALL_ADMINS

# ✅ NEW: Helper function to check if user is owner
def is_owner(user_id: int) -> bool:
    """Check if user is the main owner"""
    return user_id == config.OWNER_ID

@admin_only
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel with bulk upload option"""
    keyboard = [
        [
            InlineKeyboardButton("📦 Upload Bulk", callback_data='admin_upload_bulk'),
            InlineKeyboardButton("📊 Statistics", callback_data='admin_stats')
        ],
        [
            InlineKeyboardButton("💰 Add Balance", callback_data='admin_add_balance'),
            InlineKeyboardButton("💸 Remove Balance", callback_data='admin_remove_balance')
        ],
        [
            InlineKeyboardButton("👥 Users", callback_data='admin_users'),
            InlineKeyboardButton("📦 Inventory", callback_data='admin_inventory')
        ],
        [
            InlineKeyboardButton("💳 Transactions", callback_data='admin_transactions'),
            InlineKeyboardButton("💰 Payments", callback_data='admin_payments_menu')  # ✅ NEW SUBMENU
        ],
        [
            InlineKeyboardButton("🗑️ Delete Bulk", callback_data='admin_delete_bulk'),
            InlineKeyboardButton("🚫 Ban User", callback_data='admin_ban')
        ],
        [
            InlineKeyboardButton("✅ Unban User", callback_data='admin_unban'),
            InlineKeyboardButton("📢 Broadcast", callback_data='admin_broadcast')
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data='admin_settings')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "👨‍💼 Admin Panel\n\nSelect an option:"
    
    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

# ============================================
# BULK UPLOAD HANDLERS - NEW
# ============================================

async def admin_upload_bulk_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start bulk upload"""
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text(
        "📦 **Upload Bulk Sessions**\n\n"
        "Send a ZIP file containing:\n"
        "• `.session` files (for Telethon)\n"
        "• OR `tdata` folders (for Telegram Desktop)\n\n"
        "⚠️ Max file size: 50MB\n"
        "⚠️ Max sessions per bulk: 1000\n\n"
        "Send /cancel to abort.",
        parse_mode='Markdown'
    )
    
    return UPLOAD_BULK

async def receive_bulk_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and validate bulk ZIP"""
    document = update.message.document
    filename = document.file_name
    
    # Check extension
    if not filename.endswith('.zip'):
        await update.message.reply_text(
            "❌ Invalid file type!\n\n"
            "Please send a .zip file"
        )
        return UPLOAD_BULK
    
    # Check size
    if document.file_size > 50 * 1024 * 1024:
        await update.message.reply_text(
            "❌ File too large!\n\n"
            f"Size: {document.file_size / 1024 / 1024:.1f} MB\n"
            f"Max: 50 MB"
        )
        return UPLOAD_BULK
    
    file = await document.get_file()
    
    # Validate ZIP
    await update.message.reply_text("⏳ Validating ZIP file...")
    
    session_type, count, error = await validate_bulk_zip(context.bot, file.file_id)
    
    if error:
        await update.message.reply_text(
            f"❌ Validation failed!\n\n"
            f"Error: {error}\n\n"
            f"Make sure ZIP contains:\n"
            f"• `.session` files\n"
            f"• OR `tdata` folders"
        )
        return UPLOAD_BULK
    
    # Upload to storage channel
    try:
        storage_msg = await context.bot.send_document(
            chat_id=config.STORAGE_GROUP_ID,
            document=file.file_id,
            caption=f"📦 Bulk upload: {filename}\nUploader: {update.effective_user.id}\nType: {session_type}\nCount: {count}"
        )
        storage_file_id = storage_msg.document.file_id
    except Exception as e:
        await update.message.reply_text(
            f"❌ Upload to storage failed!\n\n"
            f"Error: {e}\n\n"
            f"Make sure bot is admin in storage channel."
        )
        return UPLOAD_BULK
    
    # Store in context
    context.user_data['bulk_file_id'] = storage_file_id
    context.user_data['bulk_session_type'] = session_type
    context.user_data['bulk_count'] = count
    context.user_data['bulk_filename'] = filename
    
    await update.message.reply_text(
        f"✅ ZIP validated!\n\n"
        f"📦 Type: **{session_type.upper()}**\n"
        f"📊 Count: **{count} sessions**\n"
        f"📁 File: {filename}\n\n"
        f"Enter country code:\n"
        f"Examples: +880, +91, +1",
        parse_mode='Markdown'
    )
    
    return BULK_COUNTRY

async def receive_bulk_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive country code for bulk"""
    country = update.message.text.strip()
    
    # Validate country
    from country_utils import get_country_info
    info = get_country_info(country)
    
    if not info:
        await update.message.reply_text(
            "❌ Unknown country code!\n\n"
            "Enter a valid code:\n"
            "Examples: +880, +91, +1, +44"
        )
        return BULK_COUNTRY
    
    context.user_data['bulk_country'] = country
    context.user_data['bulk_country_name'] = info['name']
    context.user_data['bulk_continent'] = info['continent']
    
    await update.message.reply_text(
        f"✅ Country: **{info['name']}** ({country})\n"
        f"🌍 Continent: {info['continent']}\n\n"
        f"Enter price per session:\n"
        f"Examples: 0.10, 0.50, 1.00",
        parse_mode='Markdown'
    )
    
    return BULK_PRICE

async def receive_bulk_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive price per session"""
    try:
        price = float(update.message.text.strip())
        
        if price <= 0:
            await update.message.reply_text("❌ Price must be greater than 0")
            return BULK_PRICE
        
        if price > 100:
            await update.message.reply_text("❌ Price too high! Max $100 per session")
            return BULK_PRICE
        
        context.user_data['bulk_price'] = price
        
        count = context.user_data['bulk_count']
        total_value = price * count
        
        await update.message.reply_text(
            f"💰 **Price Summary**\n\n"
            f"Per session: ${price:.2f}\n"
            f"Total sessions: {count}\n"
            f"Total value: **${total_value:.2f}**\n\n"
            f"🔒 Enter 2FA password (or type 'no' if no 2FA):",
            parse_mode='Markdown'
        )
        
        return BULK_INFO
        
    except ValueError:
        await update.message.reply_text("❌ Invalid price! Enter a number (e.g., 0.10)")
        return BULK_PRICE

async def receive_bulk_2fa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive 2FA password"""
    password = update.message.text.strip()
    
    if password.lower() in ['no', 'none', 'skip']:
        context.user_data['bulk_2fa'] = None
        has_2fa = False
    else:
        context.user_data['bulk_2fa'] = password
        has_2fa = True
    
    await update.message.reply_text(
        f"🔒 2FA: {'Yes - `' + password + '`' if has_2fa else 'No'}\n\n"
        f"Enter description (or type 'skip'):",
        parse_mode='Markdown'
    )
    
    return BULK_INFO

async def receive_bulk_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save bulk session to database"""
    info = update.message.text.strip()
    if info.lower() == 'skip':
        info = None
    
    # Create bulk session
    try:
        bulk_id = BulkSession.create(
            country_code=context.user_data['bulk_country'],
            session_type=context.user_data['bulk_session_type'],
            file_id=context.user_data['bulk_file_id'],
            total_count=context.user_data['bulk_count'],
            price_per_session=context.user_data['bulk_price'],
            uploader_id=update.effective_user.id,
            info=info,
            has_2fa=context.user_data.get('bulk_2fa') is not None,
            two_fa_password=context.user_data.get('bulk_2fa')
        )
        
        total_value = context.user_data['bulk_price'] * context.user_data['bulk_count']
        
        await update.message.reply_text(
            "✅ **Bulk Sessions Uploaded!**\n\n"
            f"📍 Country: {context.user_data['bulk_country_name']} ({context.user_data['bulk_country']})\n"
            f"🌍 Continent: {context.user_data['bulk_continent']}\n"
            f"📦 Type: {context.user_data['bulk_session_type'].upper()}\n"
            f"📊 Quantity: {context.user_data['bulk_count']} sessions\n"
            f"💰 Price: ${context.user_data['bulk_price']:.2f}/session\n"
            f"💵 Total value: ${total_value:.2f}\n"
            f"ℹ️ Info: {info or 'None'}\n\n"
            f"🆔 Bulk ID: `{bulk_id}`",
            parse_mode='Markdown'
        )
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error creating bulk: {e}")
        import traceback
        traceback.print_exc()
        
        await update.message.reply_text(
            f"❌ Error saving bulk!\n\n"
            f"Error: {str(e)}\n\n"
            f"Please try again or contact developer."
        )
        return ConversationHandler.END

async def admin_view_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View bulk inventory"""
    query = update.callback_query
    await query.answer()
    
    bulks = BulkSession.get_all_bulks(limit=20)
    
    if not bulks:
        await query.message.edit_text(
            "📦 Inventory\n\n"
            "No bulk sessions available.\n\n"
            "Upload bulk sessions to get started!"
        )
        return
    
    from country_utils import get_country_info
    
    text = "📦 **Bulk Inventory**\n\n"
    
    for i, bulk in enumerate(bulks, 1):
        info_obj = get_country_info(bulk['country_code'])
        country_name = info_obj['name'] if info_obj else bulk['country_code']
        
        remaining = bulk['remaining_count']
        total = bulk['total_count']
        percentage = (remaining / total * 100) if total > 0 else 0
        
        text += (
            f"{i}. **{country_name}** ({bulk['country_code']})\n"
            f"   📊 {remaining}/{total} available ({percentage:.0f}%)\n"
            f"   💰 ${bulk['price_per_session']:.2f}/session\n"
            f"   📁 {bulk['session_type'].upper()}\n"
            f"   🆔 `{bulk['_id']}`\n\n"
        )
    
    # Summary
    total_available = BulkSession.count_total_sessions()
    total_sold = BulkSession.count_sold_sessions()
    
    text += f"\n📊 **Summary**\n"
    text += f"Available: {total_available}\n"
    text += f"Sold: {total_sold}\n"
    text += f"Total: {total_available + total_sold}"
    
    keyboard = [[InlineKeyboardButton("« Back", callback_data='admin_panel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_delete_bulk_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start delete bulk"""
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text(
        "🗑️ **Delete Bulk**\n\n"
        "Enter bulk ID to delete:\n"
        "(Get ID from Inventory)\n\n"
        "Send /cancel to abort."
    )
    
    return DELETE_BULK_ID

async def receive_delete_bulk_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete bulk by ID"""
    bulk_id = update.message.text.strip()
    
    try:
        bulk = BulkSession.get_by_id(bulk_id)
        
        if not bulk:
            await update.message.reply_text("❌ Bulk not found!")
            return ConversationHandler.END
        
        from country_utils import get_country_info
        info = get_country_info(bulk['country_code'])
        country_name = info['name'] if info else bulk['country_code']
        
        # Delete
        if BulkSession.delete_bulk(bulk_id):
            await update.message.reply_text(
                f"✅ Bulk deleted!\n\n"
                f"Country: {country_name}\n"
                f"Remaining: {bulk['remaining_count']}/{bulk['total_count']}"
            )
        else:
            await update.message.reply_text("❌ Delete failed!")
        
        return ConversationHandler.END
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        return ConversationHandler.END

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show statistics"""
    query = update.callback_query
    await query.answer()
    
    # Users
    total_users = User.count_users()
    active_users = User.count_active_users()
    banned_users = User.count_banned_users()
    
    # Sessions (✅ UPDATED)
    available_sessions = BulkSession.count_total_sessions()
    sold_sessions = BulkSession.count_sold_sessions()
    
    # Purchases (✅ NEW)
    total_purchases = Purchase.count_total_purchases()
    total_revenue = Purchase.get_total_revenue()
    
    # Transactions
    pending_tx = Transaction.count_pending()
    completed_tx = Transaction.count_completed()
    total_deposits = Transaction.get_total_deposits()
    
    text = (
        "📊 **Bot Statistics**\n\n"
        
        "👥 **Users**\n"
        f"Total: {total_users}\n"
        f"Active: {active_users}\n"
        f"Banned: {banned_users}\n\n"
        
        "📦 **Sessions**\n"
        f"Available: {available_sessions}\n"
        f"Sold: {sold_sessions}\n"
        f"Total: {available_sessions + sold_sessions}\n\n"
        
        "💰 **Revenue**\n"
        f"Total: ${total_revenue:.2f}\n"
        f"Purchases: {total_purchases}\n"
        f"Deposits: ${total_deposits:.2f}\n\n"
        
        "💳 **Transactions**\n"
        f"Pending: {pending_tx}\n"
        f"Completed: {completed_tx}\n"
    )
    
    keyboard = [[InlineKeyboardButton("« Back", callback_data='admin_panel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show users list with pagination"""
    query = update.callback_query
    await query.answer()
    
    # Get page from callback data
    page = 0
    if query.data and '_' in query.data:
        parts = query.data.split('_')
        if len(parts) >= 3 and parts[-1].isdigit():
            page = int(parts[-1])
    
    all_users = User.get_all_users(limit=1000)
    paginated_users, total_pages, current_page = paginate_list(all_users, page, per_page=10)
    
    if not paginated_users:
        text = "👥 No users found!"
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data='admin_panel')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(text, reply_markup=reply_markup)
        return
    
    text = f"👥 Users List (Page {current_page + 1}/{total_pages})\n\n"
    
    for i, user in enumerate(paginated_users, start=current_page * 10 + 1):
        banned_status = "🚫 " if user.get('is_banned', False) else ""
        username = user.get('username', 'N/A')
        if username != 'N/A':
            username = f"@{username}"
        
        text += (
            f"{i}. {banned_status}ID: {user['telegram_id']}\n"
            f"   User: {username}\n"
            f"   Balance: ${user.get('balance', 0):.2f}\n"
            f"   Joined: {user['created_at'].strftime('%Y-%m-%d')}\n\n"
        )
    
    # Pagination buttons
    buttons = []
    nav_buttons = []
    
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f'admin_users_{current_page - 1}'))
    
    nav_buttons.append(InlineKeyboardButton(f"📄 {current_page + 1}/{total_pages}", callback_data='noop'))
    
    if current_page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f'admin_users_{current_page + 1}'))
    
    buttons.append(nav_buttons)
    buttons.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data='admin_panel')])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    await query.message.edit_text(text, reply_markup=reply_markup)

async def admin_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show sessions list"""
    query = update.callback_query
    await query.answer()
    
    from database import get_db
    db = get_db()
    sessions = list(db.sessions.find().sort("created_at", -1).limit(20))
    
    text = "📦 Sessions List (Latest 20)\n\n"
    for session in sessions:
        status = "✅ Sold" if session.get('is_sold') else "📦 Available"
        text += (
            f"Country: {session['country']}\n"
            f"Phone: {session.get('phone_number', 'N/A')}\n"
            f"Price: ${session.get('price', 0):.2f}\n"
            f"Status: {status}\n"
            f"Info: {session.get('info', 'N/A')[:30]}\n\n"
        )
    
    keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data='admin_panel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(text, reply_markup=reply_markup)

async def admin_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show transactions list with pagination"""
    query = update.callback_query
    await query.answer()
    
    # Get page from callback data
    page = 0
    if query.data and '_' in query.data:
        parts = query.data.split('_')
        if len(parts) >= 3 and parts[-1].isdigit():
            page = int(parts[-1])
    
    all_txs = Transaction.get_all_transactions(limit=1000)
    paginated_txs, total_pages, current_page = paginate_list(all_txs, page, per_page=10)
    
    if not paginated_txs:
        text = "💳 No transactions found!"
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data='admin_panel')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(text, reply_markup=reply_markup)
        return
    
    text = f"💳 Transactions (Page {current_page + 1}/{total_pages})\n\n"
    
    for i, txn in enumerate(paginated_txs, start=current_page * 10 + 1):
        status_emoji = "✅" if txn['status'] == 'completed' else "⏳" if txn['status'] == 'pending' else "❌"
        
        text += (
            f"{i}. {status_emoji} User: {txn['user_id']}\n"
            f"   Amount: ${txn['amount']:.2f}\n"
            f"   Type: {txn.get('transaction_type', 'N/A')}\n"
            f"   Status: {txn['status']}\n"
            f"   Date: {txn['created_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
        )
    
    # Pagination buttons
    buttons = []
    nav_buttons = []
    
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f'admin_transactions_{current_page - 1}'))
    
    nav_buttons.append(InlineKeyboardButton(f"📄 {current_page + 1}/{total_pages}", callback_data='noop'))
    
    if current_page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f'admin_transactions_{current_page + 1}'))
    
    buttons.append(nav_buttons)
    buttons.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data='admin_panel')])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    await query.message.edit_text(text, reply_markup=reply_markup)

async def admin_upload_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start session upload"""
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text(
        "📤 Upload Session\n\n"
        "Send your .session file\n"
        "(Telethon string session format)\n\n"
        "Send /cancel to abort."
    )
    
    return UPLOAD_SESSION

async def receive_session_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """✅ IMPROVED - Accept both .session and .zip files"""
    document = update.message.document
    filename = document.file_name
    
    # Accept both .session and .zip files
    if not (filename.endswith('.session') or filename.endswith('.zip')):
        await update.message.reply_text(
            "❌ Invalid file type!\n\n"
            "Please send a .session or .zip file\n\n"
            "Send file or /cancel"
        )
        return UPLOAD_SESSION
    
    # Check file size (max 10MB for sessions/zips)
    if document.file_size > 10 * 1024 * 1024:
        await update.message.reply_text(
            "❌ File too large!\n\n"
            "Maximum file size: 10 MB"
        )
        return UPLOAD_SESSION
    
    # Get file reference
    file = await document.get_file()
    
    try:
        # ✅ Upload to storage group and get file_id
        storage_file_id = None
        try:
            storage_msg = await context.bot.send_document(
                chat_id=config.STORAGE_GROUP_ID,
                document=file.file_id,
                caption=f"📤 Session Upload\nFilename: {filename}\nUploader: {update.effective_user.id}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            # Store the file_id from storage channel for later re-sending
            storage_file_id = storage_msg.document.file_id
            context.user_data['storage_file_id'] = storage_file_id
            context.user_data['session_filename'] = filename
            logger.info(f"✅ Session file backed up to storage group (file_id: {storage_file_id[:20]}...)")
        except Exception as e:
            logger.warning(f"Could not backup to storage group: {e}")
            await update.message.reply_text(
                "❌ Could not backup file to storage!\n\n"
                "Please make sure bot is admin in storage channel."
            )
            return UPLOAD_SESSION
        
        # ✅ Try to extract phone from filename
        phone_match = re.search(r'\+?\d{10,15}', filename)
        if phone_match:
            phone = phone_match.group(0)
            if not phone.startswith('+'):
                phone = '+' + phone
            
            from country_utils import detect_country_from_phone
            country_info = detect_country_from_phone(phone)
            
            if country_info:
                context.user_data['phone_number'] = phone
                context.user_data['country_code'] = country_info['country_code']
                context.user_data['country_name'] = country_info['country_name']
                context.user_data['continent'] = country_info['continent']
                
                logger.info(f"✅ Auto-detected from filename: {phone} → {country_info['country_name']}")
                
                await update.message.reply_text(
                    f"✅ Session file received!\n\n"
                    f"📱 Phone: {phone}\n"
                    f"🌍 Country: {country_info['country_name']} ({country_info['country_code']})\n"
                    f"🌏 Continent: {country_info['continent']}\n\n"
                    f"💰 Enter price in USD:"
                )
                
                return GET_PRICE
        
        # Could not auto-detect from filename, ask admin
        await update.message.reply_text(
            "✅ Session file received!\n\n"
            "📱 Enter phone number (e.g., +8801918255655):"
        )
        
        return GET_COUNTRY
        
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        import traceback
        traceback.print_exc()
        
        await update.message.reply_text(
            f"❌ Error processing file: {str(e)}\n\n"
            "Please try again or /cancel"
        )
        return UPLOAD_SESSION

async def receive_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """✅ IMPROVED - Receive phone number, auto-detect country"""
    phone = update.message.text.strip()
    
    # Try to detect country from phone number
    from country_utils import detect_country_from_phone
    country_info = detect_country_from_phone(phone)
    
    if country_info:
        # Successfully detected
        context.user_data['phone_number'] = phone
        context.user_data['country_code'] = country_info['country_code']
        context.user_data['country_name'] = country_info['country_name']
        context.user_data['continent'] = country_info['continent']
        
        await update.message.reply_text(
            f"✅ Phone: {phone}\n"
            f"🌍 Country: {country_info['country_name']} ({country_info['country_code']})\n"
            f"🌏 Continent: {country_info['continent']}\n\n"
            f"💰 Enter price in USD:"
        )
        
        return GET_PRICE
    else:
        # Could not detect
        await update.message.reply_text(
            "❌ Invalid phone number or unknown country code!\n\n"
            "Please enter a valid phone number with country code\n"
            "Example: +8801918255655, +919876543210\n\n"
            "Enter phone number:"
        )
        return GET_COUNTRY

async def receive_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive price"""
    try:
        price = float(update.message.text.strip())
        if price <= 0:
            await update.message.reply_text("❌ Price must be greater than 0:")
            return GET_PRICE
            
        context.user_data['price'] = price
        
        await update.message.reply_text(
            f"Price: ${price:.2f}\n\n"
            "Enter 2FA password (or 'none' if no 2FA):"
        )
        
        return GET_PASSWORD
    except ValueError:
        await update.message.reply_text("❌ Invalid price. Please enter a valid number:")
        return GET_PRICE

async def receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive 2FA password"""
    password = update.message.text.strip()
    has_2fa = True
    
    if password.lower() in ['none', 'no', 'n/a', 'skip']:
        password = None
        has_2fa = False
    
    context.user_data['password_2fa'] = password
    context.user_data['has_2fa'] = has_2fa
    
    await update.message.reply_text(
        "Enter session info/description (or 'skip'):"
    )
    
    return GET_INFO

async def receive_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """✅ IMPROVED - Create session with file_id only"""
    info = update.message.text.strip()
    if info.lower() == 'skip':
        info = None
    
    # Get phone and country
    phone = context.user_data.get('phone_number', 'Unknown')
    country = context.user_data.get('country_code') or context.user_data.get('country', 'Unknown')
    
    try:
        # Create session in database (NO session_string, just file_id)
        from bson.objectid import ObjectId
        session_id = TelegramSession.create(
            session_string="SESSION_FILE",  # ✅ Placeholder - actual file stored via file_id
            phone_number=phone,
            country=country,
            has_2fa=context.user_data.get('has_2fa', False),
            two_fa_password=context.user_data.get('password_2fa'),
            price=context.user_data['price'],
            info=info,
            uploader_id=update.effective_user.id,
            file_id=context.user_data.get('storage_file_id'),  # ✅ Store file_id
            session_type='session'  # ✅ Type is 'session'
        )
        
        # ✅ Get country name for display
        country_name = context.user_data.get('country_name', country)
        continent = context.user_data.get('continent', 'Unknown')
        
        await update.message.reply_text(
            "✅ Session uploaded successfully!\n\n"
            f"🌍 Country: {country_name} ({country})\n"
            f"🌏 Continent: {continent}\n"
            f"📱 Phone: {phone}\n"
            f"💰 Price: ${context.user_data['price']:.2f}\n"
            f"2FA: {'Yes' if context.user_data.get('has_2fa') else 'No'}\n"
            f"Info: {info or 'None'}"
        )
        
        # Clear user data
        context.user_data.clear()
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        await update.message.reply_text(
            f"❌ Error saving session: {str(e)}\n\n"
            "Please try again or contact support."
        )
        return ConversationHandler.END

# ============================================
# TDATA UPLOAD HANDLERS
# ============================================

async def admin_upload_tdata_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """✅ NEW - Start TData upload"""
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text(
        "📁 Upload TData\n\n"
        "Send your .zip file containing TData\n"
        "(Desktop Telegram tdata folder)\n\n"
        "Send /cancel to abort."
    )
    
    return UPLOAD_TDATA

async def receive_tdata_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """✅ NEW - Receive TData zip file"""
    document = update.message.document
    filename = document.file_name
    
    # Only accept .zip files
    if not filename.endswith('.zip'):
        await update.message.reply_text(
            "❌ Invalid file type!\n\n"
            "Please send a .zip file containing TData\n\n"
            "Send file or /cancel"
        )
        return UPLOAD_TDATA
    
    # Check file size (max 50MB for TData)
    if document.file_size > 50 * 1024 * 1024:
        await update.message.reply_text(
            "❌ File too large!\n\n"
            "Maximum file size: 50 MB"
        )
        return UPLOAD_TDATA
    
    # Download file
    file = await document.get_file()
    file_path = f"/tmp/{filename}"
    
    try:
        await file.download_to_drive(file_path)
        
        # Basic validation - check if it's a valid zip
        import zipfile
        if not zipfile.is_zipfile(file_path):
            await update.message.reply_text(
                "❌ Invalid ZIP file!\n\n"
                "Please send a valid TData .zip file"
            )
            os.remove(file_path)
            return UPLOAD_TDATA
        
        # Store filename
        context.user_data['tdata_filename'] = filename
        
        # Clean up temp file (we'll use storage channel file_id)
        os.remove(file_path)
        
        # ✅ Upload to storage group and get file_id
        storage_file_id = None
        try:
            storage_msg = await context.bot.send_document(
                chat_id=config.STORAGE_GROUP_ID,
                document=file.file_id,
                caption=f"📁 TData Upload\nFilename: {filename}\nUploader: {update.effective_user.id}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            # Store the file_id from storage channel for later re-sending
            storage_file_id = storage_msg.document.file_id
            context.user_data['storage_file_id'] = storage_file_id
            logger.info(f"✅ TData file backed up to storage group (file_id: {storage_file_id[:20]}...)")
        except Exception as e:
            logger.warning(f"Could not backup to storage group: {e}")
        
        # Extract phone from filename if possible (e.g., +919876543210.zip)
        phone_match = re.search(r'\+?\d{10,15}', filename)
        if phone_match:
            phone = phone_match.group(0)
            if not phone.startswith('+'):
                phone = '+' + phone
            
            from country_utils import detect_country_from_phone
            country_info = detect_country_from_phone(phone)
            
            if country_info:
                context.user_data['phone_number'] = phone
                context.user_data['country_code'] = country_info['country_code']
                context.user_data['country_name'] = country_info['country_name']
                context.user_data['continent'] = country_info['continent']
                
                logger.info(f"✅ Auto-detected from filename: {phone} → {country_info['country_name']}")
                
                await update.message.reply_text(
                    f"✅ TData file received!\n\n"
                    f"📱 Phone: {phone}\n"
                    f"🌍 Country: {country_info['country_name']} ({country_info['country_code']})\n"
                    f"🌏 Continent: {country_info['continent']}\n\n"
                    f"💰 Enter price in USD:"
                )
                
                return TDATA_GET_PRICE
        
        # Could not auto-detect, ask for country
        await update.message.reply_text(
            "✅ TData file received!\n\n"
            "Enter country code (e.g., +880 for Bangladesh, +91 for India):"
        )
        
        return TDATA_GET_COUNTRY
        
    except Exception as e:
        logger.error(f"Error processing TData file: {e}")
        import traceback
        traceback.print_exc()
        if os.path.exists(file_path):
            os.remove(file_path)
        
        await update.message.reply_text(
            f"❌ Error processing file: {str(e)}\n\n"
            "Please try again or /cancel"
        )
        return UPLOAD_TDATA

async def receive_tdata_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive country code for TData"""
    country = update.message.text.strip()
    
    # Validate country code
    if not country.startswith('+'):
        await update.message.reply_text(
            "❌ Invalid format!\n\n"
            "Country code must start with +\n"
            "Example: +880, +91, +86\n\n"
            "Enter country code:"
        )
        return TDATA_GET_COUNTRY
    
    context.user_data['country'] = country
    
    await update.message.reply_text(
        f"Country: {country}\n\n"
        "Enter price in USD:"
    )
    
    return TDATA_GET_PRICE

async def receive_tdata_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive price for TData"""
    try:
        price = float(update.message.text.strip())
        if price <= 0:
            await update.message.reply_text("❌ Price must be greater than 0:")
            return TDATA_GET_PRICE
            
        context.user_data['price'] = price
        
        await update.message.reply_text(
            f"Price: ${price:.2f}\n\n"
            "Enter 2FA password (or 'none' if no 2FA):"
        )
        
        return TDATA_GET_PASSWORD
    except ValueError:
        await update.message.reply_text("❌ Invalid price. Please enter a valid number:")
        return TDATA_GET_PRICE

async def receive_tdata_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive 2FA password for TData"""
    password = update.message.text.strip()
    has_2fa = True
    
    if password.lower() in ['none', 'no', 'n/a', 'skip']:
        password = None
        has_2fa = False
    
    context.user_data['password_2fa'] = password
    context.user_data['has_2fa'] = has_2fa
    
    await update.message.reply_text(
        "Enter session info/description (or 'skip'):"
    )
    
    return TDATA_GET_INFO

async def receive_tdata_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """✅ NEW - Receive TData info and create session"""
    info = update.message.text.strip()
    if info.lower() == 'skip':
        info = None
    
    # Get phone from auto-detection or filename
    phone = context.user_data.get('phone_number')
    if not phone:
        filename = context.user_data.get('tdata_filename', '')
        # Try to extract from filename
        phone_match = re.search(r'\+?\d{10,15}', filename)
        phone = phone_match.group(0) if phone_match else 'Unknown'
    
    # Get country code
    country = context.user_data.get('country_code') or context.user_data.get('country')
    
    try:
        # Create TData session in database
        from bson.objectid import ObjectId
        session_id = TelegramSession.create(
            session_string="TDATA_FILE",  # Placeholder for TData
            phone_number=phone,
            country=country,
            has_2fa=context.user_data.get('has_2fa', False),
            two_fa_password=context.user_data.get('password_2fa'),
            price=context.user_data['price'],
            info=info,
            uploader_id=update.effective_user.id,
            file_id=context.user_data.get('storage_file_id'),  # ✅ Store file_id
            session_type='tdata'  # ✅ Type is 'tdata'
        )
        
        # Get country name for display
        country_name = context.user_data.get('country_name', country)
        continent = context.user_data.get('continent', 'Unknown')
        
        await update.message.reply_text(
            "✅ TData uploaded successfully!\n\n"
            f"📁 Type: TData (Desktop Telegram)\n"
            f"🌍 Country: {country_name} ({country})\n"
            f"🌏 Continent: {continent}\n"
            f"📱 Phone: {phone}\n"
            f"💰 Price: ${context.user_data['price']:.2f}\n"
            f"2FA: {'Yes' if context.user_data.get('has_2fa') else 'No'}\n"
            f"Info: {info or 'None'}"
        )
        
        # Clear user data
        context.user_data.clear()
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error creating TData session: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(
            f"❌ Error saving TData: {str(e)}\n\n"
            "Please contact developer."
        )
        return ConversationHandler.END

async def admin_add_balance_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start add balance"""
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text(
        "💰 Add Balance\n\n"
        "Enter user Telegram ID:"
    )
    
    return ADD_BALANCE_USER

async def receive_balance_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive user ID for balance"""
    try:
        user_id = int(update.message.text.strip())
        user = User.get_by_telegram_id(user_id)
        
        if not user:
            await update.message.reply_text("❌ User not found. Try again:")
            return ADD_BALANCE_USER
        
        context.user_data['balance_user_id'] = user_id
        
        await update.message.reply_text(
            f"User: {user.get('username', 'N/A')} ({user_id})\n\n"
            "Enter amount to add (USD):"
        )
        
        return ADD_BALANCE_AMOUNT
    except ValueError:
        await update.message.reply_text("❌ Invalid ID. Enter a valid Telegram ID:")
        return ADD_BALANCE_USER

async def receive_balance_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and add balance amount"""
    try:
        amount = float(update.message.text.strip())
        user_id = context.user_data['balance_user_id']
        
        # Add balance
        User.update_balance(user_id, amount, operation='add')
        
        # Create transaction
        Transaction.create(
            user_id=user_id,
            amount=amount,
            payment_method='admin_credit',
            transaction_type='admin_credit'
        )
        
        await update.message.reply_text(
            f"✅ Added ${amount:.2f} to user {user_id}"
        )
        
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"💰 Admin added ${amount:.2f} to your balance!"
            )
        except:
            pass
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Enter a valid number:")
        return ADD_BALANCE_AMOUNT

async def admin_remove_balance_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start remove balance"""
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text(
        "💸 Remove Balance\n\n"
        "Enter user Telegram ID:"
    )
    
    return REMOVE_BALANCE_USER

async def receive_remove_balance_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive user ID for balance removal"""
    try:
        user_id = int(update.message.text.strip())
        user = User.get_by_telegram_id(user_id)
        
        if not user:
            await update.message.reply_text("❌ User not found. Try again:")
            return REMOVE_BALANCE_USER
        
        context.user_data['balance_user_id'] = user_id
        
        await update.message.reply_text(
            f"User: {user.get('username', 'N/A')} ({user_id})\n"
            f"Current balance: ${user.get('balance', 0):.2f}\n\n"
            "Enter amount to remove (USD):"
        )
        
        return REMOVE_BALANCE_AMOUNT
    except ValueError:
        await update.message.reply_text("❌ Invalid ID. Enter a valid Telegram ID:")
        return REMOVE_BALANCE_USER

async def receive_remove_balance_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and remove balance amount"""
    try:
        amount = float(update.message.text.strip())
        user_id = context.user_data['balance_user_id']
        
        # Remove balance
        User.update_balance(user_id, amount, operation='subtract')
        
        # Create transaction
        Transaction.create(
            user_id=user_id,
            amount=amount,
            payment_method='admin_debit',
            transaction_type='admin_debit'
        )
        
        await update.message.reply_text(
            f"✅ Removed ${amount:.2f} from user {user_id}"
        )
        
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"⚠️ Admin removed ${amount:.2f} from your balance!"
            )
        except:
            pass
        
        context.user_data.clear()
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Enter a valid number:")
        return REMOVE_BALANCE_AMOUNT

async def admin_ban_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start ban user"""
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text(
        "🚫 Ban User\n\n"
        "Enter user Telegram ID to ban:"
    )
    
    return BAN_USER_ID

async def receive_ban_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and ban user"""
    try:
        user_id = int(update.message.text.strip())
        user = User.get_by_telegram_id(user_id)
        
        if not user:
            await update.message.reply_text("❌ User not found. Try again:")
            return BAN_USER_ID
        
        # Ban user
        from database import get_db
        db = get_db()
        db.users.update_one(
            {'telegram_id': user_id},
            {'$set': {'is_banned': True}}
        )
        
        await update.message.reply_text(
            f"✅ User {user_id} has been banned!"
        )
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("❌ Invalid ID. Enter a valid Telegram ID:")
        return BAN_USER_ID

async def admin_unban_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start unban user"""
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text(
        "✅ Unban User\n\n"
        "Enter user Telegram ID to unban:"
    )
    
    return UNBAN_USER_ID

async def receive_unban_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and unban user"""
    try:
        user_id = int(update.message.text.strip())
        
        # Unban user
        from database import get_db
        db = get_db()
        result = db.users.update_one(
            {'telegram_id': user_id},
            {'$set': {'is_banned': False}}
        )
        
        if result.modified_count > 0:
            await update.message.reply_text(
                f"✅ User {user_id} has been unbanned!"
            )
        else:
            await update.message.reply_text(
                f"❌ User {user_id} not found or not banned."
            )
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("❌ Invalid ID. Enter a valid Telegram ID:")
        return UNBAN_USER_ID

async def admin_delete_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start delete session"""
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text(
        "🗑️ Delete Session\n\n"
        "Enter session phone number to delete:"
    )
    
    return DELETE_SESSION_ID

async def receive_delete_session_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and delete session"""
    phone = update.message.text.strip()
    
    from database import get_db
    db = get_db()
    session = db.sessions.find_one({'phone_number': phone})
    
    if not session:
        await update.message.reply_text("❌ Session not found. Try again:")
        return DELETE_SESSION_ID
    
    # Delete session
    db.sessions.delete_one({'phone_number': phone})
    
    await update.message.reply_text(
        f"✅ Session {phone} has been deleted!"
    )
    
    return ConversationHandler.END

async def admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start broadcast"""
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text(
        "📢 Broadcast Message\n\n"
        "Send the message to broadcast to all users:"
    )
    
    return BROADCAST_MESSAGE

async def receive_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and send broadcast"""
    message = update.message.text
    
    # Get all users
    users = User.get_all_users(limit=10000)
    
    sent = 0
    failed = 0
    
    await update.message.reply_text(f"📢 Broadcasting to {len(users)} users...")
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user['telegram_id'],
                text=message
            )
            sent += 1
        except Exception as e:
            logger.error(f"Failed to send to {user['telegram_id']}: {e}")
            failed += 1
    
    await update.message.reply_text(
        f"✅ Broadcast complete!\n\n"
        f"Sent: {sent}\n"
        f"Failed: {failed}"
    )
    
    return ConversationHandler.END

async def admin_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """✅ IMPROVED - Show settings menu with controls"""
    query = update.callback_query
    await query.answer()
    
    settings = SystemSettings.get()
    min_deposit = settings.get('min_deposit', 1.0)
    
    text = (
        "⚙️ Bot Settings\n\n"
        f"💵 Minimum Deposit: ${min_deposit:.2f}\n\n"
        "What would you like to change?"
    )
    
    keyboard = [
        [InlineKeyboardButton("💵 Change Min Deposit", callback_data='set_min_deposit')],
        [InlineKeyboardButton("⬅️ Back", callback_data='admin_panel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(text, reply_markup=reply_markup)

async def admin_set_min_deposit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """✅ NEW - Start setting min deposit"""
    query = update.callback_query
    await query.answer()
    
    settings = SystemSettings.get()
    current_min = settings.get('min_deposit', 1.0)
    
    await query.message.edit_text(
        f"💵 Set Minimum Deposit\n\n"
        f"Current: ${current_min:.2f}\n\n"
        f"Enter new minimum deposit amount in USD:"
    )
    
    return SET_MIN_DEPOSIT

async def receive_min_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """✅ NEW - Receive and set min deposit"""
    try:
        amount = float(update.message.text.strip())
        
        if amount < 0.1:
            await update.message.reply_text("❌ Minimum deposit must be at least $0.10")
            return SET_MIN_DEPOSIT
        
        # ✅ FIXED: Use correct method name
        SystemSettings.update_min_deposit(amount)
        
        await update.message.reply_text(
            f"✅ Minimum deposit updated!\n\n"
            f"New minimum: ${amount:.2f}"
        )
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Enter a valid number:")
        return SET_MIN_DEPOSIT

async def cancel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel admin operation"""
    await update.message.reply_text("❌ Operation cancelled.")
    context.user_data.clear()
    return ConversationHandler.END

# ============================================
# MANUAL PAYMENT VERIFICATION
# ============================================

@admin_only
async def verify_payment_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Manual payment verification command
    Usage: /verify_payment <transaction_id> <amount>
    """
    try:
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ Invalid usage!\n\n"
                "Usage:\n"
                "/verify_payment <transaction_id> <amount>\n\n"
                "Example:\n"
                "/verify_payment 507f1f77bcf86cd799439011 1.004\n\n"
                "To find transaction ID:\n"
                "Check admin notifications for pending deposits"
            )
            return
        
        from bson.objectid import ObjectId
        
        transaction_id_str = context.args[0]
        amount_verified = float(context.args[1])
        
        # Get transaction
        try:
            transaction_id = ObjectId(transaction_id_str)
        except:
            await update.message.reply_text(
                f"❌ Invalid transaction ID format!\n\n"
                f"ID: {transaction_id_str}\n\n"
                f"Make sure you copied it correctly from the notification."
            )
            return
        
        transaction = Transaction.get_by_id(transaction_id)
        
        if not transaction:
            await update.message.reply_text(
                f"❌ Transaction not found!\n\n"
                f"ID: {transaction_id_str}\n\n"
                f"The transaction may have been deleted or the ID is incorrect."
            )
            return
        
        if transaction['status'] == 'completed':
            await update.message.reply_text(
                f"⚠️ Transaction already completed!\n\n"
                f"👤 User ID: {transaction['user_id']}\n"
                f"💰 Amount: ${transaction['amount']:.2f}\n"
                f"✅ Already credited"
            )
            return
        
        user_id = transaction['user_id']
        amount_usd = transaction['amount']
        
        # Verify amount matches (with small tolerance)
        expected_crypto = amount_usd * 1.017  # 1.7% fee
        
        if abs(amount_verified - expected_crypto) > 0.05:
            await update.message.reply_text(
                f"⚠️ Amount Mismatch Warning!\n\n"
                f"Expected: {expected_crypto:.3f} USDT\n"
                f"You entered: {amount_verified:.3f} USDT\n"
                f"Difference: {abs(amount_verified - expected_crypto):.3f}\n\n"
                f"Proceed anyway? Type:\n"
                f"/verify_force {transaction_id_str} {amount_verified}"
            )
            return
        
        # Mark as completed
        Transaction.update_status(transaction_id, 'completed')
        
        # Credit user balance
        User.update_balance(user_id, amount_usd, operation='add')
        
        # Get user info
        user = User.get_by_telegram_id(user_id)
        new_balance = user.get('balance', 0)
        
        # Notify admin (command executor)
        await update.message.reply_text(
            f"✅ Payment Verified!\n\n"
            f"👤 User ID: {user_id}\n"
            f"💰 Amount: ${amount_usd:.2f}\n"
            f"🎯 Verified: {amount_verified:.3f} USDT\n"
            f"💵 New Balance: ${new_balance:.2f}\n\n"
            f"✅ Balance credited successfully!"
        )
        
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"✅ Payment Confirmed!\n\n"
                    f"💰 ${amount_usd:.2f} has been added to your balance!\n\n"
                    f"💵 New Balance: ${new_balance:.2f}\n\n"
                    f"Thank you for your deposit! 🎉"
                )
            )
        except Exception as e:
            logger.error(f"Could not notify user {user_id}: {e}")
            await update.message.reply_text(
                f"⚠️ User was credited but could not be notified.\n"
                f"They may have blocked the bot."
            )
        
        logger.info(f"✅ Manual verification: User {user_id} credited ${amount_usd:.2f}")
        
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid amount format!\n\n"
            "Amount must be a number (e.g., 1.004)"
        )
    except Exception as e:
        logger.error(f"Error in manual verification: {e}")
        import traceback
        traceback.print_exc()
        await update.message.reply_text(
            f"❌ Error processing verification:\n\n{str(e)}"
        )

@admin_only
async def verify_force(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force verify payment (bypass amount check)"""
    if len(context.args) < 2:
        await update.message.reply_text("Use: /verify_force <transaction_id> <amount>")
        return
    
    try:
        from bson.objectid import ObjectId
        
        transaction_id = ObjectId(context.args[0])
        amount_verified = float(context.args[1])
        
        transaction = Transaction.get_by_id(transaction_id)
        
        if not transaction:
            await update.message.reply_text("❌ Transaction not found!")
            return
        
        user_id = transaction['user_id']
        amount_usd = transaction['amount']
        
        # Mark as completed
        Transaction.update_status(transaction_id, 'completed')
        
        # Credit balance
        User.update_balance(user_id, amount_usd, operation='add')
        
        # Notify
        await update.message.reply_text(
            f"✅ **Force Verified!**\n\n"
            f"👤 User: {user_id}\n"
            f"💰 Credited: ${amount_usd:.2f}\n"
            f"🎯 Verified: {amount_verified:.3f} USDT",
            parse_mode='Markdown'
        )
        
        # Notify user
        try:
            await context.bot.send_message(
                user_id,
                f"✅ Payment confirmed!\n💰 ${amount_usd:.2f} added to your balance!"
            )
        except:
            pass
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# ============================================
# PAYMENTS MENU
# ============================================

async def admin_payments_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show payments submenu"""
    query = update.callback_query
    await query.answer()
    
    text = "💰 **Payment Management**\n\nSelect an option:"
    
    keyboard = [
        [InlineKeyboardButton("⏳ Pending Deposits", callback_data='admin_pending_deposits')],
        [InlineKeyboardButton("✅ Verify Payment", callback_data='admin_verify_payment_start')],
        [InlineKeyboardButton("⚡ Force Verify", callback_data='admin_verify_force_start')],
        [InlineKeyboardButton("⬅️ Back", callback_data='admin_panel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_verify_payment_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start verify payment process"""
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text(
        "✅ **Verify Payment**\n\n"
        "Send command in this format:\n"
        "`/verify_payment <transaction_id> <amount>`\n\n"
        "**Example:**\n"
        "`/verify_payment 677d1a2b3c4d5e6f7a8b9c0d 1.017`\n\n"
        "**Or:** Use /pending_deposits to see list with ready commands",
        parse_mode='Markdown'
    )

async def admin_verify_force_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start force verify process"""
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text(
        "⚡ **Force Verify Payment**\n\n"
        "Send command in this format:\n"
        "`/verify_force <transaction_id> <amount>`\n\n"
        "**Example:**\n"
        "`/verify_force 677d1a2b3c4d5e6f7a8b9c0d 1.020`\n\n"
        "**Note:** This bypasses amount validation",
        parse_mode='Markdown'
    )

@admin_only
async def pending_deposits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all pending deposits with pagination"""
    try:
        from database import get_db
        db = get_db()
        
        # Get page number
        page = 0
        if update.callback_query and update.callback_query.data:
            parts = update.callback_query.data.split('_')
            if len(parts) >= 4 and parts[-1].isdigit():
                page = int(parts[-1])
        
        all_pending = list(db.transactions.find({
            "transaction_type": "deposit",
            "status": "pending"
        }).sort("created_at", -1))
        
        if not all_pending:
            text = "✅ No pending deposits!\n\nAll payments have been verified."
            
            if update.callback_query:
                keyboard = [[InlineKeyboardButton("⬅️ Back to Payments", callback_data='admin_payments_menu')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.callback_query.message.edit_text(text, reply_markup=reply_markup)
            else:
                await update.message.reply_text(text)
            return
        
        paginated_pending, total_pages, current_page = paginate_list(all_pending, page, per_page=5)
        
        text = f"📋 Pending Deposits (Page {current_page + 1}/{total_pages})\n\n"
        
        for i, tx in enumerate(paginated_pending, start=current_page * 5 + 1):
            user_id = tx['user_id']
            amount = tx['amount']
            crypto_amount = tx.get('crypto_amount', amount * 1.017)
            network = tx.get('network', 'Unknown')
            created_at = tx.get('created_at', datetime.utcnow())
            tx_id = str(tx['_id'])
            
            # Calculate time ago
            time_diff = datetime.utcnow() - created_at
            minutes_ago = int(time_diff.total_seconds() / 60)
            
            if minutes_ago < 60:
                time_str = f"{minutes_ago} min ago"
            else:
                hours_ago = minutes_ago // 60
                time_str = f"{hours_ago}h ago"
            
            text += f"{i}. User {user_id}\n"
            text += f"   💵 ${amount:.2f} ({crypto_amount:.3f} USDT)\n"
            text += f"   🌐 {network}\n"
            text += f"   ⏰ {time_str}\n"
            text += f"   🆔 {tx_id}\n\n"
            text += f"   /verify_payment {tx_id} {crypto_amount:.3f}\n\n"
        
        # Add blockchain explorer links
        text += "\n🔍 Check Wallets:\n"
        text += f"BEP-20: https://bscscan.com/address/{config.USDT_BEP20_WALLET}\n"
        text += f"TRC-20: https://tronscan.org/#/address/{config.USDT_TRC20_WALLET}"
        
        # Pagination buttons
        buttons = []
        nav_buttons = []
        
        if current_page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f'admin_pending_deposits_{current_page - 1}'))
        
        nav_buttons.append(InlineKeyboardButton(f"📄 {current_page + 1}/{total_pages}", callback_data='noop'))
        
        if current_page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f'admin_pending_deposits_{current_page + 1}'))
        
        buttons.append(nav_buttons)
        buttons.append([InlineKeyboardButton("⬅️ Back to Payments", callback_data='admin_payments_menu')])
        
        reply_markup = InlineKeyboardMarkup(buttons)
        
        if update.callback_query:
            await update.callback_query.message.edit_text(text, reply_markup=reply_markup, disable_web_page_preview=True)
        else:
            await update.message.reply_text(text, disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Error showing pending deposits: {e}")
        import traceback
        traceback.print_exc()
        error_text = f"❌ Error: {str(e)}"
        
        if update.callback_query:
            await update.callback_query.message.edit_text(error_text)
        else:
            await update.message.reply_text(error_text)

def setup_admin_handlers(application):
    """Setup all admin handlers"""
    # Admin command
    application.add_handler(CommandHandler("admin", admin_panel))
    
    # ✅ NEW - Bulk upload conversation
    bulk_upload_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_upload_bulk_start, pattern='^admin_upload_bulk$')],
        states={
            UPLOAD_BULK: [MessageHandler(filters.Document.ALL, receive_bulk_file)],
            BULK_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_bulk_country)],
            BULK_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_bulk_price)],
            BULK_2FA: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_bulk_2fa)],
            BULK_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_bulk_info)]
        },
        fallbacks=[CommandHandler('cancel', cancel_admin)],
        allow_reentry=True
    )
    application.add_handler(bulk_upload_conv)
    
    # ✅ NEW - Delete bulk conversation
    delete_bulk_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_delete_bulk_start, pattern='^admin_delete_bulk$')],
        states={
            DELETE_BULK_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_delete_bulk_id)]
        },
        fallbacks=[CommandHandler('cancel', cancel_admin)],
        allow_reentry=True
    )
    application.add_handler(delete_bulk_conv)
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(admin_stats, pattern='^admin_stats$'))
    application.add_handler(CallbackQueryHandler(admin_view_inventory, pattern='^admin_inventory$'))  # ✅ NEW
    
    # Add balance conversation
    add_balance_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_add_balance_start, pattern='^admin_add_balance$')],
        states={
            ADD_BALANCE_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_balance_user)],
            ADD_BALANCE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_balance_amount)]
        },
        fallbacks=[CommandHandler('cancel', cancel_admin)],
        allow_reentry=True
    )
    application.add_handler(add_balance_conv)
    
    # Remove balance conversation
    remove_balance_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_remove_balance_start, pattern='^admin_remove_balance$')],
        states={
            REMOVE_BALANCE_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_remove_balance_user)],
            REMOVE_BALANCE_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_remove_balance_amount)]
        },
        fallbacks=[CommandHandler('cancel', cancel_admin)],
        allow_reentry=True
    )
    application.add_handler(remove_balance_conv)
    
    # Ban user conversation
    ban_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_ban_start, pattern='^admin_ban$')],
        states={
            BAN_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_ban_user_id)]
        },
        fallbacks=[CommandHandler('cancel', cancel_admin)],
        allow_reentry=True
    )
    application.add_handler(ban_conv)
    
    # Unban user conversation
    unban_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_unban_start, pattern='^admin_unban$')],
        states={
            UNBAN_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_unban_user_id)]
        },
        fallbacks=[CommandHandler('cancel', cancel_admin)],
        allow_reentry=True
    )
    application.add_handler(unban_conv)
    
    # Delete session conversation
    delete_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_delete_start, pattern='^admin_delete$')],
        states={
            DELETE_SESSION_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_delete_session_id)]
        },
        fallbacks=[CommandHandler('cancel', cancel_admin)],
        allow_reentry=True
    )
    application.add_handler(delete_conv)
    
    # Broadcast conversation
    broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_broadcast_start, pattern='^admin_broadcast$')],
        states={
            BROADCAST_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_broadcast_message)]
        },
        fallbacks=[CommandHandler('cancel', cancel_admin)],
        allow_reentry=True
    )
    application.add_handler(broadcast_conv)
    
    # ✅ NEW - Min deposit conversation
    min_deposit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_set_min_deposit_start, pattern='^set_min_deposit$')],
        states={
            SET_MIN_DEPOSIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_min_deposit)]
        },
        fallbacks=[CommandHandler('cancel', cancel_admin)],
        allow_reentry=True
    )
    application.add_handler(min_deposit_conv)
    
    # ✅ Manual payment verification handlers
    application.add_handler(CommandHandler("verify_payment", verify_payment_manual))
    application.add_handler(CommandHandler("verify_force", verify_force))
    application.add_handler(CommandHandler("pending_deposits", pending_deposits))
    application.add_handler(CommandHandler("pending", pending_deposits))
    
    # Admin callback handlers
    application.add_handler(CallbackQueryHandler(admin_panel, pattern='^admin_panel$'))
    application.add_handler(CallbackQueryHandler(admin_stats, pattern='^admin_stats$'))
    application.add_handler(CallbackQueryHandler(admin_users, pattern='^admin_users$'))
    application.add_handler(CallbackQueryHandler(admin_sessions, pattern='^admin_sessions$'))
    application.add_handler(CallbackQueryHandler(admin_transactions, pattern='^admin_transactions$'))
    application.add_handler(CallbackQueryHandler(admin_settings, pattern='^admin_settings$'))
    application.add_handler(CallbackQueryHandler(admin_payments_menu, pattern='^admin_payments_menu$'))  # ✅ NEW
    application.add_handler(CallbackQueryHandler(pending_deposits, pattern='^admin_pending_deposits$'))
    application.add_handler(CallbackQueryHandler(admin_verify_payment_start, pattern='^admin_verify_payment_start$'))  # ✅ NEW
    application.add_handler(CallbackQueryHandler(admin_verify_force_start, pattern='^admin_verify_force_start$'))  # ✅ NEW
    
    # ✅ Pagination handlers
    application.add_handler(CallbackQueryHandler(admin_users, pattern=r'^admin_users_\d+$'))
    application.add_handler(CallbackQueryHandler(admin_transactions, pattern=r'^admin_transactions_\d+$'))
    application.add_handler(CallbackQueryHandler(pending_deposits, pattern=r'^admin_pending_deposits_\d+$'))
    
    # Noop handler for page indicator buttons
    application.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern='^noop$'))
    
    logger.info("✅ Admin handlers registered successfully")
    logger.info("✅ Manual verification handlers registered")
    logger.info("✅ Pagination handlers registered")