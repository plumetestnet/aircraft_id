"""
Country Code Utilities - Auto-detect country from phone number
"""

import re
import logging

logger = logging.getLogger(__name__)

# Comprehensive country code mapping
COUNTRY_CODES = {
    # Asia
    '+91': {'name': 'India', 'name_zh': '印度', 'continent': 'Asia'},
    '+86': {'name': 'China', 'name_zh': '中国', 'continent': 'Asia'},
    '+81': {'name': 'Japan', 'name_zh': '日本', 'continent': 'Asia'},
    '+82': {'name': 'South Korea', 'name_zh': '韩国', 'continent': 'Asia'},
    '+65': {'name': 'Singapore', 'name_zh': '新加坡', 'continent': 'Asia'},
    '+60': {'name': 'Malaysia', 'name_zh': '马来西亚', 'continent': 'Asia'},
    '+66': {'name': 'Thailand', 'name_zh': '泰国', 'continent': 'Asia'},
    '+84': {'name': 'Vietnam', 'name_zh': '越南', 'continent': 'Asia'},
    '+63': {'name': 'Philippines', 'name_zh': '菲律宾', 'continent': 'Asia'},
    '+62': {'name': 'Indonesia', 'name_zh': '印度尼西亚', 'continent': 'Asia'},
    '+92': {'name': 'Pakistan', 'name_zh': '巴基斯坦', 'continent': 'Asia'},
    '+880': {'name': 'Bangladesh', 'name_zh': '孟加拉国', 'continent': 'Asia'},
    '+94': {'name': 'Sri Lanka', 'name_zh': '斯里兰卡', 'continent': 'Asia'},
    '+95': {'name': 'Myanmar', 'name_zh': '缅甸', 'continent': 'Asia'},
    '+977': {'name': 'Nepal', 'name_zh': '尼泊尔', 'continent': 'Asia'},
    '+98': {'name': 'Iran', 'name_zh': '伊朗', 'continent': 'Asia'},
    '+90': {'name': 'Turkey', 'name_zh': '土耳其', 'continent': 'Asia'},
    '+966': {'name': 'Saudi Arabia', 'name_zh': '沙特阿拉伯', 'continent': 'Asia'},
    '+971': {'name': 'UAE', 'name_zh': '阿联酋', 'continent': 'Asia'},
    '+962': {'name': 'Jordan', 'name_zh': '约旦', 'continent': 'Asia'},
    '+972': {'name': 'Israel', 'name_zh': '以色列', 'continent': 'Asia'},
    '+974': {'name': 'Qatar', 'name_zh': '卡塔尔', 'continent': 'Asia'},
    '+965': {'name': 'Kuwait', 'name_zh': '科威特', 'continent': 'Asia'},
    '+855': {'name': 'Cambodia', 'name_zh': '柬埔寨', 'continent': 'Asia'},
    '+856': {'name': 'Laos', 'name_zh': '老挝', 'continent': 'Asia'},
    
    # Europe
    '+44': {'name': 'United Kingdom', 'name_zh': '英国', 'continent': 'Europe'},
    '+49': {'name': 'Germany', 'name_zh': '德国', 'continent': 'Europe'},
    '+33': {'name': 'France', 'name_zh': '法国', 'continent': 'Europe'},
    '+39': {'name': 'Italy', 'name_zh': '意大利', 'continent': 'Europe'},
    '+34': {'name': 'Spain', 'name_zh': '西班牙', 'continent': 'Europe'},
    '+31': {'name': 'Netherlands', 'name_zh': '荷兰', 'continent': 'Europe'},
    '+7': {'name': 'Russia', 'name_zh': '俄罗斯', 'continent': 'Europe'},
    '+48': {'name': 'Poland', 'name_zh': '波兰', 'continent': 'Europe'},
    '+46': {'name': 'Sweden', 'name_zh': '瑞典', 'continent': 'Europe'},
    '+47': {'name': 'Norway', 'name_zh': '挪威', 'continent': 'Europe'},
    '+45': {'name': 'Denmark', 'name_zh': '丹麦', 'continent': 'Europe'},
    '+358': {'name': 'Finland', 'name_zh': '芬兰', 'continent': 'Europe'},
    '+41': {'name': 'Switzerland', 'name_zh': '瑞士', 'continent': 'Europe'},
    '+43': {'name': 'Austria', 'name_zh': '奥地利', 'continent': 'Europe'},
    '+32': {'name': 'Belgium', 'name_zh': '比利时', 'continent': 'Europe'},
    '+30': {'name': 'Greece', 'name_zh': '希腊', 'continent': 'Europe'},
    '+351': {'name': 'Portugal', 'name_zh': '葡萄牙', 'continent': 'Europe'},
    '+353': {'name': 'Ireland', 'name_zh': '爱尔兰', 'continent': 'Europe'},
    '+420': {'name': 'Czech Republic', 'name_zh': '捷克', 'continent': 'Europe'},
    '+36': {'name': 'Hungary', 'name_zh': '匈牙利', 'continent': 'Europe'},
    '+40': {'name': 'Romania', 'name_zh': '罗马尼亚', 'continent': 'Europe'},
    '+380': {'name': 'Ukraine', 'name_zh': '乌克兰', 'continent': 'Europe'},
    
    # Americas
    '+1': {'name': 'USA/Canada', 'name_zh': '美国/加拿大', 'continent': 'America'},
    '+52': {'name': 'Mexico', 'name_zh': '墨西哥', 'continent': 'America'},
    '+55': {'name': 'Brazil', 'name_zh': '巴西', 'continent': 'America'},
    '+54': {'name': 'Argentina', 'name_zh': '阿根廷', 'continent': 'America'},
    '+56': {'name': 'Chile', 'name_zh': '智利', 'continent': 'America'},
    '+57': {'name': 'Colombia', 'name_zh': '哥伦比亚', 'continent': 'America'},
    '+51': {'name': 'Peru', 'name_zh': '秘鲁', 'continent': 'America'},
    '+58': {'name': 'Venezuela', 'name_zh': '委内瑞拉', 'continent': 'America'},
    '+593': {'name': 'Ecuador', 'name_zh': '厄瓜多尔', 'continent': 'America'},
    '+507': {'name': 'Panama', 'name_zh': '巴拿马', 'continent': 'America'},
    
    # Africa
    '+27': {'name': 'South Africa', 'name_zh': '南非', 'continent': 'Africa'},
    '+234': {'name': 'Nigeria', 'name_zh': '尼日利亚', 'continent': 'Africa'},
    '+254': {'name': 'Kenya', 'name_zh': '肯尼亚', 'continent': 'Africa'},
    '+20': {'name': 'Egypt', 'name_zh': '埃及', 'continent': 'Africa'},
    '+212': {'name': 'Morocco', 'name_zh': '摩洛哥', 'continent': 'Africa'},
    '+233': {'name': 'Ghana', 'name_zh': '加纳', 'continent': 'Africa'},
    '+256': {'name': 'Uganda', 'name_zh': '乌干达', 'continent': 'Africa'},
    '+255': {'name': 'Tanzania', 'name_zh': '坦桑尼亚', 'continent': 'Africa'},
    '+251': {'name': 'Ethiopia', 'name_zh': '埃塞俄比亚', 'continent': 'Africa'},
    
    # Oceania
    '+61': {'name': 'Australia', 'name_zh': '澳大利亚', 'continent': 'Oceania'},
    '+64': {'name': 'New Zealand', 'name_zh': '新西兰', 'continent': 'Oceania'},
}


