import os
from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/djobea_ai")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "")
    
    # Anthropic Claude API
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    claude_model: str = "claude-sonnet-4-20250514"
    
    # OpenAI API
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    
    # Gemini API
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    
    # Twilio WhatsApp
    twilio_account_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_auth_token: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_phone_number: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    
    # Monetbil Payment
    monetbil_service_key: str = os.getenv("MONETBIL_SERVICE_KEY", "")
    monetbil_service_secret: str = os.getenv("MONETBIL_SERVICE_SECRET", "")
    monetbil_api_key: str = os.getenv("MONETBIL_API_KEY", "")
    monetbil_merchant_id: str = os.getenv("MONETBIL_MERCHANT_ID", "")
    base_url: str = os.getenv("BASE_URL", "https://djobea-ai.replit.app")
    
    # Application
    app_name: str = "Djobea AI"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    secret_key: str = os.getenv("SECRET_KEY", "")
    environment: str = os.getenv("ENVIRONMENT", "development")
    webhook_base_url: str = os.getenv("WEBHOOK_BASE_URL", "")
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "")
    
    # Provider authentication mode
    demo_mode: bool = os.getenv("DEMO_MODE", "false").lower() == "true"
    
    # Redis Configuration
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    redis_password: str = os.getenv("REDIS_PASSWORD", "")
    
    # Session Management
    session_cache_ttl: int = int(os.getenv("SESSION_CACHE_TTL", "7200"))  # 2 hours
    session_timeout_minutes: int = int(os.getenv("SESSION_TIMEOUT_MINUTES", "120"))  # 2 hours
    max_active_sessions: int = int(os.getenv("MAX_ACTIVE_SESSIONS", "1000"))
    
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
