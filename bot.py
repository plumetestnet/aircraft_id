import logging
import asyncio
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    filters, ConversationHandler, ContextTypes
)
# ✅ FIXED: Added init_db to imports
from database import User, BulkSession, Transaction, Purchase, SystemSettings, init_db
from zip_utils import extract_sessions_from_bulk
import config
from country_utils import get_country_info

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
WAITING_DEPOSIT_AMOUNT = 0
WAITING_QUANTITY = 1

# Import admin handlers
from admin import setup_admin_handlers
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
        'enter_deposit': "💳 Enter deposit amount in USD (minimum $1):\n\n💡 Or choose a preset amount:",
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
        'enter_deposit': "💳 输入充值金额(美元,最低$1):\n\n💡 或选择预设金额:",
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
            '+880': {'name': 'Bangladesh', 'name_zh': '孟加拉国'},
            '+92': {'name': 'Pakistan', 'name_zh': '巴基斯坦'},
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

def get_persistent_keyboard(lang='en'):
    """Create persistent keyboard with bottom buttons"""
    keyboard = [
        [
            KeyboardButton("🛒 Products" if lang == 'en' else "🛒 商品"),
            KeyboardButton("🌐 Recharge" if lang == 'en' else "🌐 充值")
        ],
        [
            KeyboardButton("📞 Contact Customer Service" if lang == 'en' else "📞 联系客服"),
            KeyboardButton("👤 Personal Center" if lang == 'en' else "👤 个人中心")
        ],
        [
            KeyboardButton("🌍 Language" if lang == 'en' else "🌍 语言"),
            KeyboardButton("⚠️ Rules" if lang == 'en' else "⚠️ 规则")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

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
            await select_country(update, context)
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
    
    # Get persistent keyboard
    persistent_kb = get_persistent_keyboard(lang)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(
            MESSAGES[lang]['welcome'],
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            MESSAGES[lang]['welcome'],
            reply_markup=persistent_kb
        )
        await update.message.reply_text(
            "📋 Quick Menu:",
            reply_markup=reply_markup
        )

async def show_user_center(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user center"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    user = User.get_by_telegram_id(user_id)
    balance = user.get('balance', 0) if user else 0
    created_at = user.get('created_at', datetime.utcnow()).strftime('%Y-%m-%d') if user else 'Unknown'
    
    text = MESSAGES[lang]['user_info'].format(user_id, balance, created_at)
    
    keyboard = [[InlineKeyboardButton(MESSAGES[lang]['back'], callback_data='back_to_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(text, reply_markup=reply_markup)

async def show_product_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show continent selection"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    keyboard = []
    for continent_id, continent_data in CONTINENTS.items():
        continent_name = continent_data['name'][lang]
        keyboard.append([InlineKeyboardButton(continent_name, callback_data=f'continent_{continent_id}')])
    
    keyboard.append([InlineKeyboardButton(MESSAGES[lang]['back'], callback_data='back_to_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        MESSAGES[lang]['select_continent'],
        reply_markup=reply_markup
    )

async def show_continent_countries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show countries with available bulks"""
    query = update.callback_query
    await query.answer()
    
    continent = query.data.replace('continent_', '')
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    # Get available countries from bulks (✅ UPDATED)
    countries_data = BulkSession.get_available_countries()
    
    # Filter by continent
    continent_countries = {}
    for country in countries_data:
        country_code = country['_id']
        info = get_country_info(country_code)
        
        if info and info['continent'].lower() == continent.lower():
            continent_countries[country_code] = country
    
    if not continent_countries:
        await query.message.edit_text(
            f"❌ No sessions available in {continent.title()}\n\n"
            "Check back later!"
        )
        return
    
    # Build message
    text = f"🌍 **{continent.title()} - Select Country:**\n\n"
    keyboard = []
    
    for country_code in sorted(continent_countries.keys()):
        data = continent_countries[country_code]
        info = get_country_info(country_code)
        country_name = info['name']
        
        available = data['total_available']
        min_price = data['min_price']
        
        button_text = f"{country_name} ({country_code}) - {available} - ${min_price:.2f}/each"
        keyboard.append([InlineKeyboardButton(
            button_text,
            callback_data=f'country_{country_code}'
        )])
    
    keyboard.append([InlineKeyboardButton("« Back", callback_data='product_list')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def select_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show country and ask for quantity"""
    query = update.callback_query
    await query.answer()
    
    country_code = query.data.replace('country_', '')
    user_id = update.effective_user.id
    
    # Get available bulks
    bulks = BulkSession.get_by_country(country_code)
    
    if not bulks:
        await query.message.edit_text("❌ No sessions available")
        return ConversationHandler.END
    
    # Get cheapest bulk
    bulk = bulks[0]  # Already sorted by price
    
    info = get_country_info(country_code)
    country_name = info['name'] if info else country_code
    
    # Calculate total available
    total_available = sum(b['remaining_count'] for b in bulks)
    price = bulk['price_per_session']
    session_type = bulk['session_type']
    
    text = (
        f"🌍 **{country_name}** ({country_code})\n\n"
        f"📊 Available: **{total_available} sessions**\n"
        f"💰 Price: **${price:.2f}** per session\n"
        f"📁 Type: {session_type.upper()}\n\n"
        f"Enter quantity **(1-{min(total_available, 100)})**:"
    )
    
    # Store for next step
    context.user_data['selected_country'] = country_code
    context.user_data['selected_bulk_id'] = str(bulk['_id'])
    context.user_data['max_quantity'] = total_available
    context.user_data['price_per_session'] = price
    context.user_data['session_type'] = session_type
    
    keyboard = [[InlineKeyboardButton("« Cancel", callback_data='product_list')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    return WAITING_QUANTITY

async def receive_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process quantity input"""
    user_id = update.effective_user.id
    
    try:
        quantity = int(update.message.text.strip())
        
        max_qty = min(context.user_data.get('max_quantity', 0), 100)
        
        if quantity < 1:
            await update.message.reply_text("❌ Minimum quantity is 1")
            return WAITING_QUANTITY
        
        if quantity > max_qty:
            await update.message.reply_text(
                f"❌ Maximum quantity is {max_qty}\n\n"
                f"Available: {context.user_data.get('max_quantity', 0)}\n"
                f"Per order limit: 100"
            )
            return WAITING_QUANTITY
        
        price_per = context.user_data['price_per_session']
        total_price = quantity * price_per
        
        country_code = context.user_data['selected_country']
        info = get_country_info(country_code)
        country_name = info['name'] if info else country_code
        
        # Check balance
        user = User.get_by_telegram_id(user_id)
        balance = user['balance']
        
        if balance < total_price:
            await update.message.reply_text(
                f"❌ **Insufficient Balance!**\n\n"
                f"Need: ${total_price:.2f}\n"
                f"Have: ${balance:.2f}\n"
                f"Short: ${total_price - balance:.2f}\n\n"
                f"Please recharge your account.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        # Show confirmation
        session_type = context.user_data['session_type']
        
        text = (
            f"📊 **Purchase Summary**\n\n"
            f"🌍 Country: {country_name} ({country_code})\n"
            f"📦 Quantity: {quantity} sessions\n"
            f"📁 Type: {session_type.upper()}\n"
            f"💰 Price: ${price_per:.2f} × {quantity}\n"
            f"💵 Total: **${total_price:.2f}**\n\n"
            f"💳 Your balance: ${balance:.2f}\n"
            f"💳 After purchase: ${balance - total_price:.2f}\n\n"
            f"Confirm purchase?"
        )
        
        context.user_data['purchase_quantity'] = quantity
        context.user_data['purchase_total'] = total_price
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm", callback_data='confirm_bulk_purchase'),
                InlineKeyboardButton("❌ Cancel", callback_data='cancel_purchase')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid number!\n\n"
            "Please enter a valid quantity (e.g., 10)"
        )
        return WAITING_QUANTITY

async def confirm_bulk_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process bulk purchase and extract sessions"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Get purchase details
    bulk_id = context.user_data.get('selected_bulk_id')
    quantity = context.user_data.get('purchase_quantity')
    total_price = context.user_data.get('purchase_total')
    country_code = context.user_data.get('selected_country')
    session_type = context.user_data.get('session_type')
    
    if not all([bulk_id, quantity, total_price, country_code]):
        await query.message.edit_text("❌ Session expired. Please try again.")
        return
    
    # Get bulk
    bulk = BulkSession.get_by_id(bulk_id)
    if not bulk:
        await query.message.edit_text("❌ Sessions no longer available")
        return
    
    # Purchase sessions (marks as sold in DB)
    await query.message.edit_text("⏳ Processing purchase...")
    
    purchased_indices, error = BulkSession.purchase_sessions(bulk_id, quantity)
    if error:
        await query.message.edit_text(f"❌ Purchase failed!\n\n{error}")
        return
    
    # Deduct balance
    User.update_balance(user_id, total_price, operation='subtract')
    
    # Extract sessions from bulk ZIP
    await query.message.edit_text(
        "⏳ **Preparing your sessions...**\n"
        "(Extracting from bulk ZIP)\n\n"
        "This may take a moment..."
    )
    
    new_file_id, error = await extract_sessions_from_bulk(
        context.bot,
        bulk['file_id'],
        purchased_indices,
        session_type
    )
    
    if error:
        # Refund on extraction failure
        User.update_balance(user_id, total_price, operation='add')
        # Return sessions to bulk
        # (You may want to add a method to reverse the purchase)
        
        await query.message.edit_text(
            f"❌ **Extraction Error!**\n\n"
            f"Error: {error}\n\n"
            f"Your payment has been **refunded**.\n"
            f"Please contact support if this persists."
        )
        return
    
    # Create purchase record
    Purchase.create(
        user_id=user_id,
        bulk_id=bulk_id,
        country_code=country_code,
        quantity=quantity,
        price_paid=total_price,
        session_type=session_type,
        purchased_indices=purchased_indices,
        zip_file_id=new_file_id
    )
    
    info = get_country_info(country_code)
    country_name = info['name'] if info else country_code
    
    # Get new balance
    user = User.get_by_telegram_id(user_id)
    new_balance = user['balance']
    
    # Get 2FA password from bulk
    has_2fa = bulk.get('has_2fa', False)
    two_fa_password = bulk.get('two_fa_password')
    
    text = (
        f"✅ **Purchase Successful!**\n\n"
        f"🌍 Country: {country_name} ({country_code})\n"
        f"📦 Quantity: {quantity} sessions\n"
        f"📁 Type: {session_type.upper()}\n"
        f"💰 Paid: ${total_price:.2f}\n"
        f"💳 New Balance: ${new_balance:.2f}\n"
    )
    
    # Add 2FA password if exists
    if has_2fa and two_fa_password:
        text += f"🔒 2FA Password: `{two_fa_password}`\n"
    else:
        text += f"🔒 2FA: No\n"
    
    text += f"\n📥 Sending your sessions..."
    
    await query.message.edit_text(text, parse_mode='Markdown')
    
    # Send ZIP file
    try:
        caption = f"📦 {quantity} × {country_name} sessions"
        if has_2fa and two_fa_password:
            caption += f"\n🔒 2FA: {two_fa_password}"
        
        await context.bot.send_document(
            chat_id=user_id,
            document=new_file_id,
            caption=caption
        )
    except Exception as e:
        logger.error(f"Error sending file: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text="❌ Error sending file. Please contact support with your purchase ID."
        )
    
    # Clear context
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel purchase"""
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text(
        "❌ Purchase cancelled.\n\n"
        "No charges made."
    )
    
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel and return to main menu"""
    query = update.callback_query
    await query.answer()
    
    context.user_data.clear()
    await show_main_menu(update, context)
    return ConversationHandler.END
async def start_recharge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start recharge process with preset amounts"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    # Get minimum deposit from database
    min_deposit = SystemSettings.get_min_deposit()
    
    # Preset amount buttons
    keyboard = [
        [
            InlineKeyboardButton("💵 $5", callback_data='preset_5'),
            InlineKeyboardButton("💵 $10", callback_data='preset_10'),
            InlineKeyboardButton("💵 $20", callback_data='preset_20')
        ],
        [
            InlineKeyboardButton("💵 $50", callback_data='preset_50'),
            InlineKeyboardButton("💵 $100", callback_data='preset_100')
        ],
        [
            InlineKeyboardButton("✏️ Custom Amount", callback_data='custom_amount')
        ],
        [InlineKeyboardButton(MESSAGES[lang]['cancel'], callback_data='cancel_deposit')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    deposit_msg = f"💳 Enter deposit amount in USD (minimum ${min_deposit:.0f}):\n\n💡 Or choose a preset amount:"
    
    await query.message.edit_text(
        deposit_msg,
        reply_markup=reply_markup
    )
    
    return WAITING_DEPOSIT_AMOUNT

async def handle_preset_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """✅ NEW - Handle preset amount selection"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    # Extract amount from callback data (e.g., "preset_10" -> 10)
    amount = float(query.data.split('_')[1])
    
    # Store amount
    context.user_data['deposit_amount'] = amount
    
    # Show payment method selection
    keyboard = [
        [InlineKeyboardButton(MESSAGES[lang]['usdt_bep20'], callback_data='deposit_bep20')],
        [InlineKeyboardButton(MESSAGES[lang]['usdt_trc20'], callback_data='deposit_trc20')],
        [InlineKeyboardButton(MESSAGES[lang]['cancel'], callback_data='cancel_deposit')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        f"💰 Amount: ${amount:.2f}\n\n{MESSAGES[lang]['deposit_method']}",
        reply_markup=reply_markup
    )
    
    return ConversationHandler.END

async def handle_custom_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """✅ NEW - Handle custom amount button - asks user to type amount"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    # Get min deposit from settings
    from database import SystemSettings
    settings = SystemSettings.get()
    min_deposit = settings.get('min_deposit', 1.0)
    
    keyboard = [
        [InlineKeyboardButton(MESSAGES[lang]['cancel'], callback_data='cancel_deposit')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        f"💵 **Enter Custom Amount**\n\n"
        f"Type the amount you want to deposit in USD.\n\n"
        f"Example: 15 or 25.50\n\n"
        f"Minimum: ${min_deposit:.2f}",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    # ✅ FIXED: Don't end conversation, keep it active for text input
    return WAITING_DEPOSIT_AMOUNT

async def receive_deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """✅ FIXED - Receive custom deposit amount"""
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    try:
        amount = float(update.message.text.strip().replace('$', ''))
        
        # ✅ Check against minimum deposit from settings
        from database import SystemSettings
        settings = SystemSettings.get()
        min_deposit = settings.get('min_deposit', 1.0)
        
        if amount < min_deposit:
            await update.message.reply_text(
                f"❌ Amount too low!\n\n"
                f"Minimum deposit: ${min_deposit:.2f}\n"
                f"You entered: ${amount:.2f}\n\n"
                f"Please enter an amount of at least ${min_deposit:.2f}:"
            )
            return WAITING_DEPOSIT_AMOUNT
        
        # Store amount
        context.user_data['deposit_amount'] = amount
        
        # Show payment method selection
        keyboard = [
            [InlineKeyboardButton(MESSAGES[lang]['usdt_bep20'], callback_data='deposit_bep20')],
            [InlineKeyboardButton(MESSAGES[lang]['usdt_trc20'], callback_data='deposit_trc20')],
            [InlineKeyboardButton(MESSAGES[lang]['cancel'], callback_data='cancel_deposit')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"💰 Amount: ${amount:.2f}\n\n{MESSAGES[lang]['deposit_method']}",
            reply_markup=reply_markup
        )
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text(MESSAGES[lang]['invalid_amount'])
        return WAITING_DEPOSIT_AMOUNT

async def process_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE, network: str):
    """✅ FIXED - Process deposit with specific network"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    amount = context.user_data.get('deposit_amount', 0)
    
    if amount <= 0:
        await query.edit_message_text("❌ Invalid amount. Please try again.")
        return
    
    # ✅ Generate unique random amount (1-30 thousandths = max 0.03)
    # Kept small to avoid payment verification issues
    random_micro = random.randint(1, 30)
    exact_amount = amount + (random_micro / 1000)  # e.g., 5.001, 5.015, 5.030
    
    # Get wallet address based on network
    if network == 'bep20':
        wallet = config.USDT_BEP20_WALLET
        network_name = "BEP-20 (BSC)"
    else:  # trc20
        wallet = config.USDT_TRC20_WALLET
        network_name = "TRC-20 (TRON)"
    
    try:
        # Create transaction record
        transaction_id = Transaction.create(
            user_id=user_id,
            amount=amount,
            payment_method=f'USDT-{network.upper()}',
            transaction_type='deposit'
        )
        
        # Update transaction with crypto details
        from database import get_db
        db = get_db()
        db.transactions.update_one(
            {"_id": transaction_id},
            {"$set": {
                "crypto_amount": exact_amount,
                "crypto_address": wallet,
                "network": network_name
            }}
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
                f"💰 New Deposit Request\n\n"
                f"👤 User ID: {user_id}\n"
                f"💵 Amount: ${amount:.2f}\n"
                f"🎯 Exact: {exact_amount:.3f} USDT\n"
                f"🌐 Network: {network_name}\n"
                f"📍 Wallet: {wallet[:10]}...\n"
                f"🆔 Transaction ID: {transaction_id}"
            )
            await context.bot.send_message(
                chat_id=config.OWNER_ID,
                text=admin_text
            )
        except Exception as e:
            logger.error(f"Could not notify admin: {e}")
        
        # Start payment verification in background
        asyncio.create_task(verify_payment(transaction_id, user_id, wallet, exact_amount, network, context.bot))
        
    except Exception as e:
        logger.error(f"❌ Error processing deposit: {e}")
        import traceback
        traceback.print_exc()
        
        await query.edit_message_text(
            f"❌ Error processing deposit.\n\n"
            f"Please try again or contact support.\n\n"
            f"Error: {str(e)}"
        )

async def verify_payment(transaction_id, user_id: int, wallet: str, expected_amount: float, network: str, bot):
    """✅ FIXED - Verify crypto payment (background task)"""
    lang = get_user_language(user_id)
    
    try:
        logger.info(f"🔍 Starting payment verification for user {user_id}")
        logger.info(f"   Expected: {expected_amount:.3f} USDT on {network}")
        
        # Wait 30 seconds before first check (give time for transaction to confirm)
        await asyncio.sleep(30)
        
        # Check for payment - reduced frequency to avoid rate limits
        max_checks = 40  # 10 minutes (40 * 15 seconds)
        
        for i in range(max_checks):
            await asyncio.sleep(15)  # Check every 15 seconds (instead of 10)
            
            try:
                # Check if payment received using API
                from payment import verify_crypto_payment
                verified = await verify_crypto_payment(wallet, expected_amount, network)
                
                if verified:
                    logger.info(f"✅ Payment verified for user {user_id}!")
                    
                    # Update transaction
                    Transaction.update_status(transaction_id, 'completed')
                    
                    # Get transaction to get amount
                    transaction = Transaction.get_by_id(transaction_id)
                    amount = transaction.get('amount', 0)
                    
                    # Add balance
                    User.update_balance(user_id, amount, operation='add')
                    
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
                            f"✅ Payment Verified!\n\n"
                            f"👤 User ID: {user_id}\n"
                            f"💰 Amount: ${amount:.2f}\n"
                            f"✅ Credited successfully"
                        )
                        await bot.send_message(
                            chat_id=config.OWNER_ID,
                            text=admin_text
                        )
                    except Exception as e:
                        logger.error(f"Could not notify admin: {e}")
                    
                    return
                    
            except Exception as e:
                logger.error(f"Error checking payment: {e}")
            
            # Status update every 2 minutes (8 checks * 15 seconds)
            if i > 0 and i % 8 == 0:
                minutes = (i * 15) // 60
                logger.info(f"⏳ Still checking payment for user {user_id} ({minutes} min)")
        
        # Payment not received after timeout
        logger.warning(f"⏰ Payment timeout for user {user_id}")
        # DON'T mark as failed - keep as pending so admin can manually verify
        # Transaction.update_status(transaction_id, 'failed')
        
        # Notify user
        try:
            await bot.send_message(
                chat_id=user_id,
                text=(
                    "⏰ Automatic verification timed out\n\n"
                    "Don't worry! Your payment is being verified manually.\n\n"
                    "If you sent the payment, admin will credit your balance within a few minutes.\n\n"
                    f"Transaction ID: {transaction_id}\n\n"
                    "Support: @Akash_support_bot"
                )
            )
        except:
            pass
        
        # Notify admin with manual verification command
        try:
            admin_text = (
                f"⏰ Auto-Verification Timeout\n\n"
                f"👤 User ID: {user_id}\n"
                f"💵 Expected: {expected_amount:.3f} USDT\n"
                f"🌐 Network: {network.upper()}\n"
                f"📍 Wallet: {wallet[:10]}...\n"
                f"🆔 Transaction ID: {transaction_id}\n\n"
                f"⚠️ Auto-verification failed after 10 minutes\n\n"
                f"🔍 Check manually:\n"
                f"BEP-20: https://bscscan.com/address/{wallet}\n\n"
                f"✅ To verify:\n"
                f"/verify_payment {transaction_id} {expected_amount:.3f}"
            )
            await bot.send_message(
                chat_id=config.OWNER_ID,
                text=admin_text
            )
        except:
            pass
            
    except Exception as e:
        logger.error(f"❌ Error in verify_payment: {e}")
        import traceback
        traceback.print_exc()

async def switch_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Switch user language"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    current_lang = get_user_language(user_id)
    new_lang = 'zh' if current_lang == 'en' else 'en'
    
    User.update_language(user_id, new_lang)
    
    await query.answer(MESSAGES[new_lang]['language_switched'])
    await show_main_menu(update, context)





async def handle_persistent_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle persistent keyboard button presses"""
    text = update.message.text
    user_id = update.effective_user.id
    lang = get_user_language(user_id)
    
    # Products button
    if text in ["🛒 Products", "🛒 商品"]:
        # Show continent selection for products
        keyboard = []
        for continent_id, continent_data in CONTINENTS.items():
            continent_name = continent_data['name'][lang]
            keyboard.append([InlineKeyboardButton(continent_name, callback_data=f'continent_{continent_id}')])
        
        keyboard.append([InlineKeyboardButton(MESSAGES[lang]['back'], callback_data='back_to_menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            MESSAGES[lang]['select_continent'],
            reply_markup=reply_markup
        )
    
    # Recharge button
    elif text in ["🌐 Recharge", "🌐 充值"]:
        # Get minimum deposit from database
        min_deposit = SystemSettings.get_min_deposit()
        
        # Preset amount buttons
        keyboard = [
            [
                InlineKeyboardButton("💵 $5", callback_data='preset_5'),
                InlineKeyboardButton("💵 $10", callback_data='preset_10'),
                InlineKeyboardButton("💵 $20", callback_data='preset_20')
            ],
            [
                InlineKeyboardButton("💵 $50", callback_data='preset_50'),
                InlineKeyboardButton("💵 $100", callback_data='preset_100')
            ],
            [
                InlineKeyboardButton("✏️ Custom Amount", callback_data='custom_amount')
            ],
            [InlineKeyboardButton(MESSAGES[lang]['cancel'], callback_data='cancel_deposit')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        deposit_msg = f"💳 Enter deposit amount in USD (minimum ${min_deposit:.0f}):\n\n💡 Or choose a preset amount:"
        
        await update.message.reply_text(
            deposit_msg,
            reply_markup=reply_markup
        )
    
    # Contact Customer Service button
    elif text in ["📞 Contact Customer Service", "📞 联系客服"]:
        keyboard = [[InlineKeyboardButton("💬 Contact Support", url='https://t.me/support')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📞 Customer Service\n\nClick below to contact our support team:",
            reply_markup=reply_markup
        )
    
    # Personal Center button
    elif text in ["👤 Personal Center", "👤 个人中心"]:
        user = User.get_by_telegram_id(user_id)
        if user:
            balance = user.get('balance', 0)
            created_at = user.get('created_at', 'N/A')
            
            info_text = MESSAGES[lang]['user_info'].format(
                user_id,
                balance,
                created_at
            )
        else:
            info_text = "❌ User not found"
        
        keyboard = [[InlineKeyboardButton(MESSAGES[lang]['back'], callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(info_text, reply_markup=reply_markup)
    
    # Language button
    elif text in ["🌍 Language", "🌍 语言"]:
        current_lang = get_user_language(user_id)
        new_lang = 'zh' if current_lang == 'en' else 'en'
        User.update_language(user_id, new_lang)
        
        persistent_kb = get_persistent_keyboard(new_lang)
        await update.message.reply_text(
            MESSAGES[new_lang]['language_switched'],
            reply_markup=persistent_kb
        )
    
    # Rules button
    elif text in ["⚠️ Rules", "⚠️ 规则"]:
        rules_text = (
            "⚠️ **Bot Rules**\n\n"
            "1. No refunds after purchase\n"
            "2. Sessions are delivered instantly\n"
            "3. Contact support for issues\n"
            "4. Minimum deposit: $1\n"
            "5. Use exact USDT amounts for deposits"
            if lang == 'en' else
            "⚠️ **机器人规则**\n\n"
            "1. 购买后不退款\n"
            "2. 会话即时交付\n"
            "3. 如有问题请联系客服\n"
            "4. 最低充值: $1\n"
            "5. 充值请使用准确的USDT金额"
        )
        keyboard = [[InlineKeyboardButton(MESSAGES[lang]['back'], callback_data='back_to_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            rules_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def handle_country_code_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text input for country codes - Show product list"""
    text = update.message.text.strip()
    
    # Check if it's a country code
    if text.startswith('+'):
        country_code = text
        
        # Validate the country code
        info = get_country_info(country_code)
        if not info:
            await update.message.reply_text(
                "❌ Invalid country code!\n\n"
                "Use /start for menu."
            )
            return
        
        # Get available bulks
        bulks = BulkSession.get_by_country(country_code)
        
        if not bulks:
            await update.message.reply_text(
                f"❌ No sessions for {info['name']} ({country_code})"
            )
            return
        
        # Calculate stats
        total_available = sum(b['remaining_count'] for b in bulks)
        min_price = min(b['price_per_session'] for b in bulks)
        country_name = info['name']
        
        # Show product list with button (like in your image)
        text_msg = f"**Products for {country_code} ({country_name}):**"
        
        button_text = f"{country_name} {country_code} — {min_price:.2f} (stock:{total_available})"
        keyboard = [
            [InlineKeyboardButton(button_text, callback_data=f'country_{country_code}')],
            [InlineKeyboardButton("⬅️ Back", callback_data='product_list')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text_msg, reply_markup=reply_markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """✅ FIXED - Handle all callback queries"""
    query = update.callback_query
    data = query.data
    
    # Main menu buttons
    if data == 'back_to_menu':
        await show_main_menu(update, context)
    elif data == 'user_center':
        await show_user_center(update, context)
    elif data == 'product_list':
        await show_product_list(update, context)
    elif data == 'switch_language':
        await switch_language(update, context)
    elif data == 'cancel_deposit':
        await query.answer()
        await show_main_menu(update, context)
    
    # Continent selection
    elif data.startswith('continent_'):
        await show_continent_countries(update, context)
    
    # Country selection
    elif data.startswith('country_'):
        await show_main_menu(update, context)
    
    # Session purchase
    elif data.startswith('buy_session_'):
        await buy_session(update, context)
    
    # ✅ Preset amounts
    elif data.startswith('preset_'):
        await handle_preset_amount(update, context)
    
    # ✅ REMOVED: custom_amount is now handled by ConversationHandler
    
    # Payment network selection
    elif data == 'deposit_bep20':
        await process_deposit(update, context, 'bep20')
    elif data == 'deposit_trc20':
        await process_deposit(update, context, 'trc20')


def main():
    """Start the bot"""
    # Initialize database
    init_db()
    
    # ✅ FIXED: Create application FIRST before adding any handlers
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    # Setup admin handlers
    setup_admin_handlers(application)
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    
    # Quantity selection conversation
    quantity_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(select_country, pattern='^country_'),
        ],
        states={
            WAITING_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_quantity)]
        },
        fallbacks=[CallbackQueryHandler(cancel_to_menu, pattern='^product_list$'), CallbackQueryHandler(cancel_purchase, pattern='^cancel_purchase$')],
        allow_reentry=True
    )
    application.add_handler(quantity_conv)
    
    # Purchase confirmation handlers
    application.add_handler(CallbackQueryHandler(confirm_bulk_purchase, pattern='^confirm_bulk_purchase$'))
    application.add_handler(CallbackQueryHandler(cancel_purchase, pattern='^cancel_purchase$'))
    
    # Recharge conversation handler
    recharge_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_recharge, pattern='^recharge$'),
            CallbackQueryHandler(handle_custom_amount, pattern='^custom_amount$')
        ],
        states={
            WAITING_DEPOSIT_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_deposit_amount),
                CallbackQueryHandler(handle_custom_amount, pattern='^custom_amount$')
            ],
        },
        fallbacks=[CallbackQueryHandler(show_main_menu, pattern='^cancel_deposit$')],
        allow_reentry=True
    )
    application.add_handler(recharge_conv)
    
    # Persistent keyboard button handler
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.Regex(r"^\+\d+"),
        handle_persistent_buttons
    ))
    
    # Text handler for country codes
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^\+\d+"), handle_country_code_text))

    # Callback handlers
    application.add_handler(CallbackQueryHandler(button_handler))
    
    
    # Start bot
    logger.info("🤖 Bot started successfully!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()