"""
Placeholder Broker Implementations

These are placeholder implementations for brokers that will be implemented later.
They provide basic structure and "Coming Soon" responses.
"""

from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime

from ..models.trading import (
    LoginResponse, BrokerResponse, Order, OrderRequest, Holding, Position,
    Quote, Instrument, OrderType, TransactionType, ProductType, Exchange,
    OrderStatus
)
from ..brokers.base import BaseBroker
from ..utils.logging import get_logger

logger = get_logger(__name__)


class PlaceholderBroker(BaseBroker):
    """Base placeholder broker for not-yet-implemented brokers."""
    
    def __init__(self, name: str):
        super().__init__(name)
    
    async def login(self) -> LoginResponse:
        """Login placeholder."""
        return LoginResponse(
            success=False,
            message=f"{self.name} integration coming soon! This broker is not yet implemented."
        )
    
    async def logout(self) -> BrokerResponse:
        """Logout placeholder."""
        return BrokerResponse(
            success=False,
            message=f"{self.name} integration coming soon!"
        )
    
    async def get_profile(self) -> BrokerResponse:
        """Get profile placeholder."""
        return BrokerResponse(
            success=False,
            message=f"{self.name} integration coming soon!"
        )
    
    async def place_order(self, order_request: OrderRequest) -> BrokerResponse:
        """Place order placeholder."""
        return BrokerResponse(
            success=False,
            message=f"{self.name} integration coming soon!"
        )
    
    async def modify_order(self, order_id: str, modifications: Dict[str, Any]) -> BrokerResponse:
        """Modify order placeholder."""
        return BrokerResponse(
            success=False,
            message=f"{self.name} integration coming soon!"
        )
    
    async def cancel_order(self, order_id: str) -> BrokerResponse:
        """Cancel order placeholder."""
        return BrokerResponse(
            success=False,
            message=f"{self.name} integration coming soon!"
        )
    
    async def get_orders(self) -> List[Order]:
        """Get orders placeholder."""
        return []
    
    async def get_order_history(self) -> List[Order]:
        """Get order history placeholder."""
        return []
    
    async def get_holdings(self) -> List[Holding]:
        """Get holdings placeholder."""
        return []
    
    async def get_positions(self) -> List[Position]:
        """Get positions placeholder."""
        return []
    
    async def get_quote(self, symbol: str, exchange: str) -> Quote:
        """Get quote placeholder."""
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
    
    async def get_quotes(self, symbols: List[Dict[str, str]]) -> List[Quote]:
        """Get quotes placeholder."""
        return []
    
    async def search_instruments(self, query: str) -> List[Instrument]:
        """Search instruments placeholder."""
        return []
    
    async def get_instruments(self, exchange: Optional[str] = None) -> List[Instrument]:
        """Get instruments placeholder."""
        return []
    
    async def get_margins(self) -> BrokerResponse:
        """Get margins placeholder."""
        return BrokerResponse(
            success=False,
            message=f"{self.name} integration coming soon!"
        )
    
    async def get_funds(self) -> BrokerResponse:
        """Get funds placeholder."""
        return BrokerResponse(
            success=False,
            message=f"{self.name} integration coming soon!"
        )


class FyersBroker(PlaceholderBroker):
    """Fyers broker placeholder implementation."""
    
    def __init__(self):
        super().__init__("Fyers")


class DhanBroker(PlaceholderBroker):
    """Dhan broker placeholder implementation."""
    
    def __init__(self):
        super().__init__("Dhan")


class UpstoxBroker(PlaceholderBroker):
    """Upstox broker placeholder implementation."""
    
    def __init__(self):
        super().__init__("Upstox")


# Register brokers with the factory
from .base import BrokerFactory
BrokerFactory.register_broker("Fyers", FyersBroker)
BrokerFactory.register_broker("Dhan", DhanBroker)
BrokerFactory.register_broker("Upstox", UpstoxBroker) 