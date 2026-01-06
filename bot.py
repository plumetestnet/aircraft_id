import logging
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters, ConversationHandler
)
from database import init_db, User, TelegramSession, Transaction
from config import BOT_TOKEN, OWNER_ID
from admin import setup_admin_handlers
from payment import verify_crypto_payment
import asyncio

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
WAITING_DEPOSIT_AMOUNT, WAITING_COUNTRY_CODE = range(2)

# Language dictionary
MESSAGES = {
    'en': {
        'welcome': "👋 Welcome!\n\n🤖 Select an option below:",
        'user_center': "👤 User Center",
        'product_list': "📦 Product List",
        'recharge': "💳 Recharge",
        'contact_service': "☎️ Contact Service",
        'exchange_trx': "💱 Exchange TRX",
        'switch_language': "🌐 Switch Language",
        'balance_info': "💰 Your Balance: ${:.2f}",
        'user_info': "👤 User ID: {}\n💰 Balance: ${:.2f}\n📅 Joined: {}",
        'select_continent': "🌍 Select Continent:",
        'back': "⬅️ Back",
        'close': "❌ Close",
        'select_country': "🌍 Select Country:",
        'session_format': "{} - {} session(s) - ${:.2f}",
        'no_sessions': "❌ No sessions available for this country.",
        'enter_deposit': "💳 Enter deposit amount in USD (minimum $1):",
        'deposit_method': "💳 Select payment method:",
        'usdt_bep20': "USDT (BEP-20)",
        'usdt_trc20': "USDT (TRC-20)",
        'cancel': "❌ Cancel",
        'deposit_instructions': "💳 Deposit Instructions\n\n💰 Amount: ${:.2f}\n📊 Exact amount to send: {:.6f} USDT\n\n📮 Send EXACTLY {:.6f} USDT to:\n`{}`\n\n⚠️ Network: {}\n⏱️ Verification will be automatic within 5-10 minutes.\n\n⚠️ Send ONLY {} USDT - exact amount required for verification!",
        'payment_pending': "⏳ Payment pending verification...\n\nPayment ID: {}",
        'invalid_amount': "❌ Invalid amount. Please enter a valid number (minimum $1).",
        'payment_verified': "✅ Payment verified!\n💰 ${:.2f} added to your balance.",
        'payment_failed': "❌ Payment verification failed. Please try again or contact support.",
        'enter_country_code': "🔢 Enter country code (e.g., +91 for India, +1 for USA):",
        'invalid_country_code': "❌ Invalid country code. Please enter a valid code starting with +",
        'language_switched': "✅ Language switched to English"
    },
    'zh': {
        'welcome': "👋 欢迎!\n\n🤖 请选择以下选项:",
        'user_center': "👤 用户中心",
        'product_list': "📦 商品列表",
        'recharge': "💳 充值余额",
        'contact_service': "☎️ 联系客服",
        'exchange_trx': "💱 TRX兑换",
        'switch_language': "🌐 中英文切换",
        'balance_info': "💰 您的余额: ${:.2f}",
        'user_info': "👤 用户ID: {}\n💰 余额: ${:.2f}\n📅 加入时间: {}",
        'select_continent': "🌍 选择大洲:",
        'back': "⬅️ 返回",
        'close': "❌ 关闭",
        'select_country': "🌍 选择国家:",
        'session_format': "{} - {} 会话 - ${:.2f}",
        'no_sessions': "❌ 该国家暂无可用会话。",
        'enter_deposit': "💳 输入充值金额(美元,最低$1):",
        'deposit_method': "💳 选择支付方式:",
        'usdt_bep20': "USDT (BEP-20)",
        'usdt_trc20': "USDT (TRC-20)",
        'cancel': "❌ 取消",
        'deposit_instructions': "💳 充值说明\n\n💰 金额: ${:.2f}\n📊 需要发送的确切金额: {:.6f} USDT\n\n📮 请发送准确的 {:.6f} USDT 到:\n`{}`\n\n⚠️ 网络: {}\n⏱️ 验证将在5-10分钟内自动完成。\n\n⚠️ 只发送 {} USDT - 验证需要准确金额!",
        'payment_pending': "⏳ 支付等待验证中...\n\n支付ID: {}",
        'invalid_amount': "❌ 无效金额。请输入有效数字(最低$1)。",
        'payment_verified': "✅ 支付已验证!\n💰 ${:.2f} 已添加到您的余额。",
        'payment_failed': "❌ 支付验证失败。请重试或联系客服。",
        'enter_country_code': "🔢 输入国家代码(例如: +91印度, +1美国):",
        'invalid_country_code': "❌ 无效的国家代码。请输入以+开头的有效代码",
        'language_switched': "✅ 已切换到中文"
    }
}

