import logging
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

def format_datetime(dt: datetime, lang: str = 'en') -> str:
    """Format datetime based on language"""
    if lang == 'zh':
        return dt.strftime('%Y年%m月%d日 %H:%M')
    else:
        return dt.strftime('%Y-%m-%d %H:%M')

def format_currency(amount: float, lang: str = 'en') -> str:
    """Format currency amount"""
    if lang == 'zh':
        return f"${amount:.2f}"
    else:
        return f"${amount:.2f}"

def validate_country_code(code: str) -> bool:
    """Validate country code format"""
    if not code.startswith('+'):
        return False
    if len(code) < 2 or len(code) > 5:
        return False
    try:
        int(code[1:])
        return True
    except ValueError:
        return False

def calculate_exact_amount(base_amount: float, fee_percent: float = 1.7) -> float:
    """Calculate exact amount with fee"""
    return base_amount * (1 + fee_percent / 100)

def get_country_name(country_code: str, lang: str = 'en') -> str:
    """Get country name from code"""
    from bot import CONTINENTS
    
    for continent_data in CONTINENTS.values():
        if country_code in continent_data['countries']:
            country_data = continent_data['countries'][country_code]
            return country_data['name_zh'] if lang == 'zh' else country_data['name']
    
    return country_code

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    import re
    # Remove any characters that aren't alphanumeric, dots, dashes, or underscores
    filename = re.sub(r'[^\w\s.-]', '', filename)
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    return filename

def generate_transaction_id() -> str:
    """Generate unique transaction ID"""
    import uuid
    return str(uuid.uuid4())[:8].upper()

def parse_amount(text: str) -> Optional[float]:
    """Parse amount from text input"""
    try:
        # Remove common currency symbols and whitespace
        text = text.strip().replace('$', '').replace('₹', '').replace(',', '')
        amount = float(text)
        return amount if amount > 0 else None
    except ValueError:
        return None

def format_session_info(session: Dict, lang: str = 'en') -> str:
    """Format session information for display"""
    country = session.get('country', 'Unknown')
    phone = session.get('phone_number', 'N/A')
    price = session.get('price', 0.0)
    info = session.get('info', 'No description')
    
    country_name = get_country_name(country, lang)
    
    if lang == 'zh':
        return (
            f"🌍 国家: {country_name} ({country})\n"
            f"📱 号码: {phone}\n"
            f"💰 价格: ${price:.2f}\n"
            f"ℹ️ 信息: {info}"
        )
    else:
        return (
            f"🌍 Country: {country_name} ({country})\n"
            f"📱 Phone: {phone}\n"
            f"💰 Price: ${price:.2f}\n"
            f"ℹ️ Info: {info}"
        )

def get_transaction_status_emoji(status: str) -> str:
    """Get emoji for transaction status"""
    status_map = {
        'pending': '⏳',
        'completed': '✅',
        'failed': '❌',
        'cancelled': '🚫'
    }
    return status_map.get(status, '❓')

def format_transaction(transaction: Dict, lang: str = 'en') -> str:
    """Format transaction information"""
    amount = transaction.get('amount', 0)
    tx_type = transaction.get('transaction_type', 'unknown')
    status = transaction.get('status', 'unknown')
    created_at = transaction.get('created_at', datetime.now())
    
    status_emoji = get_transaction_status_emoji(status)
    
    if lang == 'zh':
        type_names = {
            'deposit': '充值',
            'purchase': '购买',
            'admin_credit': '管理员添加',
            'admin_debit': '管理员扣除'
        }
        type_name = type_names.get(tx_type, tx_type)
        
        return (
            f"{status_emoji} {type_name}\n"
            f"💰 金额: ${amount:.2f}\n"
            f"📅 日期: {format_datetime(created_at, lang)}\n"
            f"📊 状态: {status}"
        )
    else:
        return (
            f"{status_emoji} {tx_type.title()}\n"
            f"💰 Amount: ${amount:.2f}\n"
            f"📅 Date: {format_datetime(created_at, lang)}\n"
            f"📊 Status: {status}"
        )

def truncate_text(text: str, max_length: int = 50, suffix: str = '...') -> str:
    """Truncate text to maximum length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def is_valid_wallet_address(address: str, network: str) -> bool:
    """Validate crypto wallet address format"""
    if network == 'bep20':
        # BEP-20 (BSC) addresses start with 0x and are 42 characters
        return address.startswith('0x') and len(address) == 42
    elif network == 'trc20':
        # TRC-20 (TRON) addresses start with T and are 34 characters
        return address.startswith('T') and len(address) == 34
    return False

def calculate_statistics(users: List[Dict], sessions: List[Dict], transactions: List[Dict]) -> Dict:
    """Calculate bot statistics"""
    total_users = len(users)
    active_users = len([u for u in users if not u.get('is_banned', False)])
    banned_users = len([u for u in users if u.get('is_banned', False)])
    
    available_sessions = len([s for s in sessions if not s.get('is_sold', False)])
    sold_sessions = len([s for s in sessions if s.get('is_sold', False)])
    
    total_deposits = sum(t['amount'] for t in transactions if t['transaction_type'] == 'deposit' and t['status'] == 'completed')
    total_purchases = sum(t['amount'] for t in transactions if t['transaction_type'] == 'purchase' and t['status'] == 'completed')
    
    pending_deposits = len([t for t in transactions if t['transaction_type'] == 'deposit' and t['status'] == 'pending'])
    
    return {
        'total_users': total_users,
        'active_users': active_users,
        'banned_users': banned_users,
        'available_sessions': available_sessions,
        'sold_sessions': sold_sessions,
        'total_deposits': total_deposits,
        'total_purchases': total_purchases,
        'total_revenue': total_purchases,
        'pending_deposits': pending_deposits
    }

def get_language_flag(lang: str) -> str:
    """Get flag emoji for language"""
    flags = {
        'en': '🇬🇧',
        'zh': '🇨🇳'
    }
    return flags.get(lang, '🌐')

def escape_markdown(text: str) -> str:
    """Escape special characters for Markdown"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text