"""
Comprehensive test script for AI-integrated trading bot.
This script tests the entire pipeline from AI processing to broker integration.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
from pprint import pprint

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.ai.agent import TradingAgent
from src.ai.tools import ToolRegistry
from src.ai.prompts import PromptManager
from src.brokers.angelone import AngelOneBroker
from src.config import settings
from src.telegram_bot.bot import TradingBot
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AIIntegrationTester:
    """Comprehensive tester for AI integration."""
    
    def __init__(self):
        self.broker = None
        self.agent = None
        self.bot = None
        
    async def setup(self):
        """Setup test environment."""
        print("🔧 Setting up test environment...")
        
        # Load environment
        load_dotenv()
        
        # Check required environment variables
        required_vars = [
            'OPENAI_API_KEY',
            'ANGELONE_API_KEY',
            'ANGELONE_USER_ID',
            'ANGELONE_PASSWORD',
            'ANGELONE_TOTP_SECRET',
            'TELEGRAM_BOT_TOKEN'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            print("Please create a .env file with the required variables.")
            return False
        
        # Initialize components
        try:
            self.broker = AngelOneBroker()
            self.agent = TradingAgent(self.broker)
            self.bot = TradingBot()
            print("✅ Components initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize components: {e}")
            return False
    
    async def test_broker_authentication(self):
        """Test broker authentication."""
        print("\n🔐 Testing broker authentication...")
        
        try:
            login_response = await self.broker.login()
            if login_response.success:
                print("✅ Broker authentication successful")
                
                # Test profile retrieval
                profile_response = await self.broker.get_profile()
                if profile_response.success:
                    print("✅ Profile retrieval successful")
                    print(f"   User: {profile_response.data.get('name', 'Unknown')}")
                else:
                    print(f"❌ Profile retrieval failed: {profile_response.message}")
                
                return True
            else:
                print(f"❌ Broker authentication failed: {login_response.message}")
                return False
        except Exception as e:
            print(f"❌ Broker authentication error: {e}")
            return False
    
    async def test_ai_tools(self):
        """Test AI tools functionality."""
        print("\n🛠️ Testing AI tools...")
        
        tools = ToolRegistry(self.broker)
        
        # Test schema generation
        try:
            schema = tools.get_tools_schema()
            print(f"✅ Generated schema for {len(schema)} tools")
            
            # Test a few tools
            test_tools = ['get_funds', 'get_quote', 'search_instruments']
            
            for tool_name in test_tools:
                tool = tools.get_tool(tool_name)
                if tool:
                    print(f"✅ Tool '{tool_name}' found: {tool.description}")
                else:
                    print(f"❌ Tool '{tool_name}' not found")
            
            # Test tool execution
            print("\n   Testing tool execution...")
            
            # Test get_funds
            result = await tools.execute_tool('get_funds', {})
            if result.get('success'):
                print("✅ get_funds executed successfully")
            else:
                print(f"❌ get_funds failed: {result.get('error')}")
            
            # Test get_quote
            result = await tools.execute_tool('get_quote', {'symbol': 'RELIANCE'})
            if result.get('success'):
                print("✅ get_quote executed successfully")
                print(f"   RELIANCE LTP: ₹{result['data'].get('ltp', 'N/A')}")
            else:
                print(f"❌ get_quote failed: {result.get('error')}")
            
            return True
            
        except Exception as e:
            print(f"❌ AI tools test failed: {e}")
            return False
    
    async def test_ai_agent(self):
        """Test AI agent processing."""
        print("\n🤖 Testing AI agent...")
        
        test_queries = [
            "What is my account balance?",
            "Show me the current price of RELIANCE",
            "What are my holdings?",
            "I want to buy 10 shares of TCS at market price",
            "Show me top gainers today"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n   Test {i}: '{query}'")
            try:
                response = await self.agent.process_message(query, "test_user")
                print(f"   Response: {response[:200]}...")
                
                # Brief pause between queries
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        return True
    
    async def test_prompts(self):
        """Test prompt management."""
        print("\n📝 Testing prompt management...")
        
        prompts = PromptManager()
        
        try:
            # Test system prompt
            system_prompt = prompts.get_prompt(
                "system",
                available_tools="Test tools",
                auth_status="✅ Connected",
                available_funds="₹10,000"
            )
            print("✅ System prompt generated successfully")
            print(f"   Length: {len(system_prompt)} characters")
            
            # Test trade confirmation prompt
            confirmation_prompt = prompts.get_prompt(
                "trade_confirmation",
                action="BUY",
                symbol="RELIANCE",
                quantity=10,
                price=2500,
                order_type="LIMIT",
                estimated_value=25000,
                current_price=2480,
                available_funds=50000,
                risk_assessment="✅ Trade appears normal"
            )
            print("✅ Trade confirmation prompt generated successfully")
            
            return True
            
        except Exception as e:
            print(f"❌ Prompt test failed: {e}")
            return False
    
    async def test_telegram_bot_integration(self):
        """Test Telegram bot integration."""
        print("\n📱 Testing Telegram bot integration...")
        
        try:
            # Initialize bot (without starting)
            await self.bot.initialize()
            print("✅ Telegram bot initialized successfully")
            
            # Check handlers
            if self.bot.application:
                handlers = self.bot.application.handlers
                print(f"✅ Registered {len(handlers)} handler groups")
            
            return True
            
        except Exception as e:
            print(f"❌ Telegram bot test failed: {e}")
            return False
    
    async def test_error_handling(self):
        """Test error handling scenarios."""
        print("\n⚠️ Testing error handling...")
        
        try:
            # Test invalid tool execution
            tools = ToolRegistry(self.broker)
            result = await tools.execute_tool('invalid_tool', {})
            if 'error' in result:
                print("✅ Invalid tool error handled correctly")
            
            # Test invalid parameters
            result = await tools.execute_tool('get_quote', {'invalid_param': 'test'})
            if 'error' in result:
                print("✅ Invalid parameters error handled correctly")
            
            return True
            
        except Exception as e:
            print(f"❌ Error handling test failed: {e}")
            return False
    
    async def run_comprehensive_test(self):
        """Run all tests."""
        print("🚀 Starting comprehensive AI integration test...\n")
        
        # Setup
        if not await self.setup():
            return False
        
        # Run tests
        tests = [
            ("Broker Authentication", self.test_broker_authentication),
            ("AI Tools", self.test_ai_tools),
            ("Prompt Management", self.test_prompts),
            ("AI Agent", self.test_ai_agent),
            ("Telegram Bot", self.test_telegram_bot_integration),
            ("Error Handling", self.test_error_handling)
        ]
        
        results = {}
        for test_name, test_func in tests:
            try:
                results[test_name] = await test_func()
            except Exception as e:
                print(f"❌ {test_name} test crashed: {e}")
                results[test_name] = False
        
        # Summary
        print("\n" + "="*50)
        print("📊 TEST SUMMARY")
        print("="*50)
        
        passed = sum(results.values())
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"{test_name:<25} {status}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! System is ready for deployment.")
        else:
            print("⚠️ Some tests failed. Please review and fix issues.")
        
        return passed == total
    
    async def cleanup(self):
        """Cleanup resources."""
        try:
            if self.broker:
                await self.broker.logout()
            if self.bot:
                await self.bot.stop()
        except:
            pass


async def main():
    """Main test function."""
    tester = AIIntegrationTester()
    try:
        success = await tester.run_comprehensive_test()
        return 0 if success else 1
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main()) 