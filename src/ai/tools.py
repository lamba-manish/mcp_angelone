"""Tool registry for AI trading agent."""

import json
import asyncio
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass
import structlog
from decimal import Decimal

from ..brokers.angelone import AngelOneBroker
from ..models.trading import OrderRequest, OrderType, TransactionType, ProductType, Exchange
from ..config import settings
from ..brokers.base import BrokerResponse
from ..telegram_bot.broker_manager import broker_manager

logger = structlog.get_logger(__name__)

try:
    from googleapiclient.discovery import build
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False


@dataclass
class Tool:
    """Represents a tool that the AI agent can use."""
    name: str
    description: str
    parameters: Dict[str, Any]
    function: Callable
    requires_confirmation: bool = False


class ToolRegistry:
    """Registry of all available tools for the AI agent."""
    
    def __init__(self, broker: AngelOneBroker):
        self.broker = broker
        self.google_service = self._init_google_search()
        self.tools = self._register_tools()
    
    def _init_google_search(self):
        """Initialize Google Search service if credentials are available."""
        if GOOGLE_AVAILABLE and settings.google_api_key and settings.google_search_engine_id:
            try:
                return build("customsearch", "v1", developerKey=settings.google_api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Google Search: {e}")
        return None
    
    def _register_tools(self) -> Dict[str, Tool]:
        """Register all available tools."""
        tools = {}
        
        # Account and Funds Tools
        tools["get_profile"] = Tool(
            name="get_profile",
            description="Get user profile and account information",
            parameters={},
            function=self._get_profile
        )
        
        tools["get_funds"] = Tool(
            name="get_funds",
            description="Get available funds and margins",
            parameters={},
            function=self._get_funds
        )
        
        tools["get_margins"] = Tool(
            name="get_margins",
            description="Get detailed margin information",
            parameters={},
            function=self._get_margins
        )
        
        # Market Data Tools
        tools["get_quote"] = Tool(
            name="get_quote",
            description="Get live price quote for a symbol",
            parameters={
                "symbol": {"type": "string", "description": "Stock symbol (e.g., RELIANCE)"},
                "exchange": {"type": "string", "description": "Exchange (NSE/BSE)", "default": "NSE"}
            },
            function=self._get_quote
        )
        
        tools["get_market_depth"] = Tool(
            name="get_market_depth",
            description="Get market depth (order book) for a symbol",
            parameters={
                "symbol": {"type": "string", "description": "Stock symbol"},
                "exchange": {"type": "string", "description": "Exchange (NSE/BSE)", "default": "NSE"}
            },
            function=self._get_market_depth
        )
        
        tools["get_historical_data"] = Tool(
            name="get_historical_data",
            description="Get historical price data and generate charts",
            parameters={
                "symbol": {"type": "string", "description": "Stock symbol"},
                "interval": {"type": "string", "description": "Time interval (1M, 5M, 1H, 1D)", "default": "1D"},
                "exchange": {"type": "string", "description": "Exchange (NSE/BSE)", "default": "NSE"}
            },
            function=self._get_historical_data
        )
        
        tools["get_top_gainers_losers"] = Tool(
            name="get_top_gainers_losers",
            description="Get top gainers or losers",
            parameters={
                "type": {"type": "string", "description": "Type: 'gainers' or 'losers'", "default": "gainers"}
            },
            function=self._get_top_gainers_losers
        )
        
        # Portfolio Tools
        tools["get_holdings"] = Tool(
            name="get_holdings",
            description="Get user's stock holdings",
            parameters={},
            function=self._get_holdings
        )
        
        tools["get_positions"] = Tool(
            name="get_positions",
            description="Get user's current positions",
            parameters={},
            function=self._get_positions
        )
        
        tools["get_orders"] = Tool(
            name="get_orders",
            description="Get user's order history",
            parameters={},
            function=self._get_orders
        )
        
        # Trading Tools
        tools["place_buy_order"] = Tool(
            name="place_buy_order",
            description="Place a buy order",
            parameters={
                "symbol": {"type": "string", "description": "Stock symbol"},
                "quantity": {"type": "integer", "description": "Number of shares"},
                "price": {"type": "number", "description": "Price per share (optional for market orders)"},
                "order_type": {"type": "string", "description": "Order type: 'MARKET' or 'LIMIT'", "default": "LIMIT"},
                "exchange": {"type": "string", "description": "Exchange (NSE/BSE)", "default": "NSE"}
            },
            function=self._place_buy_order,
            requires_confirmation=True
        )
        
        tools["place_sell_order"] = Tool(
            name="place_sell_order",
            description="Place a sell order",
            parameters={
                "symbol": {"type": "string", "description": "Stock symbol"},
                "quantity": {"type": "integer", "description": "Number of shares"},
                "price": {"type": "number", "description": "Price per share (optional for market orders)"},
                "order_type": {"type": "string", "description": "Order type: 'MARKET' or 'LIMIT'", "default": "LIMIT"},
                "exchange": {"type": "string", "description": "Exchange (NSE/BSE)", "default": "NSE"}
            },
            function=self._place_sell_order,
            requires_confirmation=True
        )
        
        tools["cancel_order"] = Tool(
            name="cancel_order",
            description="Cancel a specific order",
            parameters={
                "order_id": {"type": "string", "description": "Order ID to cancel"}
            },
            function=self._cancel_order,
            requires_confirmation=True
        )
        
        tools["cancel_all_orders"] = Tool(
            name="cancel_all_orders",
            description="Cancel all pending orders",
            parameters={},
            function=self._cancel_all_orders,
            requires_confirmation=True
        )
        
        # Search Tools
        tools["search_instruments"] = Tool(
            name="search_instruments",
            description="Search for stock instruments",
            parameters={
                "query": {"type": "string", "description": "Search query (company name or symbol)"}
            },
            function=self._search_instruments
        )
        
        if self.google_service:
            tools["google_search"] = Tool(
                name="google_search",
                description="Search Google for additional market information",
                parameters={
                    "query": {"type": "string", "description": "Search query"}
                },
                function=self._google_search
            )
        
        return tools
    
    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """Get OpenAI function calling schema for all tools."""
        schema = []
        for tool in self.tools.values():
            schema.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": tool.parameters,
                        "required": [k for k, v in tool.parameters.items() if "default" not in v]
                    }
                }
            })
        return schema
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self.tools.get(name)
    
    async def execute_tool(self, name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with given parameters."""
        tool = self.get_tool(name)
        if not tool:
            return {"error": f"Tool '{name}' not found"}
        
        try:
            result = await tool.function(**parameters)
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"Error executing tool '{name}': {e}", error=str(e))
            return {"error": str(e)}
    
    # Tool Implementation Methods
    async def _get_profile(self) -> Dict[str, Any]:
        """Get user profile."""
        try:
            response = await self.broker.get_profile()
            return response.data if response.success else {"error": response.message}
        except Exception as e:
            return {"error": f"Failed to get profile: {str(e)}"}
    
    async def _get_funds(self) -> Dict[str, Any]:
        """Get available funds."""
        try:
            response = await self.broker.get_funds()
            return response.data if response.success else {"error": response.message}
        except Exception as e:
            return {"error": f"Failed to get funds: {str(e)}"}
    
    async def _get_margins(self) -> Dict[str, Any]:
        """Get margin information."""
        try:
            response = await self.broker.get_margins()
            return response.data if response.success else {"error": response.message}
        except Exception as e:
            return {"error": f"Failed to get margins: {str(e)}"}
    
    async def _get_quote(self, symbol: str, exchange: str = "NSE") -> Dict[str, Any]:
        """Get live price quote for a symbol."""
        try:
            broker = await self._get_broker()
            quote = await broker.get_quote(symbol, exchange)
            
            # broker.get_quote returns a Quote object directly, not a BrokerResponse
            return {
                "status": "success",
                "symbol": symbol,
                "exchange": exchange,
                "ltp": float(quote.ltp) if quote.ltp else 0.0,
                "open_price": float(quote.open_price) if quote.open_price else 0.0,
                "high_price": float(quote.high_price) if quote.high_price else 0.0,
                "low_price": float(quote.low_price) if quote.low_price else 0.0,
                "close_price": float(quote.close_price) if quote.close_price else 0.0,
                "change": float(quote.change) if quote.change else 0.0,
                "change_percent": float(quote.change_percent) if quote.change_percent else 0.0,
                "message": f"LTP: ₹{quote.ltp}"
            }
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {e}")
            return {
                "status": "error",
                "message": f"Error getting quote: {str(e)}"
            }
    
    async def _get_market_depth(self, symbol: str, exchange: str = "NSE") -> Dict[str, Any]:
        """Get market depth."""
        try:
            response = await self.broker.get_market_depth(symbol, exchange)
            return response.data if response.success else {"error": response.message}
        except Exception as e:
            return {"error": f"Failed to get market depth: {str(e)}"}
    
    async def _get_historical_data(self, symbol: str, interval: str = "1D", exchange: str = "NSE") -> Dict[str, Any]:
        """Get historical data."""
        response = await self.broker.get_historical_data(symbol, interval, exchange)
        return response.data if response.success else {"error": response.message}
    
    async def _get_top_gainers_losers(self, type: str = "gainers") -> Dict[str, Any]:
        """Get top gainers or losers."""
        data_type = "PercPriceGainers" if type.lower() == "gainers" else "PercPriceLosers"
        response = await self.broker.get_top_gainers_losers(data_type)
        return response.data if response.success else {"error": response.message}
    
    async def _get_holdings(self) -> List[Dict[str, Any]]:
        """Get holdings."""
        try:
            holdings = await self.broker.get_holdings()
            return [
                {
                    "symbol": h.symbol,
                    "quantity": h.quantity,
                    "average_price": h.average_price,
                    "current_price": h.current_price,
                    "pnl": h.pnl,
                    "pnl_percent": h.pnl_percent
                }
                for h in holdings
            ]
        except Exception as e:
            return {"error": f"Failed to get holdings: {str(e)}"}
    
    async def _get_positions(self) -> List[Dict[str, Any]]:
        """Get positions."""
        try:
            positions = await self.broker.get_positions()
            return [
                {
                    "symbol": p.symbol,
                    "quantity": p.quantity,
                    "average_price": p.average_price,
                    "current_price": p.current_price,
                    "pnl": p.pnl,
                    "product_type": p.product_type
                }
                for p in positions
            ]
        except Exception as e:
            return {"error": f"Failed to get positions: {str(e)}"}
    
    async def _get_orders(self) -> List[Dict[str, Any]]:
        """Get orders."""
        try:
            orders = await self.broker.get_orders()
            return [
                {
                    "order_id": o.order_id,
                    "symbol": o.symbol,
                    "quantity": o.quantity,
                    "price": o.price,
                    "order_type": o.order_type,
                    "transaction_type": o.transaction_type,
                    "status": o.status,
                    "timestamp": o.timestamp
                }
                for o in orders
            ]
        except Exception as e:
            return {"error": f"Failed to get orders: {str(e)}"}
    
    async def _place_buy_order(self, symbol: str, quantity: int, price: Optional[float] = None, 
                             order_type: str = "LIMIT", exchange: str = "NSE") -> Dict[str, Any]:
        """Place buy order."""
        try:
            order_request = OrderRequest(
                symbol=symbol,
                quantity=quantity,
                price=price,
                order_type=OrderType(order_type),
                transaction_type=TransactionType.BUY,
                product_type=ProductType.DELIVERY,
                exchange=Exchange(exchange)
            )
            
            response = await self.broker.place_order(order_request)
            return response.data if response.success else {"error": response.message}
        except Exception as e:
            return {"error": f"Failed to place buy order: {str(e)}"}
    
    async def _place_sell_order(self, symbol: str, quantity: int, price: Optional[float] = None,
                               order_type: str = "LIMIT", exchange: str = "NSE") -> Dict[str, Any]:
        """Place sell order."""
        try:
            order_request = OrderRequest(
                symbol=symbol,
                quantity=quantity,
                price=price,
                order_type=OrderType(order_type),
                transaction_type=TransactionType.SELL,
                product_type=ProductType.DELIVERY,
                exchange=Exchange(exchange)
            )
            
            response = await self.broker.place_order(order_request)
            return response.data if response.success else {"error": response.message}
        except Exception as e:
            return {"error": f"Failed to place sell order: {str(e)}"}
    
    async def _cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel order."""
        response = await self.broker.cancel_order(order_id)
        return response.data if response.success else {"error": response.message}
    
    async def _cancel_all_orders(self) -> Dict[str, Any]:
        """Cancel all pending orders."""
        response = await self.broker.cancel_all_pending_orders()
        return response.data if response.success else {"error": response.message}
    
    async def _search_instruments(self, query: str) -> List[Dict[str, Any]]:
        """Search instruments."""
        try:
            instruments = await self.broker.search_instruments(query)
            return [
                {
                    "symbol": i.symbol,
                    "name": i.name,
                    "exchange": i.exchange,
                    "token": i.token
                }
                for i in instruments[:10]  # Limit to top 10 results
            ]
        except Exception as e:
            return {"error": f"Failed to search instruments: {str(e)}"}
    
    async def _google_search(self, query: str) -> Dict[str, Any]:
        """Perform Google search."""
        if not self.google_service:
            return {"error": "Google Search not configured"}
        
        try:
            result = self.google_service.cse().list(
                q=query,
                cx=settings.google_search_engine_id,
                num=5
            ).execute()
            
            items = []
            for item in result.get('items', []):
                items.append({
                    'title': item.get('title'),
                    'snippet': item.get('snippet'),
                    'link': item.get('link')
                })
            
            return {"results": items}
            
        except Exception as e:
            logger.error(f"Google search failed: {e}")
            return {"error": f"Search failed: {str(e)}"}


class BrokerTools:
    """Tools for AI agent to interact with broker."""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
    
    async def _get_broker(self):
        """Get broker instance for user."""
        # First try to get existing broker
        broker = await broker_manager.get_broker(self.user_id)
        
        # If no broker found, try to create one
        if not broker:
            logger.info(f"No broker found for user {self.user_id}, attempting to create one")
            broker = await broker_manager.get_or_create_broker(self.user_id)
            
        if not broker:
            raise Exception("Broker not connected. Please reconnect using /broker")
        return broker
    
    async def get_funds(self) -> Dict[str, Any]:
        """Get available funds and margin information."""
        try:
            broker = await self._get_broker()
            response = await broker.get_funds()
            
            if response.success:
                funds_data = response.data
                return {
                    "status": "success",
                    "available_cash": float(funds_data.get("available_cash", 0)),
                    "utilised_margin": float(funds_data.get("utilised_margin", 0)),
                    "available_margin": float(funds_data.get("available_margin", 0)),
                    "message": f"Available cash: ₹{funds_data.get('available_cash', 0)}"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to fetch funds: {response.message}"
                }
        except Exception as e:
            logger.error(f"Error getting funds: {e}")
            return {
                "status": "error",
                "message": f"Error fetching funds: {str(e)}"
            }
    
    async def get_quote(self, symbol: str, exchange: str = "NSE") -> Dict[str, Any]:
        """Get live price quote for a symbol."""
        try:
            broker = await self._get_broker()
            quote = await broker.get_quote(symbol, exchange)
            
            # broker.get_quote returns a Quote object directly, not a BrokerResponse
            return {
                "status": "success",
                "symbol": symbol,
                "exchange": exchange,
                "ltp": float(quote.ltp) if quote.ltp else 0.0,
                "open_price": float(quote.open_price) if quote.open_price else 0.0,
                "high_price": float(quote.high_price) if quote.high_price else 0.0,
                "low_price": float(quote.low_price) if quote.low_price else 0.0,
                "close_price": float(quote.close_price) if quote.close_price else 0.0,
                "change": float(quote.change) if quote.change else 0.0,
                "change_percent": float(quote.change_percent) if quote.change_percent else 0.0,
                "volume": int(quote.volume) if quote.volume else 0,
                "message": f"LTP: ₹{quote.ltp}"
            }
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {e}")
            return {
                "status": "error",
                "message": f"Error getting quote: {str(e)}"
            }
    
    async def get_holdings(self) -> Dict[str, Any]:
        """Get current holdings."""
        try:
            broker = await self._get_broker()
            holdings = await broker.get_holdings()
            
            # broker.get_holdings returns a list of Holding objects directly
            holdings_list = []
            total_value = 0
            total_pnl = 0
            
            for holding in holdings:
                value = float(holding.quantity * holding.current_price)
                pnl = float(holding.pnl)
                total_value += value
                total_pnl += pnl
                
                holdings_list.append({
                    "symbol": holding.symbol,
                    "quantity": int(holding.quantity),
                    "current_price": float(holding.current_price),
                    "value": value,
                    "pnl": pnl
                })
            
            return {
                "status": "success",
                "holdings": holdings_list,
                "total_value": total_value,
                "total_pnl": total_pnl,
                "message": f"Total holdings value: ₹{total_value:,.2f}"
            }
        except Exception as e:
            logger.error(f"Error getting holdings: {e}")
            return {
                "status": "error",
                "message": f"Error getting holdings: {str(e)}"
            }
    
    async def get_positions(self) -> Dict[str, Any]:
        """Get current positions."""
        try:
            broker = await self._get_broker()
            response = await broker.get_positions()
            
            if response.success:
                positions = response.data
                positions_list = []
                total_pnl = 0
                
                for position in positions:
                    if position.quantity == 0:
                        continue
                    
                    pnl = float(position.pnl)
                    total_pnl += pnl
                    
                    positions_list.append({
                        "symbol": position.symbol,
                        "quantity": int(position.quantity),
                        "average_price": float(position.average_price),
                        "current_price": float(position.current_price),
                        "pnl": pnl
                    })
                
                return {
                    "status": "success",
                    "positions": positions_list,
                    "total_pnl": total_pnl,
                    "message": f"Total P&L: ₹{total_pnl:,.2f}"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to get positions: {response.message}"
                }
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return {
                "status": "error",
                "message": f"Error getting positions: {str(e)}"
            }
    
    async def get_orders(self) -> Dict[str, Any]:
        """Get today's orders."""
        try:
            broker = await self._get_broker()
            orders = await broker.get_orders()
            
            # broker.get_orders returns a list of Order objects directly
            orders_list = []
            
            for order in orders:
                orders_list.append({
                    "order_id": order.order_id,
                    "symbol": order.symbol,
                    "transaction_type": order.transaction_type,
                    "quantity": int(order.quantity),
                    "price": float(order.price) if order.price else 0.0,
                    "status": order.status
                })
            
            return {
                "status": "success",
                "orders": orders_list,
                "message": f"Found {len(orders_list)} orders today"
            }
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return {
                "status": "error",
                "message": f"Error getting orders: {str(e)}"
            }
    
    async def place_order(self, symbol: str, transaction_type: str, quantity: int, 
                         price: Optional[float] = None, exchange: str = "NSE",
                         product_type: str = "CNC", order_type: str = None) -> Dict[str, Any]:
        """Place a trading order."""
        try:
            broker = await self._get_broker()
            
            # Determine order type
            if order_type is None:
                order_type = "LIMIT" if price else "MARKET"
            
            # Create order request
            order_request = OrderRequest(
                symbol=symbol.upper(),
                exchange=Exchange.NSE if exchange.upper() == "NSE" else Exchange.BSE,
                transaction_type=TransactionType.BUY if transaction_type.upper() == "BUY" else TransactionType.SELL,
                order_type=OrderType.LIMIT if order_type.upper() == "LIMIT" else OrderType.MARKET,
                product_type=ProductType.CNC if product_type.upper() == "CNC" else ProductType.MIS,
                quantity=quantity,
                price=price
            )
            
            response = await broker.place_order(order_request)
            
            if response.success:
                order_id = response.data.get('order_id', 'N/A') if hasattr(response.data, 'get') else 'N/A'
                return {
                    "status": "success",
                    "order_id": order_id,
                    "message": f"{transaction_type} order placed for {quantity} shares of {symbol}"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Order failed: {response.message}"
                }
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {
                "status": "error",
                "message": f"Error placing order: {str(e)}"
            }
    
    async def get_profile(self) -> Dict[str, Any]:
        """Get user profile information."""
        try:
            broker = await self._get_broker()
            response = await broker.get_profile()
            
            if response.success:
                profile = response.data
                return {
                    "status": "success",
                    "name": profile.get("name", "N/A"),
                    "client_id": profile.get("clientcode", "N/A"),
                    "email": profile.get("email", "N/A"),
                    "message": f"Profile: {profile.get('name', 'N/A')}"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to get profile: {response.message}"
                }
        except Exception as e:
            logger.error(f"Error getting profile: {e}")
            return {
                "status": "error",
                "message": f"Error getting profile: {str(e)}"
            }

    async def get_top_gainers_losers(self, type: str = "gainers") -> Dict[str, Any]:
        """Get top gainers or losers."""
        try:
            broker = await self._get_broker()
            
            # Map type to AngelOne data_type
            data_type = "PercPriceGainers" if type.lower() == "gainers" else "PercPriceLosers"
            
            response = await broker.get_top_gainers_losers(data_type=data_type, expiry_type="NEAR")
            
            if response.success:
                data = response.data
                items = data.get('items', [])
                
                if items:
                    return {
                        "status": "success",
                        "type": type,
                        "stocks": items[:10],  # Top 10
                        "message": f"Top {type} data fetched successfully"
                    }
                else:
                    return {
                        "status": "success",
                        "stocks": [],
                        "message": f"No {type} data available"
                    }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to get {type}: {response.message}"
                }
        except Exception as e:
            logger.error(f"Error getting {type}: {e}")
            return {
                "status": "error",
                "message": f"Error getting {type}: {str(e)}"
            }

    async def cancel_all_orders(self) -> Dict[str, Any]:
        """Cancel all pending orders."""
        try:
            broker = await self._get_broker()
            
            # First get all pending orders
            orders_response = await broker.get_orders()
            if not orders_response.success:
                return {
                    "status": "error",
                    "message": f"Failed to get orders: {orders_response.message}"
                }
            
            orders = orders_response.data.get('orders', [])
            pending_orders = [order for order in orders if order.get('status', '').lower() in ['pending', 'open', 'trigger pending']]
            
            if not pending_orders:
                return {
                    "status": "success",
                    "cancelled_count": 0,
                    "message": "No pending orders to cancel"
                }
            
            # Cancel each pending order
            cancelled_count = 0
            failed_count = 0
            
            for order in pending_orders:
                try:
                    order_id = order.get('orderid', order.get('order_id'))
                    if order_id:
                        cancel_response = await broker.cancel_order(order_id)
                        if cancel_response.success:
                            cancelled_count += 1
                        else:
                            failed_count += 1
                            logger.warning(f"Failed to cancel order {order_id}: {cancel_response.message}")
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Error cancelling individual order: {e}")
            
            return {
                "status": "success",
                "cancelled_count": cancelled_count,
                "failed_count": failed_count,
                "message": f"Cancelled {cancelled_count} orders, {failed_count} failed"
            }
            
        except Exception as e:
            logger.error(f"Error cancelling all orders: {e}")
            return {
                "status": "error",
                "message": f"Error cancelling orders: {str(e)}"
            }

    async def get_market_depth(self, symbol: str, exchange: str = "NSE") -> Dict[str, Any]:
        """Get market depth for a symbol."""
        try:
            broker = await self._get_broker()
            response = await broker.get_market_depth(symbol, exchange)
            
            if response.success:
                data = response.data
                return {
                    "status": "success",
                    "symbol": symbol,
                    "exchange": exchange,
                    "market_depth": data,
                    "message": f"Market depth for {symbol} fetched successfully"
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to get market depth for {symbol}: {response.message}"
                }
        except Exception as e:
            logger.error(f"Error getting market depth for {symbol}: {e}")
            return {
                "status": "error",
                "message": f"Error getting market depth: {str(e)}"
            }


