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
    
    # Monetbil Payment
    monetbil_service_key: str = os.getenv("MONETBIL_SERVICE_KEY", "")
    monetbil_service_secret: str = os.getenv("MONETBIL_SERVICE_SECRET", "")
    base_url: str = os.getenv("BASE_URL", "https://djobea-ai.replit.app")
    
    # Application
    app_name: str = "Djobea AI"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Provider authentication mode
    demo_mode: bool = os.getenv("DEMO_MODE", "false").lower() == "true"
    
    # Business rules
    max_concurrent_requests: int = 50
    response_timeout_seconds: int = 5
    provider_response_timeout_minutes: int = 10
    commission_rate: float = 0.15  # 15% commission
    
    # Communication settings
    instant_confirmation_seconds: int = 30
    proactive_update_interval_minutes: int = 2
    urgent_update_interval_minutes: int = 1
    countdown_threshold_minutes: int = 3
    
    # Target area
    target_city: str = "Douala"
    target_district: str = "Bonamoussadi"
    
    # Supported services
    supported_services: list = [
        "plomberie",
        "électricité", 
        "réparation électroménager"
    ]
    
    # Service pricing estimates (XAF)
    service_pricing: dict = {
        "plomberie": {
            "min": 5000,
            "max": 15000,
            "description": "Intervention de base, matériel simple"
        },
        "électricité": {
            "min": 3000,
            "max": 10000,
            "description": "Diagnostic et réparation standard"
        },
        "réparation électroménager": {
            "min": 2000,
            "max": 8000,
            "description": "Diagnostic et réparation courante"
        }
    }

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