# Continent to countries mapping
CONTINENTS = {
    'asia': {
        'name': {'en': '🌏 Asia', 'zh': '🌏 亚洲'},
        'countries': {
            '+91': {'name': 'India', 'name_zh': '印度'},
            '+86': {'name': 'China', 'name_zh': '中国'},
            '+81': {'name': 'Japan', 'name_zh': '日本'},
            '+82': {'name': 'South Korea', 'name_zh': '韩国'},
            '+65': {'name': 'Singapore', 'name_zh': '新加坡'},
            '+60': {'name': 'Malaysia', 'name_zh': '马来西亚'},
            '+66': {'name': 'Thailand', 'name_zh': '泰国'},
            '+84': {'name': 'Vietnam', 'name_zh': '越南'},
            '+63': {'name': 'Philippines', 'name_zh': '菲律宾'},
            '+62': {'name': 'Indonesia', 'name_zh': '印度尼西亚'},
        }
    },
    'europe': {
        'name': {'en': '🌍 Europe', 'zh': '🌍 欧洲'},
        'countries': {
            '+44': {'name': 'United Kingdom', 'name_zh': '英国'},
            '+49': {'name': 'Germany', 'name_zh': '德国'},
            '+33': {'name': 'France', 'name_zh': '法国'},
            '+39': {'name': 'Italy', 'name_zh': '意大利'},
            '+34': {'name': 'Spain', 'name_zh': '西班牙'},
            '+31': {'name': 'Netherlands', 'name_zh': '荷兰'},
            '+7': {'name': 'Russia', 'name_zh': '俄罗斯'},
        }
    },
    'america': {
        'name': {'en': '🌎 America', 'zh': '🌎 美洲'},
        'countries': {
            '+1': {'name': 'USA/Canada', 'name_zh': '美国/加拿大'},
            '+52': {'name': 'Mexico', 'name_zh': '墨西哥'},
            '+55': {'name': 'Brazil', 'name_zh': '巴西'},
            '+54': {'name': 'Argentina', 'name_zh': '阿根廷'},
        }
    },
    'africa': {
        'name': {'en': '🌍 Africa', 'zh': '🌍 非洲'},
        'countries': {
            '+27': {'name': 'South Africa', 'name_zh': '南非'},
            '+234': {'name': 'Nigeria', 'name_zh': '尼日利亚'},
            '+254': {'name': 'Kenya', 'name_zh': '肯尼亚'},
            '+20': {'name': 'Egypt', 'name_zh': '埃及'},
        }
    },
    'oceania': {
        'name': {'en': '🌏 Oceania', 'zh': '🌏 大洋洲'},
        'countries': {
            '+61': {'name': 'Australia', 'name_zh': '澳大利亚'},
            '+64': {'name': 'New Zealand', 'name_zh': '新西兰'},
        }
    }
}

def get_user_language(user_id: int) -> str:
    """Get user's preferred language"""
    user = User.get_by_telegram_id(user_id)
    return user.get('language', 'en') if user else 'en'