def extract_country_code(phone_number):
    """
    Extract country code from phone number
    
    Args:
        phone_number: Phone number (with or without +)
    
    Returns:
        tuple: (country_code, remaining_number) or (None, phone_number)
    
    Examples:
        '+919876543210' → ('+91', '9876543210')
        '919876543210' → ('+91', '9876543210')
        '+14151234567' → ('+1', '4151234567')
    """
    # Ensure it starts with +
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number
    
    # Try matching country codes from longest to shortest
    # Sort by length (descending) to match longer codes first
    sorted_codes = sorted(COUNTRY_CODES.keys(), key=len, reverse=True)
    
    for code in sorted_codes:
        if phone_number.startswith(code):
            remaining = phone_number[len(code):]
            return (code, remaining)
    
    return (None, phone_number)


def get_country_info(country_code):
    """
    Get country information from country code
    
    Args:
        country_code: Country code (e.g., '+91', '+1')
    
    Returns:
        dict: Country info or None
    
    Example:
        get_country_info('+91') → {
            'name': 'India',
            'name_zh': '印度',
            'continent': 'Asia'
        }
    """
    if not country_code.startswith('+'):
        country_code = '+' + country_code
    
    return COUNTRY_CODES.get(country_code)


def detect_country_from_phone(phone_number):
    """
    Auto-detect country from phone number
    
    Args:
        phone_number: Full phone number
    
    Returns:
        dict: {
            'country_code': '+91',
            'country_name': 'India',
            'country_name_zh': '印度',
            'continent': 'Asia',
            'phone_number': '9876543210'  # without country code
        } or None if not detected
    
    Examples:
        detect_country_from_phone('+919876543210') → 
        {
            'country_code': '+91',
            'country_name': 'India',
            'country_name_zh': '印度',
            'continent': 'Asia',
            'phone_number': '9876543210'
        }
    """
    country_code, remaining = extract_country_code(phone_number)
    
    if not country_code:
        logger.warning(f"Could not detect country code from: {phone_number}")
        return None
    
    country_info = get_country_info(country_code)
    
    if not country_info:
        logger.warning(f"Unknown country code: {country_code}")
        return None
    
    return {
        'country_code': country_code,
        'country_name': country_info['name'],
        'country_name_zh': country_info['name_zh'],
        'continent': country_info['continent'],
        'phone_number': remaining
    }


