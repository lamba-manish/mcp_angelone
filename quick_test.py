#!/usr/bin/env python3
"""Quick test script for quote functionality."""

import asyncio
import sys
sys.path.insert(0, 'src')

from src.brokers.angelone import AngelOneBroker
from src.brokers.base import BrokerFactory

async def test_quote():
    broker = BrokerFactory.create_broker('angelone')
    
    # Test login
    print("🔐 Testing login...")
    login_result = await broker.login()
    if not login_result.success:
        print(f'❌ Login failed: {login_result.message}')
        return
    
    print('✅ Login successful')
    
    # Test quote for ITC and RELIANCE
    for symbol in ['ITC', 'RELIANCE']:
        print(f'🔍 Testing quote for {symbol}...')
        try:
            quote = await broker.get_quote(symbol, 'NSE')
            print(f'✅ {symbol}: ₹{quote.ltp} (Change: {quote.change})')
            if quote.ltp > 0:
                print(f'   🎉 Quote working correctly!')
            else:
                print(f'   ⚠️ Still returning 0 - may need different token')
        except Exception as e:
            print(f'❌ {symbol} error: {e}')
    
    await broker.logout()
    print("✅ Test completed")

if __name__ == "__main__":
    asyncio.run(test_quote()) 