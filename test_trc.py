#!/usr/bin/env python3
"""
TRC-20 TronGrid API Debug & Test Script
Find and fix the issue with TRC-20 verification
"""

import asyncio
import aiohttp
import json
from datetime import datetime

# Configuration - UPDATE THESE WITH YOUR ACTUAL VALUES
TRONGRID_API_KEY = "d826000c-48be-4f05-9640-d6a8ffe20b39"
TEST_WALLET = "TGgcKJ32bL4qtt8BaXuwvZQtmVfA8cUujL"  # Your TRC-20 wallet
USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"  # USDT on TRON

# Colors
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text:^80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")

def print_debug(text):
    print(f"{Colors.MAGENTA}🔍 {text}{Colors.END}")

async def test_1_account_info():
    """Test 1: Get account information"""
    print_header("Test 1: Account Information API")
    
    url = f"https://api.trongrid.io/v1/accounts/{TEST_WALLET}"
    headers = {'TRON-PRO-API-KEY': TRONGRID_API_KEY}
    
    print_debug(f"URL: {url}")
    print_debug(f"Headers: {headers}")
    print()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                print_info(f"Status Code: {response.status}")
                
                text = await response.text()
                print_debug(f"Raw Response: {text[:500]}...")
                print()
                
                try:
                    data = json.loads(text)
                    print_info("JSON Response:")
                    print(json.dumps(data, indent=2)[:1000])
                    print()
                    
                    if 'data' in data and len(data['data']) > 0:
                        account = data['data'][0]
                        print_success("Account found!")
                        print_info(f"Address: {account.get('address')}")
                        print_info(f"Balance: {account.get('balance', 0) / 1e6:.6f} TRX")
                        return True
                    else:
                        print_error("No account data returned")
                        print_warning("Possible reasons:")
                        print_warning("  1. Wallet address format is wrong")
                        print_warning("  2. Account doesn't exist on TRON network")
                        print_warning("  3. API endpoint changed")
                        return False
                        
                except json.JSONDecodeError as e:
                    print_error(f"JSON decode error: {e}")
                    print_debug(f"Response text: {text}")
                    return False
                    
    except Exception as e:
        print_error(f"Request failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_2_alternative_account_api():
    """Test 2: Try alternative account API"""
    print_header("Test 2: Alternative Account API (wallet/getAccount)")
    
    # Try the alternative API endpoint
    url = "https://api.trongrid.io/wallet/getaccount"
    headers = {'TRON-PRO-API-KEY': TRONGRID_API_KEY}
    payload = {
        "address": TEST_WALLET,
        "visible": True
    }
    
    print_debug(f"URL: {url}")
    print_debug(f"Payload: {json.dumps(payload, indent=2)}")
    print()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                print_info(f"Status Code: {response.status}")
                
                text = await response.text()
                print_debug(f"Raw Response: {text[:500]}...")
                print()
                
                try:
                    data = json.loads(text)
                    print_info("JSON Response:")
                    print(json.dumps(data, indent=2)[:1000])
                    print()
                    
                    if 'address' in data:
                        print_success("Account found via alternative API!")
                        print_info(f"Address: {data.get('address')}")
                        print_info(f"Balance: {data.get('balance', 0) / 1e6:.6f} TRX")
                        return True
                    else:
                        print_error("Account not found")
                        return False
                        
                except json.JSONDecodeError as e:
                    print_error(f"JSON decode error: {e}")
                    return False
                    
    except Exception as e:
        print_error(f"Request failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_3_trc20_transactions():
    """Test 3: Get TRC-20 transactions"""
    print_header("Test 3: TRC-20 USDT Transactions")
    
    url = f"https://api.trongrid.io/v1/accounts/{TEST_WALLET}/transactions/trc20"
    headers = {'TRON-PRO-API-KEY': TRONGRID_API_KEY}
    params = {
        'contract_address': USDT_CONTRACT,
        'only_to': 'true',
        'limit': 20
    }
    
    print_debug(f"URL: {url}")
    print_debug(f"Params: {json.dumps(params, indent=2)}")
    print()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                print_info(f"Status Code: {response.status}")
                
                text = await response.text()
                print_debug(f"Raw Response Length: {len(text)} bytes")
                print_debug(f"First 500 chars: {text[:500]}...")
                print()
                
                try:
                    data = json.loads(text)
                    
                    if 'data' in data:
                        transactions = data['data']
                        
                        if not transactions:
                            print_warning("No TRC-20 transactions found")
                            print_info("This means:")
                            print_info("  1. Wallet has never received USDT, OR")
                            print_info("  2. API parameters are wrong")
                            print()
                            print_info("Let's check transaction history without filters...")
                            return await test_4_all_transactions()
                        
                        print_success(f"Found {len(transactions)} TRC-20 transaction(s)!")
                        print()
                        
                        for i, tx in enumerate(transactions[:5], 1):
                            amount = float(tx.get('value', 0)) / 1e6
                            timestamp = datetime.fromtimestamp(tx.get('block_timestamp', 0) / 1000)
                            
                            print(f"{Colors.BOLD}{i}. Transaction{Colors.END}")
                            print(f"   Amount: {Colors.GREEN}{amount:.6f} USDT{Colors.END}")
                            print(f"   From: {tx.get('from', 'N/A')[:20]}...")
                            print(f"   To: {tx.get('to', 'N/A')[:20]}...")
                            print(f"   Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                            print(f"   TX: {tx.get('transaction_id', 'N/A')[:30]}...")
                            print()
                        
                        return True
                    else:
                        print_error("No 'data' field in response")
                        print_debug(f"Response keys: {list(data.keys())}")
                        print_debug(f"Full response: {json.dumps(data, indent=2)[:1000]}")
                        return False
                        
                except json.JSONDecodeError as e:
                    print_error(f"JSON decode error: {e}")
                    print_debug(f"Response: {text}")
                    return False
                    
    except Exception as e:
        print_error(f"Request failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_4_all_transactions():
    """Test 4: Get ALL transactions (no filter)"""
    print_header("Test 4: All TRC-20 Transactions (No Filter)")
    
    url = f"https://api.trongrid.io/v1/accounts/{TEST_WALLET}/transactions/trc20"
    headers = {'TRON-PRO-API-KEY': TRONGRID_API_KEY}
    params = {'limit': 20}
    
    print_debug(f"URL: {url}")
    print_debug(f"Params: {json.dumps(params, indent=2)}")
    print()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                print_info(f"Status Code: {response.status}")
                
                text = await response.text()
                
                try:
                    data = json.loads(text)
                    
                    if 'data' in data and data['data']:
                        transactions = data['data']
                        print_success(f"Found {len(transactions)} total TRC-20 transaction(s)!")
                        print()
                        
                        # Group by token
                        tokens = {}
                        for tx in transactions:
                            token = tx.get('token_info', {}).get('symbol', 'Unknown')
                            tokens[token] = tokens.get(token, 0) + 1
                        
                        print_info("Token breakdown:")
                        for token, count in tokens.items():
                            print(f"  - {token}: {count} transactions")
                        print()
                        
                        # Show USDT transactions
                        usdt_txs = [tx for tx in transactions if tx.get('token_info', {}).get('symbol') == 'USDT']
                        if usdt_txs:
                            print_success(f"Found {len(usdt_txs)} USDT transaction(s)!")
                            
                            for i, tx in enumerate(usdt_txs[:3], 1):
                                amount = float(tx.get('value', 0)) / 1e6
                                timestamp = datetime.fromtimestamp(tx.get('block_timestamp', 0) / 1000)
                                direction = "⬅️ IN" if tx.get('to') == TEST_WALLET else "➡️ OUT"
                                
                                print(f"\n{i}. {direction}")
                                print(f"   Amount: {amount:.6f} USDT")
                                print(f"   Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                                print(f"   TX: {tx.get('transaction_id', '')[:30]}...")
                        else:
                            print_warning("No USDT transactions found")
                            print_info("Wallet has TRC-20 activity but no USDT")
                        
                        return True
                    else:
                        print_warning("No TRC-20 transactions at all")
                        print_info("This wallet has never interacted with TRC-20 tokens")
                        return False
                        
                except json.JSONDecodeError as e:
                    print_error(f"JSON decode error: {e}")
                    return False
                    
    except Exception as e:
        print_error(f"Request failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_5_verify_specific_amount(amount):
    """Test 5: Verify specific amount"""
    print_header(f"Test 5: Verify {amount} USDT Payment")
    
    url = f"https://api.trongrid.io/v1/accounts/{TEST_WALLET}/transactions/trc20"
    headers = {'TRON-PRO-API-KEY': TRONGRID_API_KEY}
    params = {
        'contract_address': USDT_CONTRACT,
        'only_to': 'true',
        'limit': 50
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status != 200:
                    print_error(f"HTTP {response.status}")
                    return False
                
                data = await response.json()
                
                if 'data' not in data or not data['data']:
                    print_warning("No transactions found")
                    return False
                
                transactions = data['data']
                print_info(f"Checking {len(transactions)} transactions...")
                print()
                
                for tx in transactions:
                    if tx.get('to') == TEST_WALLET:
                        tx_amount = float(tx.get('value', 0)) / 1e6
                        
                        print_debug(f"Checking: {tx_amount:.6f} USDT vs {amount:.6f} USDT")
                        
                        if abs(tx_amount - amount) < 0.01:
                            print_success(f"MATCH FOUND!")
                            print_info(f"Amount: {tx_amount:.6f} USDT")
                            print_info(f"TX: {tx.get('transaction_id')}")
                            print_success("✅ Bot WILL detect this payment!")
                            return True
                
                print_warning(f"No transaction matching {amount:.6f} USDT")
                print_info("Recent amounts:")
                for tx in transactions[:5]:
                    if tx.get('to') == TEST_WALLET:
                        tx_amount = float(tx.get('value', 0)) / 1e6
                        print_info(f"  - {tx_amount:.6f} USDT")
                
                return False
                
    except Exception as e:
        print_error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests"""
    
    print(f"\n{Colors.BOLD}🚀 TRC-20 TronGrid API Comprehensive Test{Colors.END}\n")
    print_info(f"API Key: {TRONGRID_API_KEY[:20]}...")
    print_info(f"Wallet: {TEST_WALLET}")
    print_info(f"USDT Contract: {USDT_CONTRACT}")
    print()
    
    results = {}
    
    # Test 1: Account info
    results['account_v1'] = await test_1_account_info()
    
    # Test 2: Alternative API
    if not results['account_v1']:
        results['account_wallet'] = await test_2_alternative_account_api()
    
    # Test 3: TRC-20 filtered
    results['trc20_filtered'] = await test_3_trc20_transactions()
    
    # Test 5: Specific amount (if user wants)
    print_header("Test 5: Specific Amount Check")
    print_info("Do you want to test a specific payment amount? (y/n): ", end='')
    try:
        choice = input().strip().lower()
        if choice == 'y':
            print_info("Enter amount in USDT (e.g., 1.017): ", end='')
            amount = float(input().strip())
            results['specific_amount'] = await test_5_verify_specific_amount(amount)
    except:
        pass
    
    # Final Summary
    print_header("Final Test Summary")
    
    print(f"\n{Colors.BOLD}Test Results:{Colors.END}")
    for test_name, result in results.items():
        status = f"{Colors.GREEN}✅ PASS{Colors.END}" if result else f"{Colors.RED}❌ FAIL{Colors.END}"
        print(f"  {test_name}: {status}")
    
    print()
    
    if any(results.values()):
        print_success("At least one API method works!")
        print()
        print_info("Recommended fixes:")
        
        if results.get('account_v1'):
            print_info("  ✅ Use v1/accounts API (already working)")
        
        if results.get('account_wallet'):
            print_info("  ✅ Use wallet/getaccount API (alternative)")
        
        if results.get('trc20_filtered'):
            print_success("  ✅ TRC-20 verification will work!")
        else:
            print_warning("  ⚠️ Need to debug TRC-20 transaction fetching")
            print_info("  💡 Check if wallet has USDT transactions")
    else:
        print_error("All tests failed!")
        print()
        print_warning("Possible issues:")
        print_warning("  1. Wallet address format is wrong")
        print_warning("  2. API key is invalid")
        print_warning("  3. Wallet doesn't exist on TRON")
        print_warning("  4. Network/firewall blocking requests")
        print()
        print_info("Solutions:")
        print_info("  1. Verify wallet on TronScan: https://tronscan.org/#/address/" + TEST_WALLET)
        print_info("  2. Check API key at: https://www.trongrid.io/dashboard")
        print_info("  3. Make a test USDT deposit to activate wallet")
    
    print()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Test interrupted{Colors.END}\n")