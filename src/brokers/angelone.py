"""
AngelOne Broker Implementation

This module implements the AngelOne broker integration following the 
SmartAPI documentation for trading operations.
"""

import asyncio
import socket
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
import aiohttp
import pyotp
import structlog

from ..models.trading import (
    LoginResponse, BrokerResponse, Order, OrderRequest, Holding, Position,
    Quote, Instrument, OrderType, TransactionType, ProductType, Exchange,
    OrderStatus
)
from ..brokers.base import BaseBroker
from ..utils.exceptions import (
    BrokerError, AuthenticationError, APIError, OrderError
)
from ..config import settings

logger = structlog.get_logger(__name__)

# Interval mapping for AngelOne API
INTERVAL_MAPPING = {
    "1M": "ONE_MINUTE",
    "3M": "THREE_MINUTE", 
    "5M": "FIVE_MINUTE",
    "10M": "TEN_MINUTE",
    "15M": "FIFTEEN_MINUTE",
    "30M": "THIRTY_MINUTE",
    "1H": "ONE_HOUR",
    "1D": "ONE_DAY"
}

# Max days for each interval to ensure we get ~100 candles
INTERVAL_MAX_DAYS = {
    "ONE_MINUTE": 1,     # 100 minutes = ~1.6 hours
    "THREE_MINUTE": 1,   # 300 minutes = 5 hours
    "FIVE_MINUTE": 1,    # 500 minutes = ~8 hours  
    "TEN_MINUTE": 2,     # 1000 minutes = ~16 hours
    "FIFTEEN_MINUTE": 2, # 1500 minutes = 25 hours
    "THIRTY_MINUTE": 3,  # 3000 minutes = 50 hours
    "ONE_HOUR": 5,       # 100 hours = ~4 days
    "ONE_DAY": 100       # 100 days
}

