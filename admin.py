import logging
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler, CallbackQueryHandler, MessageHandler,
    filters, ConversationHandler, ContextTypes
)
from database import User, TelegramSession, Transaction, SystemSettings
import config

logger = logging.getLogger(__name__)

# Conversation states
(UPLOAD_SESSION, GET_COUNTRY, GET_PRICE, GET_PASSWORD, GET_INFO,
 ADD_BALANCE_USER, ADD_BALANCE_AMOUNT, REMOVE_BALANCE_USER, REMOVE_BALANCE_AMOUNT,
 BAN_USER_ID, UNBAN_USER_ID, DELETE_SESSION_ID, BROADCAST_MESSAGE,
 EDIT_WALLET_BEP20, EDIT_WALLET_TRC20) = range(15)

def admin_only(func):
    """Decorator to restrict commands to admin only"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id != config.OWNER_ID:
            await update.message.reply_text("❌ You don't have permission to use this command.")
            return
        return await func(update, context)
    return wrapper

@admin_only
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel"""
    keyboard = [
        [
            InlineKeyboardButton("📤 Upload Session", callback_data='admin_upload'),
            InlineKeyboardButton("📊 Statistics", callback_data='admin_stats')
        ],
        [
            InlineKeyboardButton("💰 Add Balance", callback_data='admin_add_balance'),
            InlineKeyboardButton("💸 Remove Balance", callback_data='admin_remove_balance')
        ],
        [
            InlineKeyboardButton("👥 Users", callback_data='admin_users'),
            InlineKeyboardButton("📦 Sessions", callback_data='admin_sessions')
        ],
        [
            InlineKeyboardButton("💳 Transactions", callback_data='admin_transactions'),
            InlineKeyboardButton("🗑️ Delete Session", callback_data='admin_delete')
        ],
        [
            InlineKeyboardButton("🚫 Ban User", callback_data='admin_ban'),
            InlineKeyboardButton("✅ Unban User", callback_data='admin_unban')
        ],
        [
            InlineKeyboardButton("📢 Broadcast", callback_data='admin_broadcast'),
            InlineKeyboardButton("⚙️ Settings", callback_data='admin_settings')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "🔧 Admin Panel\n\nSelect an option below:"
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    else:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup)

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show statistics"""
    query = update.callback_query
    await query.answer()
    
    # Get stats
    total_users = User.count_users()
    available_sessions = TelegramSession.count_available()
    sold_sessions = TelegramSession.count_sold()
    
    # Get total revenue
    all_transactions = Transaction.get_all_transactions(limit=1000)
    total_revenue = sum(t['amount'] for t in all_transactions if t['transaction_type'] == 'purchase')
    
    text = (
        "📊 Bot Statistics\n\n"
        f"👥 Total Users: {total_users}\n"
        f"📦 Available Sessions: {available_sessions}\n"
        f"✅ Sold Sessions: {sold_sessions}\n"
        f"💰 Total Revenue: ${total_revenue:.2f}\n"
    )
    
    keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data='admin_panel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(text, reply_markup=reply_markup)

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show users list"""
    query = update.callback_query
    await query.answer()
    
    users = User.get_all_users()[:20]  # Show first 20 users
    
    text = "👥 Users List (Latest 20)\n\n"
    for user in users:
        text += (
            f"ID: {user['telegram_id']}\n"
            f"Username: @{user.get('username', 'N/A')}\n"
            f"Balance: ${user.get('balance', 0):.2f}\n"
            f"Language: {user.get('language', 'en')}\n"
            f"Banned: {'Yes' if user.get('is_banned') else 'No'}\n"
            f"Joined: {user['created_at'].strftime('%Y-%m-%d')}\n\n"
        )
    
    keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data='admin_panel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(text, reply_markup=reply_markup)

async def admin_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show sessions list"""
    query = update.callback_query
    await query.answer()
    
    sessions = TelegramSession.get_all_sessions()[:20]  # Show first 20
    
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
    """Show transactions list"""
    query = update.callback_query
    await query.answer()
    
    transactions = Transaction.get_all_transactions(limit=20)
    
    text = "💳 Transactions (Latest 20)\n\n"
    for txn in transactions:
        text += (
            f"User ID: {txn['user_id']}\n"
            f"Amount: ${txn['amount']:.2f}\n"
            f"Type: {txn['transaction_type']}\n"
            f"Status: {txn['status']}\n"
            f"Date: {txn['created_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
        )
    
    keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data='admin_panel')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(text, reply_markup=reply_markup)

async def admin_upload_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start session upload"""
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text(
        "📤 Upload Session\n\n"
        "Send either:\n"
        "• .session file (Telethon format)\n"
        "• .tdata.zip file (Telegram Desktop format)\n\n"
        "Both formats are supported!"
    )
    
    return UPLOAD_SESSION

async def receive_session_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive session file - supports both .session and .tdata.zip"""
    document = update.message.document
    filename = document.file_name
    
    # Download file
    file = await document.get_file()
    file_path = f"/tmp/{filename}"
    await file.download_to_drive(file_path)
    
    try:
        # Check file type
        if filename.endswith('.session'):
            # Standard .session file
            with open(file_path, 'r') as f:
                session_string = f.read()
            
            context.user_data['session_string'] = session_string
            context.user_data['session_filename'] = filename
            context.user_data['file_type'] = 'session'
            
            await update.message.reply_text(
                "✅ .session file received!\n\n"
                "Enter country code (e.g., +91 for India):"
            )
            
        elif filename.endswith('.zip') or filename.endswith('.tdata.zip'):
            # TData ZIP file - need to convert
            await update.message.reply_text(
                "📦 TData ZIP received!\n"
                "🔄 Converting to session format..."
            )
            
            try:
                from tdata_converter import extract_session_from_tdata
                
                session_string = extract_session_from_tdata(file_path)
                
                if session_string:
                    context.user_data['session_string'] = session_string
                    context.user_data['session_filename'] = filename.replace('.zip', '.session')
                    context.user_data['file_type'] = 'tdata'
                    
                    await update.message.reply_text(
                        "✅ TData converted successfully!\n\n"
                        "Enter country code (e.g., +91 for India):"
                    )
                else:
                    await update.message.reply_text(
                        "❌ Could not convert TData to session.\n\n"
                        "⚠️ TData→Session conversion is experimental.\n"
                        "Please upload .session file instead.\n\n"
                        "Send another file or /cancel"
                    )
                    return UPLOAD_SESSION
                    
            except Exception as e:
                logger.error(f"TData conversion error: {e}")
                await update.message.reply_text(
                    "❌ Error converting TData.\n\n"
                    "Please upload .session file instead.\n\n"
                    "Send another file or /cancel"
                )
                return UPLOAD_SESSION
        else:
            await update.message.reply_text(
                "❌ Invalid file type!\n\n"
                "Please send:\n"
                "• .session file, or\n"
                "• .tdata.zip file\n\n"
                "Send file or /cancel"
            )
            return UPLOAD_SESSION
        
        # Clean up temp file
        os.remove(file_path)
        
        return GET_COUNTRY
        
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        
        await update.message.reply_text(
            f"❌ Error processing file: {str(e)}\n\n"
            "Please try again or /cancel"
        )
        return UPLOAD_SESSION

async def receive_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive country code"""
    country = update.message.text.strip()
    context.user_data['country'] = country
    
    await update.message.reply_text(
        f"Country: {country}\n\n"
        "Enter price in USD:"
    )
    
    return GET_PRICE

async def receive_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive price"""
    try:
        price = float(update.message.text.strip())
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
    if password.lower() == 'none':
        password = None
    
    context.user_data['password_2fa'] = password
    
    await update.message.reply_text(
        "Enter session info/description (or 'skip'):"
    )
    
    return GET_INFO

async def receive_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive session info and create session"""
    info = update.message.text.strip()
    if info.lower() == 'skip':
        info = None
    
    # Get phone number from filename
    filename = context.user_data.get('session_filename', '')
    phone = filename.replace('.session', '')
    
    # Create session
    session = TelegramSession.create(
        country=context.user_data['country'],
        phone_number=phone,
        session_string=context.user_data['session_string'],
        price=context.user_data['price'],
        password_2fa=context.user_data.get('password_2fa'),
        info=info
    )
    
    await update.message.reply_text(
        "✅ Session uploaded successfully!\n\n"
        f"Country: {session['country']}\n"
        f"Phone: {session['phone_number']}\n"
        f"Price: ${session['price']:.2f}\n"
        f"2FA: {session.get('password_2fa', 'None')}\n"
        f"Info: {session.get('info', 'None')}"
    )
    
    # Clear user data
    context.user_data.clear()
    
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
        User.update_balance(user_id, amount)
        
        # Create transaction
        Transaction.create(
            user_id=user_id,
            amount=amount,
            transaction_type='admin_credit',
            status='completed',
            description='Balance added by admin'
        )
        
        await update.message.reply_text(
            f"✅ Added ${amount:.2f} to user {user_id}'s balance!"
        )
        
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
        
        # Remove balance (negative amount)
        User.update_balance(user_id, -amount)
        
        # Create transaction
        Transaction.create(
            user_id=user_id,
            amount=-amount,
            transaction_type='admin_debit',
            status='completed',
            description='Balance removed by admin'
        )
        
        await update.message.reply_text(
            f"✅ Removed ${amount:.2f} from user {user_id}'s balance!"
        )
        
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
        User.ban_user(user_id)
        
        await update.message.reply_text(
            f"✅ User {user_id} (@{user.get('username', 'N/A')}) has been banned!"
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
        user = User.get_by_telegram_id(user_id)
        
        if not user:
            await update.message.reply_text("❌ User not found. Try again:")
            return UNBAN_USER_ID
        
        # Unban user
        User.unban_user(user_id)
        
        await update.message.reply_text(
            f"✅ User {user_id} (@{user.get('username', 'N/A')}) has been unbanned!"
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
    
    # Find session by phone
    from database import get_db
    db = get_db()
    session = db.sessions.find_one({'phone_number': phone})
    
    if not session:
        await update.message.reply_text("❌ Session not found. Try again:")
        return DELETE_SESSION_ID
    
    # Delete session
    TelegramSession.delete_session(str(session['_id']))
    
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
    users = User.get_all_users()
    
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
    """Show settings menu"""
    query = update.callback_query
    await query.answer()
    
    settings = SystemSettings.get()
    
    text = (
        "⚙️ Settings\n\n"
        f"Min Deposit: ${settings.get('min_deposit', 1):.2f}\n"
        f"BEP-20 Wallet: {settings.get('usdt_bep20_wallet', 'Not set')[:20]}...\n"
        f"TRC-20 Wallet: {settings.get('usdt_trc20_wallet', 'Not set')[:20]}...\n"
    )
    
    keyboard = [
        [InlineKeyboardButton("📝 Edit BEP-20 Wallet", callback_data='edit_bep20')],
        [InlineKeyboardButton("📝 Edit TRC-20 Wallet", callback_data='edit_trc20')],
        [InlineKeyboardButton("⬅️ Back", callback_data='admin_panel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(text, reply_markup=reply_markup)

async def cancel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel admin operation"""
    await update.message.reply_text("❌ Operation cancelled.")
    return ConversationHandler.END

def setup_admin_handlers(application):
    """Setup all admin handlers"""
    
    # Admin command
    application.add_handler(CommandHandler("admin", admin_panel))
    
    # Upload session conversation
    upload_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_upload_start, pattern='^admin_upload$')],
        states={
            UPLOAD_SESSION: [MessageHandler(filters.Document.ALL, receive_session_file)],
            GET_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_country)],
            GET_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_price)],
            GET_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_password)],
            GET_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_info)]
        },
        fallbacks=[CommandHandler('cancel', cancel_admin)],
        allow_reentry=True
    )
    application.add_handler(upload_conv)
    
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
    
    # Admin callback handlers
    application.add_handler(CallbackQueryHandler(admin_panel, pattern='^admin_panel$'))
    application.add_handler(CallbackQueryHandler(admin_stats, pattern='^admin_stats$'))
    application.add_handler(CallbackQueryHandler(admin_users, pattern='^admin_users$'))
    application.add_handler(CallbackQueryHandler(admin_sessions, pattern='^admin_sessions$'))
    application.add_handler(CallbackQueryHandler(admin_transactions, pattern='^admin_transactions$'))
    application.add_handler(CallbackQueryHandler(admin_settings, pattern='^admin_settings$'))
    
    logger.info("✅ Admin handlers registered successfully")