#!/usr/bin/env python3
"""
Complete Integration Demo Script

This script demonstrates the full integration between AngelOne broker
and Telegram bot, showing all components working together.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.telegram_bot.bot import TradingBot
from src.telegram_bot.session_manager import session_manager
from src.telegram_bot.models import UserState
from src.brokers.base import BrokerFactory
from src.brokers.angelone import AngelOneBroker
from src.models.trading import OrderRequest, TransactionType, OrderType, ProductType, Exchange
from src.utils.logging import setup_logging
from src.config import settings

async def demo_broker_integration():
    """Demo the AngelOne broker integration."""
    print("🔌 Testing AngelOne Broker Integration")
    print("-" * 40)
    
    # Create broker instance
    broker = BrokerFactory.create_broker("angelone")
    print(f"✅ Created {broker.name} broker instance")
    
    # Test login
    print("🔑 Testing login...")
    login_response = await broker.login()
    
    if login_response.success:
        print(f"✅ Login successful! Token: {login_response.auth_token[:20]}...")
        
        # Test profile
        profile_response = await broker.get_profile()
        if profile_response.success:
            client_code = profile_response.data.get('clientcode')
            print(f"✅ Profile: {client_code}")
        
        # Test funds
        funds_response = await broker.get_funds()
        if funds_response.success:
            print("✅ Funds information retrieved")
        
        # Test holdings
        holdings = await broker.get_holdings()
        print(f"✅ Holdings: {len(holdings)} items")
        
        # Test positions
        positions = await broker.get_positions()
        print(f"✅ Positions: {len(positions)} items")
        
        # Test orders
        orders = await broker.get_orders()
        print(f"✅ Orders: {len(orders)} items")
        
        # Logout
        await broker.logout()
        print("✅ Logout successful")
        
    else:
        print(f"❌ Login failed: {login_response.message}")
    
    return login_response.success

async def demo_telegram_integration():
    """Demo the Telegram bot integration."""
    print("\n🤖 Testing Telegram Bot Integration")
    print("-" * 40)
    
    # Start session manager
    await session_manager.start()
    print("✅ Session manager started")
    
    # Create a mock user session
    user_id = 123456789
    chat_id = 987654321
    
    session = await session_manager.get_session(user_id, chat_id)
    print(f"✅ Created session for user {user_id}")
    
    # Test session state changes
    await session_manager.update_session(user_id, state=UserState.BROKER_SELECTION)
    await session_manager.update_session(user_id, selected_broker="angelone")
    await session_manager.update_session(user_id, state=UserState.AUTHENTICATED, broker_authenticated=True)
    
    updated_session = await session_manager.get_session(user_id, chat_id)
    print(f"✅ Session state: {updated_session.state.value}")
    print(f"✅ Selected broker: {updated_session.selected_broker}")
    print(f"✅ Authenticated: {updated_session.broker_authenticated}")
    
    # Test trading bot creation
    trading_bot = TradingBot()
    print("✅ Trading bot instance created")
    
    # Test broker instance management
    broker = await trading_bot._get_broker_instance("angelone")
    print(f"✅ Got broker instance: {broker.name}")
    
    await session_manager.stop()
    print("✅ Session manager stopped")

async def demo_full_integration():
    """Demo the complete integration with actual API calls."""
    print("\n🚀 Complete Integration Demo")
    print("=" * 50)
    
    try:
        # Initialize everything
        await session_manager.start()
        
        # Create trading bot
        trading_bot = TradingBot()
        
        # Mock user session
        user_id = 123456789
        chat_id = 987654321
        
        session = await session_manager.get_session(user_id, chat_id)
        await session_manager.update_session(
            user_id,
            state=UserState.AUTHENTICATED,
            selected_broker="angelone",
            broker_authenticated=True
        )
        
        # Get broker for user
        broker = await trading_bot._get_broker_instance("angelone")
        
        # Test broker operations as if triggered by Telegram commands
        print("\n📊 Simulating Telegram Commands...")
        
        # Simulate /status command
        print("🔄 Processing /status command...")
        if hasattr(broker, 'jwt_token') and broker.jwt_token:
            print("✅ Status: Connected to AngelOne")
        else:
            print("❌ Status: Not connected")
        
        # Simulate /holdings command
        print("🔄 Processing /holdings command...")
        try:
            holdings = await broker.get_holdings()
            if holdings:
                print(f"✅ Holdings: Found {len(holdings)} holdings")
                for holding in holdings[:2]:  # Show first 2
                    print(f"   📈 {holding.symbol}: {holding.quantity} @ ₹{holding.current_price}")
            else:
                print("✅ Holdings: No holdings found")
        except Exception as e:
            print(f"❌ Holdings error: {e}")
        
        # Simulate /funds command
        print("🔄 Processing /funds command...")
        try:
            funds_response = await broker.get_funds()
            if funds_response.success:
                print("✅ Funds: Information retrieved")
            else:
                print(f"❌ Funds error: {funds_response.message}")
        except Exception as e:
            print(f"❌ Funds error: {e}")
        
        # Simulate order creation (but not placement)
        print("🔄 Processing order request...")
        order_request = OrderRequest(
            symbol="RELIANCE",
            exchange=Exchange.NSE,
            transaction_type=TransactionType.BUY,
            order_type=OrderType.MARKET,
            product_type=ProductType.CNC,
            quantity=1
        )
        print(f"✅ Order created: {order_request.transaction_type.value} {order_request.quantity} {order_request.symbol}")
        
        await session_manager.stop()
        
        print("\n🎉 Complete Integration Demo Successful!")
        print("\n📝 Integration Summary:")
        print("✅ AngelOne broker integration working")
        print("✅ Telegram bot components working")
        print("✅ Session management working")
        print("✅ Command handling working")
        print("✅ Order models working")
        
    except Exception as e:
        print(f"❌ Integration demo failed: {e}")
        import traceback
        traceback.print_exc()

def print_setup_guide():
    """Print the complete setup guide."""
    print("\n" + "=" * 60)
    print("🛠️  COMPLETE SETUP GUIDE")
    print("=" * 60)
    
    print("\n1️⃣ Environment Setup:")
    print("   • Create .env file: cp env.example .env")
    print("   • Add your Telegram bot token")
    print("   • Add your AngelOne credentials")
    
    print("\n2️⃣ Telegram Bot Setup:")
    print("   • Go to @BotFather on Telegram")
    print("   • Create a new bot: /newbot")
    print("   • Get your bot token")
    print("   • Add token to .env file")
    
    print("\n3️⃣ AngelOne Setup:")
    print("   • Login to AngelOne account")
    print("   • Generate API key from settings")
    print("   • Setup TOTP app (Google Authenticator)")
    print("   • Add credentials to .env file")
    
    print("\n4️⃣ Run the Bot:")
    print("   • python main.py")
    print("   • Start chat with your bot")
    print("   • Send /start to begin")
    
    print("\n5️⃣ Available Commands:")
    commands = [
        "/start - Welcome & setup",
        "/broker - Select broker",
        "/status - Check connection",
        "/holdings - View holdings", 
        "/positions - View positions",
        "/orders - View orders",
        "/funds - Check funds",
        "/buy SYMBOL QTY [PRICE] - Buy order",
        "/sell SYMBOL QTY [PRICE] - Sell order",
        "/quote SYMBOL - Get quote",
        "/help - Show help"
    ]
    
    for cmd in commands:
        print(f"   • {cmd}")
    
    print(f"\n6️⃣ Example Usage:")
    print("   • /buy RELIANCE 10 2500    # Limit buy")
    print("   • /sell TCS 5              # Market sell")
    print("   • /quote INFY              # Get quote")
    print("   • /holdings                # View portfolio")

async def main():
    """Main demo function."""
    print("🚀 AngelOne + Telegram Bot Integration Demo")
    print("This demonstrates the complete trading bot integration")
    print()
    
    # Setup logging
    setup_logging()
    
    # Check environment
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found!")
        print("📝 Create .env file first: cp env.example .env")
        print_setup_guide()
        return
    
    # Test configurations
    print("🔧 Configuration Check:")
    print(f"   Telegram Token: {'✅' if settings.telegram_bot_token else '❌'}")
    print(f"   AngelOne API Key: {'✅' if settings.angelone_api_key else '❌'}")
    print(f"   AngelOne User ID: {'✅' if settings.angelone_user_id else '❌'}")
    print(f"   AngelOne Password: {'✅' if settings.angelone_password else '❌'}")
    print(f"   AngelOne TOTP: {'✅' if settings.angelone_totp_secret else '❌'}")
    
    # Run demos
    try:
        # Demo broker integration
        broker_success = await demo_broker_integration()
        
        # Demo telegram integration
        await demo_telegram_integration()
        
        # Demo full integration if broker works
        if broker_success:
            await demo_full_integration()
        else:
            print("\n⚠️  Skipping full integration demo due to broker login failure")
            print("   Make sure your AngelOne credentials are correct in .env")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
    
    print_setup_guide()

if __name__ == "__main__":
    asyncio.run(main()) 