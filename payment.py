"""
Payment Verification Module
- BEP-20: Web3 (FREE, automatic)
- TRC-20: TronGrid API (FREE, automatic)
"""

from web3 import Web3
import aiohttp
import logging
import config

logger = logging.getLogger(__name__)

# BSC Public RPC Node (FREE, NO API KEY)
BSC_RPC_URL = "https://bsc-rpc.publicnode.com"

# USDT contract addresses
USDT_BEP20_CONTRACT = "0x55d398326f99059fF775485246999027B3197955"
USDT_TRC20_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

# Transfer event signature
TRANSFER_EVENT_SIGNATURE = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

# Initialize Web3 connection
w3 = Web3(Web3.HTTPProvider(BSC_RPC_URL))

def check_web3_connection():
    """Check if Web3 is connected to BSC"""
    try:
        if not w3.is_connected():
            logger.error("Web3 not connected to BSC")
            return False
        
        chain_id = w3.eth.chain_id
        if chain_id != 56:
            logger.error(f"Wrong chain! Expected 56 (BSC), got {chain_id}")
            return False
        
        logger.info(f"✅ Web3 connected to BSC (block: {w3.eth.block_number:,})")
        return True
    except Exception as e:
        logger.error(f"Web3 connection check failed: {e}")
        return False

async def verify_bep20_payment_web3(wallet: str, expected_amount: float) -> bool:
    """
    Verify BEP-20 USDT payment using Web3 (NO API KEY NEEDED!)
    
    Connects DIRECTLY to BSC blockchain via public RPC node.
    100% FREE, no rate limits, real-time.
    """
    try:
        if not check_web3_connection():
            logger.error("Web3 not connected, cannot verify payment")
            return False
        
        logger.info(f"🔍 Checking BEP-20 USDT transfers to {wallet[:10]}... (Web3)")
        
        # Get current block
        latest_block = w3.eth.block_number
        from_block = latest_block - 1000  # Check last ~1000 blocks (~50 minutes)
        
        # Calculate minimum timestamp (only accept payments from last 15 minutes)
        import time
        current_time = int(time.time())
        min_timestamp = current_time - (15 * 60)  # 15 minutes ago
        
        logger.info(f"📊 Scanning blocks {from_block:,} to {latest_block:,}")
        logger.info(f"⏰ Only accepting transactions from last 15 minutes")
        
        # Pad wallet address to 32 bytes for topic filtering
        wallet_topic = '0x' + wallet[2:].lower().zfill(64)
        
        # Get Transfer events where TO = our wallet
        logs = w3.eth.get_logs({
            'fromBlock': from_block,
            'toBlock': 'latest',
            'address': USDT_BEP20_CONTRACT,
            'topics': [
                TRANSFER_EVENT_SIGNATURE,  # Transfer event
                None,                       # From (any address)
                wallet_topic                # To (our wallet)
            ]
        })
        
        if not logs:
            logger.info("⚠️ No BEP-20 USDT transfers found in recent blocks")
            return False
        
        logger.info(f"📥 Found {len(logs)} incoming BEP-20 USDT transfer(s)")
        
        # Check each transfer
        for log in logs:
            # ✅ NEW: Get block timestamp to verify transaction is recent
            block = w3.eth.get_block(log['blockNumber'])
            block_timestamp = block['timestamp']
            
            # Skip old transactions
            if block_timestamp < min_timestamp:
                logger.info(f"⏸️ Skipping old transaction from block {log['blockNumber']} ({datetime.fromtimestamp(block_timestamp)})")
                continue
            
            # Decode amount from log data
            amount_wei = int(log['data'].hex(), 16)
            amount_usdt = amount_wei / (10 ** 18)
            
            logger.info(f"💰 Incoming (recent): {amount_usdt:.6f} USDT (expected: {expected_amount:.6f})")
            logger.info(f"   Timestamp: {datetime.fromtimestamp(block_timestamp)}")
            
            # Check if amount matches (with tolerance)
            if abs(amount_usdt - expected_amount) < 0.01:
                tx_hash = log['transactionHash'].hex()
                block_num = log['blockNumber']
                
                logger.info(f"✅ BEP-20 payment verified!")
                logger.info(f"   Amount: {amount_usdt:.6f} USDT")
                logger.info(f"   Block: {block_num:,}")
                logger.info(f"   TX: {tx_hash}")
                logger.info(f"   Time: {datetime.fromtimestamp(block_timestamp)}")
                
                return True
        
        logger.warning(f"⚠️ No matching BEP-20 payment found. Expected: {expected_amount:.6f} USDT")
        return False
        
    except Exception as e:
        logger.error(f"Error in Web3 BEP-20 verification: {e}")
        import traceback
        traceback.print_exc()
        return False

