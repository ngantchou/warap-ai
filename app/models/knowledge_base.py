"""
Knowledge Base Models for Contextual Information System
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class KnowledgeCategory(Base):
    """Categories for organizing knowledge base content"""
    __tablename__ = "knowledge_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(String(255), unique=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    parent_category_id = Column(String(255))
    service_type = Column(String(100))  # plomberie, électricité, électroménager
    zone = Column(String(100))  # Bonamoussadi, Douala, etc.
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    articles = relationship("KnowledgeArticle", back_populates="category")
    faqs = relationship("FAQ", back_populates="category")

class KnowledgeArticle(Base):
    """Knowledge base articles with contextual information"""
    __tablename__ = "knowledge_articles"
    
    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(String(255), unique=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text)
    category_id = Column(String(255), ForeignKey("knowledge_categories.category_id"))
    service_type = Column(String(100))
    zone = Column(String(100))
    tags = Column(JSON)  # List of tags for searching
    view_count = Column(Integer, default=0)
    usefulness_score = Column(Float, default=0.0)
    difficulty_level = Column(String(20), default='beginner')  # beginner, intermediate, advanced
    estimated_read_time = Column(Integer, default=2)  # minutes
    version = Column(String(50), default='1.0')
    is_featured = Column(Boolean, default=False)
    is_published = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    category = relationship("KnowledgeCategory", back_populates="articles")
    feedback = relationship("ArticleFeedback", back_populates="article")

class FAQ(Base):
    """Frequently Asked Questions with contextual targeting"""
    __tablename__ = "faqs"
    
    id = Column(Integer, primary_key=True, index=True)
    faq_id = Column(String(255), unique=True, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    category_id = Column(String(255), ForeignKey("knowledge_categories.category_id"))
    service_type = Column(String(100))
    zone = Column(String(100))
    user_type = Column(String(50))  # new, returning, premium
    keywords = Column(JSON)  # Keywords for matching
    view_count = Column(Integer, default=0)
    helpful_count = Column(Integer, default=0)
    not_helpful_count = Column(Integer, default=0)
    priority = Column(Integer, default=0)  # Higher = more important
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    category = relationship("KnowledgeCategory", back_populates="faqs")

class PricingInformation(Base):
    """Contextual pricing information by service and zone"""
    __tablename__ = "pricing_information"
    
    id = Column(Integer, primary_key=True, index=True)
    pricing_id = Column(String(255), unique=True, index=True)
    service_type = Column(String(100), nullable=False)
    service_subtype = Column(String(100))
    zone = Column(String(100), nullable=False)
    min_price = Column(Float, nullable=False)
    max_price = Column(Float, nullable=False)
    average_price = Column(Float)
    currency = Column(String(10), default='XAF')
    unit = Column(String(50), default='service')  # service, hour, m2, etc.
    factors = Column(JSON)  # Factors affecting price
    last_updated = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
class ServiceProcess(Base):
    """Service processes and timelines by type"""
    __tablename__ = "service_processes"
    
    id = Column(Integer, primary_key=True, index=True)
    process_id = Column(String(255), unique=True, index=True)
    service_type = Column(String(100), nullable=False)
    process_name = Column(String(255), nullable=False)
    description = Column(Text)
    steps = Column(JSON)  # List of process steps
    estimated_duration = Column(Integer)  # in minutes
    required_materials = Column(JSON)  # List of materials needed
    preparation_tips = Column(Text)
    zone = Column(String(100))
    difficulty_level = Column(String(20), default='medium')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserQuestion(Base):
    """Track user questions for FAQ improvement"""
    __tablename__ = "user_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(String(255), unique=True, index=True)
    user_id = Column(String(255), nullable=False)
    question_text = Column(Text, nullable=False)
    context = Column(JSON)  # Context when question was asked
    service_type = Column(String(100))
    zone = Column(String(100))
    intent = Column(String(100))  # Detected intent
    confidence = Column(Float, default=0.0)
    was_answered = Column(Boolean, default=False)
    answer_source = Column(String(50))  # faq, article, bot, human
    satisfaction_score = Column(Integer)  # 1-5 rating
    created_at = Column(DateTime, default=datetime.utcnow)
    
class ArticleFeedback(Base):
    """Feedback on knowledge articles"""
    __tablename__ = "article_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    feedback_id = Column(String(255), unique=True, index=True)
    article_id = Column(String(255), ForeignKey("knowledge_articles.article_id"))
    user_id = Column(String(255))
    rating = Column(Integer)  # 1-5 stars
    comment = Column(Text)
    is_helpful = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    article = relationship("KnowledgeArticle", back_populates="feedback")

class SupportSession(Base):
    """Support session tracking"""
    __tablename__ = "support_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, index=True)
    user_id = Column(String(255), nullable=False)
    session_type = Column(String(50))  # faq, bot, human
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    status = Column(String(50), default='active')  # active, resolved, escalated
    satisfaction_score = Column(Integer)
    resolution_method = Column(String(100))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class SupportEscalation(Base):
    """Support escalation tracking"""
    __tablename__ = "support_escalations"
    
    id = Column(Integer, primary_key=True, index=True)
    escalation_id = Column(String(255), unique=True, index=True)
    session_id = Column(String(255), ForeignKey("support_sessions.session_id"))
    user_id = Column(String(255), nullable=False)
    escalation_reason = Column(String(255))
    escalation_level = Column(String(50))  # bot_to_human, human_to_specialist
    priority = Column(String(20), default='medium')
    status = Column(String(50), default='pending')
    assigned_to = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)