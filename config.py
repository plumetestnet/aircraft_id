import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID', '0'))

ADMIN_IDS_STR = os.getenv('ADMIN_IDS', '')
if ADMIN_IDS_STR:
    ADMIN_IDS = [int(id.strip()) for id in ADMIN_IDS_STR.split(',') if id.strip()]
else:
    ADMIN_IDS = []
# All admins = owner + additional admins
ALL_ADMINS = [OWNER_ID] + ADMIN_IDS

# Telegram API credentials
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')

# Alternative names for compatibility
TELEGRAM_API_ID = API_ID
TELEGRAM_API_HASH = API_HASH

# ✅ Storage Group ID for sessions and tdata files
STORAGE_GROUP_ID = -1003611140902

# MongoDB
MONGODB_URI = os.getenv('MONGODB_URI')
MONGODB_URL = MONGODB_URI  # Alternative name

# Crypto wallets
USDT_BEP20_WALLET = os.getenv('USDT_BEP20_WALLET', '0x10dE74EBDFa84f5e6390a1A61DEad8d491754039')
USDT_TRC20_WALLET = os.getenv('USDT_TRC20_WALLET', 'TGgcKJ32bL4qtt8BaXuwvZQtmVfA8cUujL')

# BSCScan API (for BEP-20 verification)
BSCSCAN_API_KEY = os.getenv('BSCSCAN_API_KEY', '4PP2HAPX69PZQW1886QS9J3YEMJ94RA17V')

# TronGrid API (for TRC-20 verification)
TRONGRID_API_KEY = os.getenv('TRONGRID_API_KEY', 'd826000c-48be-4f05-9640-d6a8ffe20b39')

# Minimum deposit
MIN_DEPOSIT = float(os.getenv('MIN_DEPOSIT', '1.0'))
DATABASE_PATH = os.getenv('DATABASE_PATH', 'bot.db')
# Verification fee (1.7%)
# VERIFICATION_FEE = 0.017