async def verify_trc20_payment(wallet: str, expected_amount: float) -> bool:
    """
    Verify TRC-20 USDT payment using TronGrid API (FREE!)
    
    Uses TronGrid API with 90k requests/day limit.
    Checks every 15 seconds = ~5,760 checks/day (plenty of headroom!)
    """
    if not config.TRONGRID_API_KEY:
        logger.warning("TronGrid API key not configured")
        return False
    
    try:
        logger.info(f"🔍 Checking TRC-20 USDT transfers to {wallet[:10]}... (TronGrid)")
        
        # Get current timestamp (in milliseconds)
        import time
        current_time = int(time.time() * 1000)
        # Only accept transactions from last 15 minutes (900,000 ms)
        min_timestamp = current_time - (15 * 60 * 1000)
        
        logger.info(f"⏰ Only checking transactions from last 15 minutes")
        
        url = f"https://api.trongrid.io/v1/accounts/{wallet}/transactions/trc20"
        headers = {'TRON-PRO-API-KEY': config.TRONGRID_API_KEY}
        params = {
            'contract_address': USDT_TRC20_CONTRACT,
            'only_to': 'true',
            'limit': 20,
            'min_timestamp': min_timestamp  # ✅ NEW: Only recent transactions
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                
                if response.status != 200:
                    logger.error(f"TronGrid API returned status {response.status}")
                    return False
                
                data = await response.json()
                
                if 'data' not in data:
                    logger.warning("⚠️ TronGrid API returned no data")
                    return False
                
                transactions = data['data']
                
                if not transactions:
                    logger.info("⚠️ No recent TRC-20 USDT transfers found")
                    return False
                
                logger.info(f"📊 Found {len(transactions)} recent TRC-20 USDT transaction(s)")
                
                # Check each transaction
                for tx in transactions:
                    # Verify it's incoming to our wallet
                    if tx.get('to') != wallet:
                        continue
                    
                    # ✅ NEW: Verify transaction is recent (within last 15 minutes)
                    tx_timestamp = tx.get('block_timestamp', 0)
                    if tx_timestamp < min_timestamp:
                        logger.info(f"⏸️ Skipping old transaction from {datetime.fromtimestamp(tx_timestamp/1000)}")
                        continue
                    
                    # Convert from smallest unit (6 decimals for TRC-20 USDT)
                    amount = float(tx.get('value', 0)) / (10 ** 6)
                    
                    logger.info(f"💰 Incoming (recent): {amount:.6f} USDT (expected: {expected_amount:.6f})")
                    logger.info(f"   Timestamp: {datetime.fromtimestamp(tx_timestamp/1000)}")
                    
                    # Check if amount matches (with tolerance)
                    if abs(amount - expected_amount) < 0.01:
                        tx_id = tx.get('transaction_id', '')
                        
                        logger.info(f"✅ TRC-20 payment verified!")
                        logger.info(f"   Amount: {amount:.6f} USDT")
                        logger.info(f"   TX: {tx_id}")
                        logger.info(f"   Time: {datetime.fromtimestamp(tx_timestamp/1000)}")
                        
                        return True
                
                logger.warning(f"⚠️ No matching TRC-20 payment found. Expected: {expected_amount:.6f} USDT")
                return False
                
    except Exception as e:
        logger.error(f"Error in TRC-20 verification: {e}")
        import traceback
        traceback.print_exc()
        return False

async def verify_crypto_payment(wallet: str, expected_amount: float, network: str) -> bool:
    """
    Verify crypto payment
    
    - BEP-20: Web3 automatic (FREE, unlimited)
    - TRC-20: TronGrid automatic (FREE, 90k/day)
    
    Args:
        wallet: Wallet address that received payment
        expected_amount: Expected USDT amount
        network: 'bep20', 'BEP-20', 'trc20', 'TRC-20', etc.
    
    Returns:
        True if payment verified, False otherwise
    """
    
    # Normalize network to lowercase and remove special chars
    network_lower = network.lower().replace('-', '').replace('_', '').strip()
    
    logger.info(f"🔍 Verifying payment: {expected_amount:.6f} USDT on {network}")
    logger.info(f"   Normalized network: {network_lower}")
    
    if 'bep20' in network_lower or 'bsc' in network_lower:
        logger.info("✅ Using BEP-20 Web3 verification (automatic)")
        return await verify_bep20_payment_web3(wallet, expected_amount)
    elif 'trc20' in network_lower or 'tron' in network_lower:
        logger.info("✅ Using TRC-20 TronGrid verification (automatic)")
        return await verify_trc20_payment(wallet, expected_amount)
    else:
        logger.error(f"❌ Unknown network: {network}")
        return False

# Test connection on import
if __name__ != "__main__":
    try:
        check_web3_connection()
    except:
        logger.warning("Web3 connection test failed on import")