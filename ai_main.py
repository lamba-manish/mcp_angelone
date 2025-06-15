"""
Main entry point for AI-integrated trading bot.
This script starts the Telegram bot with AI capabilities.
"""

import asyncio
import signal
import sys
import os
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.telegram_bot.bot import TradingBot
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AITradingBotRunner:
    """Runner for AI-integrated trading bot."""
    
    def __init__(self):
        self.bot = None
        self.shutdown_event = asyncio.Event()
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        asyncio.create_task(self.shutdown())
    
    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("Shutting down AI Trading Bot...")
        self.shutdown_event.set()
        
        if self.bot:
            await self.bot.stop()
        
        logger.info("AI Trading Bot stopped.")
    
    async def start(self):
        """Start the AI trading bot."""
        try:
            # Load environment variables
            load_dotenv()
            
            # Check critical environment variables
            required_vars = [
                'TELEGRAM_BOT_TOKEN',
                'ANGELONE_API_KEY',
                'ANGELONE_USER_ID',
                'ANGELONE_PASSWORD',
                'ANGELONE_TOTP_SECRET',
                'OPENAI_API_KEY'
            ]
            
            missing_vars = []
            for var in required_vars:
                if not os.getenv(var):
                    missing_vars.append(var)
            
            if missing_vars:
                logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
                logger.error("Please create a .env file with all required variables.")
                logger.error("Check env.example for the required format.")
                return False
            
            # Initialize and start bot
            logger.info("🤖 Starting AI-Integrated Trading Bot...")
            logger.info("Features enabled:")
            logger.info("  ✅ Natural Language Processing with OpenAI")
            logger.info("  ✅ AngelOne Broker Integration")
            logger.info("  ✅ Telegram Bot Interface")
            logger.info("  ✅ Advanced Trade Confirmation")
            logger.info("  ✅ Real-time Market Data")
            
            self.bot = TradingBot()
            
            # Setup signal handlers
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            
            # Start bot
            await self.bot.start()
            
            logger.info("🚀 AI Trading Bot is now running!")
            logger.info("Send a message to your Telegram bot to get started.")
            logger.info("The AI assistant will help you with:")
            logger.info("  • Account management and funds checking")
            logger.info("  • Live market data and quotes")
            logger.info("  • Portfolio analysis and holdings review")
            logger.info("  • Intelligent trade execution with confirmations")
            logger.info("  • Market research and trend analysis")
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
            return True
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
            await self.shutdown()
            return True
        except Exception as e:
            logger.error(f"Failed to start AI Trading Bot: {e}")
            if self.bot:
                await self.bot.stop()
            return False


async def main():
    """Main function."""
    runner = AITradingBotRunner()
    success = await runner.start()
    return 0 if success else 1


def run():
    """Entry point for running the bot."""
    print("=" * 60)
    print("🤖 AI-INTEGRATED TRADING BOT")
    print("=" * 60)
    print("Features:")
    print("• Natural language conversation with OpenAI GPT")
    print("• AngelOne broker integration for live trading")
    print("• Intelligent trade confirmations and risk assessment")
    print("• Real-time market data and analysis")
    print("• Portfolio management and holdings analysis")
    print("• Advanced market research capabilities")
    print("=" * 60)
    print()
    
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run() 