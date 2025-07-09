"""
Human Escalation Service for Djobea AI
Service pour la gestion des escalations vers support humain
"""
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from loguru import logger

from app.models.human_escalation_models import (
    HumanAgent, EscalationCase, HandoverSession, CaseAction, 
    EscalationFeedback, EscalationWorkflow, EscalationMetrics
)
from app.models.database_models import Conversation, ServiceRequest


class HumanEscalationService:
    """Service principal pour les escalations humaines"""
    
    def __init__(self, db: Session):
        self.db = db
        
    def create_escalation_case(self, escalation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Créer un nouveau cas d'escalation"""
        try:
            # Générer un ID unique pour le cas
            case_id = f"case_{uuid.uuid4().hex[:12]}"
            
            # Créer le cas d'escalation
            case = EscalationCase(
                case_id=case_id,
                user_id=escalation_data.get('user_id'),
                session_id=escalation_data.get('session_id'),
                original_request_id=escalation_data.get('original_request_id'),
                escalation_trigger=escalation_data.get('escalation_trigger'),
                escalation_score=escalation_data.get('escalation_score', 0.0),
                escalation_reason=escalation_data.get('escalation_reason'),
                urgency_level=self._determine_urgency_level(escalation_data),
                service_type=escalation_data.get('service_type'),
                problem_category=escalation_data.get('problem_category'),
                problem_description=escalation_data.get('problem_description'),
                customer_context=escalation_data.get('customer_context', {}),
                case_metadata=escalation_data.get('metadata', {})
            )
            
            self.db.add(case)
            self.db.commit()
            
            # Assigner automatiquement un agent
            assignment_result = self._auto_assign_agent(case)
            
            # Créer la session de handover
            handover_result = self._create_handover_session(case)
            
            # Notifier l'agent assigné
            if assignment_result.get('success'):
                notification_result = self._notify_assigned_agent(case)
            
            return {
                'success': True,
                'case_id': case_id,
                'case_status': case.status,
                'assigned_agent': assignment_result.get('agent_id'),
                'handover_session': handover_result.get('session_id'),
                'estimated_response_time': self._calculate_estimated_response_time(case)
            }
            
        except Exception as e:
            logger.error(f"Error creating escalation case: {e}")
            self.db.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    def _determine_urgency_level(self, escalation_data: Dict[str, Any]) -> str:
        """Déterminer le niveau d'urgence du cas"""
        escalation_score = escalation_data.get('escalation_score', 0.0)
        escalation_trigger = escalation_data.get('escalation_trigger', '')
        service_type = escalation_data.get('service_type', '')
        
        # Urgence critique
        if escalation_score > 0.9 or escalation_trigger in ['safety_risk', 'emergency']:
            return 'critical'
        
        # Urgence élevée
        if escalation_score > 0.7 or service_type in ['électricité', 'plomberie']:
            return 'high'
        
        # Urgence moyenne
        if escalation_score > 0.5:
            return 'medium'
        
        return 'low'
    
    def _auto_assign_agent(self, case: EscalationCase) -> Dict[str, Any]:
        """Assigner automatiquement un agent au cas"""
        try:
            # Obtenir les agents disponibles
            available_agents = self.db.query(HumanAgent).filter(
                and_(
                    HumanAgent.status == 'online',
                    HumanAgent.availability_status == 'available',
                    HumanAgent.current_case_count < HumanAgent.max_concurrent_cases
                )
            ).all()
            
            if not available_agents:
                # Aucun agent disponible, mettre en file d'attente
                case.status = 'pending'
                self.db.commit()
                return {
                    'success': False,
                    'reason': 'no_available_agents',
                    'queue_position': self._get_queue_position(case)
                }
            
            # Sélectionner le meilleur agent basé sur plusieurs critères
            best_agent = self._select_best_agent(available_agents, case)
            
            # Assigner l'agent
            case.assigned_agent_id = best_agent.agent_id
            case.assigned_at = datetime.utcnow()
            case.assignment_method = 'auto'
            case.status = 'assigned'
            
            # Incrémenter le compteur de cas de l'agent
            best_agent.current_case_count += 1
            
            self.db.commit()
            
            return {
                'success': True,
                'agent_id': best_agent.agent_id,
                'agent_name': best_agent.name,
                'agent_specializations': best_agent.specializations
            }
            
        except Exception as e:
            logger.error(f"Error auto-assigning agent: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _select_best_agent(self, available_agents: List[HumanAgent], case: EscalationCase) -> HumanAgent:
        """Sélectionner le meilleur agent pour le cas"""
        best_agent = None
        best_score = -1
        
        for agent in available_agents:
            score = self._calculate_agent_score(agent, case)
            if score > best_score:
                best_score = score
                best_agent = agent
        
        return best_agent or available_agents[0]
    
    def _calculate_agent_score(self, agent: HumanAgent, case: EscalationCase) -> float:
        """Calculer le score d'un agent pour un cas donné"""
        score = 0.0
        
        # Spécialisation dans le type de service (40%)
        if case.service_type in (agent.specializations or []):
            score += 0.4
        
        # Charge de travail actuelle (30%)
        workload_ratio = agent.current_case_count / max(agent.max_concurrent_cases, 1)
        score += 0.3 * (1 - workload_ratio)
        
        # Performance historique (20%)
        if agent.customer_satisfaction_score > 0:
            score += 0.2 * (agent.customer_satisfaction_score / 5.0)
        
        # Taux de succès d'escalation (10%)
        if agent.escalation_success_rate > 0:
            score += 0.1 * agent.escalation_success_rate
        
        return score
    
    def _create_handover_session(self, case: EscalationCase) -> Dict[str, Any]:
        """Créer une session de handover"""
        try:
            session_id = f"handover_{uuid.uuid4().hex[:12]}"
            
            # Générer le briefing automatique
            briefing = self._generate_case_briefing(case)
            
            # Créer la session de handover
            handover = HandoverSession(
                session_id=session_id,
                case_id=case.case_id,
                agent_id=case.assigned_agent_id,
                handover_type='immediate',
                handover_trigger=case.escalation_trigger,
                handover_reason=case.escalation_reason,
                case_summary=briefing['case_summary'],
                conversation_summary=briefing['conversation_summary'],
                key_issues=briefing['key_issues'],
                recommended_actions=briefing['recommended_actions'],
                blocking_points=briefing['blocking_points'],
                technical_context=briefing['technical_context'],
                service_history=briefing['service_history'],
                briefing_completeness=briefing['completeness_score'],
                context_clarity=briefing['clarity_score']
            )
            
            self.db.add(handover)
            self.db.commit()
            
            return {
                'success': True,
                'session_id': session_id,
                'briefing_quality': briefing['completeness_score']
            }
            
        except Exception as e:
            logger.error(f"Error creating handover session: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_case_briefing(self, case: EscalationCase) -> Dict[str, Any]:
        """Générer le briefing automatique du cas"""
        try:
            # Récupérer l'historique des conversations
            conversations = self.db.query(Conversation).filter(
                Conversation.session_id == case.session_id
            ).order_by(Conversation.created_at.desc()).limit(10).all()
            
            # Récupérer les demandes de service associées
            service_requests = self.db.query(ServiceRequest).filter(
                ServiceRequest.user_id == case.user_id
            ).order_by(ServiceRequest.created_at.desc()).limit(5).all()
            
            # Résumé du cas
            case_summary = self._generate_case_summary(case, conversations)
            
            # Résumé de la conversation
            conversation_summary = self._generate_conversation_summary(conversations)
            
            # Identifier les points clés
            key_issues = self._identify_key_issues(case, conversations)
            
            # Recommandations d'actions
            recommended_actions = self._generate_action_recommendations(case, conversations)
            
            # Points de blocage
            blocking_points = self._identify_blocking_points(case, conversations)
            
            # Contexte technique
            technical_context = self._extract_technical_context(case, conversations)
            
            # Historique des services
            service_history = self._compile_service_history(service_requests)
            
            return {
                'case_summary': case_summary,
                'conversation_summary': conversation_summary,
                'key_issues': key_issues,
                'recommended_actions': recommended_actions,
                'blocking_points': blocking_points,
                'technical_context': technical_context,
                'service_history': service_history,
                'completeness_score': 0.9,  # Score basé sur la complétude
                'clarity_score': 0.85       # Score basé sur la clarté
            }
            
        except Exception as e:
            logger.error(f"Error generating case briefing: {e}")
            return {
                'case_summary': f"Cas d'escalation pour {case.problem_category}",
                'conversation_summary': "Historique non disponible",
                'key_issues': [],
                'recommended_actions': [],
                'blocking_points': [],
                'technical_context': {},
                'service_history': [],
                'completeness_score': 0.3,
                'clarity_score': 0.3
            }
    
    def _generate_case_summary(self, case: EscalationCase, conversations: List[Conversation]) -> str:
        """Générer un résumé du cas"""
        summary_parts = []
        
        # Informations de base
        summary_parts.append(f"Cas d'escalation #{case.case_id}")
        summary_parts.append(f"Service: {case.service_type}")
        summary_parts.append(f"Urgence: {case.urgency_level}")
        summary_parts.append(f"Score d'escalation: {case.escalation_score:.2f}")
        
        # Problème principal
        if case.problem_description:
            summary_parts.append(f"Problème: {case.problem_description}")
        
        # Raison d'escalation
        if case.escalation_reason:
            summary_parts.append(f"Raison d'escalation: {case.escalation_reason}")
        
        # Durée de la conversation
        if conversations:
            first_message = conversations[-1].created_at
            last_message = conversations[0].created_at
            duration = (last_message - first_message).total_seconds() / 60
            summary_parts.append(f"Durée de conversation: {duration:.0f} minutes")
        
        return " | ".join(summary_parts)
    
    def _generate_conversation_summary(self, conversations: List[Conversation]) -> str:
        """Générer un résumé de la conversation"""
        if not conversations:
            return "Aucun historique de conversation disponible"
        
        summary_parts = []
        summary_parts.append(f"Conversation de {len(conversations)} messages")
        
        # Derniers messages pertinents
        recent_messages = conversations[:3]
        for i, conv in enumerate(recent_messages):
            if conv.message_content:
                message_preview = conv.message_content[:100] + "..." if len(conv.message_content) > 100 else conv.message_content
                summary_parts.append(f"Message {i+1}: {message_preview}")
        
        return "\n".join(summary_parts)
    
    def _identify_key_issues(self, case: EscalationCase, conversations: List[Conversation]) -> List[Dict[str, Any]]:
        """Identifier les points clés du cas"""
        key_issues = []
        
        # Problème principal
        if case.problem_description:
            key_issues.append({
                'type': 'main_problem',
                'description': case.problem_description,
                'severity': case.urgency_level
            })
        
        # Frustration client
        if case.escalation_trigger in ['sentiment', 'frustration']:
            key_issues.append({
                'type': 'customer_frustration',
                'description': 'Client exprime de la frustration',
                'severity': 'high'
            })
        
        # Complexité technique
        if case.escalation_trigger == 'complexity':
            key_issues.append({
                'type': 'technical_complexity',
                'description': 'Problème technique complexe',
                'severity': 'medium'
            })
        
        return key_issues
    
    def _generate_action_recommendations(self, case: EscalationCase, conversations: List[Conversation]) -> List[Dict[str, Any]]:
        """Générer des recommandations d'actions"""
        recommendations = []
        
        # Contact immédiat si urgence élevée
        if case.urgency_level in ['high', 'critical']:
            recommendations.append({
                'action': 'immediate_contact',
                'description': 'Contacter immédiatement le client',
                'priority': 'high',
                'estimated_duration': 5
            })
        
        # Résolution technique
        if case.service_type in ['électricité', 'plomberie']:
            recommendations.append({
                'action': 'technical_resolution',
                'description': 'Envoyer un technicien spécialisé',
                'priority': 'medium',
                'estimated_duration': 60
            })
        
        # Suivi client
        recommendations.append({
            'action': 'customer_follow_up',
            'description': 'Effectuer un suivi avec le client',
            'priority': 'medium',
            'estimated_duration': 10
        })
        
        return recommendations
    
    def _identify_blocking_points(self, case: EscalationCase, conversations: List[Conversation]) -> List[Dict[str, Any]]:
        """Identifier les points de blocage"""
        blocking_points = []
        
        # Échecs répétés
        if case.escalation_trigger == 'failure':
            blocking_points.append({
                'type': 'repeated_failures',
                'description': 'Échecs répétés de résolution',
                'impact': 'high'
            })
        
        # Manque de compréhension
        if case.escalation_trigger == 'comprehension':
            blocking_points.append({
                'type': 'comprehension_issues',
                'description': 'Problèmes de compréhension',
                'impact': 'medium'
            })
        
        return blocking_points
    
    def _extract_technical_context(self, case: EscalationCase, conversations: List[Conversation]) -> Dict[str, Any]:
        """Extraire le contexte technique"""
        return {
            'service_type': case.service_type,
            'problem_category': case.problem_category,
            'customer_context': case.customer_context,
            'escalation_score': case.escalation_score,
            'conversation_length': len(conversations)
        }
    
    def _compile_service_history(self, service_requests: List[ServiceRequest]) -> List[Dict[str, Any]]:
        """Compiler l'historique des services"""
        history = []
        
        for request in service_requests:
            history.append({
                'request_id': request.request_id,
                'service_type': request.service_type,
                'status': request.status,
                'created_at': request.created_at.isoformat(),
                'description': request.description[:100] if request.description else None
            })
        
        return history
    
    def _notify_assigned_agent(self, case: EscalationCase) -> Dict[str, Any]:
        """Notifier l'agent assigné"""
        try:
            # Récupérer l'agent
            agent = self.db.query(HumanAgent).filter(
                HumanAgent.agent_id == case.assigned_agent_id
            ).first()
            
            if not agent:
                return {'success': False, 'error': 'Agent not found'}
            
            # Préparer les données de notification
            notification_data = {
                'case_id': case.case_id,
                'urgency_level': case.urgency_level,
                'service_type': case.service_type,
                'problem_description': case.problem_description,
                'escalation_reason': case.escalation_reason,
                'customer_id': case.user_id
            }
            
            # Envoyer la notification (implémentation selon les canaux)
            for channel in (agent.notification_channels or ['email']):
                if channel == 'email':
                    self._send_email_notification(agent, notification_data)
                elif channel == 'sms':
                    self._send_sms_notification(agent, notification_data)
                elif channel == 'whatsapp':
                    self._send_whatsapp_notification(agent, notification_data)
            
            return {'success': True, 'channels_used': agent.notification_channels}
            
        except Exception as e:
            logger.error(f"Error notifying agent: {e}")
            return {'success': False, 'error': str(e)}
    
    def _send_email_notification(self, agent: HumanAgent, notification_data: Dict[str, Any]):
        """Envoyer notification par email"""
        logger.info(f"Email notification sent to {agent.email} for case {notification_data['case_id']}")
    
    def _send_sms_notification(self, agent: HumanAgent, notification_data: Dict[str, Any]):
        """Envoyer notification par SMS"""
        logger.info(f"SMS notification sent to {agent.phone} for case {notification_data['case_id']}")
    
    def _send_whatsapp_notification(self, agent: HumanAgent, notification_data: Dict[str, Any]):
        """Envoyer notification par WhatsApp"""
        logger.info(f"WhatsApp notification sent to {agent.phone} for case {notification_data['case_id']}")
    
    def _get_queue_position(self, case: EscalationCase) -> int:
        """Obtenir la position dans la file d'attente"""
        pending_cases = self.db.query(EscalationCase).filter(
            EscalationCase.status == 'pending'
        ).count()
        return pending_cases
    
    def _calculate_estimated_response_time(self, case: EscalationCase) -> int:
        """Calculer le temps de réponse estimé en minutes"""
        base_time = 15  # minutes
        
        if case.urgency_level == 'critical':
            return 5
        elif case.urgency_level == 'high':
            return 10
        elif case.urgency_level == 'medium':
            return base_time
        else:
            return 30
    
    def get_agent_dashboard(self, agent_id: str) -> Dict[str, Any]:
        """Obtenir le tableau de bord d'un agent"""
        try:
            agent = self.db.query(HumanAgent).filter(
                HumanAgent.agent_id == agent_id
            ).first()
            
            if not agent:
                return {'success': False, 'error': 'Agent not found'}
            
            # Cas assignés
            assigned_cases = self.db.query(EscalationCase).filter(
                and_(
                    EscalationCase.assigned_agent_id == agent_id,
                    EscalationCase.status.in_(['assigned', 'in_progress'])
                )
            ).all()
            
            # Cas en attente
            pending_cases = self.db.query(EscalationCase).filter(
                EscalationCase.status == 'pending'
            ).count()
            
            # Métriques de performance
            performance_metrics = self._calculate_agent_performance(agent)
            
            return {
                'success': True,
                'agent_info': {
                    'agent_id': agent.agent_id,
                    'name': agent.name,
                    'status': agent.status,
                    'availability_status': agent.availability_status,
                    'current_case_count': len(assigned_cases),
                    'max_concurrent_cases': agent.max_concurrent_cases
                },
                'assigned_cases': [
                    {
                        'case_id': case.case_id,
                        'urgency_level': case.urgency_level,
                        'service_type': case.service_type,
                        'problem_description': case.problem_description,
                        'created_at': case.created_at.isoformat(),
                        'status': case.status
                    }
                    for case in assigned_cases
                ],
                'pending_cases_count': pending_cases,
                'performance_metrics': performance_metrics
            }
            
        except Exception as e:
            logger.error(f"Error getting agent dashboard: {e}")
            return {'success': False, 'error': str(e)}
    
    def _calculate_agent_performance(self, agent: HumanAgent) -> Dict[str, Any]:
        """Calculer les métriques de performance d'un agent"""
        try:
            # Cas traités dans les 30 derniers jours
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            handled_cases = self.db.query(EscalationCase).filter(
                and_(
                    EscalationCase.assigned_agent_id == agent.agent_id,
                    EscalationCase.created_at >= thirty_days_ago
                )
            ).all()
            
            # Cas résolus
            resolved_cases = [case for case in handled_cases if case.status == 'resolved']
            
            # Temps de réponse moyen
            response_times = []
            for case in handled_cases:
                if case.first_response_time and case.assigned_at:
                    response_time = (case.first_response_time - case.assigned_at).total_seconds() / 60
                    response_times.append(response_time)
            
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            # Temps de résolution moyen
            resolution_times = []
            for case in resolved_cases:
                if case.resolution_time and case.assigned_at:
                    resolution_time = (case.resolution_time - case.assigned_at).total_seconds() / 60
                    resolution_times.append(resolution_time)
            
            avg_resolution_time = sum(resolution_times) / len(resolution_times) if resolution_times else 0
            
            return {
                'cases_handled_30_days': len(handled_cases),
                'cases_resolved_30_days': len(resolved_cases),
                'resolution_rate': len(resolved_cases) / max(len(handled_cases), 1),
                'avg_response_time_minutes': round(avg_response_time, 2),
                'avg_resolution_time_minutes': round(avg_resolution_time, 2),
                'customer_satisfaction_score': agent.customer_satisfaction_score,
                'escalation_success_rate': agent.escalation_success_rate
            }
            
        except Exception as e:
            logger.error(f"Error calculating agent performance: {e}")
            return {}
    
    def submit_case_feedback(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Soumettre un feedback sur un cas"""
        try:
            feedback_id = f"feedback_{uuid.uuid4().hex[:12]}"
            
            feedback = EscalationFeedback(
                feedback_id=feedback_id,
                case_id=feedback_data.get('case_id'),
                agent_id=feedback_data.get('agent_id'),
                feedback_type=feedback_data.get('feedback_type', 'escalation_quality'),
                feedback_category=feedback_data.get('feedback_category', 'positive'),
                feedback_title=feedback_data.get('feedback_title'),
                feedback_description=feedback_data.get('feedback_description'),
                improvement_suggestions=feedback_data.get('improvement_suggestions', []),
                escalation_appropriateness=feedback_data.get('escalation_appropriateness'),
                context_completeness=feedback_data.get('context_completeness'),
                handover_quality=feedback_data.get('handover_quality'),
                ai_performance_rating=feedback_data.get('ai_performance_rating'),
                missed_opportunities=feedback_data.get('missed_opportunities', []),
                successful_patterns=feedback_data.get('successful_patterns', [])
            )
            
            self.db.add(feedback)
            self.db.commit()
            
            return {
                'success': True,
                'feedback_id': feedback_id,
                'status': 'submitted'
            }
            
        except Exception as e:
            logger.error(f"Error submitting feedback: {e}")
            self.db.rollback()
            return {'success': False, 'error': str(e)}
    
    def get_escalation_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Obtenir les analytics d'escalation"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Cas d'escalation dans la période
            escalation_cases = self.db.query(EscalationCase).filter(
                EscalationCase.created_at >= start_date
            ).all()
            
            # Métriques globales
            total_cases = len(escalation_cases)
            resolved_cases = len([c for c in escalation_cases if c.status == 'resolved'])
            
            # Répartition par urgence
            urgency_distribution = {}
            for case in escalation_cases:
                urgency = case.urgency_level
                urgency_distribution[urgency] = urgency_distribution.get(urgency, 0) + 1
            
            # Répartition par service
            service_distribution = {}
            for case in escalation_cases:
                service = case.service_type
                service_distribution[service] = service_distribution.get(service, 0) + 1
            
            # Temps de réponse moyen
            response_times = []
            for case in escalation_cases:
                if case.first_response_time and case.assigned_at:
                    response_time = (case.first_response_time - case.assigned_at).total_seconds() / 60
                    response_times.append(response_time)
            
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            # Satisfaction client moyenne
            satisfaction_scores = [c.customer_satisfaction for c in escalation_cases if c.customer_satisfaction]
            avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0
            
            return {
                'success': True,
                'period_days': days,
                'total_cases': total_cases,
                'resolved_cases': resolved_cases,
                'resolution_rate': resolved_cases / max(total_cases, 1),
                'avg_response_time_minutes': round(avg_response_time, 2),
                'avg_customer_satisfaction': round(avg_satisfaction, 2),
                'urgency_distribution': urgency_distribution,
                'service_distribution': service_distribution,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting escalation analytics: {e}")
            return {'success': False, 'error': str(e)}