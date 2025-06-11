"""Main application entry point for the trading bot."""

import asyncio
import signal
import sys
from contextlib import asynccontextmanager

from src.telegram_bot.bot import trading_bot
from src.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class TradingBotApplication:
    """Main application class for the trading bot."""
    
    def __init__(self):
        """Initialize the application."""
        self.running = False
        self.shutdown_event = asyncio.Event()
    
    async def startup(self):
        """Startup sequence for the application."""
        logger.info("Starting Trading Bot Application")
        logger.info(f"Environment: {settings.environment}")
        logger.info(f"Debug mode: {settings.debug}")
        
        try:
            # Initialize and start the trading bot
            await trading_bot.initialize()
            logger.info("Trading bot initialized successfully")
            
            # Start the bot
            await trading_bot.start()
            logger.info("Trading bot started successfully")
            
            self.running = True
            logger.info("Application startup completed")
            
        except Exception as e:
            logger.error(f"Failed to start application: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown sequence for the application."""
        logger.info("Shutting down Trading Bot Application")
        
        try:
            # Stop the trading bot
            await trading_bot.stop()
            logger.info("Trading bot stopped successfully")
            
            self.running = False
            self.shutdown_event.set()
            logger.info("Application shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            raise
    
    async def run(self):
        """Run the application."""
        try:
            await self.startup()
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Application error: {e}")
            raise
        finally:
            await self.shutdown()
    
    def handle_signal(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}")
        asyncio.create_task(self.shutdown())


def setup_signal_handlers(app: TradingBotApplication):
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown")
        if app.running:
            asyncio.create_task(app.shutdown())
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if hasattr(signal, 'SIGHUP'):
        signal.signal(signal.SIGHUP, signal_handler)


async def main():
    """Main application function."""
    logger.info("=" * 50)
    logger.info("Trading Bot Application Starting")
    logger.info("=" * 50)
    
    app = TradingBotApplication()
    setup_signal_handlers(app)
    
    try:
        await app.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    
    logger.info("Trading Bot Application Exited")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        sys.exit(1) 