import logging
import aiohttp
import config

logger = logging.getLogger(__name__)

async def verify_crypto_payment(wallet: str, expected_amount: float, network: str = 'bep20') -> bool:
    """
    Verify crypto payment using blockchain API
    
    Args:
        wallet: Wallet address to check
        expected_amount: Expected USDT amount
        network: 'bep20' or 'trc20'
    
    Returns:
        bool: True if payment verified, False otherwise
    """
    try:
        if network == 'bep20':
            return await verify_bep20_payment(wallet, expected_amount)
        elif network == 'trc20':
            return await verify_trc20_payment(wallet, expected_amount)
        else:
            logger.error(f"Unknown network: {network}")
            return False
    except Exception as e:
        logger.error(f"Error verifying payment: {e}")
        return False

async def verify_bep20_payment(wallet: str, expected_amount: float) -> bool:
    """
    Verify BEP-20 USDT payment using BSCScan API
    """
    if not config.BSCSCAN_API_KEY:
        logger.warning("BSCScan API key not configured")
        return False
    
    try:
        # USDT contract on BSC
        usdt_contract = "0x55d398326f99059fF775485246999027B3197955"
        
        url = "https://api.bscscan.com/api"
        params = {
            'module': 'account',
            'action': 'tokentx',
            'contractaddress': usdt_contract,
            'address': wallet,
            'sort': 'desc',
            'apikey': config.BSCSCAN_API_KEY
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                
                if data['status'] == '1' and data['result']:
                    # Check recent transactions
                    for tx in data['result'][:10]:  # Check last 10 transactions
                        # Convert from smallest unit (18 decimals for USDT)
                        amount = float(tx['value']) / (10 ** 18)
                        
                        # Check if amount matches (with small tolerance)
                        if abs(amount - expected_amount) < 0.01:
                            logger.info(f"✅ BEP-20 payment verified: {amount} USDT")
                            return True
                
                return False
    except Exception as e:
        logger.error(f"Error verifying BEP-20 payment: {e}")
        return False

async def verify_trc20_payment(wallet: str, expected_amount: float) -> bool:
    """
    Verify TRC-20 USDT payment using TronGrid API
    """
    try:
        # USDT contract on TRON
        usdt_contract = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
        
        url = f"https://api.trongrid.io/v1/accounts/{wallet}/transactions/trc20"
        params = {
            'limit': 20,
            'contract_address': usdt_contract
        }
        
        headers = {}
        if config.TRONGRID_API_KEY:
            headers['TRON-PRO-API-KEY'] = config.TRONGRID_API_KEY
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                data = await response.json()
                
                if 'data' in data:
                    # Check recent transactions
                    for tx in data['data'][:10]:
                        if tx['to'] == wallet:
                            # Convert from smallest unit (6 decimals for USDT)
                            amount = float(tx['value']) / (10 ** 6)
                            
                            # Check if amount matches (with small tolerance)
                            if abs(amount - expected_amount) < 0.01:
                                logger.info(f"✅ TRC-20 payment verified: {amount} USDT")
                                return True
                
                return False
    except Exception as e:
        logger.error(f"Error verifying TRC-20 payment: {e}")
        return False

async def get_wallet_balance(wallet: str, network: str = 'bep20') -> float:
    """
    Get wallet USDT balance
    
    Args:
        wallet: Wallet address
        network: 'bep20' or 'trc20'
    
    Returns:
        float: Balance in USDT
    """
    try:
        if network == 'bep20':
            return await get_bep20_balance(wallet)
        elif network == 'trc20':
            return await get_trc20_balance(wallet)
        else:
            return 0.0
    except Exception as e:
        logger.error(f"Error getting wallet balance: {e}")
        return 0.0

async def get_bep20_balance(wallet: str) -> float:
    """Get BEP-20 USDT balance"""
    if not config.BSCSCAN_API_KEY:
        return 0.0
    
    try:
        usdt_contract = "0x55d398326f99059fF775485246999027B3197955"
        
        url = "https://api.bscscan.com/api"
        params = {
            'module': 'account',
            'action': 'tokenbalance',
            'contractaddress': usdt_contract,
            'address': wallet,
            'tag': 'latest',
            'apikey': config.BSCSCAN_API_KEY
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                data = await response.json()
                
                if data['status'] == '1':
                    balance = float(data['result']) / (10 ** 18)
                    return balance
                return 0.0
    except Exception as e:
        logger.error(f"Error getting BEP-20 balance: {e}")
        return 0.0

async def get_trc20_balance(wallet: str) -> float:
    """Get TRC-20 USDT balance"""
    try:
        usdt_contract = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
        
        url = f"https://api.trongrid.io/v1/accounts/{wallet}"
        
        headers = {}
        if config.TRONGRID_API_KEY:
            headers['TRON-PRO-API-KEY'] = config.TRONGRID_API_KEY
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                data = await response.json()
                
                if 'data' in data and len(data['data']) > 0:
                    account_data = data['data'][0]
                    if 'trc20' in account_data:
                        for token_address, token_data in account_data['trc20'].items():
                            if token_address == usdt_contract:
                                balance = float(token_data) / (10 ** 6)
                                return balance
                return 0.0
    except Exception as e:
        logger.error(f"Error getting TRC-20 balance: {e}")
        return 0.0