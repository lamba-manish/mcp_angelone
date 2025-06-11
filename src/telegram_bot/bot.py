"""Main Telegram bot implementation."""

import asyncio
from typing import Dict, Optional, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    filters,
    ContextTypes
)

from .models import UserState, CommandContext
from .session_manager import session_manager
from .handlers import (
    start_handler,
    broker_selection_handler,
    trading_handler,
    help_handler,
    status_handler
)
from ..brokers.base import BrokerFactory
from ..brokers.angelone import AngelOneBroker
from ..config import settings
from ..utils.logging import get_logger
from ..utils.exceptions import TelegramBotError

logger = get_logger(__name__)


class TradingBot:
    """Main trading bot class."""
    
    def __init__(self):
        """Initialize the trading bot."""
        self.application: Optional[Application] = None
        self.broker_instances: Dict[str, any] = {}
        
    async def initialize(self):
        """Initialize the bot application and handlers."""
        try:
            # Create application
            self.application = Application.builder().token(settings.telegram_bot_token).build()
            
            # Start session manager
            await session_manager.start()
            
            # Register handlers
            await self._register_handlers()
            
            logger.info("Trading bot initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize trading bot: {e}")
            raise TelegramBotError(f"Bot initialization failed: {e}")
    
    async def start(self):
        """Start the bot."""
        if not self.application:
            await self.initialize()
        
        logger.info("Starting trading bot")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(drop_pending_updates=True)
    
    async def stop(self):
        """Stop the bot."""
        if self.application:
            logger.info("Stopping trading bot")
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
        
        await session_manager.stop()
    
    async def _register_handlers(self):
        """Register command and message handlers."""
        app = self.application
        
        # Command handlers
        app.add_handler(CommandHandler("start", start_handler))
        app.add_handler(CommandHandler("help", help_handler))
        app.add_handler(CommandHandler("status", status_handler))
        app.add_handler(CommandHandler("broker", broker_selection_handler))
        app.add_handler(CommandHandler("buy", trading_handler))
        app.add_handler(CommandHandler("sell", trading_handler))
        app.add_handler(CommandHandler("holdings", trading_handler))
        app.add_handler(CommandHandler("positions", trading_handler))
        app.add_handler(CommandHandler("orders", trading_handler))
        app.add_handler(CommandHandler("funds", trading_handler))
        app.add_handler(CommandHandler("quote", trading_handler))
        app.add_handler(CommandHandler("cancel_all_pending_orders", trading_handler))
        app.add_handler(CommandHandler("top_gainers", trading_handler))
        app.add_handler(CommandHandler("top_losers", trading_handler))
        app.add_handler(CommandHandler("market_depth", trading_handler))
        app.add_handler(CommandHandler("graph", trading_handler))
        app.add_handler(CommandHandler("logout", trading_handler))
        
        # Callback query handler for inline keyboards
        app.add_handler(CallbackQueryHandler(self._handle_callback_query))
        
        # Message handler for text messages
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
        
        # Setup bot commands menu
        await self._setup_bot_commands()
        
        logger.info("Registered all bot handlers")
    
    async def _setup_bot_commands(self):
        """Setup the bot commands menu that appears when users type '/'."""
        commands = [
            BotCommand("start", "Welcome & setup"),
            BotCommand("broker", "Select/change broker"),
            BotCommand("funds", "Check available funds"),
            BotCommand("orders", "View today's orders"),
            BotCommand("positions", "View current positions"),
            BotCommand("holdings", "View your holdings"),
            BotCommand("buy", "Place buy order (usage: /buy SYMBOL QTY [PRICE])"),
            BotCommand("sell", "Place sell order (usage: /sell SYMBOL QTY [PRICE])"),
            BotCommand("quote", "Get live price quote (usage: /quote SYMBOL)"),
            BotCommand("market_depth", "View market depth (usage: /market_depth SYMBOL)"),
            BotCommand("graph", "Generate candlestick chart (usage: /graph SYMBOL TIMEFRAME)"),
            BotCommand("top_gainers", "View top price gainers"),
            BotCommand("top_losers", "View top price losers"),
            BotCommand("cancel_all_pending_orders", "Cancel all pending orders"),
            BotCommand("status", "Check connection status"),
            BotCommand("logout", "Logout from broker"),
            BotCommand("help", "Show detailed help")
        ]
        
        try:
            await self.application.bot.set_my_commands(commands)
            logger.info("Bot commands menu set successfully")
        except Exception as e:
            logger.error(f"Failed to set bot commands: {e}")
    
    async def _handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard callbacks."""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        chat_id = query.message.chat_id
        data = query.data
        
        try:
            session = await session_manager.get_session(user_id, chat_id)
            
            # Handle broker selection
            if data.startswith("broker_"):
                broker_name = data.replace("broker_", "")
                await self._handle_broker_selection(query, session, broker_name)
            
            # Handle other callbacks as needed
            elif data == "refresh_status":
                await status_handler(update, context)
            
        except Exception as e:
            logger.error(f"Error handling callback query: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages based on user state."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        message_text = update.message.text
        
        try:
            session = await session_manager.get_session(user_id, chat_id)
            
            # Route message based on current state
            if session.state == UserState.START:
                await self._handle_start_state(update, session)
            elif session.state == UserState.BROKER_SELECTION:
                await self._handle_broker_selection_state(update, session, message_text)
            elif session.state == UserState.AUTHENTICATED:
                await self._handle_authenticated_state(update, session, message_text)
            elif session.state in [UserState.WAITING_SYMBOL, UserState.WAITING_QUANTITY, UserState.WAITING_PRICE]:
                await self._handle_order_input_state(update, session, message_text)
            else:
                await update.message.reply_text("I didn't understand that. Type /help for available commands.")
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def _handle_start_state(self, update: Update, session):
        """Handle messages in START state."""
        await update.message.reply_text(
            "👋 Welcome to the Trading Bot!\n\n"
            "Please select your broker first using /broker command."
        )
        await session_manager.update_session(
            session.user_id, 
            state=UserState.BROKER_SELECTION
        )
    
    async def _handle_broker_selection_state(self, update: Update, session, message_text: str):
        """Handle broker selection via text."""
        available_brokers = BrokerFactory.get_available_brokers()
        broker_name = message_text.upper()
        
        if broker_name in [b.upper() for b in available_brokers]:
            # Find the actual broker name (case-sensitive)
            actual_broker = next(b for b in available_brokers if b.upper() == broker_name)
            await self._select_broker(update, session, actual_broker)
        else:
            await update.message.reply_text(
                f"❌ Unknown broker: {message_text}\n\n"
                f"Available brokers: {', '.join(available_brokers)}\n"
                "Please use /broker command to select."
            )
    
    async def _handle_authenticated_state(self, update: Update, session, message_text: str):
        """Handle messages when user is authenticated."""
        # Parse natural language commands
        text_lower = message_text.lower()
        
        if any(word in text_lower for word in ["buy", "purchase"]):
            await update.message.reply_text(
                "📈 To place a buy order, use: /buy SYMBOL QUANTITY [PRICE]\n"
                "Example: /buy RELIANCE 10 2500"
            )
        elif any(word in text_lower for word in ["sell"]):
            await update.message.reply_text(
                "📉 To place a sell order, use: /sell SYMBOL QUANTITY [PRICE]\n"
                "Example: /sell RELIANCE 5 2600"
            )
        elif any(word in text_lower for word in ["holdings", "portfolio"]):
            # Trigger holdings command
            context = CommandContext(
                user_session=session,
                message_text="/holdings",
                command="holdings"
            )
            await trading_handler(update, None)
        elif any(word in text_lower for word in ["positions"]):
            context = CommandContext(
                user_session=session,
                message_text="/positions",
                command="positions"
            )
            await trading_handler(update, None)
        else:
            await update.message.reply_text(
                "💡 Here are some commands you can use:\n\n"
                "📊 Trading Commands:\n"
                "• /buy - Place buy order\n"
                "• /sell - Place sell order\n"
                "• /holdings - View holdings\n"
                "• /positions - View positions\n"
                "• /orders - View orders\n"
                "• /funds - Check funds\n"
                "• /quote SYMBOL - Get live quote\n\n"
                "📈 Market Data:\n"
                "• /top_gainers - Top gainers\n"
                "• /top_losers - Top losers\n"
                "• /market_depth SYMBOL - Market depth\n"
                "• /graph SYMBOL TIMEFRAME - Candlestick chart\n\n"
                "⚙️ Other Commands:\n"
                "• /status - Check connection status\n"
                "• /broker - Change broker\n"
                "• /help - Show help"
            )
    
    async def _handle_order_input_state(self, update: Update, session, message_text: str):
        """Handle order input in multi-step flow."""
        # This will be implemented when we add the order placement flow
        await update.message.reply_text("Order input handling coming soon...")
    
    async def _handle_broker_selection(self, query, session, broker_name: str):
        """Handle broker selection from inline keyboard."""
        await self._select_broker_internal(query.message, session, broker_name)
        await query.edit_message_text(f"✅ Selected broker: {broker_name}")
    
    async def _select_broker(self, update: Update, session, broker_name: str):
        """Select broker and attempt authentication."""
        await self._select_broker_internal(update.message, session, broker_name)
    
    async def _select_broker_internal(self, message, session, broker_name: str):
        """Internal broker selection logic."""
        try:
            # Update session with selected broker
            await session_manager.update_session(
                session.user_id,
                selected_broker=broker_name
            )
            
            # Get or create broker instance
            broker = await self._get_broker_instance(broker_name)
            
            # Attempt authentication
            await message.reply_text(f"🔄 Connecting to {broker_name}...")
            
            login_response = await broker.login()
            
            if login_response.success:
                await session_manager.update_session(
                    session.user_id,
                    state=UserState.AUTHENTICATED,
                    broker_authenticated=True
                )
                
                await message.reply_text(
                    f"✅ Successfully connected to {broker_name}!\n\n"
                    "You can now start trading. Type /help for available commands."
                )
            else:
                await message.reply_text(
                    f"❌ Failed to connect to {broker_name}: {login_response.message}\n\n"
                    "Please check your credentials in the .env file."
                )
                
        except Exception as e:
            logger.error(f"Error selecting broker {broker_name}: {e}")
            await message.reply_text(
                f"❌ Error connecting to {broker_name}: {str(e)}"
            )
    
    async def _get_broker_instance(self, broker_name: str):
        """Get or create broker instance."""
        if broker_name not in self.broker_instances:
            self.broker_instances[broker_name] = BrokerFactory.create_broker(broker_name)
        
        return self.broker_instances[broker_name]
    
    def get_broker_for_user(self, user_id: int):
        """Get broker instance for a user."""
        if user_id in session_manager._sessions:
            session = session_manager._sessions[user_id]
            if session.selected_broker and session.broker_authenticated:
                return self.broker_instances.get(session.selected_broker)
        return None


# Global bot instance
trading_bot = TradingBot() 