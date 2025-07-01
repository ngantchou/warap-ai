import os
from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/djobea_ai")
    
    # Anthropic Claude API
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    claude_model: str = "claude-sonnet-4-20250514"
    
    # Twilio WhatsApp
    twilio_account_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_auth_token: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_phone_number: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    
    # Application
    app_name: str = "Djobea AI"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Business rules
    max_concurrent_requests: int = 50
    response_timeout_seconds: int = 5
    provider_response_timeout_minutes: int = 10
    commission_rate: float = 0.15  # 15% commission
    
    # Target area
    target_city: str = "Douala"
    target_district: str = "Bonamoussadi"
    
    # Supported services
    supported_services: list = [
        "plomberie",
        "électricité", 
        "réparation électroménager"
    ]

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