class AngelOneBroker(BaseBroker):
    """AngelOne (Angel Broking) broker implementation."""
    
    def __init__(self):
        super().__init__("angelone")
        self.base_url = settings.angelone_base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
        }
        self.jwt_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.feed_token: Optional[str] = None
        
    async def _get_network_info(self) -> Dict[str, str]:
        """Get network information for headers."""
        try:
            # Get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            
            # For public IP, we'll use a service or default to local
            # In production, you might want to use an external service
            public_ip = local_ip  # Simplified for now
            
            # Get MAC address
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) 
                           for i in range(0, 8*6, 8)][::-1])
            
            return {
                "X-ClientLocalIP": local_ip,
                "X-ClientPublicIP": public_ip,
                "X-MACAddress": mac
            }
        except Exception as e:
            logger.warning("Failed to get network info", error=str(e))
            return {
                "X-ClientLocalIP": "127.0.0.1",
                "X-ClientPublicIP": "127.0.0.1", 
                "X-MACAddress": "00:00:00:00:00:00"
            }
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        authenticated: bool = True
    ) -> Dict:
        """Make HTTP request to AngelOne API."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        # Add network info to headers
        network_info = await self._get_network_info()
        headers = {**self.headers, **network_info}
        
        # Add API key
        headers["X-PrivateKey"] = settings.angelone_api_key
        
        # Add JWT token for authenticated requests
        if authenticated and self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with self.session.request(
                method, url, json=data, headers=headers
            ) as response:
                # Check content type first
                content_type = response.headers.get('content-type', '').lower()
                
                if 'application/json' not in content_type:
                    # Response is not JSON - likely HTML error page
                    response_text = await response.text()
                    logger.error(f"API returned non-JSON response: {response.status}", 
                               content_type=content_type, 
                               response_text=response_text[:500],
                               url=str(response.url),
                               method=method,
                               request_data=data)
                    
                    if response.status == 401:
                        raise AuthenticationError("Authentication failed - session may have expired")
                    elif response.status == 403:
                        raise AuthenticationError("Access forbidden - check API credentials")
                    elif response.status == 400:
                        # For 400 errors, try to extract more meaningful error info
                        if "invalid" in response_text.lower() or "error" in response_text.lower():
                            raise APIError(f"Bad request: {response_text[:200]}")
                        else:
                            raise APIError(f"Bad request (400): Check order parameters. Response: {response_text[:200]}")
                    elif response.status >= 500:
                        raise APIError(f"Server error {response.status}: Service temporarily unavailable")
                    else:
                        raise APIError(f"API error {response.status}: {response_text[:200] if response_text else 'No response body'}")
                
                response_data = await response.json()
                
                # Check AngelOne response format
                if not response_data.get("status"):
                    error_code = response_data.get("errorcode", "Unknown")
                    error_msg = response_data.get("message", "Unknown error")
                    
                    # Handle specific error codes
                    if error_code in ["AG8001", "AG8002", "AG8003"]:
                        raise AuthenticationError(f"Token error: {error_msg}")
                    elif error_code in ["AB1000", "AB1001", "AB1002", "AB1007"]:
                        raise AuthenticationError(f"Login error: {error_msg}")
                    else:
                        raise APIError(f"API error {error_code}: {error_msg}")
                
                return response_data.get("data", {})
                
        except aiohttp.ClientError as e:
            raise BrokerError(f"Network error: {str(e)}")
        except (ValueError, UnicodeDecodeError) as e:
            # JSON decode error or encoding issues
            raise APIError(f"Invalid response format: {str(e)}")
    
    async def login(self) -> LoginResponse:
        """Login to AngelOne broker."""
        try:
            # Use credentials from settings
            user_id = settings.angelone_user_id
            password = settings.angelone_password
            totp_secret = settings.angelone_totp_secret
            
            # Generate TOTP if secret provided
            totp = None
            if totp_secret:
                totp_gen = pyotp.TOTP(totp_secret)
                totp = totp_gen.now()
            
            login_data = {
                "clientcode": user_id,
                "password": password
            }
            
            if totp:
                login_data["totp"] = totp
            
            response_data = await self._make_request(
                "POST",
                "/rest/auth/angelbroking/user/v1/loginByPassword",
                data=login_data,
                authenticated=False
            )
            
            # Extract tokens
            self.jwt_token = response_data.get("jwtToken")
            self.refresh_token = response_data.get("refreshToken") 
            self.feed_token = response_data.get("feedToken")
            
            # Set authenticated state
            if self.jwt_token:
                self._set_authenticated(self.jwt_token, response_data)
            
            logger.info("Successfully logged in to AngelOne", user_id=user_id)
            
            return LoginResponse(
                success=True,
                message="Login successful",
                auth_token=self.jwt_token,
                refresh_token=self.refresh_token,
                user_id=user_id,
                session_data={
                    "feed_token": self.feed_token
                }
            )
            
        except Exception as e:
            logger.error("AngelOne login failed", error=str(e))
            return LoginResponse(
                success=False,
                message=f"Login failed: {str(e)}"
            )
    
    async def get_profile(self) -> BrokerResponse:
        """Get user profile information."""
        try:
            profile_data = await self._make_request(
                "GET",
                "/rest/secure/angelbroking/user/v1/getProfile"
            )
            
            return BrokerResponse(
                success=True,
                message="Profile retrieved successfully",
                data=profile_data
            )
            
        except Exception as e:
            logger.error("Failed to get profile", error=str(e))
            return BrokerResponse(
                success=False,
                message=f"Failed to get profile: {str(e)}"
            )
    
    async def _validate_authentication(self) -> bool:
        """Validate if current authentication is still valid."""
        if not self.jwt_token:
            return False
        
        try:
            # Try to get profile to check if token is valid
            profile_response = await self.get_profile()
            return profile_response.success
        except AuthenticationError:
            return False
        except Exception:
            # If we can't determine, assume it's valid to avoid breaking existing functionality
            return True
    
    async def place_order(self, order_request: OrderRequest) -> BrokerResponse:
        """Place a trading order."""
        try:
            # Check if we're authenticated
            if not await self._validate_authentication():
                logger.error("Not authenticated - JWT token missing")
                return BrokerResponse(
                    success=False,
                    message="Not authenticated. Please login first using /broker command."
                )
            
            # Format symbol for NSE (add -EQ suffix if not present)
            formatted_symbol = order_request.symbol
            if order_request.exchange == Exchange.NSE and not order_request.symbol.endswith("-EQ"):
                formatted_symbol = f"{order_request.symbol}-EQ"
            
            # Get symbol token if not provided
            symbol_token = order_request.token
            if not symbol_token:
                try:
                    symbol_token = await self._get_symbol_token(formatted_symbol, order_request.exchange.value)
                except Exception as token_error:
                    logger.error(f"Failed to get symbol token for {formatted_symbol}", error=str(token_error))
                    return BrokerResponse(
                        success=False,
                        message=f"Invalid symbol: {order_request.symbol}. Symbol not found on {order_request.exchange.value}."
                    )
            
            # Map our order types to AngelOne format
            variety_map = {
                OrderType.MARKET: "NORMAL",
                OrderType.LIMIT: "NORMAL", 
                OrderType.SL: "STOPLOSS",
                OrderType.SL_M: "STOPLOSS"
            }
            
            # Map product types to AngelOne format - updated based on API docs
            product_map = {
                ProductType.CNC: "DELIVERY",  # Changed from "CNC" to "DELIVERY"
                ProductType.MIS: "INTRADAY",  # Changed from "MIS" to "INTRADAY" 
                ProductType.NRML: "NORMAL"    # Changed from "NRML" to "NORMAL"
            }
            
            # For market orders, get current price to avoid sending "0"
            order_price = "0"
            if order_request.order_type == OrderType.MARKET:
                try:
                    # Get current market price for market orders
                    quote = await self.get_quote(order_request.symbol, order_request.exchange.value)
                    order_price = str(float(quote.ltp))
                except Exception as e:
                    logger.warning(f"Could not get market price for {order_request.symbol}, using 0", error=str(e))
                    order_price = "0"
            else:
                order_price = str(order_request.price) if order_request.price else "0"
            
            order_data = {
                "variety": variety_map.get(order_request.order_type, "NORMAL"),
                "tradingsymbol": formatted_symbol,
                "symboltoken": symbol_token,
                "transactiontype": order_request.transaction_type.value,
                "exchange": order_request.exchange.value,
                "ordertype": order_request.order_type.value,
                "producttype": product_map.get(order_request.product_type, "DELIVERY"),
                "duration": "DAY",
                "price": order_price,
                "squareoff": "0",
                "stoploss": str(order_request.trigger_price) if order_request.trigger_price else "0",
                "quantity": str(order_request.quantity)
            }
            
            logger.info(f"Placing order: {order_data}")
            
            response_data = await self._make_request(
                "POST",
                "/rest/secure/angelbroking/order/v1/placeOrder",
                data=order_data
            )
            
            return BrokerResponse(
                success=True,
                message="Order placed successfully",
                data={
                    "order_id": response_data.get("orderid"),
                    "response": response_data
                }
            )
            
        except AuthenticationError as auth_error:
            logger.error("Authentication error during order placement", error=str(auth_error))
            return BrokerResponse(
                success=False,
                message=f"Authentication failed: {str(auth_error)}. Please use /logout and then /broker to login again."
            )
        except APIError as api_error:
            logger.error("API error during order placement", error=str(api_error))
            return BrokerResponse(
                success=False,
                message=f"API error: {str(api_error)}"
            )
        except Exception as e:
            logger.error("Failed to place order", error=str(e))
            return BrokerResponse(
                success=False,
                message=f"Failed to place order: {str(e)}"
            )
    
    async def get_orders(self) -> List[Order]:
        """Get all orders."""
        try:
            orders_data = await self._make_request(
                "GET",
                "/rest/secure/angelbroking/order/v1/getOrderBook"
            )
            
            # Handle case where orders_data might be None or not a list
            if not orders_data or not isinstance(orders_data, list):
                logger.info("No orders data or empty response", data=orders_data)
                return []
            
            # Convert to our Order model format
            orders = []
            for order_data in orders_data:
                # Handle case where order_data might be a string or not a dict
                if not isinstance(order_data, dict):
                    logger.warning("Invalid order data format", data=order_data)
                    continue
                
                # Map AngelOne product types to our enum
                product_type_mapping = {
                    "DELIVERY": "CNC",
                    "INTRADAY": "MIS",
                    "MARGIN": "NRML",
                    "CNC": "CNC",
                    "MIS": "MIS",
                    "NRML": "NRML"
                }
                
                raw_product_type = order_data.get("producttype", "CNC")
                mapped_product_type = product_type_mapping.get(raw_product_type, "CNC")
                
                orders.append(Order(
                    order_id=order_data.get("orderid", ""),
                    symbol=order_data.get("tradingsymbol", ""),
                    exchange=Exchange(order_data.get("exchange", "NSE")),
                    transaction_type=TransactionType(order_data.get("transactiontype", "BUY")),
                    order_type=OrderType(order_data.get("ordertype", "MARKET")),
                    product_type=ProductType(mapped_product_type),
                    quantity=int(order_data.get("quantity", 0)),
                    price=Decimal(str(order_data.get("price", 0))),
                    trigger_price=Decimal(str(order_data.get("triggerprice", 0))) if order_data.get("triggerprice") else None,
                    status=OrderStatus(order_data.get("status", "PENDING")),
                    filled_quantity=int(order_data.get("filledshares", 0)),
                    average_price=Decimal(str(order_data.get("averageprice", 0))) if order_data.get("averageprice") else None,
                    order_timestamp=datetime.now(),  # Parse from order_data if available
                    raw_data=order_data
                ))
            
            return orders
            
        except Exception as e:
            logger.error("Failed to get orders", error=str(e))
            return []
    
    async def get_order_history(self) -> List[Order]:
        """Get order history (same as order book in AngelOne)."""
        return await self.get_orders()
    
    async def get_holdings(self) -> List[Holding]:
        """Get portfolio holdings."""
        try:
            response_data = await self._make_request(
                "GET",
                "/rest/secure/angelbroking/portfolio/v1/getAllHolding"
            )
            
            # AngelOne returns holdings in a nested structure
            holdings_data = response_data.get("holdings", []) if response_data else []
            
            # Handle case where holdings_data might be None or not a list
            if not holdings_data or not isinstance(holdings_data, list):
                logger.info("No holdings data or empty response", data=response_data)
                return []
            
            # Convert to our Holding model format
            holdings = []
            for holding_data in holdings_data:
                # Handle case where holding_data might be a string or not a dict
                if not isinstance(holding_data, dict):
                    logger.warning("Invalid holding data format", data=holding_data)
                    continue
                
                # Map AngelOne product types to our enum
                product_type_mapping = {
                    "DELIVERY": "CNC",
                    "INTRADAY": "MIS",
                    "MARGIN": "NRML",
                    "CNC": "CNC",
                    "MIS": "MIS",
                    "NRML": "NRML"
                }
                
                raw_product_type = holding_data.get("product", "CNC")
                mapped_product_type = product_type_mapping.get(raw_product_type, "CNC")
                    
                holdings.append(Holding(
                    symbol=holding_data.get("tradingsymbol", ""),
                    exchange=Exchange(holding_data.get("exchange", "NSE")),
                    quantity=int(holding_data.get("quantity", 0)),
                    average_price=Decimal(str(holding_data.get("averageprice", 0))),
                    current_price=Decimal(str(holding_data.get("ltp", 0))),
                    pnl=Decimal(str(holding_data.get("profitandloss", 0))),
                    product_type=ProductType(mapped_product_type),
                    raw_data=holding_data
                ))
            
            return holdings
            
        except Exception as e:
            logger.error("Failed to get holdings", error=str(e))
            return []
    
    async def get_positions(self) -> List[Position]:
        """Get trading positions."""
        try:
            positions_data = await self._make_request(
                "GET", 
                "/rest/secure/angelbroking/order/v1/getPosition"
            )
            
            # Handle case where positions_data might be None or not a list
            if not positions_data or not isinstance(positions_data, list):
                logger.info("No positions data or empty response", data=positions_data)
                return []
            
            # Convert to our Position model format
            positions = []
            for position_data in positions_data:
                # Handle case where position_data might be a string or not a dict
                if not isinstance(position_data, dict):
                    logger.warning("Invalid position data format", data=position_data)
                    continue
                    
                positions.append(Position(
                    symbol=position_data.get("tradingsymbol", ""),
                    exchange=Exchange(position_data.get("exchange", "NSE")),
                    quantity=int(position_data.get("netqty", 0)),
                    average_price=Decimal(str(position_data.get("avgnetprice", 0))),
                    current_price=Decimal(str(position_data.get("ltp", 0))),
                    pnl=Decimal(str(position_data.get("pnl", 0))),
                    product_type=ProductType(position_data.get("producttype", "MIS")),
                    raw_data=position_data
                ))
            
            return positions
            
        except Exception as e:
            logger.error("Failed to get positions", error=str(e))
            return []
    
    async def get_funds(self) -> BrokerResponse:
        """Get account funds/margin information."""
        try:
            funds_data = await self._make_request(
                "GET",
                "/rest/secure/angelbroking/user/v1/getRMS"
            )
            
            return BrokerResponse(
                success=True,
                message="Funds retrieved successfully",
                data={
                    "available_cash": Decimal(str(funds_data.get("availablecash", 0))),
                    "utilised_margin": Decimal(str(funds_data.get("utilisedmargin", 0))),
                    "available_margin": Decimal(str(funds_data.get("availablemargin", 0))),
                    "raw_data": funds_data
                }
            )
            
        except Exception as e:
            logger.error("Failed to get funds", error=str(e))
            return BrokerResponse(
                success=False,
                message=f"Failed to get funds: {str(e)}"
            )
    
    async def get_quote(self, symbol: str, exchange: str = "NSE") -> Quote:
        """Get live quote for a symbol."""
        try:
            # Format symbol correctly for NSE
            formatted_symbol = f"{symbol}-EQ" if exchange.upper() == "NSE" and not symbol.endswith("-EQ") else symbol
            
            # Get symbol token
            token = await self._get_symbol_token(formatted_symbol, exchange)
            
            if not token:
                logger.warning(f"No token found for {formatted_symbol}, trying with original symbol")
                token = await self._get_symbol_token(symbol, exchange)
            
            if not token:
                # Create a default quote with 0 values if token not found
                logger.warning(f"No valid token found for {symbol}, returning default quote")
                return Quote(
                    symbol=symbol,
                    exchange=Exchange(exchange),
                    ltp=Decimal("0"),
                    open_price=Decimal("0"),
                    high_price=Decimal("0"),
                    low_price=Decimal("0"),
                    close_price=Decimal("0"),
                    change=Decimal("0"),
                    change_percent=Decimal("0"),
                    volume=0,
                    timestamp=datetime.now()
                )
            
            # Make API call for quote - using correct endpoint
            response_data = await self._make_request(
                "POST",
                "/rest/secure/angelbroking/order/v1/getLtpData",
                data={
                    "exchange": exchange,
                    "tradingsymbol": formatted_symbol,
                    "symboltoken": token
                }
            )
            
            if not response_data:
                raise ValueError("Empty response from quote API")
            
            # Parse the response - AngelOne returns data in a specific format
            quote_data = response_data
            if isinstance(response_data, dict) and 'data' in response_data:
                quote_data = response_data['data']
            
            # Handle case where data might be nested
            if isinstance(quote_data, list) and len(quote_data) > 0:
                quote_data = quote_data[0]
            
            # Extract price data with proper field names from AngelOne API
            ltp = Decimal(str(quote_data.get("ltp", quote_data.get("close", "0"))))
            open_price = Decimal(str(quote_data.get("open", "0")))
            high_price = Decimal(str(quote_data.get("high", "0")))
            low_price = Decimal(str(quote_data.get("low", "0")))
            close_price = Decimal(str(quote_data.get("close", ltp)))  # Use LTP if close not available
            volume = int(quote_data.get("volume", quote_data.get("totaltradedvolume", 0)))
            
            # Calculate change
            change = ltp - close_price
            change_percent = (change / close_price * 100) if close_price > 0 else Decimal("0")
            
            return Quote(
                symbol=symbol,
                exchange=Exchange(exchange),
                ltp=ltp,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                change=change,
                change_percent=change_percent,
                volume=volume,
                timestamp=datetime.now(),
                raw_data=response_data
            )
            
        except Exception as e:
            logger.error("Failed to get quote", error=str(e))
            raise
    
    async def _get_symbol_token(self, symbol: str, exchange: str) -> str:
        """Get symbol token for AngelOne API calls."""
        
        # Hardcoded mapping for common NSE equity symbols
        # In production, this should be replaced with instrument master file loading
        nse_symbol_tokens = {
            # Major Stocks
            "RELIANCE-EQ": "2885",
            "TCS-EQ": "11536",
            "HDFCBANK-EQ": "1333",
            "INFY-EQ": "1594",
            "ICICIBANK-EQ": "4963",
            "ITC-EQ": "1660",
            "KOTAKBANK-EQ": "1922",
            "SBIN-EQ": "3045",
            "BHARTIARTL-EQ": "10604",
            "HINDUNILVR-EQ": "1394",
            "ASIANPAINT-EQ": "236",
            "MARUTI-EQ": "2031",
            "AXISBANK-EQ": "5900",
            "LT-EQ": "11483",
            "SUNPHARMA-EQ": "3351",
            "TITAN-EQ": "3506",
            "NESTLEIND-EQ": "17963",
            "BAJFINANCE-EQ": "16669",
            "ULTRACEMCO-EQ": "11532",
            "WIPRO-EQ": "3787",
            "ONGC-EQ": "2475",
            "TATAMOTORS-EQ": "3456",
            "TECHM-EQ": "13538",
            "NTPC-EQ": "11630",
            "POWERGRID-EQ": "14977",
            "HCLTECH-EQ": "7229",
            "JSWSTEEL-EQ": "11723",
            "TATASTEEL-EQ": "3499",
            "INDUSINDBK-EQ": "5258",
            "BAJAJFINSV-EQ": "16675",
            "M&M-EQ": "1207",
            "ADANIPORTS-EQ": "15083",
            "COALINDIA-EQ": "20374",
            "BRITANNIA-EQ": "547",
            "DRREDDY-EQ": "881",
            "EICHERMOT-EQ": "910",
            "GRASIM-EQ": "1232",
            "HEROMOTOCO-EQ": "1348",
            "HINDALCO-EQ": "1363",
            "CIPLA-EQ": "694",
            "BPCL-EQ": "526",
            "DIVISLAB-EQ": "10940",
            "TATACONSUM-EQ": "3432",
            "APOLLOHOSP-EQ": "157",
            "UPL-EQ": "11287",
            "SHREECEM-EQ": "3103",
            "ADANIENT-EQ": "25",
            "SBILIFE-EQ": "21808",
            "HDFCLIFE-EQ": "467",
            "BAJAJ-AUTO-EQ": "16669",
            "TRIDENT-EQ": "2029",  # Added TRIDENT
            "VEDL-EQ": "3063",     # Vedanta
            "SAIL-EQ": "2963",     # SAIL
            "IDEA-EQ": "7929",     # Idea
            "YESBANK-EQ": "11915", # YES Bank
        }
        
        try:
            # First try to use the hardcoded mapping for NSE equity
            if exchange.upper() == "NSE" and symbol in nse_symbol_tokens:
                logger.info(f"Using hardcoded token for {symbol}: {nse_symbol_tokens[symbol]}")
                return nse_symbol_tokens[symbol]
            
            # Try to use the searchScrip API
            search_data = await self._make_request(
                "POST",
                "/rest/secure/angelbroking/order/v1/searchScrip",
                data={
                    "exchange": exchange,
                    "searchtext": symbol
                }
            )
            
            # Look for exact match
            if search_data and isinstance(search_data, list):
                for item in search_data:
                    if item.get("tradingsymbol") == symbol:
                        token = item.get("symboltoken", "")
                        logger.info(f"Found token via search API for {symbol}: {token}")
                        return token
            
            # If no exact match found via API, try partial matching for hardcoded symbols
            if exchange.upper() == "NSE":
                # Try to find by base symbol (without -EQ suffix)
                base_symbol = symbol.replace("-EQ", "")
                for mapped_symbol, token in nse_symbol_tokens.items():
                    if mapped_symbol.replace("-EQ", "") == base_symbol:
                        logger.info(f"Using hardcoded token via base symbol match for {symbol}: {token}")
                        return token
            
            # Return empty string if no token found
            logger.warning(f"No token found for {symbol}, quote may not work properly")
            return ""
            
        except Exception as e:
            logger.warning("Failed to get symbol token", symbol=symbol, error=str(e))
            
            # As a fallback, try hardcoded mapping even on error
            if exchange.upper() == "NSE" and symbol in nse_symbol_tokens:
                return nse_symbol_tokens[symbol]
            
            return ""
    
    async def get_quotes(self, symbols: List[Dict[str, str]]) -> List[Quote]:
        """Get quotes for multiple symbols."""
        quotes = []
        for symbol_info in symbols:
            try:
                quote = await self.get_quote(
                    symbol_info.get("symbol", ""), 
                    symbol_info.get("exchange", "NSE")
                )
                quotes.append(quote)
            except Exception as e:
                logger.error("Failed to get quote for symbol", 
                           symbol=symbol_info.get("symbol"), error=str(e))
        
        return quotes
    
    async def search_instruments(self, query: str) -> List[Instrument]:
        """Search for trading instruments."""
        try:
            # AngelOne doesn't have a direct search API, this would typically
            # require downloading instrument master files and searching locally
            # For now, returning empty list
            
            logger.info("Instrument search requested", query=query)
            return []
            
        except Exception as e:
            logger.error("Failed to search instruments", error=str(e))
            return []
    
    async def get_instruments(self, exchange: Optional[str] = None) -> List[Instrument]:
        """Get instruments for exchange."""
        try:
            # AngelOne provides instrument master files that need to be downloaded
            # For now, returning empty list
            
            logger.info("Instruments list requested", exchange=exchange)
            return []
            
        except Exception as e:
            logger.error("Failed to get instruments", error=str(e))
            return []
    
    async def cancel_order(self, order_id: str) -> BrokerResponse:
        """Cancel an order."""
        try:
            response_data = await self._make_request(
                "POST",
                "/rest/secure/angelbroking/order/v1/cancelOrder",
                data={
                    "variety": "NORMAL",
                    "orderid": order_id
                }
            )
            
            return BrokerResponse(
                success=True,
                message="Order cancelled successfully",
                data=response_data
            )
            
        except Exception as e:
            logger.error("Failed to cancel order", error=str(e))
            return BrokerResponse(
                success=False,
                message=f"Failed to cancel order: {str(e)}"
            )
    
    async def cancel_all_pending_orders(self) -> BrokerResponse:
        """Cancel all pending orders."""
        try:
            # Get all orders first
            orders = await self.get_orders()
            
            # Filter for pending/open orders
            pending_orders = [
                order for order in orders 
                if order.status.value.upper() in ['PENDING', 'OPEN', 'pending', 'open']
            ]
            
            if not pending_orders:
                return BrokerResponse(
                    success=True,
                    message="No pending orders to cancel",
                    data={"cancelled_count": 0}
                )
            
            cancelled_count = 0
            failed_cancellations = []
            
            # Cancel each pending order
            for order in pending_orders:
                try:
                    result = await self.cancel_order(order.order_id)
                    if result.success:
                        cancelled_count += 1
                    else:
                        failed_cancellations.append({
                            "order_id": order.order_id,
                            "symbol": order.symbol,
                            "error": result.message
                        })
                except Exception as e:
                    failed_cancellations.append({
                        "order_id": order.order_id,
                        "symbol": order.symbol,
                        "error": str(e)
                    })
            
            success_message = f"Cancelled {cancelled_count} orders"
            if failed_cancellations:
                success_message += f", {len(failed_cancellations)} failed"
            
            return BrokerResponse(
                success=True,
                message=success_message,
                data={
                    "cancelled_count": cancelled_count,
                    "failed_count": len(failed_cancellations),
                    "failed_orders": failed_cancellations
                }
            )
            
        except Exception as e:
            logger.error("Failed to cancel all pending orders", error=str(e))
            return BrokerResponse(
                success=False,
                message=f"Failed to cancel all pending orders: {str(e)}"
            )
    
    async def modify_order(self, order_id: str, modifications: Dict[str, Any]) -> BrokerResponse:
        """Modify an existing order."""
        try:
            modify_data = {
                "variety": "NORMAL",
                "orderid": order_id,
                **modifications
            }
            
            response_data = await self._make_request(
                "POST",
                "/rest/secure/angelbroking/order/v1/modifyOrder",
                data=modify_data
            )
            
            return BrokerResponse(
                success=True,
                message="Order modified successfully",
                data=response_data
            )
            
        except Exception as e:
            logger.error("Failed to modify order", error=str(e))
            return BrokerResponse(
                success=False,
                message=f"Failed to modify order: {str(e)}"
            )
    
    async def logout(self) -> BrokerResponse:
        """Logout from the broker."""
        try:
            if self.jwt_token:
                await self._make_request(
                    "POST",
                    "/rest/secure/angelbroking/user/v1/logout",
                    data={"clientcode": settings.angelone_user_id}
                )
            
            # Clear session data
            self.jwt_token = None
            self.refresh_token = None
            self.feed_token = None
            
            if self.session:
                await self.session.close()
                self.session = None
            
            return BrokerResponse(
                success=True,
                message="Logged out successfully"
            )
            
        except Exception as e:
            logger.error("Failed to logout", error=str(e))
            # Even if logout API fails, clear local session
            self.jwt_token = None
            self.refresh_token = None
            self.feed_token = None
            
            if self.session:
                await self.session.close()
                self.session = None
            
            return BrokerResponse(
                success=True,
                message="Session cleared (logout API may have failed)"
            )
    
    async def get_margins(self) -> BrokerResponse:
        """Get margin information (same as funds in AngelOne)."""
        return await self.get_funds()
    
    async def get_top_gainers_losers(self, data_type: str = "PercPriceGainers", expiry_type: str = "NEAR") -> BrokerResponse:
        """Get top gainers/losers data from AngelOne.
        
        Args:
            data_type: Type of data (PercPriceGainers, PercPriceLosers, PercOIGainers, PercOILosers)
            expiry_type: Expiry type (NEAR, NEXT, FAR)
        """
        try:
            response_data = await self._make_request(
                "POST",
                "/rest/secure/angelbroking/marketData/v1/gainersLosers",
                data={
                    "datatype": data_type,
                    "expirytype": expiry_type
                }
            )
            
            # Parse and format the response
            gainers_losers_data = []
            if response_data and isinstance(response_data, list):
                for item in response_data:
                    gainers_losers_data.append({
                        "symbol": item.get("tradingSymbol", ""),
                        "percent_change": float(item.get("percentChange", 0)),
                        "symbol_token": item.get("symbolToken", ""),
                        "open_interest": item.get("opnInterest", 0),
                        "net_change_oi": item.get("netChangeOpnInterest", 0)
                    })
            
            return BrokerResponse(
                success=True,
                message=f"Top {data_type} retrieved successfully",
                data={
                    "data_type": data_type,
                    "expiry_type": expiry_type,
                    "items": gainers_losers_data
                }
            )
            
        except Exception as e:
            logger.error("Failed to get top gainers/losers", error=str(e))
            return BrokerResponse(
                success=False,
                message=f"Failed to get top gainers/losers: {str(e)}"
            )
    
    async def get_market_depth(self, symbol: str, exchange: str = "NSE") -> BrokerResponse:
        """Get market depth data for a symbol.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange (NSE, BSE, NFO, etc.)
        """
        try:
            # Format symbol correctly for NSE
            formatted_symbol = f"{symbol}-EQ" if exchange.upper() == "NSE" and not symbol.endswith("-EQ") else symbol
            
            # Get symbol token
            symbol_token = await self._get_symbol_token(formatted_symbol, exchange)
            
            if not symbol_token:
                logger.warning(f"No token found for {formatted_symbol}, trying with original symbol")
                symbol_token = await self._get_symbol_token(symbol, exchange)
            
            if not symbol_token:
                return BrokerResponse(
                    success=False,
                    message=f"Invalid symbol: {symbol}. Symbol not found on {exchange}."
                )
            
            # Make API call for market depth - using FULL mode to get depth data
            response_data = await self._make_request(
                "POST",
                "/rest/secure/angelbroking/market/v1/quote/",
                data={
                    "mode": "FULL",
                    "exchangeTokens": {
                        exchange: [symbol_token]
                    }
                }
            )
            
            if not response_data:
                raise ValueError("Empty response from market depth API")
            
            # Parse the response
            fetched_data = response_data.get("fetched", [])
            if not fetched_data:
                return BrokerResponse(
                    success=False,
                    message=f"No market depth data available for {symbol}"
                )
            
            market_data = fetched_data[0]  # Get first (and should be only) result
            
            return BrokerResponse(
                success=True,
                message="Market depth retrieved successfully",
                data={
                    "symbol": market_data.get("tradingSymbol", symbol),
                    "exchange": market_data.get("exchange", exchange),
                    "ltp": float(market_data.get("ltp", 0)),
                    "open": float(market_data.get("open", 0)),
                    "high": float(market_data.get("high", 0)),
                    "low": float(market_data.get("low", 0)),
                    "close": float(market_data.get("close", 0)),
                    "net_change": float(market_data.get("netChange", 0)),
                    "percent_change": float(market_data.get("percentChange", 0)),
                    "volume": int(market_data.get("tradeVolume", 0)),
                    "avg_price": float(market_data.get("avgPrice", 0)),
                    "upper_circuit": float(market_data.get("upperCircuit", 0)),
                    "lower_circuit": float(market_data.get("lowerCircuit", 0)),
                    "total_buy_quantity": int(market_data.get("totBuyQuan", 0)),
                    "total_sell_quantity": int(market_data.get("totSellQuan", 0)),
                    "52_week_high": float(market_data.get("52WeekHigh", 0)),
                    "52_week_low": float(market_data.get("52WeekLow", 0)),
                    "depth": market_data.get("depth", {}),
                    "raw_data": market_data
                }
            )
            
        except Exception as e:
            logger.error("Failed to get market depth", error=str(e))
            return BrokerResponse(
                success=False,
                message=f"Failed to get market depth: {str(e)}"
            )
    
    async def get_historical_data(self, symbol: str, interval: str, exchange: str = "NSE") -> BrokerResponse:
        """Get historical candlestick data for a symbol.
        
        Args:
            symbol: Trading symbol
            interval: Time interval (1M, 5M, 1H, 1D, etc.)
            exchange: Exchange (NSE, BSE, NFO, etc.)
        """
        try:
            # Format symbol correctly for NSE
            formatted_symbol = f"{symbol}-EQ" if exchange.upper() == "NSE" and not symbol.endswith("-EQ") else symbol
            
            # Get symbol token
            symbol_token = await self._get_symbol_token(formatted_symbol, exchange)
            
            if not symbol_token:
                logger.warning(f"No token found for {formatted_symbol}, trying with original symbol")
                symbol_token = await self._get_symbol_token(symbol, exchange)
            
            if not symbol_token:
                return BrokerResponse(
                    success=False,
                    message=f"Invalid symbol: {symbol}. Symbol not found on {exchange}."
                )
            
            # Map interval to AngelOne format
            api_interval = INTERVAL_MAPPING.get(interval.upper())
            if not api_interval:
                return BrokerResponse(
                    success=False,
                    message=f"Invalid interval: {interval}. Supported: {list(INTERVAL_MAPPING.keys())}"
                )
            
            # Calculate date range to get ~100 candles
            days_back = INTERVAL_MAX_DAYS.get(api_interval, 5)
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days_back)
            
            # Format dates for AngelOne API
            from_date_str = from_date.strftime("%Y-%m-%d %H:%M")
            to_date_str = to_date.strftime("%Y-%m-%d %H:%M")
            
            # Make API call for historical data
            response_data = await self._make_request(
                "POST",
                "/rest/secure/angelbroking/historical/v1/getCandleData",
                data={
                    "exchange": exchange,
                    "symboltoken": symbol_token,
                    "interval": api_interval,
                    "fromdate": from_date_str,
                    "todate": to_date_str
                }
            )
            
            if not response_data:
                raise ValueError("Empty response from historical data API")
            
            # Parse response - data is in format [[timestamp, open, high, low, close, volume], ...]
            if not isinstance(response_data, list) or len(response_data) == 0:
                return BrokerResponse(
                    success=False,
                    message=f"No historical data available for {symbol}"
                )
            
            # Convert to structured format
            candle_data = []
            for candle in response_data:
                if len(candle) >= 6:
                    candle_data.append({
                        "timestamp": candle[0],
                        "open": float(candle[1]),
                        "high": float(candle[2]), 
                        "low": float(candle[3]),
                        "close": float(candle[4]),
                        "volume": int(candle[5])
                    })
            
            return BrokerResponse(
                success=True,
                message="Historical data retrieved successfully",
                data={
                    "symbol": symbol,
                    "exchange": exchange,
                    "interval": interval,
                    "candles": candle_data,
                    "count": len(candle_data)
                }
            )
            
        except Exception as e:
            logger.error("Failed to get historical data", error=str(e))
            return BrokerResponse(
                success=False,
                message=f"Failed to get historical data: {str(e)}"
            )
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.logout()


# Register the broker with the factory
from .base import BrokerFactory
BrokerFactory.register_broker("angelone", AngelOneBroker) 