def get_message(user_id: int, key: str) -> str:
    """Get translated message for user"""
    lang = get_user_language(user_id)
    return MESSAGES[lang].get(key, MESSAGES['en'][key])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user = update.effective_user
    user_id = user.id
    
    # Create user if doesn't exist
    existing_user = User.get_by_telegram_id(user_id)
    if not existing_user:
        User.create(telegram_id=user_id, username=user.username or user.first_name)
        logger.info(f"New user created: {user_id}")
    
    # Check if user entered country code
    if context.args and len(context.args) > 0:
        country_code = context.args[0]
        if country_code.startswith('+'):
            await show_country_sessions(update, context, country_code)
            return
    
    await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu with language support"""
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    keyboard = [
        [
            InlineKeyboardButton(MESSAGES[lang]['user_center'], callback_data='user_center'),
            InlineKeyboardButton(MESSAGES[lang]['product_list'], callback_data='product_list')
        ],
        [
            InlineKeyboardButton(MESSAGES[lang]['recharge'], callback_data='recharge')
        ],
        [
            InlineKeyboardButton(MESSAGES[lang]['contact_service'], url='https://t.me/support')
        ],
        [
            InlineKeyboardButton(MESSAGES[lang]['switch_language'], callback_data='switch_language')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(
            MESSAGES[lang]['welcome'],
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            MESSAGES[lang]['welcome'],
            reply_markup=reply_markup
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data == 'user_center':
        await show_user_center(update, context)
    elif data == 'product_list':
        await show_continents(update, context)
    elif data == 'recharge':
        return await start_recharge(update, context)
    elif data == 'switch_language':
        await switch_language(update, context)
    elif data == 'back_to_menu':
        await show_main_menu(update, context)
    elif data.startswith('continent_'):
        continent = data.replace('continent_', '')
        await show_countries(update, context, continent)
    elif data.startswith('country_'):
        country_code = data.replace('country_', '')
        await show_country_sessions(update, context, country_code)
    elif data.startswith('buy_session_'):
        session_id = data.replace('buy_session_', '')
        await purchase_session_handler(update, context, session_id)
    elif data.startswith('deposit_'):
        network = data.replace('deposit_', '')
        await process_deposit(update, context, network)
    elif data == 'cancel_deposit':
        await show_main_menu(update, context)
        return ConversationHandler.END

async def show_user_center(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user center with balance info"""
    query = update.callback_query
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    user = User.get_by_telegram_id(user_id)
    balance = user.get('balance', 0.0)
    created_at = user.get('created_at', datetime.now()).strftime('%Y-%m-%d')
    
    text = MESSAGES[lang]['user_info'].format(user_id, balance, created_at)
    
    keyboard = [
        [InlineKeyboardButton(MESSAGES[lang]['back'], callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(text, reply_markup=reply_markup)

async def show_continents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show continent selection"""
    query = update.callback_query
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    keyboard = []
    for continent_code, continent_data in CONTINENTS.items():
        continent_name = continent_data['name'][lang]
        keyboard.append([InlineKeyboardButton(
            continent_name,
            callback_data=f'continent_{continent_code}'
        )])
    
    keyboard.append([InlineKeyboardButton(MESSAGES[lang]['back'], callback_data='back_to_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        MESSAGES[lang]['select_continent'],
        reply_markup=reply_markup
    )

async def show_countries(update: Update, context: ContextTypes.DEFAULT_TYPE, continent: str):
    """Show countries in selected continent"""
    query = update.callback_query
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    continent_data = CONTINENTS.get(continent, {})
    countries = continent_data.get('countries', {})
    
    keyboard = []
    for code, country_data in countries.items():
        country_name = country_data['name_zh'] if lang == 'zh' else country_data['name']
        # Get session count for this country
        sessions = TelegramSession.get_available_by_country(code)
        count = len(sessions)
        
        button_text = f"{country_name} ({count})"
        keyboard.append([InlineKeyboardButton(
            button_text,
            callback_data=f'country_{code}'
        )])
    
    keyboard.append([InlineKeyboardButton(MESSAGES[lang]['back'], callback_data='product_list')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        MESSAGES[lang]['select_country'],
        reply_markup=reply_markup
    )

async def show_country_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE, country_code: str):
    """Show available sessions for a country"""
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    sessions = TelegramSession.get_available_by_country(country_code)
    
    if not sessions:
        text = MESSAGES[lang]['no_sessions']
        keyboard = [[InlineKeyboardButton(MESSAGES[lang]['back'], callback_data='product_list')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.message.edit_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
        return
    
    # Get country name
    country_name = country_code
    for continent_data in CONTINENTS.values():
        if country_code in continent_data['countries']:
            country_data = continent_data['countries'][country_code]
            country_name = country_data['name_zh'] if lang == 'zh' else country_data['name']
            break
    
    text = f"🌍 {country_name} - {len(sessions)} sessions available\n\n"
    
    keyboard = []
    for session in sessions[:10]:  # Show max 10 sessions
        session_id = str(session['_id'])
        price = session.get('price', 0.0)
        info = session.get('info', 'No info')
        
        button_text = f"${price:.2f} - {info[:30]}"
        keyboard.append([InlineKeyboardButton(
            button_text,
            callback_data=f'buy_session_{session_id}'
        )])
    
    keyboard.append([
        InlineKeyboardButton(MESSAGES[lang]['back'], callback_data='product_list'),
        InlineKeyboardButton(MESSAGES[lang]['close'], callback_data='back_to_menu')
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

async def purchase_session_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, session_id: str):
    """Handle session purchase with TData support"""
    query = update.callback_query
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    user = User.get_by_telegram_id(user_id)
    session = TelegramSession.get_by_id(session_id)
    
    if not session:
        await query.answer("❌ Session not found!", show_alert=True)
        return
    
    price = session.get('price', 0.0)
    balance = user.get('balance', 0.0)
    
    if balance < price:
        await query.answer(f"❌ Insufficient balance! Need ${price:.2f}", show_alert=True)
        return
    
    # Deduct balance
    User.update_balance(user_id, -price)
    
    # Mark session as sold
    TelegramSession.mark_as_sold(session_id, user_id)
    
    # Create transaction record
    Transaction.create(
        user_id=user_id,
        amount=price,
        transaction_type='purchase',
        status='completed',
        description=f"Purchased session for {session.get('country')}"
    )
    
    # Send session details
    session_string = session.get('session_string', '')
    phone = session.get('phone_number', 'N/A')
    password_2fa = session.get('password_2fa', 'No 2FA')
    
    details = (
        f"✅ Purchase Successful!\n\n"
        f"📱 Phone: {phone}\n"
        f"🔐 2FA: {password_2fa}\n\n"
        f"💰 Remaining balance: ${balance - price:.2f}\n\n"
        f"📥 Preparing files..."
    )
    
    await query.message.reply_text(details)
    
    # Prepare files (both .session and .tdata)
    try:
        from tdata_converter import prepare_tdata_for_user, cleanup_temp_files
        
        files_result = await prepare_tdata_for_user(session_string, phone)
        
        if files_result['success']:
            # Send .session file
            if files_result['session_file']:
                with open(files_result['session_file'], 'rb') as f:
                    await query.message.reply_document(
                        document=f,
                        filename=f"{phone}.session",
                        caption="📄 Telethon Session File"
                    )
            
            # Send .tdata.zip if available
            if files_result['tdata_file']:
                with open(files_result['tdata_file'], 'rb') as f:
                    await query.message.reply_document(
                        document=f,
                        filename=f"{phone}_tdata.zip",
                        caption="📦 TData Format (for Telegram Desktop)"
                    )
            
            # Cleanup
            cleanup_files = [
                files_result.get('session_file'),
                files_result.get('tdata_file')
            ]
            cleanup_temp_files([f for f in cleanup_files if f])
            
        else:
            # Fallback - send as text
            session_bytes = session_string.encode()
            await query.message.reply_document(
                document=session_bytes,
                filename=f"{phone}.session"
            )
            
    except Exception as e:
        logger.error(f"Error preparing files: {e}")
        # Fallback
        session_bytes = session_string.encode()
        await query.message.reply_document(
            document=session_bytes,
            filename=f"{phone}.session"
        )
    
    await show_main_menu(update, context)

async def start_recharge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start recharge process"""
    query = update.callback_query
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    await query.message.edit_text(
        MESSAGES[lang]['enter_deposit']
    )
    
    return WAITING_DEPOSIT_AMOUNT

async def receive_deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and validate deposit amount"""
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    try:
        amount = float(update.message.text.strip())
        if amount < 1:
            await update.message.reply_text(MESSAGES[lang]['invalid_amount'])
            return WAITING_DEPOSIT_AMOUNT
        
        context.user_data['deposit_amount'] = amount
        
        # Show payment method selection
        keyboard = [
            [InlineKeyboardButton(MESSAGES[lang]['usdt_bep20'], callback_data='deposit_bep20')],
            [InlineKeyboardButton(MESSAGES[lang]['usdt_trc20'], callback_data='deposit_trc20')],
            [InlineKeyboardButton(MESSAGES[lang]['cancel'], callback_data='cancel_deposit')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            MESSAGES[lang]['deposit_method'],
            reply_markup=reply_markup
        )
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text(MESSAGES[lang]['invalid_amount'])
        return WAITING_DEPOSIT_AMOUNT

async def process_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE, network: str):
    """Process deposit with specific network"""
    query = update.callback_query
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    amount = context.user_data.get('deposit_amount', 0)
    
    # Generate unique random amount for verification (1-99 cents)
    import random
    random_cents = random.randint(1, 99)
    exact_amount = amount + (random_cents / 1000)  # e.g., 5.017, 5.043, 5.091
    
    # Get wallet address based on network
    if network == 'bep20':
        wallet = config.USDT_BEP20_WALLET
        network_name = "BEP-20 (BSC)"
    else:  # trc20
        wallet = config.USDT_TRC20_WALLET
        network_name = "TRC-20 (TRON)"
    
    # Create transaction record
    transaction = Transaction.create(
        user_id=user_id,
        amount=amount,
        transaction_type='deposit',
        status='pending',
        payment_method=f'USDT-{network.upper()}',
        description=f"Deposit ${amount:.2f} via {network_name}",
        crypto_amount=exact_amount,
        crypto_address=wallet
    )
    
    text = MESSAGES[lang]['deposit_instructions'].format(
        amount, exact_amount, exact_amount, wallet, network_name, exact_amount
    )
    
    keyboard = [
        [InlineKeyboardButton(MESSAGES[lang]['back'], callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    # Notify admin about pending deposit
    try:
        admin_text = (
            f"New Deposit Request\n\n"
            f"User ID: {user_id}\n"
            f"Amount: ${amount:.2f}\n"
            f"Exact: {exact_amount:.3f} USDT\n"
            f"Network: {network_name}\n"
            f"Wallet: {wallet[:10]}...\n"
            f"Transaction ID: {transaction['_id']}"
        )
        await context.bot.send_message(
            chat_id=config.OWNER_ID,
            text=admin_text
        )
    except Exception as e:
        logger.error(f"Could not notify admin: {e}")
    
    # Start payment verification in background
    asyncio.create_task(verify_payment(transaction['_id'], user_id, wallet, exact_amount, context.bot))

async def verify_payment(transaction_id, user_id: int, wallet: str, expected_amount: float, bot):
    """Verify crypto payment (background task)"""
    lang = get_user_language(user_id)
    
    # Wait and check for payment (simplified - use real API in production)
    await asyncio.sleep(10)  # Check every 10 seconds
    
    max_checks = 60  # 10 minutes total
    for i in range(max_checks):
        # Check if payment received using API
        verified = await verify_crypto_payment(wallet, expected_amount)
        
        if verified:
            # Update transaction
            Transaction.update_status(transaction_id, 'completed')
            
            # Add balance
            transaction = Transaction.get_by_id(transaction_id)
            amount = transaction.get('amount', 0)
            User.update_balance(user_id, amount)
            
            # Notify user
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=MESSAGES[lang]['payment_verified'].format(amount)
                )
            except Exception as e:
                logger.error(f"Could not notify user {user_id}: {e}")
            
            # Notify admin
            try:
                admin_text = (
                    f"Payment Verified!\n\n"
                    f"User ID: {user_id}\n"
                    f"Amount: ${amount:.2f}\n"
                    f"Credited successfully"
                )
                await bot.send_message(
                    chat_id=config.OWNER_ID,
                    text=admin_text
                )
            except Exception as e:
                logger.error(f"Could not notify admin: {e}")
            
            return
        
        await asyncio.sleep(10)
    
    # Payment not received after timeout
    Transaction.update_status(transaction_id, 'failed')
    
    # Notify admin of failed payment
    try:
        admin_text = (
            f"Payment Timeout\n\n"
            f"User ID: {user_id}\n"
            f"Expected: {expected_amount:.3f} USDT\n"
            f"Status: Not received after 10 minutes"
        )
        await bot.send_message(
            chat_id=config.OWNER_ID,
            text=admin_text
        )
    except:
        pass

async def switch_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Switch user language"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    current_lang = get_user_language(user_id)
    new_lang = 'zh' if current_lang == 'en' else 'en'
    
    User.update_language(user_id, new_lang)
    
    await query.answer(MESSAGES[new_lang]['language_switched'])
    await show_main_menu(update, context)

async def handle_country_code_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text input for country codes"""
    text = update.message.text.strip()
    
    # Check if it's a country code
    if text.startswith('+'):
        await show_country_sessions(update, context, text)
    else:
        # Not a country code, ignore or show help
        pass

def main():
    """Start the bot"""
    # Initialize database
    init_db()
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Setup admin handlers
    setup_admin_handlers(application)
    
    # Recharge conversation handler
    recharge_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_recharge, pattern='^recharge$')],
        states={
            WAITING_DEPOSIT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_deposit_amount)],
        },
        fallbacks=[CallbackQueryHandler(show_main_menu, pattern='^cancel_deposit$')],
        allow_reentry=True
    )
    application.add_handler(recharge_conv)
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Text handler for country codes
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_country_code_text))
    
    # Start bot
    logger.info("🤖 Bot started successfully!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()