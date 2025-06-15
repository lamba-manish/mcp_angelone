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
from .broker_manager import broker_manager
from .ai_handler import ai_handler
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
        
    async def initialize(self):
        """Initialize the bot application and handlers."""
        try:
            # Create application
            self.application = Application.builder().token(settings.telegram_bot_token).build()
            
            # Start session and broker managers
            await session_manager.start()
            await broker_manager.start()
            
            # Register handlers
            await self._register_handlers()
            
            # Setup bot commands menu
            await self._setup_bot_commands()
            
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
        await broker_manager.stop()
    
    async def _register_handlers(self):
        """Register all command and message handlers."""
        from .handlers import (
            start_handler, help_handler, broker_selection_handler, 
            status_handler, trading_handler
        )
        
        # Command handlers - these should bypass AI and go directly to handlers
        self.application.add_handler(CommandHandler("start", start_handler))
        self.application.add_handler(CommandHandler("help", help_handler))
        self.application.add_handler(CommandHandler("broker", broker_selection_handler))
        self.application.add_handler(CommandHandler("status", status_handler))
        
        # Direct trading command handlers - bypass AI completely
        self.application.add_handler(CommandHandler("buy", trading_handler))
        self.application.add_handler(CommandHandler("sell", trading_handler))
        self.application.add_handler(CommandHandler("holdings", trading_handler))
        self.application.add_handler(CommandHandler("positions", trading_handler))
        self.application.add_handler(CommandHandler("orders", trading_handler))
        self.application.add_handler(CommandHandler("funds", trading_handler))
        self.application.add_handler(CommandHandler("quote", trading_handler))
        self.application.add_handler(CommandHandler("cancel_all_pending_orders", trading_handler))
        self.application.add_handler(CommandHandler("logout", trading_handler))
        self.application.add_handler(CommandHandler("market_depth", trading_handler))
        self.application.add_handler(CommandHandler("top_gainers", trading_handler))
        self.application.add_handler(CommandHandler("top_losers", trading_handler))
        self.application.add_handler(CommandHandler("graph", trading_handler))
        
        # AI-specific commands
        self.application.add_handler(CommandHandler("ai", self._ai_toggle_handler))
        self.application.add_handler(CommandHandler("clear_conversation", self._clear_conversation_handler))
        
        # Callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self._handle_callback_query))
        
        # Message handler for text messages (only for AI chat, not commands)
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self._handle_message
        ))
        
        logger.info("All handlers registered successfully")
    
    async def _setup_bot_commands(self):
        """Setup the bot commands menu that appears when users type '/'."""
        commands = [
            BotCommand("start", "Welcome & setup"),
            BotCommand("broker", "Select/change broker"),
            BotCommand("ai", "Toggle AI assistant mode"),
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
            BotCommand("clear_conversation", "Clear AI conversation history"),
            BotCommand("status", "Check connection status"),
            BotCommand("logout", "Logout from broker"),
            BotCommand("help", "Show detailed help")
        ]
        
        try:
            await self.application.bot.set_my_commands(commands)
            logger.info("Bot commands menu set successfully")
        except Exception as e:
            logger.error(f"Failed to set bot commands: {e}")
    
    async def _ai_toggle_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle AI toggle command."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        try:
            session = await session_manager.get_session(user_id, chat_id)
            
            # Toggle AI mode
            ai_enabled = session.context_data.get('ai_enabled', True)
            await session_manager.update_session(
                user_id, 
                context={'ai_enabled': not ai_enabled}
            )
            
            if not ai_enabled:  # AI is being enabled
                # Get agent and show examples
                agent = await ai_handler.get_or_create_agent(user_id)
                
                if agent:
                    # Get authentication status
                    try:
                        profile_response = await agent.broker.get_profile()
                        auth_status = "✅ Connected to AngelOne" if profile_response.success else "❌ Not Connected"
                    except:
                        auth_status = "❌ Not Connected"
                    
                    # Get available funds
                    try:
                        funds_response = await agent.broker.get_funds()
                        if funds_response.success:
                            available_funds = f"₹{funds_response.data.get('availableCash', 0):,.2f}"
                        else:
                            available_funds = "Not available"
                    except:
                        available_funds = "Not available"
                    
                    ai_help_message = agent.prompts.get_prompt(
                        "ai_help",
                        auth_status=auth_status,
                        available_funds=available_funds
                    )
                    await update.message.reply_text(ai_help_message, parse_mode='Markdown')
                else:
                    await update.message.reply_text(
                        "🤖 **AI Assistant Enabled!**\n\n"
                        "You can now chat naturally with me!\n\n"
                        "**Examples:**\n"
                        "• \"What's my balance?\"\n"
                        "• \"RELIANCE current price\"\n"
                        "• \"Show my holdings\"\n"
                        "• \"Buy 10 TCS shares\"\n\n"
                        "Please ensure you're logged in with /broker first."
                    )
            else:
                await update.message.reply_text(
                    "🤖 AI Assistant has been **disabled**.\n\n"
                    "AI responses are now disabled. Use specific commands like /funds, /holdings, etc."
                )
            
        except Exception as e:
            logger.error(f"Error toggling AI mode: {e}")
            await update.message.reply_text("❌ Error toggling AI mode.")
    
    async def _clear_conversation_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle clear conversation command."""
        user_id = update.effective_user.id
        
        try:
            await ai_handler.clear_conversation(user_id)
            await update.message.reply_text("🗑️ Conversation history cleared!")
        except Exception as e:
            logger.error(f"Error clearing conversation: {e}")
            await update.message.reply_text("❌ Error clearing conversation.")
    
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
        """Handle text messages - with AI processing or traditional routing."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        message_text = update.message.text
        
        try:
            session = await session_manager.get_session(user_id, chat_id)
            
            # Check if AI is enabled (default: True)
            ai_enabled = session.context_data.get('ai_enabled', True)
            
            # If AI is enabled and user is authenticated, use AI handler
            if ai_enabled and session.state == UserState.AUTHENTICATED:
                await ai_handler.handle_ai_message(update, context)
                return
            
            # Fall back to traditional state-based handling
            await self._handle_traditional_message(update, session, message_text)
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def _handle_traditional_message(self, update: Update, session, message_text: str):
        """Handle messages using traditional state-based routing."""
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
            await update.message.reply_text(
                "I didn't understand that. You can:\n"
                "• Use /ai to enable AI assistant\n"
                "• Use specific commands like /help\n"
                "• Type /broker to login"
            )
    
    async def _handle_start_state(self, update: Update, session):
        """Handle messages in START state."""
        await update.message.reply_text(
            "👋 Welcome to the Trading Bot!\n\n"
            "🤖 **AI Assistant**: I can understand natural language! Ask me anything about trading.\n"
            "⚙️ **Commands**: You can also use specific commands.\n\n"
            "Please select your broker first using /broker command."
        )
        await session_manager.update_session(
            session.user_id, 
            state=UserState.BROKER_SELECTION
        )
    
    async def _handle_broker_selection_state(self, update: Update, session, message_text: str):
        """Handle messages in BROKER_SELECTION state."""
        await update.message.reply_text(
            "🏦 Please select your broker using the /broker command.\n\n"
            "Available brokers:\n"
            "• AngelOne - Use `/broker` to set up"
        )
    
    async def _handle_authenticated_state(self, update: Update, session, message_text: str):
        """Handle messages in AUTHENTICATED state."""
        # Suggest using AI or commands
        await update.message.reply_text(
            "✅ You're authenticated! You can:\n\n"
            "🤖 **Chat naturally**: Ask me anything!\n"
            "Example: \"What's my balance?\" or \"Buy 10 shares of RELIANCE\"\n\n"
            "⚙️ **Use commands**: Type /help for all commands\n\n"
            "🔄 **Switch modes**: Use /ai to toggle AI assistant"
        )
    
    async def _handle_order_input_state(self, update: Update, session, message_text: str):
        """Handle messages in order input states."""
        # This should be handled by the trading handler
        await update.message.reply_text("Please use the specific trading commands or enable AI mode with /ai")
    
    async def _handle_broker_selection(self, query, session, broker_name: str):
        """Handle broker selection from callback."""
        await self._select_broker_internal(query.message, session, broker_name)
    
    async def _select_broker(self, update: Update, session, broker_name: str):
        """Select broker for user."""
        await self._select_broker_internal(update.message, session, broker_name)
    
    async def _select_broker_internal(self, message, session, broker_name: str):
        """Internal broker selection logic."""
        try:
            # Use centralized broker manager
            broker = await broker_manager.get_or_create_broker(session.user_id)
            
            if broker:
                # Update session with broker selection and ensure authentication status
                await session_manager.update_session(
                    session.user_id,
                    state=UserState.AUTHENTICATED,
                    broker_authenticated=True,
                    selected_broker=broker_name
                )
                
                # Get profile info to show user details
                try:
                    profile_response = await broker.get_profile()
                    if profile_response.success:
                        profile = profile_response.data
                        client_name = profile.get('name', 'N/A')
                        client_id = profile.get('clientcode', 'N/A')
                        
                        await message.edit_text(
                            f"✅ Successfully connected to {broker_name}!\n\n"
                            f"👤 **Account Details:**\n"
                            f"• Name: {client_name}\n"
                            f"• Client ID: {client_id}\n\n"
                            f"🤖 **AI Assistant is now active!**\n"
                            f"You can chat naturally with me or use specific commands.\n\n"
                            f"Try asking: \"What's my balance?\" or \"Show me RELIANCE price\""
                        )
                    else:
                        await message.edit_text(
                            f"✅ Successfully connected to {broker_name}!\n\n"
                            f"🤖 **AI Assistant is now active!**\n"
                            f"You can chat naturally with me or use specific commands.\n\n"
                            f"Try asking: \"What's my balance?\" or \"Show me RELIANCE price\""
                        )
                except Exception as profile_error:
                    logger.warning(f"Could not fetch profile after connection: {profile_error}")
                    await message.edit_text(
                        f"✅ Successfully connected to {broker_name}!\n\n"
                        f"🤖 **AI Assistant is now active!**\n"
                        f"You can chat naturally with me or use specific commands.\n\n"
                        f"Try asking: \"What's my balance?\" or \"Show me RELIANCE price\""
                    )
            else:
                await session_manager.update_session(
                    session.user_id,
                    broker_authenticated=False
                )
                await message.edit_text(f"❌ Failed to connect to {broker_name}. Please try again.")
                
        except Exception as e:
            logger.error(f"Error selecting broker {broker_name}: {e}")
            await session_manager.update_session(
                session.user_id,
                broker_authenticated=False
            )
            await message.edit_text(f"❌ Error connecting to {broker_name}: {str(e)}")
    
    def get_broker_for_user(self, user_id: int):
        """Get broker instance for user (legacy method for compatibility)."""
        # This method is now handled by broker_manager
        return None  # Will be replaced by broker_manager calls


# Global bot instance
trading_bot = TradingBot() 