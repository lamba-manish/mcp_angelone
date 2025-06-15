#!/usr/bin/env python3
"""
End-to-end test for the trading bot functionality.
Tests broker manager, AI agent, and tools integration.
"""

import asyncio
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.telegram_bot.broker_manager import broker_manager
from src.telegram_bot.session_manager import session_manager, UserSession
from src.telegram_bot.models import UserState
from src.ai.agent import ai_handler
from src.ai.tools import BrokerTools


async def test_broker_manager():
    """Test centralized broker manager."""
    print("🔧 Testing Broker Manager...")
    
    # Start managers
    await session_manager.start()
    await broker_manager.start()
    
    # Create test user session
    test_user_id = 123456
    test_chat_id = 789012
    
    # Create user session
    session = await session_manager.get_session(test_user_id, test_chat_id)
    await session_manager.update_session(
        test_user_id,
        state=UserState.AUTHENTICATED,
        selected_broker="angelone",
        broker_authenticated=True
    )
    
    # Test broker creation
    broker = await broker_manager.get_or_create_broker(test_user_id)
    
    if broker:
        print("✅ Broker manager: Broker created successfully")
        
        # Test broker functionality
        try:
            profile_response = await broker.get_profile()
            if profile_response.success:
                print("✅ Broker manager: Profile fetch successful")
            else:
                print(f"⚠️ Broker manager: Profile fetch failed - {profile_response.message}")
        except Exception as e:
            print(f"❌ Broker manager: Profile test error - {e}")
    else:
        print("❌ Broker manager: Failed to create broker")
    
    return broker is not None


async def test_ai_tools():
    """Test AI tools with broker manager."""
    print("\n🤖 Testing AI Tools...")
    
    test_user_id = 123456
    tools = BrokerTools(test_user_id)
    
    # Test funds
    try:
        funds_result = await tools.get_funds()
        if funds_result.get("status") == "success":
            print(f"✅ AI Tools: Funds fetch successful - ₹{funds_result.get('available_cash', 0):,.2f}")
        else:
            print(f"⚠️ AI Tools: Funds fetch failed - {funds_result.get('message', 'Unknown error')}")
    except Exception as e:
        print(f"❌ AI Tools: Funds test error - {e}")
    
    # Test quote
    try:
        quote_result = await tools.get_quote("RELIANCE", "NSE")
        if quote_result.get("status") == "success":
            ltp = quote_result.get("ltp", 0)
            print(f"✅ AI Tools: Quote fetch successful - RELIANCE LTP: ₹{ltp}")
        else:
            print(f"⚠️ AI Tools: Quote fetch failed - {quote_result.get('message', 'Unknown error')}")
    except Exception as e:
        print(f"❌ AI Tools: Quote test error - {e}")
    
    # Test profile
    try:
        profile_result = await tools.get_profile()
        if profile_result.get("status") == "success":
            name = profile_result.get("name", "N/A")
            client_id = profile_result.get("client_id", "N/A")
            print(f"✅ AI Tools: Profile fetch successful - {name} ({client_id})")
        else:
            print(f"⚠️ AI Tools: Profile fetch failed - {profile_result.get('message', 'Unknown error')}")
    except Exception as e:
        print(f"❌ AI Tools: Profile test error - {e}")


async def test_ai_agent():
    """Test AI agent functionality."""
    print("\n🧠 Testing AI Agent...")
    
    test_user_id = 123456
    
    # Test agent creation
    agent = await ai_handler.get_or_create_agent(test_user_id)
    
    if agent:
        print("✅ AI Agent: Agent created successfully")
        
        # Test greeting
        try:
            greeting_response = await agent.process_message("Hello")
            if greeting_response and len(greeting_response) > 10:
                print("✅ AI Agent: Greeting processed successfully")
                print(f"   Response length: {len(greeting_response)} characters")
            else:
                print(f"⚠️ AI Agent: Greeting response too short - {greeting_response[:100]}...")
        except Exception as e:
            print(f"❌ AI Agent: Greeting test error - {e}")
        
        # Test stock query
        try:
            stock_response = await agent.process_message("What's the current price of ITC?")
            if stock_response and "ITC" in stock_response:
                print("✅ AI Agent: Stock query processed successfully")
                print(f"   Response: {stock_response[:200]}...")
            else:
                print(f"⚠️ AI Agent: Stock query unexpected response - {stock_response[:100]}...")
        except Exception as e:
            print(f"❌ AI Agent: Stock query test error - {e}")
        
        # Test balance query
        try:
            balance_response = await agent.process_message("What's my balance?")
            if balance_response:
                print("✅ AI Agent: Balance query processed successfully")
                print(f"   Response: {balance_response[:200]}...")
            else:
                print("⚠️ AI Agent: Balance query returned empty response")
        except Exception as e:
            print(f"❌ AI Agent: Balance query test error - {e}")
    else:
        print("❌ AI Agent: Failed to create agent")


