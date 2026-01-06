import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID', '0'))

# Telegram API credentials
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')

# Alternative names for compatibility
TELEGRAM_API_ID = API_ID
TELEGRAM_API_HASH = API_HASH

# MongoDB
MONGODB_URI = os.getenv('MONGODB_URI')
MONGODB_URL = MONGODB_URI  # Alternative name

# Crypto wallets
USDT_BEP20_WALLET = os.getenv('USDT_BEP20_WALLET', '0xfcba958d6e6ea95beecf0919772dd9e9ea32bd33')
USDT_TRC20_WALLET = os.getenv('USDT_TRC20_WALLET', 'TGgcKJ32bL4qtt8BaXuwvZQtmVfA8cUujL')

# BSCScan API (for BEP-20 verification)
BSCSCAN_API_KEY = os.getenv('BSCSCAN_API_KEY', '')

# TronGrid API (for TRC-20 verification)
TRONGRID_API_KEY = os.getenv('TRONGRID_API_KEY', '')

# Minimum deposit
MIN_DEPOSIT = float(os.getenv('MIN_DEPOSIT', '1.0'))

# Verification fee (1.7%)
VERIFICATION_FEE = 0.017