# Tool function definitions for OpenAI function calling
TOOL_FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_funds",
            "description": "Get available funds and margin information",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_quote",
            "description": "Get live price quote for a stock symbol",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol (e.g., RELIANCE, TCS, INFY, ITC)"
                    },
                    "exchange": {
                        "type": "string",
                        "description": "Exchange (NSE or BSE)",
                        "default": "NSE"
                    }
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_holdings",
            "description": "Get current stock holdings",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_positions",
            "description": "Get current trading positions",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_orders",
            "description": "Get today's orders",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "place_order",
            "description": "Place a buy or sell order",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol (e.g., RELIANCE, TCS)"
                    },
                    "transaction_type": {
                        "type": "string",
                        "enum": ["BUY", "SELL"],
                        "description": "Transaction type"
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Number of shares"
                    },
                    "price": {
                        "type": "number",
                        "description": "Price per share (optional for market orders)"
                    },
                    "exchange": {
                        "type": "string",
                        "enum": ["NSE", "BSE"],
                        "default": "NSE"
                    },
                    "product_type": {
                        "type": "string",
                        "enum": ["CNC", "MIS"],
                        "default": "CNC",
                        "description": "Product type - CNC for delivery, MIS for intraday"
                    },
                    "order_type": {
                        "type": "string",
                        "enum": ["MARKET", "LIMIT"],
                        "description": "Order type - auto-determined if not provided"
                    }
                },
                "required": ["symbol", "transaction_type", "quantity"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_profile",
            "description": "Get user profile information",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_gainers_losers",
            "description": "Get top gainers or losers in the market",
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["gainers", "losers"],
                        "description": "Type of data to fetch - gainers or losers",
                        "default": "gainers"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_all_orders",
            "description": "Cancel all pending orders",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_depth",
            "description": "Get market depth (order book) for a stock symbol",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol (e.g., RELIANCE, TCS)"
                    },
                    "exchange": {
                        "type": "string",
                        "description": "Exchange (NSE or BSE)",
                        "default": "NSE"
                    }
                },
                "required": ["symbol"]
            }
        }
    }
] 