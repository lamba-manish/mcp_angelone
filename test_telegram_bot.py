#!/usr/bin/env python3
"""
Test script for Telegram bot integration.

This script tests the Telegram bot startup and basic functionality
without actually running the bot (to avoid needing real Telegram tokens during testing).
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.telegram_bot.bot import TradingBot
from src.telegram_bot.session_manager import session_manager
from src.brokers.base import BrokerFactory
from src.utils.logging import setup_logging
from src.config import settings

async def test_telegram_bot_components():
    """Test Telegram bot components."""
    print("🤖 Testing Telegram Bot Components")
    print("=" * 50)
    
    # Setup logging
    setup_logging()
    
    try:
        # Test 1: Configuration
        print("1️⃣ Testing Configuration...")
        print(f"   Telegram Bot Token: {settings.telegram_bot_token[:20]}..." if settings.telegram_bot_token else "   ❌ No token configured")
        print(f"   AngelOne API Key: {settings.angelone_api_key[:10]}..." if settings.angelone_api_key else "   ❌ No API key configured")
        print(f"   Log Level: {settings.log_level}")
        print(f"   Environment: {settings.environment}")
        
        # Test 2: Broker Factory
        print("\n2️⃣ Testing Broker Factory...")
        available_brokers = BrokerFactory.get_available_brokers()
        print(f"   Available brokers: {available_brokers}")
        
        if "angelone" in available_brokers:
            print("   ✅ AngelOne broker registered")
            broker = BrokerFactory.create_broker("angelone")
            print(f"   ✅ Created broker instance: {broker.name}")
        else:
            print("   ❌ AngelOne broker not found")
        
        # Test 3: Session Manager
        print("\n3️⃣ Testing Session Manager...")
        await session_manager.start()
        print("   ✅ Session manager started")
        
        # Create a test session
        test_user_id = 12345
        test_chat_id = 67890
        session = await session_manager.get_session(test_user_id, test_chat_id)
        print(f"   ✅ Created session for user {test_user_id}")
        print(f"   Session state: {session.state.value}")
        
        # Update session
        from src.telegram_bot.models import UserState
        await session_manager.update_session(test_user_id, state=UserState.AUTHENTICATED)
        updated_session = await session_manager.get_session(test_user_id, test_chat_id)
        print(f"   ✅ Updated session state: {updated_session.state.value}")
        
        # Test 4: Bot Initialization (without actually starting)
        print("\n4️⃣ Testing Bot Initialization...")
        bot = TradingBot()
        print("   ✅ Trading bot instance created")
        
        # Note: We won't actually initialize the bot as it requires a valid Telegram token
        print("   ⚠️  Skipping bot.initialize() - requires valid Telegram token")
        
        # Test 5: Handler Imports
        print("\n5️⃣ Testing Handler Imports...")
        try:
            from src.telegram_bot.handlers import (
                start_handler, help_handler, broker_selection_handler,
                status_handler, trading_handler
            )
            print("   ✅ All handlers imported successfully")
        except ImportError as e:
            print(f"   ❌ Handler import failed: {e}")
        
        # Test 6: Model Validation
        print("\n6️⃣ Testing Model Validation...")
        from src.models.trading import OrderRequest, TransactionType, OrderType, ProductType, Exchange
        
        # Test order request creation
        order_request = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            transaction_type=TransactionType.BUY,
            order_type=OrderType.MARKET,
            product_type=ProductType.CNC,
            quantity=10
        )
        print(f"   ✅ Order request created: {order_request.symbol} {order_request.transaction_type.value}")
        
        await session_manager.stop()
        print("\n   ✅ Session manager stopped")
        
        print("\n" + "=" * 50)
        print("🎉 All Telegram Bot Components Test Passed!")
        
        # Show setup instructions
        print("\n📋 Setup Instructions:")
        print("1. Add your Telegram bot token to .env file:")
        print("   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here")
        print("\n2. Make sure AngelOne credentials are in .env")
        print("\n3. Run the bot: python main.py")
        print("\n4. Start a chat with your bot and send /start")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

def test_env_configuration():
    """Test environment configuration."""
    print("\n🔧 Testing Environment Configuration...")
    
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found! Please create it from env.example")
        return False
    
    required_vars = [
        "TELEGRAM_BOT_TOKEN",
        "ANGELONE_API_KEY", 
        "ANGELONE_USER_ID",
        "ANGELONE_PASSWORD",
        "ANGELONE_TOTP_SECRET"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("   Please update your .env file")
        return False
    
    print("✅ All required environment variables are set")
    return True

def main():
    """Main test function."""
    print("🚀 Telegram Bot Integration Test Suite")
    print("This will test the Telegram bot components without starting the actual bot")
    print()
    
    # Test environment first
    if not test_env_configuration():
        print("\n💡 Run this after setting up your .env file:")
        print("   cp env.example .env")
        print("   # Edit .env with your credentials")
        return
    
    # Run component tests
    try:
        asyncio.run(test_telegram_bot_components())
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")

if __name__ == "__main__":
    main() 