"""Telegram bot data models."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class UserState(str, Enum):
    """User conversation states."""
    START = "START"
    BROKER_SELECTION = "BROKER_SELECTION"
    AUTHENTICATED = "AUTHENTICATED"
    TRADING = "TRADING"
    WAITING_ORDER_DETAILS = "WAITING_ORDER_DETAILS"
    WAITING_SYMBOL = "WAITING_SYMBOL"
    WAITING_QUANTITY = "WAITING_QUANTITY"
    WAITING_PRICE = "WAITING_PRICE"


class TelegramUser(BaseModel):
    """Telegram user model."""
    user_id: int = Field(..., description="Telegram user ID")
    username: Optional[str] = Field(None, description="Telegram username")
    first_name: Optional[str] = Field(None, description="User first name")
    last_name: Optional[str] = Field(None, description="User last name")
    language_code: Optional[str] = Field(None, description="User language code")
    is_bot: bool = Field(default=False, description="Is bot user")


class UserSession(BaseModel):
    """User session model for maintaining conversation state."""
    user_id: int = Field(..., description="Telegram user ID")
    chat_id: int = Field(..., description="Telegram chat ID")
    state: UserState = Field(default=UserState.START, description="Current conversation state")
    selected_broker: Optional[str] = Field(None, description="Selected broker")
    broker_authenticated: bool = Field(default=False, description="Broker authentication status")
    context_data: Dict[str, Any] = Field(default_factory=dict, description="Conversation context")
    created_at: datetime = Field(default_factory=datetime.now, description="Session creation time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")
    
    def update_state(self, new_state: UserState, context: Optional[Dict[str, Any]] = None):
        """Update user state and context."""
        self.state = new_state
        self.updated_at = datetime.now()
        if context:
            self.context_data.update(context)
    
    def clear_context(self):
        """Clear conversation context."""
        self.context_data = {}
        self.updated_at = datetime.now()


class CommandContext(BaseModel):
    """Command execution context."""
    user_session: UserSession = Field(..., description="User session")
    message_text: str = Field(..., description="Original message text")
    command: Optional[str] = Field(None, description="Extracted command")
    arguments: list[str] = Field(default_factory=list, description="Command arguments")
    raw_message: Dict[str, Any] = Field(default_factory=dict, description="Raw Telegram message") 