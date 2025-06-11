#!/usr/bin/env python3
"""
Test script for AngelOne broker integration.

This script tests the basic functionality of the AngelOne broker
integration including login, profile, and data retrieval.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.brokers.angelone import AngelOneBroker
from src.utils.logging import setup_logging
from src.config import settings

async def test_angelone_broker():
    """Test AngelOne broker functionality."""
    print("🔧 Testing AngelOne Broker Integration")
    print("=" * 50)
    
    # Setup logging
    setup_logging()
    
    # Create broker instance
    broker = AngelOneBroker()
    
    try:
        # Test 1: Login
        print("1️⃣ Testing Login...")
        login_response = await broker.login()
        
        if login_response.success:
            print(f"✅ Login successful! Token: {login_response.auth_token[:20]}...")
        else:
            print(f"❌ Login failed: {login_response.message}")
            return
        
        # Test 2: Get Profile
        print("\n2️⃣ Testing Profile Retrieval...")
        profile_response = await broker.get_profile()
        
        if profile_response.success:
            print("✅ Profile retrieved successfully!")
            profile_data = profile_response.data
            print(f"   Client Code: {profile_data.get('clientcode')}")
            print(f"   Name: {profile_data.get('name')}")
            print(f"   Email: {profile_data.get('email')}")
            print(f"   Exchanges: {profile_data.get('exchanges')}")
        else:
            print(f"❌ Profile retrieval failed: {profile_response.message}")
        
        # Test 3: Get Funds
        print("\n3️⃣ Testing Funds Retrieval...")
        funds_response = await broker.get_funds()
        
        if funds_response.success:
            print("✅ Funds retrieved successfully!")
            funds_data = funds_response.data
            print(f"   Available Cash: {funds_data.get('availablecash')}")
            print(f"   Net: {funds_data.get('net')}")
        else:
            print(f"❌ Funds retrieval failed: {funds_response.message}")
        
        # Test 4: Get Holdings
        print("\n4️⃣ Testing Holdings Retrieval...")
        holdings = await broker.get_holdings()
        print(f"✅ Retrieved {len(holdings)} holdings")
        
        if holdings:
            for holding in holdings[:3]:  # Show first 3
                print(f"   {holding.symbol}: {holding.quantity} @ ₹{holding.average_price}")
        
        # Test 5: Get Positions
        print("\n5️⃣ Testing Positions Retrieval...")
        positions = await broker.get_positions()
        print(f"✅ Retrieved {len(positions)} positions")
        
        if positions:
            for position in positions[:3]:  # Show first 3
                print(f"   {position.symbol}: Net Qty {position.quantity}")
        
        # Test 6: Get Orders
        print("\n6️⃣ Testing Orders Retrieval...")
        orders = await broker.get_orders()
        print(f"✅ Retrieved {len(orders)} orders")
        
        if orders:
            for order in orders[:3]:  # Show first 3
                print(f"   {order.symbol}: {order.transaction_type} {order.quantity} @ {order.status}")
        
        # Test 7: Get Quote
        print("\n7️⃣ Testing Quote Retrieval...")
        try:
            # Note: AngelOne requires symbol tokens for quote API
            # For testing, we'll skip this or use market search
            print("⚠️  Quote API requires symbol tokens - skipping for now")
            # quote = await broker.get_quote("SBIN-EQ", "NSE")
            # print(f"✅ Quote for SBIN-EQ: ₹{quote.ltp}")
            # print(f"   O: {quote.open_price}, H: {quote.high_price}, L: {quote.low_price}")
        except Exception as e:
            print(f"❌ Quote retrieval failed: {str(e)}")
        
        # Test 8: Logout
        print("\n8️⃣ Testing Logout...")
        logout_response = await broker.logout()
        
        if logout_response.success:
            print("✅ Logout successful!")
        else:
            print(f"❌ Logout failed: {logout_response.message}")
            
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Ensure cleanup
        if broker.session and not broker.session.closed:
            await broker.session.close()
    
    print("\n" + "=" * 50)
    print("🏁 AngelOne Broker Test Complete!")

async def test_broker_factory():
    """Test broker factory functionality."""
    print("\n🏭 Testing Broker Factory...")
    
    from src.brokers.base import BrokerFactory
    
    # Test broker registration
    available_brokers = BrokerFactory.get_available_brokers()
    print(f"Available brokers: {available_brokers}")
    
    if "angelone" in available_brokers:
        print("✅ AngelOne broker registered successfully!")
        
        # Create broker instance through factory
        broker = BrokerFactory.create_broker("angelone")
        print(f"✅ Created broker instance: {broker.name}")
    else:
        print("❌ AngelOne broker not registered!")

def main():
    """Main test function."""
    print("🚀 AngelOne Broker Integration Test Suite")
    print("This will test the AngelOne broker with LIVE API credentials!")
    print("Make sure you have proper credentials in .env file\n")
    
    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found! Please create it from env.example")
        print("   cp env.example .env")
        print("   # Then edit .env with your credentials")
        return
    
    try:
        # Validate required settings
        required_settings = [
            'angelone_api_key',
            'angelone_user_id', 
            'angelone_password',
            'angelone_totp_secret'
        ]
        
        missing_settings = []
        for setting in required_settings:
            if not hasattr(settings, setting) or not getattr(settings, setting):
                missing_settings.append(setting.upper())
        
        if missing_settings:
            print(f"❌ Missing required settings: {', '.join(missing_settings)}")
            print("Please update your .env file with proper values")
            return
        
        print("✅ Configuration validated!")
        
        # Run tests
        asyncio.run(test_broker_factory())
        asyncio.run(test_angelone_broker())
        
    except Exception as e:
        print(f"❌ Test setup failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 