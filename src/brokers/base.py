"""Abstract broker interface defining standard trading methods."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from decimal import Decimal

from ..models.trading import (
    LoginResponse,
    OrderRequest,
    Order,
    Holding,
    Position,
    Quote,
    Instrument,
    BrokerResponse
)


class BaseBroker(ABC):
    """Abstract base class for all broker implementations."""
    
    def __init__(self, name: str):
        """Initialize broker with name."""
        self.name = name
        self._authenticated = False
        self._auth_token: Optional[str] = None
        self._session_data: Dict[str, Any] = {}
    
    @property
    def is_authenticated(self) -> bool:
        """Check if broker is authenticated."""
        return self._authenticated
    
    @property
    def auth_token(self) -> Optional[str]:
        """Get current authentication token."""
        return self._auth_token
    
    @abstractmethod
    async def login(self) -> LoginResponse:
        """
        Authenticate with the broker.
        
        Returns:
            LoginResponse: Authentication result with token and user info
        """
        pass
    
    @abstractmethod
    async def logout(self) -> BrokerResponse:
        """
        Logout from the broker.
        
        Returns:
            BrokerResponse: Logout operation result
        """
        pass
    
    @abstractmethod
    async def get_profile(self) -> BrokerResponse:
        """
        Get user profile information.
        
        Returns:
            BrokerResponse: User profile data
        """
        pass
    
    @abstractmethod
    async def place_order(self, order_request: OrderRequest) -> BrokerResponse:
        """
        Place a trading order.
        
        Args:
            order_request: Order details
            
        Returns:
            BrokerResponse: Order placement result with order_id
        """
        pass
    
    @abstractmethod
    async def modify_order(self, order_id: str, modifications: Dict[str, Any]) -> BrokerResponse:
        """
        Modify an existing order.
        
        Args:
            order_id: Order ID to modify
            modifications: Fields to modify
            
        Returns:
            BrokerResponse: Order modification result
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> BrokerResponse:
        """
        Cancel an existing order.
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            BrokerResponse: Order cancellation result
        """
        pass
    
    @abstractmethod
    async def get_orders(self) -> List[Order]:
        """
        Get all orders for the current session.
        
        Returns:
            List[Order]: List of orders
        """
        pass
    
    @abstractmethod
    async def get_order_history(self) -> List[Order]:
        """
        Get order history.
        
        Returns:
            List[Order]: List of historical orders
        """
        pass
    
    @abstractmethod
    async def get_holdings(self) -> List[Holding]:
        """
        Get current holdings.
        
        Returns:
            List[Holding]: List of holdings
        """
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """
        Get current positions.
        
        Returns:
            List[Position]: List of positions
        """
        pass
    
    @abstractmethod
    async def get_quote(self, symbol: str, exchange: str) -> Quote:
        """
        Get live quote for a symbol.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange name
            
        Returns:
            Quote: Live market quote
        """
        pass
    
    @abstractmethod
    async def get_quotes(self, symbols: List[Dict[str, str]]) -> List[Quote]:
        """
        Get live quotes for multiple symbols.
        
        Args:
            symbols: List of symbol-exchange pairs
            
        Returns:
            List[Quote]: List of live market quotes
        """
        pass
    
    @abstractmethod
    async def search_instruments(self, query: str) -> List[Instrument]:
        """
        Search for trading instruments.
        
        Args:
            query: Search query
            
        Returns:
            List[Instrument]: List of matching instruments
        """
        pass
    
    @abstractmethod
    async def get_instruments(self, exchange: Optional[str] = None) -> List[Instrument]:
        """
        Get all available instruments.
        
        Args:
            exchange: Optional exchange filter
            
        Returns:
            List[Instrument]: List of instruments
        """
        pass
    
    @abstractmethod
    async def get_margins(self) -> BrokerResponse:
        """
        Get margin information.
        
        Returns:
            BrokerResponse: Margin data
        """
        pass
    
    @abstractmethod
    async def get_funds(self) -> BrokerResponse:
        """
        Get available funds.
        
        Returns:
            BrokerResponse: Funds data
        """
        pass
    
    async def refresh_token(self) -> BrokerResponse:
        """
        Refresh authentication token if supported.
        
        Returns:
            BrokerResponse: Token refresh result
        """
        return BrokerResponse(
            success=False,
            message=f"Token refresh not supported by {self.name}",
            error_code="NOT_SUPPORTED"
        )
    
    def _set_authenticated(self, auth_token: str, session_data: Dict[str, Any] = None):
        """Set authentication state."""
        self._authenticated = True
        self._auth_token = auth_token
        self._session_data = session_data or {}
    
    def _clear_authentication(self):
        """Clear authentication state."""
        self._authenticated = False
        self._auth_token = None
        self._session_data = {}

    async def cancel_all_pending_orders(self) -> BrokerResponse:
        """
        Cancel all pending orders.
        
        Returns:
            BrokerResponse: Cancellation result with count of cancelled orders
        """
        # Default implementation - can be overridden by brokers
        try:
            orders = await self.get_orders()
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
            return BrokerResponse(
                success=False,
                message=f"Failed to cancel all pending orders: {str(e)}"
            )


class BrokerFactory:
    """Factory class for creating broker instances."""
    
    _brokers: Dict[str, type] = {}
    
    @classmethod
    def register_broker(cls, name: str, broker_class: type):
        """Register a broker implementation."""
        cls._brokers[name] = broker_class
    
    @classmethod
    def create_broker(cls, name: str, **kwargs) -> BaseBroker:
        """Create a broker instance by name."""
        if name not in cls._brokers:
            raise ValueError(f"Unknown broker: {name}")
        
        return cls._brokers[name](**kwargs)
    
    @classmethod
    def get_available_brokers(cls) -> List[str]:
        """Get list of available broker names."""
        return list(cls._brokers.keys()) 