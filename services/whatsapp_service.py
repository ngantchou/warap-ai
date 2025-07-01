import os
from typing import Dict, List, Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
from utils.logger import setup_logger
from config import get_settings

logger = setup_logger(__name__)
settings = get_settings()

class WhatsAppService:
    """Service for handling WhatsApp communication via Twilio"""
    
    def __init__(self):
        self.account_sid = settings.twilio_account_sid
        self.auth_token = settings.twilio_auth_token
        self.phone_number = settings.twilio_phone_number
        
        if not all([self.account_sid, self.auth_token, self.phone_number]):
            logger.error("Missing Twilio credentials in environment variables")
            raise ValueError("Twilio credentials not properly configured")
        
        self.client = Client(self.account_sid, self.auth_token)
        
    def send_message(self, to_phone_number: str, message: str) -> bool:
        """Send WhatsApp message to a phone number"""
        try:
            # Format phone number for WhatsApp
            if not to_phone_number.startswith('whatsapp:'):
                to_phone_number = f"whatsapp:{to_phone_number}"
            
            from_number = f"whatsapp:{self.phone_number}"
            
            message_obj = self.client.messages.create(
                body=message,
                from_=from_number,
                to=to_phone_number
            )
            
            logger.info(f"WhatsApp message sent successfully. SID: {message_obj.sid}")
            return True
            
        except TwilioException as e:
            logger.error(f"Twilio error sending message: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending WhatsApp message: {e}")
            return False
    
    def parse_incoming_message(self, webhook_data: Dict) -> Dict:
        """Parse incoming WhatsApp webhook data"""
        try:
            message_data = {
                "from": webhook_data.get("From", "").replace("whatsapp:", ""),
                "to": webhook_data.get("To", "").replace("whatsapp:", ""),
                "body": webhook_data.get("Body", ""),
                "message_sid": webhook_data.get("MessageSid", ""),
                "timestamp": webhook_data.get("Timestamp", "")
            }
            
            logger.info(f"Parsed incoming WhatsApp message: {message_data}")
            return message_data
            
        except Exception as e:
            logger.error(f"Error parsing incoming WhatsApp message: {e}")
            return {}
    
    def send_provider_notification(self, provider_phone: str, notification_message: str) -> bool:
        """Send notification to service provider"""
        return self.send_message(provider_phone, notification_message)
    
    def send_user_update(self, user_phone: str, update_message: str) -> bool:
        """Send status update to user"""
        return self.send_message(user_phone, update_message)
    
    def validate_phone_number(self, phone_number: str) -> bool:
        """Validate phone number format for Cameroon"""
        # Remove spaces and special characters
        clean_number = phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        
        # Check if it's a valid Cameroon number
        if clean_number.startswith("+237"):
            return len(clean_number) == 12  # +237 + 9 digits
        elif clean_number.startswith("237"):
            return len(clean_number) == 12  # 237 + 9 digits
        elif clean_number.startswith("6"):
            return len(clean_number) == 9   # 6 + 8 digits (local format)
        
        return False
    
    def format_phone_number(self, phone_number: str) -> str:
        """Format phone number to international format"""
        clean_number = phone_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        
        if clean_number.startswith("+237"):
            return clean_number
        elif clean_number.startswith("237"):
            return f"+{clean_number}"
        elif clean_number.startswith("6") and len(clean_number) == 9:
            return f"+237{clean_number}"
        
        return phone_number  # Return as-is if can't format

# Global WhatsApp service instance
whatsapp_service = WhatsAppService()
