"""Configuration management for the trading backend."""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Telegram Configuration
    telegram_bot_token: str = Field(..., description="Telegram bot token")
    
    # AngelOne Configuration
    angelone_api_key: str = Field(..., description="AngelOne API key")
    angelone_user_id: str = Field(..., description="AngelOne user ID")
    angelone_password: str = Field(..., description="AngelOne password")
    angelone_totp_secret: str = Field(..., description="AngelOne TOTP secret")
    angelone_base_url: str = Field(
        default="https://apiconnect.angelone.in",
        description="AngelOne API base URL"
    )
    
    # Application Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="production", description="Environment")
    
    # Database Configuration
    database_url: str = Field(
        default="sqlite:///./trading_bot.db",
        description="Database URL"
    )
    
    # Security
    secret_key: str = Field(..., description="Secret key for encryption")


# Global settings instance
settings = Settings() 