async def test_conversation_history_management():
    """Test smart conversation history management."""
    print("\n💭 Testing Conversation History Management...")
    
    test_user_id = 123456
    agent = await ai_handler.get_or_create_agent(test_user_id)
    
    if agent:
        # Clear conversation to start fresh
        agent.clear_conversation()
        
        # Test standalone commands (should not include history)
        await agent.process_message("What's my balance?")  # Standalone
        history_count_1 = len(agent.conversation_history)
        
        await agent.process_message("What's RELIANCE price?")  # Another standalone
        history_count_2 = len(agent.conversation_history)
        
        # Test context-requiring message (should include history)
        await agent.process_message("What about TCS?")  # Context-requiring
        history_count_3 = len(agent.conversation_history)
        
        print(f"✅ History Management: Standalone command 1 - {history_count_1} messages")
        print(f"✅ History Management: Standalone command 2 - {history_count_2} messages")
        print(f"✅ History Management: Context command - {history_count_3} messages")
        
        # History should be managed smartly
        if history_count_3 > history_count_1:
            print("✅ History Management: Context-requiring messages include more history")
        else:
            print("⚠️ History Management: Context detection may need adjustment")
    else:
        print("❌ History Management: Could not test - no agent")


async def test_greeting_detection():
    """Test intelligent greeting detection."""
    print("\n👋 Testing Greeting Detection...")
    
    test_user_id = 123456
    agent = await ai_handler.get_or_create_agent(test_user_id)
    
    if agent:
        # Test pure greetings (should trigger greeting response)
        test_cases = [
            ("Hello", True, "Pure greeting"),
            ("Hi", True, "Simple hi"),
            ("What can you do?", True, "Help request"),
            ("ITC LTP", False, "Stock query with LTP"),
            ("RELIANCE price", False, "Stock price query"),
            ("What's the price of ITC?", False, "Price question"),
            ("Hello, what's RELIANCE price?", False, "Greeting + stock query")
        ]
        
        for message, should_be_greeting, description in test_cases:
            greeting_response = agent._handle_greetings(message)
            is_greeting = greeting_response is not None
            
            if is_greeting == should_be_greeting:
                status = "✅"
            else:
                status = "⚠️"
            
            print(f"{status} Greeting Detection: '{message}' - {description} (Expected: {should_be_greeting}, Got: {is_greeting})")
    else:
        print("❌ Greeting Detection: Could not test - no agent")


async def cleanup():
    """Cleanup test resources."""
    print("\n🧹 Cleaning up...")
    await broker_manager.stop()
    await session_manager.stop()
    print("✅ Cleanup completed")


async def main():
    """Run all tests."""
    print("🚀 Starting End-to-End Testing for Trading Bot\n")
    print("=" * 60)
    
    try:
        # Run tests
        broker_working = await test_broker_manager()
        
        if broker_working:
            await test_ai_tools()
            await test_ai_agent()
            await test_conversation_history_management()
            await test_greeting_detection()
        else:
            print("\n❌ Skipping AI tests due to broker manager failure")
        
        print("\n" + "=" * 60)
        print("🏁 End-to-End Testing Completed")
        
    except Exception as e:
        print(f"\n❌ Test suite error: {e}")
    finally:
        await cleanup()


if __name__ == "__main__":
    asyncio.run(main()) 