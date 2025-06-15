"""Telegram bot command handlers."""

from typing import List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from .models import UserState
from .session_manager import session_manager
from ..brokers.base import BrokerFactory
from ..models.trading import OrderRequest, TransactionType, OrderType, ProductType, Exchange
from ..utils.logging import get_logger

logger = get_logger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Get or create session
    session = await session_manager.get_session(user.id, chat_id)
    
    welcome_text = f"""🤖 <b>Welcome to the Trading Bot, {user.first_name}!</b>

I'm your personal trading assistant that helps you trade through multiple brokers.

<b>Getting Started:</b>
1. Select your broker using /broker
2. I'll authenticate with your broker
3. Start trading with simple commands!

<b>Available Commands:</b>
📊 Trading: /buy, /sell, /holdings, /positions, /orders
💰 Account: /funds, /quote
📈 Market Data: /market_depth, /graph, /top_gainers, /top_losers
⚙️ Settings: /broker, /status, /logout, /help

Let's get started! Use /broker to select your broker."""
    
    await update.message.reply_text(welcome_text, parse_mode='HTML')
    
    # Update session state
    await session_manager.update_session(
        user.id,
        state=UserState.BROKER_SELECTION
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = """🤖 **Trading Bot Help**

**📋 Available Commands:**

**🔧 Setup & Info:**
• `/start` - Welcome & setup
• `/broker` - Select/change broker
• `/status` - Check connection status
• `/logout` - Logout from broker

**💰 Account Commands:**
• `/funds` - Check available funds
• `/orders` - View today's orders
• `/positions` - View current positions
• `/holdings` - View your holdings

**📊 Trading Commands:**
• `/buy SYMBOL QTY [PRICE]` - Place buy order
• `/sell SYMBOL QTY [PRICE]` - Place sell order
• `/quote SYMBOL` - Get live price quote

**📈 Market Data:**
• `/market_depth SYMBOL` - View detailed market depth data
• `/graph SYMBOL TIMEFRAME` - Generate candlestick chart
• `/top_gainers` - View top price gainers (derivatives)
• `/top_losers` - View top price losers (derivatives)

**🔧 Other:**
• `/cancel_all_pending_orders` - Cancel all pending orders
• `/help` - Show this detailed help

**📝 Examples:**
• `/buy RELIANCE 1 1450` - Buy 1 share of Reliance at ₹1450
• `/sell TCS 2 3800` - Sell 2 shares of TCS at ₹3800  
• `/buy ITC 10` - Buy 10 shares of ITC at market price
• `/quote HDFC` - Get live price of HDFC
• `/market_depth SBIN` - Get market depth for SBI
• `/graph RELIANCE 5M` - Generate 5-minute candlestick chart for Reliance

**⏰ Chart Timeframes:**
• 1M, 3M, 5M, 10M, 15M, 30M, 1H, 1D

**📱 Note:** Use the menu button (/) to see all commands.

**💡 Tips:**
• You can type natural commands like "buy reliance" 
• All prices are in ₹ (INR)
• Market orders execute immediately
• Limit orders execute at your specified price
• For NSE stocks, you can use just the symbol name (e.g., RELIANCE)
• Top gainers/losers data is from derivatives segment

**🔐 Security:**
Your credentials are stored securely and never shared.

Need more help? Contact support."""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def broker_selection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /broker command."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    session = await session_manager.get_session(user_id, chat_id)
    available_brokers = BrokerFactory.get_available_brokers()
    
    if not available_brokers:
        await update.message.reply_text(
            "❌ No brokers are currently available. Please contact support."
        )
        return
    
    # Create inline keyboard for broker selection
    keyboard = []
    for broker in available_brokers:
        # Capitalize broker names for display
        display_name = broker.upper()
        keyboard.append([InlineKeyboardButton(
            f"📈 {display_name}", 
            callback_data=f"broker_{broker}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    current_broker = session.selected_broker
    status_text = f"Current broker: {current_broker}" if current_broker else "No broker selected"
    
    await update.message.reply_text(
        f"🏦 **Select Your Broker**\n\n{status_text}\n\nChoose from available brokers:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    await session_manager.update_session(user_id, state=UserState.BROKER_SELECTION)


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    session = await session_manager.get_session(user_id, chat_id)
    
    # Get status information
    broker_status = "✅ Connected" if session.broker_authenticated else "❌ Not connected"
    selected_broker = session.selected_broker or "None"
    session_state = session.state.value
    
    status_text = f"""📊 **Connection Status**

**Broker:** {selected_broker}
**Status:** {broker_status}
**Session State:** {session_state}
**Last Updated:** {session.updated_at.strftime('%Y-%m-%d %H:%M:%S')}

**Available Brokers:** {', '.join(BrokerFactory.get_available_brokers())}"""
    
    # Get profile information if connected
    if session.broker_authenticated and selected_broker:
        try:
            from .bot import trading_bot
            broker = trading_bot.get_broker_for_user(user_id)
            if broker:
                profile_response = await broker.get_profile()
                if profile_response.success and profile_response.data:
                    client_code = profile_response.data.get('clientcode', 'N/A')
                    client_name = profile_response.data.get('name', 'N/A')
                    status_text += f"""

**👤 Account Details:**
**Client ID:** {client_code}
**Name:** {client_name}"""
        except Exception as e:
            logger.error(f"Error getting profile for status: {e}")
    
    # Add refresh button
    keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="refresh_status")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        status_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def trading_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle trading commands."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Get user session
    session = await session_manager.get_session(user_id, chat_id)
    
    if not session.broker_authenticated:
        await update.message.reply_text(
            "❌ Please select and connect to a broker first using /broker"
        )
        return
    
    # Get broker from centralized broker manager
    from .broker_manager import broker_manager
    broker = await broker_manager.get_broker(user_id)
    
    if not broker:
        await update.message.reply_text(
            "❌ Broker connection lost. Please reconnect using /broker"
        )
        return
    
    # Parse command
    command_text = update.message.text
    parts = command_text.split()
    command = parts[0][1:] if parts[0].startswith('/') else parts[0]  # Remove '/'
    
    try:
        if command in ['buy', 'sell']:
            await handle_order_command(update, context, broker, command, parts[1:])
        elif command == 'holdings':
            await handle_holdings_command(update, context, broker)
        elif command == 'positions':
            await handle_positions_command(update, context, broker)
        elif command == 'orders':
            await handle_orders_command(update, context, broker)
        elif command == 'funds':
            await handle_funds_command(update, context, broker)
        elif command == 'quote':
            await handle_quote_command(update, context, broker, parts[1:])
        elif command == 'cancel_all_pending_orders':
            await handle_cancel_all_pending_orders_command(update, context, broker)
        elif command == 'logout':
            await handle_logout_command(update, context, broker, user_id)
        elif command == 'top_gainers':
            await handle_top_gainers_command(update, context, broker)
        elif command == 'top_losers':
            await handle_top_losers_command(update, context, broker)
        elif command == 'market_depth':
            await handle_market_depth_command(update, context, broker, parts[1:])
        elif command == 'graph':
            await handle_graph_command(update, context, broker, parts[1:])
        else:
            await update.message.reply_text(
                f"❌ Unknown trading command: {command}\n"
                "Use /help to see available commands."
            )
            
    except Exception as e:
        logger.error(f"Error handling trading command {command}: {e}")
        await update.message.reply_text(
            f"❌ Error executing {command}: {str(e)}"
        )


async def handle_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                             broker, command: str, args: List[str]):
    """Handle buy/sell order commands."""
    if len(args) < 2:
        await update.message.reply_text(
            f"❌ Usage: /{command} SYMBOL QUANTITY [PRICE]\n"
            f"Example: /{command} RELIANCE 10 2500"
        )
        return
    
    symbol = args[0].upper()
    try:
        quantity = int(args[1])
    except ValueError:
        await update.message.reply_text("❌ Quantity must be a number")
        return
    
    price = None
    order_type = OrderType.MARKET
    
    if len(args) > 2:
        try:
            price = float(args[2])
            order_type = OrderType.LIMIT
        except ValueError:
            await update.message.reply_text("❌ Price must be a number")
            return
    
    # Create order request
    order_request = OrderRequest(
        symbol=symbol,
        exchange=Exchange.NSE,  # Default to NSE
        transaction_type=TransactionType.BUY if command == 'buy' else TransactionType.SELL,
        order_type=order_type,
        product_type=ProductType.CNC,  # Default to CNC for delivery
        quantity=quantity,
        price=price
    )
    
    await update.message.reply_text(
        f"🔄 Placing {command} order for {symbol}..."
    )
    
    try:
        response = await broker.place_order(order_request)
        
        if response.success:
            price_text = f" at ₹{price}" if price else " (Market Price)"
            await update.message.reply_text(
                f"✅ {command.title()} order placed successfully!\n\n"
                f"📊 **Order Details:**\n"
                f"Symbol: {symbol}\n"
                f"Quantity: {quantity}\n"
                f"Price: {price_text}\n"
                f"Order ID: {response.data.get('order_id', 'N/A') if hasattr(response.data, 'get') else 'N/A'}"
            )
        else:
            await update.message.reply_text(
                f"❌ Order failed: {response.message}"
            )
            
    except Exception as e:
        await update.message.reply_text(
            f"❌ Error placing order: {str(e)}"
        )


async def handle_holdings_command(update: Update, context: ContextTypes.DEFAULT_TYPE, broker):
    """Handle holdings command."""
    await update.message.reply_text("🔄 Fetching your holdings...")
    
    try:
        holdings = await broker.get_holdings()
        
        if not holdings:
            await update.message.reply_text("📊 You have no holdings.")
            return
        
        holdings_text = "📊 **Your Holdings:**\n\n"
        total_value = 0
        total_pnl = 0
        
        for holding in holdings[:10]:  # Limit to 10 for readability
            value = holding.quantity * holding.current_price
            total_value += float(value)
            total_pnl += float(holding.pnl)
            
            pnl_emoji = "📈" if holding.pnl >= 0 else "📉"
            
            holdings_text += (
                f"**{holding.symbol}**\n"
                f"Qty: {holding.quantity} | LTP: ₹{holding.current_price}\n"
                f"Value: ₹{value:,.2f} | P&L: {pnl_emoji} ₹{holding.pnl:,.2f}\n\n"
            )
        
        if len(holdings) > 10:
            holdings_text += f"... and {len(holdings) - 10} more holdings\n\n"
        
        total_pnl_emoji = "📈" if total_pnl >= 0 else "📉"
        holdings_text += (
            f"**Summary:**\n"
            f"Total Value: ₹{total_value:,.2f}\n"
            f"Total P&L: {total_pnl_emoji} ₹{total_pnl:,.2f}"
        )
        
        await update.message.reply_text(holdings_text, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching holdings: {str(e)}")


async def handle_positions_command(update: Update, context: ContextTypes.DEFAULT_TYPE, broker):
    """Handle positions command."""
    await update.message.reply_text("🔄 Fetching your positions...")
    
    try:
        positions = await broker.get_positions()
        
        if not positions:
            await update.message.reply_text("📊 You have no open positions.")
            return
        
        positions_text = "📊 **Your Positions:**\n\n"
        total_pnl = 0
        
        for position in positions:
            if position.quantity == 0:
                continue
                
            total_pnl += float(position.pnl)
            pnl_emoji = "📈" if position.pnl >= 0 else "📉"
            
            positions_text += (
                f"**{position.symbol}**\n"
                f"Net Qty: {position.quantity} | LTP: ₹{position.current_price}\n"
                f"P&L: {pnl_emoji} ₹{position.pnl:,.2f}\n\n"
            )
        
        total_pnl_emoji = "📈" if total_pnl >= 0 else "📉"
        positions_text += f"**Total P&L: {total_pnl_emoji} ₹{total_pnl:,.2f}**"
        
        await update.message.reply_text(positions_text, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching positions: {str(e)}")


async def handle_orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE, broker):
    """Handle orders command."""
    await update.message.reply_text("🔄 Fetching your orders...")
    
    try:
        orders = await broker.get_orders()
        
        if not orders:
            await update.message.reply_text("📊 You have no orders today.")
            return
        
        # Sort orders by status priority: OPEN -> COMPLETE -> CANCELLED/REJECTED
        def get_status_priority(order):
            status = order.status.value.upper()
            if status in ['OPEN', 'PENDING']:
                return 0  # Highest priority
            elif status in ['COMPLETE']:
                return 1  # Medium priority
            else:  # CANCELLED, REJECTED, etc.
                return 2  # Lowest priority
        
        # Sort orders by status priority
        sorted_orders = sorted(orders, key=get_status_priority)
        
        orders_text = "📊 **Today's Orders:**\n\n"
        
        # Show last 15 orders to give more visibility
        for order in sorted_orders[-15:]:
            status_emoji = {
                "COMPLETE": "✅", "complete": "✅",
                "PENDING": "⏳", "pending": "⏳", 
                "OPEN": "🔄", "open": "🔄",
                "CANCELLED": "❌", "cancelled": "❌",
                "REJECTED": "❌", "rejected": "❌"
            }.get(order.status.value, "❓")
            
            price_text = f"₹{order.price}" if order.price else "Market"
            
            orders_text += (
                f"{status_emoji} **{order.symbol}** - {order.transaction_type.value}\n"
                f"Qty: {order.quantity} | Price: {price_text}\n"
                f"Status: {order.status.value}\n\n"
            )
        
        await update.message.reply_text(orders_text, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching orders: {str(e)}")


async def handle_funds_command(update: Update, context: ContextTypes.DEFAULT_TYPE, broker):
    """Handle funds command."""
    await update.message.reply_text("🔄 Fetching fund information...")
    
    try:
        response = await broker.get_funds()
        
        if response.success and response.data:
            funds_data = response.data
            
            funds_text = (
                "💰 **Fund Information:**\n\n"
                f"Available Cash: ₹{funds_data.get('available_cash', 0):,.2f}\n"
                f"Used Margin: ₹{funds_data.get('used_margin', 0):,.2f}\n"
                f"Available Margin: ₹{funds_data.get('available_margin', 0):,.2f}\n"
                f"Total Balance: ₹{funds_data.get('total', 0):,.2f}"
            )
            
            await update.message.reply_text(funds_text, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ Could not fetch funds: {response.message}")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching funds: {str(e)}")


async def handle_quote_command(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                             broker, args: List[str]):
    """Handle quote command."""
    if not args:
        await update.message.reply_text(
            "❌ Usage: /quote SYMBOL\n"
            "Example: /quote RELIANCE"
        )
        return
    
    symbol = args[0].upper()
    await update.message.reply_text(f"🔄 Fetching quote for {symbol}...")
    
    try:
        quote = await broker.get_quote(symbol, "NSE")
        
        change = float(quote.ltp) - float(quote.close_price)
        change_percent = (change / float(quote.close_price)) * 100 if quote.close_price > 0 else 0
        
        change_emoji = "📈" if change >= 0 else "📉"
        change_text = f"+₹{change:.2f}" if change >= 0 else f"₹{change:.2f}"
        
        quote_text = (
            f"📊 **{symbol} Live Quote**\n\n"
            f"LTP: ₹{quote.ltp}\n"
            f"Change: {change_emoji} {change_text} ({change_percent:+.2f}%)\n"
            f"Open: ₹{quote.open_price}\n"
            f"High: ₹{quote.high_price}\n"
            f"Low: ₹{quote.low_price}\n"
            f"Volume: {quote.volume:,}\n"
            f"Time: {quote.timestamp.strftime('%H:%M:%S')}"
        )
        
        await update.message.reply_text(quote_text, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching quote for {symbol}: {str(e)}") 


async def handle_cancel_all_pending_orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE, broker):
    """Handle cancel all pending orders command."""
    await update.message.reply_text("🔄 Cancelling all pending orders...")
    
    try:
        response = await broker.cancel_all_pending_orders()
        
        if response.success:
            cancelled_count = response.data.get('cancelled_count', 0)
            failed_count = response.data.get('failed_count', 0)
            
            if cancelled_count == 0:
                await update.message.reply_text("📊 No pending orders to cancel.")
            else:
                success_text = f"✅ **Orders Cancelled Successfully!**\n\n"
                success_text += f"📊 **Summary:**\n"
                success_text += f"Cancelled: {cancelled_count} orders\n"
                
                if failed_count > 0:
                    success_text += f"Failed: {failed_count} orders\n"
                    failed_orders = response.data.get('failed_orders', [])
                    if failed_orders:
                        success_text += f"\n**❌ Failed Orders:**\n"
                        for failed in failed_orders[:5]:  # Show first 5 failed orders
                            success_text += f"• {failed.get('symbol', 'N/A')} - {failed.get('error', 'Unknown error')}\n"
                
                await update.message.reply_text(success_text, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ Failed to cancel orders: {response.message}")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error cancelling orders: {str(e)}")


async def handle_logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE, broker, user_id: int):
    """Handle logout command."""
    await update.message.reply_text("🔄 Logging out...")
    
    try:
        response = await broker.logout()
        
        # Update session state
        await session_manager.update_session(
            user_id,
            state=UserState.BROKER_SELECTION,
            broker_authenticated=False
        )
        
        if response.success:
            await update.message.reply_text(
                "✅ **Logged out successfully!**\n\n"
                "Use /broker to connect to a broker again."
            )
        else:
            await update.message.reply_text(
                f"⚠️ Logout completed with warnings: {response.message}\n\n"
                "Session has been cleared locally."
            )
            
    except Exception as e:
        # Even if logout fails, clear local session
        await session_manager.update_session(
            user_id,
            state=UserState.BROKER_SELECTION,
            broker_authenticated=False
        )
        await update.message.reply_text(
            f"⚠️ Logout error: {str(e)}\n\n"
            "Session has been cleared locally. Use /broker to reconnect."
        )


async def handle_market_depth_command(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                     broker, args: List[str]):
    """Handle market depth command."""
    if not args:
        await update.message.reply_text(
            "❌ Please provide a symbol.\n"
            "Usage: `/market_depth SYMBOL`\n"
            "Example: `/market_depth RELIANCE`"
        )
        return
    
    symbol = args[0].upper()
    await update.message.reply_text(f"🔄 Fetching market depth for {symbol}...")
    
    try:
        response = await broker.get_market_depth(symbol)
        
        if not response.success:
            await update.message.reply_text(f"❌ {response.message}")
            return
        
        data = response.data
        depth = data.get("depth", {})
        
        # Format the market depth display
        header = f"📊 **Market Depth - {data['symbol']}**\n"
        header += f"💰 **LTP:** ₹{data['ltp']:.2f}"
        
        # Add change information
        net_change = data['net_change']
        percent_change = data['percent_change']
        change_symbol = "+" if net_change >= 0 else ""
        change_emoji = "🟢" if net_change >= 0 else "🔴"
        header += f" ({change_symbol}{net_change:.2f}, {change_symbol}{percent_change:.2f}%) {change_emoji}\n"
        
        # Add basic info
        header += f"📈 **High:** ₹{data['high']:.2f} | 📉 **Low:** ₹{data['low']:.2f}\n"
        header += f"📊 **Volume:** {data['volume']:,} | 💹 **Avg:** ₹{data['avg_price']:.2f}\n\n"
        
        # Format buy orders (bids) - improved table format
        buy_orders = depth.get("buy", [])
        sell_orders = depth.get("sell", [])
        
        buy_text = "🟢 **BUY ORDERS (BID)**\n"
        buy_text += "```\n"
        buy_text += "Price    │ Qty     │ Orders\n"
        buy_text += "─────────┼─────────┼───────\n"
        
        # Filter out zero values and show meaningful data
        valid_buy_orders = [order for order in buy_orders if order.get("price", 0) > 0 and order.get("quantity", 0) > 0]
        
        if valid_buy_orders:
            for order in valid_buy_orders[:5]:  # Show top 5 buy orders
                price = float(order.get("price", 0))
                quantity = int(order.get("quantity", 0))
                orders = int(order.get("orders", 0))
                buy_text += f"{price:8.2f} │ {quantity:7,} │ {orders:5}\n"
        else:
            buy_text += "No buy orders available\n"
        
        buy_text += "```\n"
        
        # Format sell orders (asks) - improved table format  
        sell_text = "🔴 **SELL ORDERS (ASK)**\n"
        sell_text += "```\n"
        sell_text += "Price    │ Qty     │ Orders\n"
        sell_text += "─────────┼─────────┼───────\n"
        
        # Filter out zero values and show meaningful data
        valid_sell_orders = [order for order in sell_orders if order.get("price", 0) > 0 and order.get("quantity", 0) > 0]
        
        if valid_sell_orders:
            for order in valid_sell_orders[:5]:  # Show top 5 sell orders
                price = float(order.get("price", 0))
                quantity = int(order.get("quantity", 0))
                orders = int(order.get("orders", 0))
                sell_text += f"{price:8.2f} │ {quantity:7,} │ {orders:5}\n"
        else:
            sell_text += "No sell orders available\n"
        
        sell_text += "```\n"
        
        # Add summary
        total_buy_qty = data.get("total_buy_quantity", 0)
        total_sell_qty = data.get("total_sell_quantity", 0)
        
        summary = f"📋 **Summary**\n"
        summary += f"🟢 Total Buy Qty: {total_buy_qty:,}\n"
        summary += f"🔴 Total Sell Qty: {total_sell_qty:,}\n"
        summary += f"📈 52W High: ₹{data['52_week_high']:.2f}\n"
        summary += f"📉 52W Low: ₹{data['52_week_low']:.2f}"
        
        # Send as separate messages due to formatting
        await update.message.reply_text(header, parse_mode='Markdown')
        await update.message.reply_text(buy_text, parse_mode='Markdown')
        await update.message.reply_text(sell_text, parse_mode='Markdown')
        await update.message.reply_text(summary, parse_mode='Markdown')
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching market depth: {str(e)}")


async def handle_top_gainers_command(update: Update, context: ContextTypes.DEFAULT_TYPE, broker):
    """Handle top gainers command."""
    await update.message.reply_text("🔄 Fetching top gainers...")
    
    try:
        response = await broker.get_top_gainers_losers("PercPriceGainers", "NEAR")
        
        if response.success and response.data:
            items = response.data.get('items', [])
            
            if not items:
                await update.message.reply_text("📊 No gainers data available.")
                return
            
            gainers_text = "📈 **Top Price Gainers (Current Month Derivatives):**\n\n"
            
            # Show top 10 gainers
            for i, item in enumerate(items[:10], 1):
                symbol = item.get('symbol', 'N/A')
                percent_change = item.get('percent_change', 0)
                
                # Clean up symbol name (remove date and FUT suffix for readability)
                clean_symbol = symbol.replace('FUT', '').split('25')[0].split('26')[0].split('27')[0].split('24')[0]
                
                gainers_text += (
                    f"{i}. **{clean_symbol}**\n"
                    f"📈 +{percent_change:.2f}%\n\n"
                )
            
            gainers_text += "_Data from AngelOne derivatives segment_"
            
            await update.message.reply_text(gainers_text, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ Could not fetch gainers: {response.message}")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching top gainers: {str(e)}")


async def handle_top_losers_command(update: Update, context: ContextTypes.DEFAULT_TYPE, broker):
    """Handle top losers command."""
    await update.message.reply_text("🔄 Fetching top losers...")
    
    try:
        response = await broker.get_top_gainers_losers("PercPriceLosers", "NEAR")
        
        if response.success and response.data:
            items = response.data.get('items', [])
            
            if not items:
                await update.message.reply_text("📊 No losers data available.")
                return
            
            losers_text = "📉 **Top Price Losers (Current Month Derivatives):**\n\n"
            
            # Show top 10 losers
            for i, item in enumerate(items[:10], 1):
                symbol = item.get('symbol', 'N/A')
                percent_change = item.get('percent_change', 0)
                
                # Clean up symbol name (remove date and FUT suffix for readability)
                clean_symbol = symbol.replace('FUT', '').split('25')[0].split('26')[0].split('27')[0].split('24')[0]
                
                losers_text += (
                    f"{i}. **{clean_symbol}**\n"
                    f"📉 {percent_change:.2f}%\n\n"
                )
            
            losers_text += "_Data from AngelOne derivatives segment_"
            
            await update.message.reply_text(losers_text, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ Could not fetch losers: {response.message}")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching top losers: {str(e)}")


async def handle_graph_command(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                               broker, args: List[str]):
    """Handle graph command to generate candlestick charts."""
    if len(args) < 2:
        await update.message.reply_text(
            "❌ Please provide symbol and timeframe.\n"
            "Usage: `/graph SYMBOL TIMEFRAME`\n"
            "Timeframes: 1M, 3M, 5M, 10M, 15M, 30M, 1H, 1D\n"
            "Example: `/graph RELIANCE 5M`"
        )
        return
    
    symbol = args[0].upper()
    interval = args[1].upper()
    
    # Validate interval
    valid_intervals = ["1M", "3M", "5M", "10M", "15M", "30M", "1H", "1D"]
    if interval not in valid_intervals:
        await update.message.reply_text(
            f"❌ Invalid timeframe: {interval}\n"
            f"Valid timeframes: {', '.join(valid_intervals)}"
        )
        return
    
    await update.message.reply_text(f"🔄 Generating {interval} chart for {symbol}...")
    
    try:
        # Get historical data
        response = await broker.get_historical_data(symbol, interval)
        
        if not response.success:
            await update.message.reply_text(f"❌ {response.message}")
            return
        
        candles = response.data.get("candles", [])
        if len(candles) < 10:
            await update.message.reply_text(
                f"❌ Insufficient data for {symbol}. Need at least 10 candles, got {len(candles)}."
            )
            return
        
        # Generate chart
        chart_buffer = await generate_candlestick_chart(candles, symbol, interval)
        
        # Send chart image
        chart_buffer.seek(0)
        caption = f"📊 **{symbol} - {interval} Candlestick Chart**"
        
        await update.message.reply_photo(
            photo=chart_buffer,
            caption=caption,
            parse_mode='Markdown'
        )
        
        chart_buffer.close()
        
    except Exception as e:
        logger.error(f"Error generating chart for {symbol}: {e}")
        await update.message.reply_text(f"❌ Error generating chart: {str(e)}")


async def generate_candlestick_chart(candles: List[dict], symbol: str, interval: str):
    """Generate candlestick chart from OHLC data."""
    import io
    import pandas as pd
    import mplfinance as mpf
    from datetime import datetime
    
    # Convert candles to DataFrame
    data = []
    for candle in candles:
        # Parse timestamp
        timestamp_str = candle["timestamp"]
        try:
            # Handle different timestamp formats from AngelOne
            if "T" in timestamp_str:
                # Format: "2023-09-06T11:15:00+05:30"
                timestamp = datetime.fromisoformat(timestamp_str.replace("+05:30", ""))
            else:
                # Alternative format handling
                timestamp = datetime.strptime(timestamp_str[:19], "%Y-%m-%d %H:%M:%S")
        except:
            # Fallback to current time with offset
            timestamp = datetime.now()
        
        data.append({
            'Date': timestamp,
            'Open': candle["open"],
            'High': candle["high"],
            'Low': candle["low"],
            'Close': candle["close"],
            'Volume': candle["volume"]
        })
    
    df = pd.DataFrame(data)
    df.set_index('Date', inplace=True)
    df = df.sort_index()  # Ensure chronological order
    
    # Create the chart
    chart_buffer = io.BytesIO()
    
    # Custom style for better appearance
    mc = mpf.make_marketcolors(
        up='g', down='r',
        edge='inherit',
        wick={'up':'green', 'down':'red'},
        volume='in'
    )
    
    style = mpf.make_mpf_style(
        marketcolors=mc,
        gridstyle='-',
        y_on_right=False
    )
    
    # Plot the chart
    mpf.plot(
        df,
        type='candle',
        style=style,
        volume=True,
        title=f'{symbol} - {interval} Candlestick Chart',
        ylabel='Price (₹)',
        ylabel_lower='Volume',
        figsize=(12, 8),
        savefig=dict(fname=chart_buffer, dpi=150, bbox_inches='tight')
    )
    
    chart_buffer.seek(0)
    return chart_buffer 