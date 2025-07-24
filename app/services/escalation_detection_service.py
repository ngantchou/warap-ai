"""
Escalation Detection Service for Djobea AI
Advanced escalation detection with machine learning and sentiment analysis
"""
import uuid
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc
from loguru import logger

from app.models.escalation_detection_models import (
    EscalationDetector, EscalationDetectionLog, EscalationBusinessRule, EscalationExecution,
    ComplexityScoring, EscalationAnalytics, EscalationPattern, EscalationFeedback
)

class EscalationDetectionService:
    """Service for detecting and managing escalations"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # Frustration keywords in French
        self.frustration_keywords = [
            'frustré', 'énervé', 'marre', 'problème', 'impossible', 
            'nul', 'mauvais', 'lent', 'rapide', 'urgent', 'immédiat',
            'catastrophe', 'désastre', 'inacceptable', 'ridicule',
            'perte de temps', 'n\'importe quoi', 'incompétent'
        ]
        
        # Complexity indicators
        self.complexity_indicators = [
            'compliqué', 'complexe', 'difficile', 'spécial', 'technique',
            'plusieurs', 'nombreux', 'différent', 'exception', 'particulier'
        ]
        
        # Positive sentiment words
        self.positive_words = [
            'merci', 'parfait', 'excellent', 'bon', 'bien', 'super',
            'génial', 'formidable', 'satisfait', 'content', 'heureux'
        ]
        
        # Negative sentiment words
        self.negative_words = [
            'pas', 'non', 'mauvais', 'terrible', 'horrible', 'déçu',
            'triste', 'fâché', 'colère', 'mécontent', 'insatisfait'
        ]
    
    def detect_escalation(self, user_id: str, session_id: str, message: str,
                         context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Main escalation detection function"""
        try:
            # Get conversation history
            conversation_history = self._get_conversation_history(user_id, session_id)
            
            # Run all active detectors
            detection_results = []
            active_detectors = self._get_active_detectors()
            
            for detector in active_detectors:
                result = self._run_detector(detector, user_id, session_id, message, 
                                          conversation_history, context)
                detection_results.append(result)
            
            # Calculate overall escalation score
            overall_score = self._calculate_overall_score(detection_results)
            
            # Check escalation rules
            escalation_decision = self._check_escalation_rules(
                detection_results, overall_score, user_id, session_id, context
            )
            
            # Log detection
            detection_log = self._log_detection(
                user_id, session_id, message, detection_results, 
                overall_score, escalation_decision, context
            )
            
            # Execute escalation if triggered
            if escalation_decision.get('escalate', False):
                execution_result = self._execute_escalation(
                    escalation_decision, detection_log, user_id, session_id, context
                )
                return {
                    'success': True,
                    'escalation_triggered': True,
                    'escalation_score': overall_score,
                    'escalation_reason': escalation_decision.get('reason'),
                    'escalation_type': escalation_decision.get('type'),
                    'execution_id': execution_result.get('execution_id'),
                    'detection_log_id': detection_log.log_id
                }
            
            return {
                'success': True,
                'escalation_triggered': False,
                'escalation_score': overall_score,
                'detection_results': detection_results,
                'detection_log_id': detection_log.log_id
            }
            
        except Exception as e:
            logger.error(f"Error in escalation detection: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'escalation_triggered': False
            }
    
    def _run_detector(self, detector: EscalationDetector, user_id: str, session_id: str,
                     message: str, history: List[Dict], context: Dict[str, Any]) -> Dict[str, Any]:
        """Run a specific detector"""
        try:
            if detector.detector_type == 'failure_counter':
                return self._detect_failure_count(detector, user_id, session_id, history)
            
            elif detector.detector_type == 'sentiment_analysis':
                return self._detect_sentiment(detector, message, history)
            
            elif detector.detector_type == 'duration_based':
                return self._detect_duration_issues(detector, user_id, session_id, history)
            
            elif detector.detector_type == 'complexity_scoring':
                return self._detect_complexity(detector, message, history, context)
            
            else:
                return {
                    'detector_id': detector.detector_id,
                    'detector_type': detector.detector_type,
                    'score': 0.0,
                    'triggered': False,
                    'error': f"Unknown detector type: {detector.detector_type}"
                }
                
        except Exception as e:
            logger.error(f"Error running detector {detector.detector_id}: {str(e)}")
            return {
                'detector_id': detector.detector_id,
                'detector_type': detector.detector_type,
                'score': 0.0,
                'triggered': False,
                'error': str(e)
            }
    
    def _detect_failure_count(self, detector: EscalationDetector, user_id: str,
                             session_id: str, history: List[Dict]) -> Dict[str, Any]:
        """Detect escalation based on failure count"""
        # Count comprehension failures in recent history
        failure_count = 0
        clarification_requests = 0
        
        for entry in history[-10:]:  # Last 10 messages
            message = entry.get('message', '').lower()
            
            # Check for AI confusion indicators
            if any(phrase in message for phrase in [
                'je ne comprends pas', 'pouvez-vous préciser', 'clarifier',
                'reformuler', 'expliquer', 'détailler'
            ]):
                failure_count += 1
            
            # Check for clarification requests
            if any(phrase in message for phrase in [
                'que voulez-vous dire', 'comment', 'pourquoi', 'où exactement'
            ]):
                clarification_requests += 1
        
        # Calculate score
        total_failures = failure_count + (clarification_requests * 0.5)
        score = min(total_failures / detector.failure_count_threshold, 1.0)
        triggered = score >= detector.escalation_threshold
        
        return {
            'detector_id': detector.detector_id,
            'detector_type': detector.detector_type,
            'score': score,
            'triggered': triggered,
            'failure_count': failure_count,
            'clarification_requests': clarification_requests,
            'details': {
                'total_failures': total_failures,
                'threshold': detector.failure_count_threshold
            }
        }
    
    def _detect_sentiment(self, detector: EscalationDetector, message: str,
                         history: List[Dict]) -> Dict[str, Any]:
        """Detect escalation based on sentiment analysis"""
        # Simple sentiment analysis for French
        message_lower = message.lower()
        
        # Count positive and negative words
        positive_count = sum(1 for word in self.positive_words if word in message_lower)
        negative_count = sum(1 for word in self.negative_words if word in message_lower)
        frustration_count = sum(1 for word in self.frustration_keywords if word in message_lower)
        
        # Calculate sentiment score (-1 to 1)
        total_words = len(message.split())
        if total_words == 0:
            sentiment_score = 0.0
        else:
            sentiment_score = (positive_count - negative_count - frustration_count * 2) / total_words
        
        # Check recent message sentiment
        recent_sentiment = []
        for entry in history[-5:]:
            hist_message = entry.get('message', '').lower()
            hist_negative = sum(1 for word in self.negative_words if word in hist_message)
            hist_frustration = sum(1 for word in self.frustration_keywords if word in hist_message)
            hist_words = len(hist_message.split())
            
            if hist_words > 0:
                hist_sentiment = -(hist_negative + hist_frustration * 2) / hist_words
                recent_sentiment.append(hist_sentiment)
        
        # Calculate trend
        avg_recent_sentiment = sum(recent_sentiment) / len(recent_sentiment) if recent_sentiment else 0
        
        # Calculate escalation score
        escalation_score = 0.0
        if sentiment_score <= detector.sentiment_threshold:
            escalation_score = abs(sentiment_score - detector.sentiment_threshold) / abs(detector.sentiment_threshold)
        
        # Boost score if trend is negative
        if avg_recent_sentiment < -0.2:
            escalation_score *= 1.5
        
        escalation_score = min(escalation_score, 1.0)
        triggered = escalation_score >= detector.escalation_threshold
        
        return {
            'detector_id': detector.detector_id,
            'detector_type': detector.detector_type,
            'score': escalation_score,
            'triggered': triggered,
            'sentiment_score': sentiment_score,
            'recent_sentiment': avg_recent_sentiment,
            'details': {
                'positive_count': positive_count,
                'negative_count': negative_count,
                'frustration_count': frustration_count,
                'sentiment_threshold': detector.sentiment_threshold
            }
        }
    
    def _detect_duration_issues(self, detector: EscalationDetector, user_id: str,
                               session_id: str, history: List[Dict]) -> Dict[str, Any]:
        """Detect escalation based on conversation duration"""
        if not history:
            return {
                'detector_id': detector.detector_id,
                'detector_type': detector.detector_type,
                'score': 0.0,
                'triggered': False,
                'duration_minutes': 0.0
            }
        
        # Calculate conversation duration
        start_time = history[0].get('timestamp', datetime.utcnow())
        end_time = history[-1].get('timestamp', datetime.utcnow())
        
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        if isinstance(end_time, str):
            end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        
        duration = end_time - start_time
        duration_minutes = duration.total_seconds() / 60
        
        # Calculate score
        score = min(duration_minutes / detector.duration_threshold_minutes, 1.0)
        triggered = score >= detector.escalation_threshold
        
        # Consider message density
        message_density = len(history) / max(duration_minutes, 1)
        if message_density > 2:  # High message density might indicate struggle
            score *= 1.2
        
        score = min(score, 1.0)
        
        return {
            'detector_id': detector.detector_id,
            'detector_type': detector.detector_type,
            'score': score,
            'triggered': triggered,
            'duration_minutes': duration_minutes,
            'message_count': len(history),
            'message_density': message_density,
            'details': {
                'duration_threshold': detector.duration_threshold_minutes,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }
        }
    
    def _detect_complexity(self, detector: EscalationDetector, message: str,
                          history: List[Dict], context: Dict[str, Any]) -> Dict[str, Any]:
        """Detect escalation based on complexity scoring"""
        # Calculate complexity factors
        complexity_factors = {
            'message_length': len(message) / 100,  # Normalize to 0-1
            'technical_terms': sum(1 for word in self.complexity_indicators 
                                 if word in message.lower()) / 5,
            'question_count': message.count('?') / 3,
            'conversation_length': len(history) / 20,
            'topic_switches': self._count_topic_switches(history),
            'repetition_level': self._calculate_repetition(history)
        }
        
        # Service-specific complexity
        service_type = context.get('service_type', '')
        if service_type in ['électricité', 'plomberie']:
            complexity_factors['service_complexity'] = 0.8
        elif service_type in ['électroménager']:
            complexity_factors['service_complexity'] = 0.6
        else:
            complexity_factors['service_complexity'] = 0.4
        
        # Calculate weighted complexity score
        weights = {
            'message_length': 0.1,
            'technical_terms': 0.2,
            'question_count': 0.15,
            'conversation_length': 0.15,
            'topic_switches': 0.15,
            'repetition_level': 0.15,
            'service_complexity': 0.1
        }
        
        complexity_score = sum(
            complexity_factors.get(factor, 0) * weights.get(factor, 0)
            for factor in weights
        )
        
        complexity_score = min(complexity_score, 1.0)
        triggered = complexity_score >= detector.escalation_threshold
        
        return {
            'detector_id': detector.detector_id,
            'detector_type': detector.detector_type,
            'score': complexity_score,
            'triggered': triggered,
            'complexity_factors': complexity_factors,
            'details': {
                'complexity_threshold': detector.complexity_threshold,
                'weighted_factors': {k: v * weights.get(k, 0) for k, v in complexity_factors.items()}
            }
        }
    
    def _count_topic_switches(self, history: List[Dict]) -> float:
        """Count topic switches in conversation"""
        if len(history) < 2:
            return 0.0
        
        topic_keywords = {
            'plomberie': ['eau', 'fuite', 'robinet', 'tuyau', 'évier'],
            'électricité': ['courant', 'électricité', 'lumière', 'prise', 'interrupteur'],
            'électroménager': ['réfrigérateur', 'machine', 'four', 'lave-linge', 'climatiseur']
        }
        
        topics = []
        for entry in history:
            message = entry.get('message', '').lower()
            detected_topics = []
            
            for topic, keywords in topic_keywords.items():
                if any(keyword in message for keyword in keywords):
                    detected_topics.append(topic)
            
            if detected_topics:
                topics.append(detected_topics[0])  # Take first detected topic
        
        # Count switches
        switches = 0
        for i in range(1, len(topics)):
            if topics[i] != topics[i-1]:
                switches += 1
        
        return min(switches / 3, 1.0)  # Normalize to 0-1
    
    def _calculate_repetition(self, history: List[Dict]) -> float:
        """Calculate repetition level in conversation"""
        if len(history) < 2:
            return 0.0
        
        messages = [entry.get('message', '').lower() for entry in history]
        
        # Count similar messages
        repetition_count = 0
        for i in range(len(messages)):
            for j in range(i + 1, len(messages)):
                similarity = self._message_similarity(messages[i], messages[j])
                if similarity > 0.7:
                    repetition_count += 1
        
        return min(repetition_count / 5, 1.0)  # Normalize to 0-1
    
    def _message_similarity(self, msg1: str, msg2: str) -> float:
        """Calculate similarity between two messages"""
        words1 = set(msg1.split())
        words2 = set(msg2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _calculate_overall_score(self, detection_results: List[Dict]) -> float:
        """Calculate overall escalation score"""
        if not detection_results:
            return 0.0
        
        # Weight different detector types
        weights = {
            'failure_counter': 0.3,
            'sentiment_analysis': 0.3,
            'duration_based': 0.2,
            'complexity_scoring': 0.2
        }
        
        weighted_scores = []
        for result in detection_results:
            detector_type = result.get('detector_type', '')
            score = result.get('score', 0.0)
            weight = weights.get(detector_type, 0.1)
            
            weighted_scores.append(score * weight)
        
        return min(sum(weighted_scores), 1.0)
    
    def _check_escalation_rules(self, detection_results: List[Dict], overall_score: float,
                               user_id: str, session_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Check if escalation rules are met"""
        try:
            # Get active rules
            active_rules = self.db.query(EscalationBusinessRule).filter(
                EscalationBusinessRule.is_active == True
            ).order_by(EscalationBusinessRule.priority_order).all()
            
            for rule in active_rules:
                # Check if rule conditions are met
                if self._rule_conditions_met(rule, detection_results, overall_score, context):
                    # Check exceptions
                    if not self._check_exceptions(rule, user_id, session_id, context):
                        # Check cooldown
                        if self._check_cooldown(rule, user_id):
                            return {
                                'escalate': True,
                                'rule_id': rule.rule_id,
                                'rule_name': rule.rule_name,
                                'reason': f"Rule '{rule.rule_name}' triggered with score {overall_score:.2f}",
                                'type': rule.escalation_action,
                                'target': rule.escalation_target,
                                'channels': rule.notification_channels
                            }
            
            return {
                'escalate': False,
                'reason': f"No rules triggered (score: {overall_score:.2f})"
            }
            
        except Exception as e:
            logger.error(f"Error checking escalation rules: {str(e)}")
            return {
                'escalate': False,
                'error': str(e)
            }
    
    def _rule_conditions_met(self, rule: EscalationBusinessRule, detection_results: List[Dict],
                            overall_score: float, context: Dict[str, Any]) -> bool:
        """Check if rule conditions are met"""
        # Check overall threshold
        if overall_score < rule.escalation_threshold:
            return False
        
        # Check specific detector conditions
        if rule.primary_detector:
            primary_result = next(
                (r for r in detection_results if r.get('detector_id') == rule.primary_detector),
                None
            )
            if not primary_result or not primary_result.get('triggered', False):
                return False
        
        # Check service type filter
        if rule.service_type_filter:
            service_type = context.get('service_type', '')
            if service_type != rule.service_type_filter:
                return False
        
        # Check zone filter
        if rule.zone_filter:
            zone = context.get('zone', '')
            if zone != rule.zone_filter:
                return False
        
        return True
    
    def _check_exceptions(self, rule: EscalationBusinessRule, user_id: str, session_id: str,
                         context: Dict[str, Any]) -> bool:
        """Check if any exception conditions apply"""
        if not rule.exception_conditions:
            return False
        
        # Check for specific exception conditions
        exceptions = rule.exception_conditions
        
        # Check user type exceptions
        if 'user_type' in exceptions:
            user_type = context.get('user_type', 'regular')
            if user_type in exceptions['user_type']:
                return True
        
        # Check time-based exceptions
        if 'time_restrictions' in exceptions:
            current_hour = datetime.utcnow().hour
            restricted_hours = exceptions['time_restrictions']
            if current_hour in restricted_hours:
                return True
        
        return False
    
    def _check_cooldown(self, rule: EscalationBusinessRule, user_id: str) -> bool:
        """Check if cooldown period has passed"""
        if rule.cooldown_minutes <= 0:
            return True
        
        # Get last escalation for this user and rule
        cooldown_time = datetime.utcnow() - timedelta(minutes=rule.cooldown_minutes)
        
        recent_escalation = self.db.query(EscalationExecution).filter(
            and_(
                EscalationExecution.rule_id == rule.rule_id,
                EscalationExecution.user_id == user_id,
                EscalationExecution.execution_timestamp >= cooldown_time
            )
        ).first()
        
        return recent_escalation is None
    
    def _get_conversation_history(self, user_id: str, session_id: str) -> List[Dict]:
        """Get conversation history for analysis"""
        try:
            # Get recent detection logs for this session
            logs = self.db.query(EscalationDetectionLog).filter(
                and_(
                    EscalationDetectionLog.user_id == user_id,
                    EscalationDetectionLog.session_id == session_id
                )
            ).order_by(EscalationDetectionLog.timestamp.desc()).limit(20).all()
            
            history = []
            for log in reversed(logs):
                history.append({
                    'message': log.message_content or '',
                    'timestamp': log.timestamp,
                    'sentiment': log.message_sentiment,
                    'failures': log.comprehension_failures or [],
                    'frustration': log.frustration_indicators or []
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            return []
    
    def _get_active_detectors(self) -> List[EscalationDetector]:
        """Get all active detectors"""
        return self.db.query(EscalationDetector).filter(
            EscalationDetector.is_active == True
        ).order_by(EscalationDetector.priority_level.desc()).all()
    
    def _log_detection(self, user_id: str, session_id: str, message: str,
                      detection_results: List[Dict], overall_score: float,
                      escalation_decision: Dict[str, Any], context: Dict[str, Any]) -> EscalationDetectionLog:
        """Log detection event"""
        try:
            log = EscalationDetectionLog(
                log_id=f"detection_{uuid.uuid4().hex[:12]}",
                user_id=user_id,
                session_id=session_id,
                request_id=context.get('request_id'),
                conversation_turn=context.get('conversation_turn', 1),
                escalation_triggered=escalation_decision.get('escalate', False),
                escalation_score=overall_score,
                escalation_reason=escalation_decision.get('reason'),
                escalation_type=escalation_decision.get('type'),
                message_content=message,
                service_type=context.get('service_type'),
                zone=context.get('zone'),
                user_type=context.get('user_type'),
                urgency_level=context.get('urgency_level'),
                detection_metadata={
                    'detection_results': detection_results,
                    'escalation_decision': escalation_decision,
                    'context': context
                }
            )
            
            # Extract specific metrics from detection results
            for result in detection_results:
                if result.get('detector_type') == 'failure_counter':
                    log.failure_count = result.get('failure_count', 0)
                elif result.get('detector_type') == 'sentiment_analysis':
                    log.sentiment_score = result.get('sentiment_score', 0.0)
                    log.message_sentiment = 'negative' if result.get('sentiment_score', 0) < -0.2 else 'neutral'
                elif result.get('detector_type') == 'duration_based':
                    log.duration_minutes = result.get('duration_minutes', 0.0)
                elif result.get('detector_type') == 'complexity_scoring':
                    log.complexity_score = result.get('score', 0.0)
            
            self.db.add(log)
            self.db.commit()
            
            return log
            
        except Exception as e:
            logger.error(f"Error logging detection: {str(e)}")
            self.db.rollback()
            raise
    
    def _execute_escalation(self, escalation_decision: Dict[str, Any], detection_log: EscalationDetectionLog,
                           user_id: str, session_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute escalation actions"""
        try:
            execution = EscalationExecution(
                execution_id=f"exec_{uuid.uuid4().hex[:12]}",
                rule_id=escalation_decision.get('rule_id'),
                detection_log_id=detection_log.log_id,
                user_id=user_id,
                session_id=session_id,
                request_id=context.get('request_id'),
                escalation_score=escalation_decision.get('score', 0.0),
                execution_reason=escalation_decision.get('reason'),
                execution_metadata={
                    'escalation_decision': escalation_decision,
                    'context': context
                }
            )
            
            self.db.add(execution)
            self.db.commit()
            
            # TODO: Implement actual escalation actions
            # - Send notifications
            # - Alert human operators
            # - Trigger automated responses
            
            return {
                'success': True,
                'execution_id': execution.execution_id,
                'escalation_type': escalation_decision.get('type'),
                'target': escalation_decision.get('target')
            }
            
        except Exception as e:
            logger.error(f"Error executing escalation: {str(e)}")
            self.db.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_detector(self, detector_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new escalation detector"""
        try:
            detector = EscalationDetector(
                detector_id=f"detector_{uuid.uuid4().hex[:12]}",
                detector_name=detector_data['detector_name'],
                detector_type=detector_data['detector_type'],
                is_active=detector_data.get('is_active', True),
                priority_level=detector_data.get('priority_level', 1),
                escalation_threshold=detector_data.get('escalation_threshold', 0.7),
                failure_count_threshold=detector_data.get('failure_count_threshold', 3),
                sentiment_threshold=detector_data.get('sentiment_threshold', -0.5),
                duration_threshold_minutes=detector_data.get('duration_threshold_minutes', 15),
                complexity_threshold=detector_data.get('complexity_threshold', 0.8),
                configuration_data=detector_data.get('configuration_data', {})
            )
            
            self.db.add(detector)
            self.db.commit()
            
            return {
                'success': True,
                'detector_id': detector.detector_id,
                'message': f"Detector '{detector.detector_name}' created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error creating detector: {str(e)}")
            self.db.rollback()
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_escalation_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get escalation analytics"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get detection statistics
            total_detections = self.db.query(EscalationDetectionLog).filter(
                EscalationDetectionLog.timestamp >= start_date
            ).count()
            
            escalations_triggered = self.db.query(EscalationDetectionLog).filter(
                and_(
                    EscalationDetectionLog.timestamp >= start_date,
                    EscalationDetectionLog.escalation_triggered == True
                )
            ).count()
            
            # Get average scores
            avg_escalation_score = self.db.query(
                func.avg(EscalationDetectionLog.escalation_score)
            ).filter(
                EscalationDetectionLog.timestamp >= start_date
            ).scalar() or 0.0
            
            # Get escalation rate by type
            escalation_types = self.db.query(
                EscalationDetectionLog.escalation_type,
                func.count(EscalationDetectionLog.id)
            ).filter(
                and_(
                    EscalationDetectionLog.timestamp >= start_date,
                    EscalationDetectionLog.escalation_triggered == True
                )
            ).group_by(EscalationDetectionLog.escalation_type).all()
            
            return {
                'success': True,
                'period_days': days,
                'analytics': {
                    'total_detections': total_detections,
                    'escalations_triggered': escalations_triggered,
                    'escalation_rate': escalations_triggered / max(total_detections, 1),
                    'average_escalation_score': round(avg_escalation_score, 3),
                    'escalation_types': dict(escalation_types)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting escalation analytics: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }