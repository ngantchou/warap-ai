"""
Knowledge Base Service - Contextual Information Management
"""
import uuid
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
import json

from app.models.knowledge_base import (
    KnowledgeCategory, KnowledgeArticle, FAQ, PricingInformation,
    ServiceProcess, UserQuestion, ArticleFeedback, SupportSession
)
from app.database import get_db
from loguru import logger

class KnowledgeBaseService:
    """Service for managing contextual knowledge base"""
    
    def __init__(self, db: Session):
        self.db = db
        
    def search_knowledge(self, query: str, service_type: str = None, 
                        zone: str = None, user_type: str = None) -> Dict[str, Any]:
        """Search knowledge base with contextual filtering"""
        try:
            results = {
                'faqs': [],
                'articles': [],
                'pricing': [],
                'processes': [],
                'suggestions': []
            }
            
            # Search FAQs
            faq_query = self.db.query(FAQ).filter(FAQ.is_active == True)
            if service_type:
                faq_query = faq_query.filter(FAQ.service_type == service_type)
            if zone:
                faq_query = faq_query.filter(FAQ.zone == zone)
            if user_type:
                faq_query = faq_query.filter(FAQ.user_type == user_type)
            
            # Search by keywords
            if query:
                faq_query = faq_query.filter(
                    or_(
                        FAQ.question.ilike(f'%{query}%'),
                        FAQ.answer.ilike(f'%{query}%')
                    )
                )
            
            faqs = faq_query.order_by(desc(FAQ.priority), desc(FAQ.helpful_count)).limit(5).all()
            results['faqs'] = [self._format_faq(faq) for faq in faqs]
            
            # Search Articles
            article_query = self.db.query(KnowledgeArticle).filter(
                KnowledgeArticle.is_published == True
            )
            if service_type:
                article_query = article_query.filter(KnowledgeArticle.service_type == service_type)
            if zone:
                article_query = article_query.filter(KnowledgeArticle.zone == zone)
            
            if query:
                article_query = article_query.filter(
                    or_(
                        KnowledgeArticle.title.ilike(f'%{query}%'),
                        KnowledgeArticle.content.ilike(f'%{query}%'),
                        KnowledgeArticle.summary.ilike(f'%{query}%')
                    )
                )
            
            articles = article_query.order_by(desc(KnowledgeArticle.usefulness_score)).limit(3).all()
            results['articles'] = [self._format_article(article) for article in articles]
            
            # Get pricing information
            if service_type and zone:
                pricing = self.get_pricing_info(service_type, zone)
                if pricing:
                    results['pricing'] = pricing
            
            # Get service processes
            if service_type:
                processes = self.get_service_processes(service_type, zone)
                results['processes'] = processes
            
            # Generate suggestions
            suggestions = self.get_contextual_suggestions(query, service_type, zone, user_type)
            results['suggestions'] = suggestions
            
            return {
                'success': True,
                'data': results,
                'query': query,
                'filters': {
                    'service_type': service_type,
                    'zone': zone,
                    'user_type': user_type
                }
            }
            
        except Exception as e:
            logger.error(f"Error searching knowledge base: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'data': {
                    'faqs': [],
                    'articles': [],
                    'pricing': [],
                    'processes': [],
                    'suggestions': []
                }
            }
    
    def get_faq_by_category(self, category_id: str, service_type: str = None, 
                           zone: str = None) -> List[Dict]:
        """Get FAQs by category with contextual filtering"""
        try:
            query = self.db.query(FAQ).filter(
                FAQ.category_id == category_id,
                FAQ.is_active == True
            )
            
            if service_type:
                query = query.filter(FAQ.service_type == service_type)
            if zone:
                query = query.filter(FAQ.zone == zone)
            
            faqs = query.order_by(desc(FAQ.priority), desc(FAQ.helpful_count)).all()
            return [self._format_faq(faq) for faq in faqs]
            
        except Exception as e:
            logger.error(f"Error getting FAQs by category: {str(e)}")
            return []
    
    def get_pricing_info(self, service_type: str, zone: str) -> Optional[Dict]:
        """Get contextual pricing information"""
        try:
            pricing = self.db.query(PricingInformation).filter(
                PricingInformation.service_type == service_type,
                PricingInformation.zone == zone,
                PricingInformation.is_active == True
            ).first()
            
            if pricing:
                return {
                    'service_type': pricing.service_type,
                    'zone': pricing.zone,
                    'min_price': pricing.min_price,
                    'max_price': pricing.max_price,
                    'average_price': pricing.average_price,
                    'currency': pricing.currency,
                    'unit': pricing.unit,
                    'factors': pricing.factors,
                    'last_updated': pricing.last_updated.isoformat()
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting pricing info: {str(e)}")
            return None
    
    def get_service_processes(self, service_type: str, zone: str = None) -> List[Dict]:
        """Get service processes with contextual information"""
        try:
            query = self.db.query(ServiceProcess).filter(
                ServiceProcess.service_type == service_type
            )
            
            if zone:
                query = query.filter(ServiceProcess.zone == zone)
            
            processes = query.all()
            return [self._format_process(process) for process in processes]
            
        except Exception as e:
            logger.error(f"Error getting service processes: {str(e)}")
            return []
    
    def get_contextual_suggestions(self, query: str, service_type: str = None, 
                                  zone: str = None, user_type: str = None) -> List[Dict]:
        """Generate contextual suggestions"""
        try:
            suggestions = []
            
            # Popular FAQs in same category
            if service_type:
                popular_faqs = self.db.query(FAQ).filter(
                    FAQ.service_type == service_type,
                    FAQ.is_active == True
                ).order_by(desc(FAQ.view_count)).limit(3).all()
                
                for faq in popular_faqs:
                    suggestions.append({
                        'type': 'faq',
                        'title': faq.question,
                        'url': f'/faq/{faq.faq_id}',
                        'reason': 'Popular dans cette catégorie'
                    })
            
            # Related articles
            if service_type:
                related_articles = self.db.query(KnowledgeArticle).filter(
                    KnowledgeArticle.service_type == service_type,
                    KnowledgeArticle.is_published == True
                ).order_by(desc(KnowledgeArticle.view_count)).limit(2).all()
                
                for article in related_articles:
                    suggestions.append({
                        'type': 'article',
                        'title': article.title,
                        'url': f'/knowledge/{article.article_id}',
                        'reason': 'Article connexe'
                    })
            
            # Zone-specific suggestions
            if zone:
                zone_faqs = self.db.query(FAQ).filter(
                    FAQ.zone == zone,
                    FAQ.is_active == True
                ).order_by(desc(FAQ.helpful_count)).limit(2).all()
                
                for faq in zone_faqs:
                    suggestions.append({
                        'type': 'faq',
                        'title': faq.question,
                        'url': f'/faq/{faq.faq_id}',
                        'reason': f'Spécifique à {zone}'
                    })
            
            return suggestions[:5]  # Limit to 5 suggestions
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {str(e)}")
            return []
    
    def record_user_question(self, user_id: str, question: str, context: Dict = None,
                           service_type: str = None, zone: str = None) -> str:
        """Record user question for analysis"""
        try:
            question_id = f"q_{uuid.uuid4().hex[:12]}"
            
            user_question = UserQuestion(
                question_id=question_id,
                user_id=user_id,
                question_text=question,
                context=context or {},
                service_type=service_type,
                zone=zone
            )
            
            self.db.add(user_question)
            self.db.commit()
            
            return question_id
            
        except Exception as e:
            logger.error(f"Error recording user question: {str(e)}")
            self.db.rollback()
            return ""
    
    def mark_faq_helpful(self, faq_id: str, helpful: bool = True) -> bool:
        """Mark FAQ as helpful or not helpful"""
        try:
            faq = self.db.query(FAQ).filter(FAQ.faq_id == faq_id).first()
            if faq:
                if helpful:
                    faq.helpful_count += 1
                else:
                    faq.not_helpful_count += 1
                
                self.db.commit()
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error marking FAQ helpful: {str(e)}")
            self.db.rollback()
            return False
    
    def get_popular_questions(self, service_type: str = None, zone: str = None, 
                            limit: int = 10) -> List[Dict]:
        """Get popular questions for content improvement"""
        try:
            query = self.db.query(UserQuestion)
            
            if service_type:
                query = query.filter(UserQuestion.service_type == service_type)
            if zone:
                query = query.filter(UserQuestion.zone == zone)
            
            # Group by similar questions and count
            questions = query.filter(
                UserQuestion.was_answered == False
            ).order_by(desc(UserQuestion.created_at)).limit(limit).all()
            
            return [
                {
                    'question': q.question_text,
                    'count': 1,  # In real implementation, would group similar questions
                    'service_type': q.service_type,
                    'zone': q.zone,
                    'created_at': q.created_at.isoformat()
                }
                for q in questions
            ]
            
        except Exception as e:
            logger.error(f"Error getting popular questions: {str(e)}")
            return []
    
    def _format_faq(self, faq: FAQ) -> Dict:
        """Format FAQ for response"""
        return {
            'id': faq.faq_id,
            'question': faq.question,
            'answer': faq.answer,
            'category': faq.category_id,
            'service_type': faq.service_type,
            'zone': faq.zone,
            'helpful_count': faq.helpful_count,
            'view_count': faq.view_count,
            'keywords': faq.keywords
        }
    
    def _format_article(self, article: KnowledgeArticle) -> Dict:
        """Format article for response"""
        return {
            'id': article.article_id,
            'title': article.title,
            'summary': article.summary,
            'service_type': article.service_type,
            'zone': article.zone,
            'tags': article.tags,
            'difficulty_level': article.difficulty_level,
            'estimated_read_time': article.estimated_read_time,
            'usefulness_score': article.usefulness_score,
            'view_count': article.view_count
        }
    
    def _format_process(self, process: ServiceProcess) -> Dict:
        """Format service process for response"""
        return {
            'id': process.process_id,
            'name': process.process_name,
            'description': process.description,
            'service_type': process.service_type,
            'steps': process.steps,
            'estimated_duration': process.estimated_duration,
            'required_materials': process.required_materials,
            'preparation_tips': process.preparation_tips,
            'difficulty_level': process.difficulty_level
        }