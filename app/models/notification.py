"""
Notification queue model for handling failed WhatsApp messages
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base

class NotificationQueue(Base):
    """Queue for storing failed notifications that need to be retried"""
    __tablename__ = "notification_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), index=True)
    request_id = Column(Integer, index=True)
    message = Column(Text)
    notification_type = Column(String(50))  # confirmation, status_update, error
    status = Column(String(20), default="pending")  # pending, failed, sent
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    created_at = Column(DateTime, default=func.now())
    last_retry_at = Column(DateTime)
    sent_at = Column(DateTime)
    error_message = Column(Text)
    is_active = Column(Boolean, default=True)