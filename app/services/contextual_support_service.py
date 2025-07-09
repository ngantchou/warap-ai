"""
Contextual Support Service - Intelligent Support System
"""
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
import json

from app.models.knowledge_base import (
    SupportSession, SupportEscalation, UserQuestion, FAQ, KnowledgeArticle
)
from app.services.knowledge_base_service import KnowledgeBaseService
from app.database import get_db
from loguru import logger

class ContextualSupportService:
    """Service for intelligent contextual support"""
    
    def __init__(self, db: Session):
        self.db = db
        self.knowledge_service = KnowledgeBaseService(db)
        
    def detect_support_need(self, message: str, user_id: str, context: Dict = None) -> Dict[str, Any]:
        """Detect if user needs support and determine appropriate response"""
        try:
            # Support detection patterns
            help_patterns = [
                'aide', 'help', 'aidez-moi', 'je ne comprends pas',
                'comment', 'pourquoi', 'problème', 'erreur', 'bug',
                'ça marche pas', 'ne fonctionne pas', 'bloqué', 'perdu',
                'question', 'expliquer', 'clarifier'
            ]
            
            escalation_patterns = [
                'urgent', 'important', 'immédiat', 'rapidement',
                'parler à quelqu\'un', 'agent humain', 'personne réelle',
                'insatisfait', 'mécontent', 'plainte', 'problème grave'
            ]
            
            message_lower = message.lower()
            
            # Determine support need level
            support_level = 'none'
            confidence = 0.0
            
            # Check for help patterns
            help_score = sum(1 for pattern in help_patterns if pattern in message_lower)
            if help_score > 0:
                support_level = 'faq'
                confidence = min(help_score * 0.3, 1.0)
            
            # Check for escalation patterns
            escalation_score = sum(1 for pattern in escalation_patterns if pattern in message_lower)
            if escalation_score > 0:
                support_level = 'human'
                confidence = min(escalation_score * 0.4, 1.0)
            
            # Check question patterns
            question_indicators = ['?', 'comment', 'pourquoi', 'que', 'quand', 'où']
            question_score = sum(1 for indicator in question_indicators if indicator in message_lower)
            if question_score > 0 and support_level == 'none':
                support_level = 'bot'
                confidence = min(question_score * 0.2, 1.0)
            
            # Get contextual response
            response = self.get_contextual_response(
                message, user_id, support_level, context
            )
            
            return {
                'support_needed': support_level != 'none',
                'support_level': support_level,
                'confidence': confidence,
                'response': response,
                'escalation_suggested': support_level == 'human'
            }
            
        except Exception as e:
            logger.error(f"Error detecting support need: {str(e)}")
            return {
                'support_needed': False,
                'support_level': 'none',
                'confidence': 0.0,
                'response': self._get_default_response(),
                'escalation_suggested': False
            }
    
    def get_contextual_response(self, message: str, user_id: str, 
                               support_level: str, context: Dict = None) -> Dict[str, Any]:
        """Generate contextual support response"""
        try:
            service_type = context.get('service_type') if context else None
            zone = context.get('zone') if context else None
            
            if support_level == 'faq':
                # Search FAQ for relevant answers
                faq_results = self.knowledge_service.search_knowledge(
                    message, service_type, zone
                )
                
                if faq_results['success'] and faq_results['data']['faqs']:
                    return self._format_faq_response(faq_results['data'])
                else:
                    return self._get_bot_response(message, user_id, context)
            
            elif support_level == 'bot':
                return self._get_bot_response(message, user_id, context)
            
            elif support_level == 'human':
                return self._initiate_human_support(message, user_id, context)
            
            else:
                return self._get_default_response()
                
        except Exception as e:
            logger.error(f"Error generating contextual response: {str(e)}")
            return self._get_default_response()
    
    def start_support_session(self, user_id: str, session_type: str = 'bot') -> str:
        """Start a new support session"""
        try:
            session_id = f"support_{uuid.uuid4().hex[:12]}"
            
            session = SupportSession(
                session_id=session_id,
                user_id=user_id,
                session_type=session_type,
                status='active'
            )
            
            self.db.add(session)
            self.db.commit()
            
            return session_id
            
        except Exception as e:
            logger.error(f"Error starting support session: {str(e)}")
            self.db.rollback()
            return ""
    
    def escalate_support(self, session_id: str, user_id: str, reason: str, 
                        priority: str = 'medium') -> Dict[str, Any]:
        """Escalate support to human agent"""
        try:
            escalation_id = f"esc_{uuid.uuid4().hex[:12]}"
            
            escalation = SupportEscalation(
                escalation_id=escalation_id,
                session_id=session_id,
                user_id=user_id,
                escalation_reason=reason,
                escalation_level='bot_to_human',
                priority=priority,
                status='pending'
            )
            
            self.db.add(escalation)
            
            # Update session status
            session = self.db.query(SupportSession).filter(
                SupportSession.session_id == session_id
            ).first()
            
            if session:
                session.status = 'escalated'
            
            self.db.commit()
            
            return {
                'success': True,
                'escalation_id': escalation_id,
                'status': 'escalated',
                'estimated_wait_time': self._get_estimated_wait_time(priority),
                'message': self._get_escalation_message(priority)
            }
            
        except Exception as e:
            logger.error(f"Error escalating support: {str(e)}")
            self.db.rollback()
            return {
                'success': False,
                'error': str(e),
                'message': "Erreur lors de l'escalade vers un agent humain"
            }
    
    def provide_guided_resolution(self, issue_type: str, service_type: str = None, 
                                 zone: str = None) -> Dict[str, Any]:
        """Provide guided resolution for common issues"""
        try:
            # Get relevant service processes
            processes = self.knowledge_service.get_service_processes(service_type, zone)
            
            # Get troubleshooting steps
            troubleshooting_steps = self._get_troubleshooting_steps(issue_type, service_type)
            
            # Get FAQ answers
            faq_results = self.knowledge_service.search_knowledge(
                issue_type, service_type, zone
            )
            
            return {
                'issue_type': issue_type,
                'service_type': service_type,
                'zone': zone,
                'troubleshooting_steps': troubleshooting_steps,
                'processes': processes,
                'related_faqs': faq_results['data']['faqs'] if faq_results['success'] else [],
                'escalation_available': True
            }
            
        except Exception as e:
            logger.error(f"Error providing guided resolution: {str(e)}")
            return {
                'issue_type': issue_type,
                'troubleshooting_steps': [],
                'processes': [],
                'related_faqs': [],
                'escalation_available': True
            }
    
    def track_satisfaction(self, session_id: str, score: int, feedback: str = None) -> bool:
        """Track user satisfaction with support"""
        try:
            session = self.db.query(SupportSession).filter(
                SupportSession.session_id == session_id
            ).first()
            
            if session:
                session.satisfaction_score = score
                session.end_time = datetime.utcnow()
                session.status = 'resolved'
                
                if feedback:
                    session.notes = feedback
                
                self.db.commit()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error tracking satisfaction: {str(e)}")
            self.db.rollback()
            return False
    
    def get_support_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get support analytics for improvement"""
        try:
            since_date = datetime.utcnow() - timedelta(days=days)
            
            # Session statistics
            total_sessions = self.db.query(SupportSession).filter(
                SupportSession.created_at >= since_date
            ).count()
            
            resolved_sessions = self.db.query(SupportSession).filter(
                SupportSession.created_at >= since_date,
                SupportSession.status == 'resolved'
            ).count()
            
            escalated_sessions = self.db.query(SupportSession).filter(
                SupportSession.created_at >= since_date,
                SupportSession.status == 'escalated'
            ).count()
            
            # Average satisfaction
            avg_satisfaction = self.db.query(func.avg(SupportSession.satisfaction_score)).filter(
                SupportSession.created_at >= since_date,
                SupportSession.satisfaction_score.isnot(None)
            ).scalar() or 0
            
            # Popular questions
            popular_questions = self.knowledge_service.get_popular_questions(limit=10)
            
            return {
                'period_days': days,
                'total_sessions': total_sessions,
                'resolved_sessions': resolved_sessions,
                'escalated_sessions': escalated_sessions,
                'resolution_rate': (resolved_sessions / total_sessions * 100) if total_sessions > 0 else 0,
                'escalation_rate': (escalated_sessions / total_sessions * 100) if total_sessions > 0 else 0,
                'average_satisfaction': round(avg_satisfaction, 2),
                'popular_questions': popular_questions
            }
            
        except Exception as e:
            logger.error(f"Error getting support analytics: {str(e)}")
            return {
                'period_days': days,
                'total_sessions': 0,
                'resolved_sessions': 0,
                'escalated_sessions': 0,
                'resolution_rate': 0,
                'escalation_rate': 0,
                'average_satisfaction': 0,
                'popular_questions': []
            }
    
    def _get_bot_response(self, message: str, user_id: str, context: Dict = None) -> Dict[str, Any]:
        """Generate bot response for user query"""
        service_type = context.get('service_type') if context else None
        zone = context.get('zone') if context else None
        
        # Search knowledge base
        search_results = self.knowledge_service.search_knowledge(
            message, service_type, zone
        )
        
        if search_results['success'] and search_results['data']['faqs']:
            return self._format_faq_response(search_results['data'])
        
        return {
            'type': 'bot',
            'message': f"🤖 **Assistant Support**\n\nJe peux vous aider avec:\n\n• **Questions fréquentes** sur nos services\n• **Informations tarifaires** pour {service_type or 'tous nos services'}\n• **Processus** et délais\n• **Conseils pratiques**\n\nPour obtenir une aide plus spécifique, décrivez votre problème en détail.",
            'suggestions': search_results['data']['suggestions'] if search_results['success'] else [],
            'escalation_available': True
        }
    
    def _format_faq_response(self, data: Dict) -> Dict[str, Any]:
        """Format FAQ response for user"""
        message = "📚 **Réponses trouvées:**\n\n"
        
        for faq in data['faqs'][:3]:  # Limit to 3 FAQs
            message += f"**Q:** {faq['question']}\n"
            message += f"**R:** {faq['answer']}\n\n"
        
        if data['pricing']:
            pricing = data['pricing']
            message += f"💰 **Tarifs {pricing['service_type']} à {pricing['zone']}:**\n"
            message += f"• {pricing['min_price']} - {pricing['max_price']} {pricing['currency']}\n\n"
        
        return {
            'type': 'faq',
            'message': message,
            'faqs': data['faqs'],
            'pricing': data['pricing'],
            'suggestions': data['suggestions'],
            'escalation_available': True
        }
    
    def _initiate_human_support(self, message: str, user_id: str, context: Dict = None) -> Dict[str, Any]:
        """Initiate human support session"""
        session_id = self.start_support_session(user_id, 'human')
        
        return {
            'type': 'human',
            'session_id': session_id,
            'message': "🧑‍💼 **Connexion à un agent humain**\n\nUn de nos agents va vous contacter dans les plus brefs délais.\n\n**Temps d'attente estimé:** 5-15 minutes\n\n**Votre demande:** " + message,
            'estimated_wait_time': 10,
            'escalation_available': False
        }
    
    def _get_default_response(self) -> Dict[str, Any]:
        """Get default support response"""
        return {
            'type': 'default',
            'message': "🤖 **Assistant Djobea AI**\n\nComment puis-je vous aider aujourd'hui?\n\n• Tapez **'aide'** pour voir les commandes disponibles\n• Décrivez votre problème pour obtenir de l'aide\n• Demandez **'agent humain'** pour parler à une personne",
            'suggestions': [],
            'escalation_available': True
        }
    
    def _get_troubleshooting_steps(self, issue_type: str, service_type: str = None) -> List[Dict]:
        """Get troubleshooting steps for common issues"""
        steps = []
        
        if service_type == 'plomberie':
            if 'fuite' in issue_type.lower():
                steps = [
                    {'step': 1, 'title': 'Couper l\'eau', 'description': 'Fermez le robinet principal'},
                    {'step': 2, 'title': 'Localiser la fuite', 'description': 'Identifiez l\'origine exacte'},
                    {'step': 3, 'title': 'Évaluer la gravité', 'description': 'Débit et localisation'},
                    {'step': 4, 'title': 'Contacter un plombier', 'description': 'Si la fuite persiste'}
                ]
        
        elif service_type == 'électricité':
            if 'panne' in issue_type.lower():
                steps = [
                    {'step': 1, 'title': 'Vérifier les disjoncteurs', 'description': 'Réenclencher si nécessaire'},
                    {'step': 2, 'title': 'Tester autres appareils', 'description': 'Vérifier si panne générale'},
                    {'step': 3, 'title': 'Vérifier les fusibles', 'description': 'Remplacer si grillés'},
                    {'step': 4, 'title': 'Contacter un électricien', 'description': 'Si problème persiste'}
                ]
        
        return steps
    
    def _get_estimated_wait_time(self, priority: str) -> int:
        """Get estimated wait time based on priority"""
        wait_times = {
            'low': 30,
            'medium': 15,
            'high': 5,
            'urgent': 2
        }
        return wait_times.get(priority, 15)
    
    def _get_escalation_message(self, priority: str) -> str:
        """Get escalation message based on priority"""
        if priority == 'urgent':
            return "🚨 **Escalade urgente** - Un agent va vous contacter dans les 2 minutes"
        elif priority == 'high':
            return "⚡ **Escalade prioritaire** - Un agent va vous contacter dans les 5 minutes"
        else:
            return "👥 **Escalade vers un agent** - Un agent va vous contacter dans les 15 minutes"