def validate_phone_number(phone_number):
    """
    Validate phone number format
    
    Args:
        phone_number: Phone number to validate
    
    Returns:
        tuple: (is_valid, error_message)
    """
    # Clean phone number
    phone_number = phone_number.strip()
    
    # Check if empty
    if not phone_number:
        return (False, "Phone number is empty")
    
    # Remove spaces and dashes
    cleaned = phone_number.replace(' ', '').replace('-', '')
    
    # Check if starts with + or digit
    if not cleaned[0] in ['+', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
        return (False, "Phone number must start with + or digit")
    
    # Check if contains only valid characters
    if not re.match(r'^[\+\d]+$', cleaned):
        return (False, "Phone number contains invalid characters")
    
    # Check length
    if len(cleaned) < 10:
        return (False, "Phone number too short")
    
    if len(cleaned) > 15:
        return (False, "Phone number too long")
    
    # Try to detect country
    result = detect_country_from_phone(cleaned)
    if not result:
        return (False, f"Could not detect country from number: {cleaned}")
    
    return (True, None)


def format_phone_number(phone_number):
    """
    Format phone number with country code
    
    Args:
        phone_number: Raw phone number
    
    Returns:
        str: Formatted phone number with country code
    
    Example:
        format_phone_number('919876543210') → '+91 9876543210'
        format_phone_number('+14151234567') → '+1 4151234567'
    """
    result = detect_country_from_phone(phone_number)
    if result:
        return f"{result['country_code']} {result['phone_number']}"
    return phone_number


# Testing
if __name__ == "__main__":
    # Test cases
    test_numbers = [
        '+919876543210',
        '919876543210',
        '+14151234567',
        '+447912345678',
        '+861234567890'
    ]
    
    print("Country Detection Test\n" + "="*50)
    for number in test_numbers:
        result = detect_country_from_phone(number)
        if result:
            print(f"✅ {number}")
            print(f"   Country: {result['country_name']} ({result['country_code']})")
            print(f"   Continent: {result['continent']}")
            print(f"   Number: {result['phone_number']}")
        else:
            print(f"❌ {number} - Could not detect")
        print()