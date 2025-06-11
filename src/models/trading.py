"""Trading data models and enums."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class OrderType(str, Enum):
    """Order type enumeration."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"  # Stop Loss
    SL_M = "SL-M"  # Stop Loss Market


class TransactionType(str, Enum):
    """Transaction type enumeration."""
    BUY = "BUY"
    SELL = "SELL"


class ProductType(str, Enum):
    """Product type enumeration."""
    CNC = "CNC"  # Cash and Carry
    MIS = "MIS"  # Margin Intraday Square Off
    NRML = "NRML"  # Normal
    CO = "CO"  # Cover Order
    BO = "BO"  # Bracket Order


class OrderStatus(str, Enum):
    """Order status enumeration."""
    PENDING = "PENDING"
    OPEN = "OPEN"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    rejected = "rejected"  # AngelOne uses lowercase
    open = "open"
    complete = "complete"
    cancelled = "cancelled"
    pending = "pending"


class Exchange(str, Enum):
    """Exchange enumeration."""
    NSE = "NSE"
    BSE = "BSE"
    NFO = "NFO"  # NSE Futures & Options
    BFO = "BFO"  # BSE Futures & Options
    MCX = "MCX"
    CDS = "CDS"


class Instrument(BaseModel):
    """Trading instrument model."""
    symbol: str = Field(..., description="Trading symbol")
    token: str = Field(..., description="Instrument token")
    exchange: Exchange = Field(..., description="Exchange")
    name: str = Field(..., description="Instrument name")
    lot_size: int = Field(default=1, description="Lot size")
    tick_size: Decimal = Field(default=Decimal("0.01"), description="Tick size")
    instrument_type: str = Field(..., description="Instrument type (EQ, FUT, CE, PE)")
    expiry: Optional[datetime] = Field(None, description="Expiry date for derivatives")
    strike_price: Optional[Decimal] = Field(None, description="Strike price for options")


class OrderRequest(BaseModel):
    """Order placement request model."""
    symbol: str = Field(..., description="Trading symbol")
    token: Optional[str] = Field(None, description="Symbol token (required by some brokers)")
    exchange: Exchange = Field(..., description="Exchange")
    transaction_type: TransactionType = Field(..., description="Buy or Sell")
    order_type: OrderType = Field(..., description="Order type")
    product_type: ProductType = Field(..., description="Product type")
    quantity: int = Field(..., gt=0, description="Order quantity")
    price: Optional[Decimal] = Field(None, description="Order price (for limit orders)")
    trigger_price: Optional[Decimal] = Field(None, description="Trigger price (for stop orders)")
    disclosed_quantity: int = Field(default=0, description="Disclosed quantity")
    validity: str = Field(default="DAY", description="Order validity")


class Order(BaseModel):
    """Order response model."""
    order_id: str = Field(..., description="Order ID")
    symbol: str = Field(..., description="Trading symbol")
    exchange: Exchange = Field(..., description="Exchange")
    transaction_type: TransactionType = Field(..., description="Buy or Sell")
    order_type: OrderType = Field(..., description="Order type")
    product_type: ProductType = Field(..., description="Product type")
    quantity: int = Field(..., description="Order quantity")
    filled_quantity: int = Field(default=0, description="Filled quantity")
    price: Optional[Decimal] = Field(None, description="Order price")
    average_price: Optional[Decimal] = Field(None, description="Average executed price")
    trigger_price: Optional[Decimal] = Field(None, description="Trigger price")
    status: OrderStatus = Field(..., description="Order status")
    order_timestamp: datetime = Field(..., description="Order placement time")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Raw broker response")


class Holding(BaseModel):
    """Holdings model."""
    symbol: str = Field(..., description="Trading symbol")
    exchange: Exchange = Field(..., description="Exchange")
    quantity: int = Field(..., description="Total quantity")
    average_price: Decimal = Field(..., description="Average buy price")
    current_price: Decimal = Field(..., description="Current market price")
    pnl: Decimal = Field(..., description="Profit and Loss")
    product_type: ProductType = Field(..., description="Product type")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Raw broker response")


class Position(BaseModel):
    """Positions model."""
    symbol: str = Field(..., description="Trading symbol")
    exchange: Exchange = Field(..., description="Exchange")
    quantity: int = Field(..., description="Net quantity")
    average_price: Decimal = Field(..., description="Average price")
    current_price: Decimal = Field(..., description="Current market price")
    pnl: Decimal = Field(..., description="Profit and Loss")
    product_type: ProductType = Field(..., description="Product type")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Raw broker response")


class Quote(BaseModel):
    """Market quote model."""
    symbol: str = Field(..., description="Trading symbol")
    exchange: Exchange = Field(..., description="Exchange")
    ltp: Decimal = Field(..., description="Last traded price")
    open_price: Decimal = Field(..., description="Open price")
    high_price: Decimal = Field(..., description="High price")
    low_price: Decimal = Field(..., description="Low price")
    close_price: Decimal = Field(..., description="Close price")
    change: Decimal = Field(default=Decimal("0"), description="Price change from close")
    change_percent: Decimal = Field(default=Decimal("0"), description="Percentage change")
    volume: int = Field(..., description="Volume")
    timestamp: datetime = Field(..., description="Quote timestamp")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Raw broker response")


class LoginResponse(BaseModel):
    """Broker login response model."""
    success: bool = Field(..., description="Login success status")
    auth_token: Optional[str] = Field(None, description="Authentication token")
    refresh_token: Optional[str] = Field(None, description="Refresh token")
    user_id: Optional[str] = Field(None, description="User ID")
    message: str = Field(..., description="Login response message")
    session_data: Dict[str, Any] = Field(default_factory=dict, description="Additional session data")


class BrokerResponse(BaseModel):
    """Generic broker API response model."""
    success: bool = Field(..., description="Response success status")
    data: Optional[Any] = Field(None, description="Response data")
    message: str = Field(..., description="Response message")
    error_code: Optional[str] = Field(None, description="Error code if any")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp") 