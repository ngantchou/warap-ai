"""
Complexity Scoring Service with Machine Learning
Advanced complexity analysis and prediction for escalation detection
"""
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from loguru import logger

from app.models.escalation_detection_models import (
    ComplexityScoring, EscalationPattern, EscalationDetectionLog
)

class ComplexityScoringService:
    """Service for complexity scoring and pattern learning"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # Technical complexity indicators
        self.technical_patterns = {
            'plomberie': [
                'pression', 'débit', 'soudure', 'raccord', 'étanchéité',
                'évacuation', 'ventilation', 'chaudière', 'circuit'
            ],
            'électricité': [
                'voltage', 'ampérage', 'disjoncteur', 'différentiel', 'terre',
                'phase', 'neutre', 'circuit', 'installation', 'norme'
            ],
            'électroménager': [
                'thermostat', 'compresseur', 'résistance', 'moteur', 'programmateur',
                'carte électronique', 'capteur', 'diagnostic', 'pièce détachée'
            ]
        }
        
        # Complexity level indicators
        self.complexity_levels = {
            'simple': ['changer', 'remplacer', 'réparer', 'nettoyer', 'déboucher'],
            'medium': ['installer', 'configurer', 'diagnostiquer', 'vérifier', 'régler'],
            'complex': ['refaire', 'restructurer', 'concevoir', 'adapter', 'modifier'],
            'expert': ['système', 'réseau', 'programmation', 'automatisation', 'intégration']
        }
        
        # Emotional complexity indicators
        self.emotional_complexity = {
            'urgency': ['urgent', 'immédiat', 'rapide', 'vite', 'maintenant'],
            'stress': ['stressé', 'inquiet', 'paniqué', 'anxieux', 'préoccupé'],
            'frustration': ['frustré', 'énervé', 'agacé', 'marre', 'impatient'],
            'confusion': ['confus', 'perdu', 'comprends pas', 'difficile', 'compliqué']
        }
    
    def calculate_complexity_score(self, message: str, conversation_history: List[Dict],
                                 context: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive complexity score"""
        try:
            # Initialize scoring components
            scoring_data = {
                'message_content': message,
                'conversation_length': len(conversation_history),
                'service_type': context.get('service_type', ''),
                'zone': context.get('zone', ''),
                'user_id': context.get('user_id', ''),
                'session_id': context.get('session_id', ''),
                'request_id': context.get('request_id', '')
            }
            
            # Calculate individual complexity factors
            linguistic_complexity = self._calculate_linguistic_complexity(message)
            technical_complexity = self._calculate_technical_complexity(message, context)
            behavioral_complexity = self._calculate_behavioral_complexity(conversation_history)
            emotional_complexity = self._calculate_emotional_complexity(message, conversation_history)
            contextual_complexity = self._calculate_contextual_complexity(context)
            
            # Calculate overall complexity
            complexity_components = {
                'linguistic': linguistic_complexity,
                'technical': technical_complexity,
                'behavioral': behavioral_complexity,
                'emotional': emotional_complexity,
                'contextual': contextual_complexity
            }
            
            # Weighted average
            weights = {
                'linguistic': 0.15,
                'technical': 0.25,
                'behavioral': 0.25,
                'emotional': 0.20,
                'contextual': 0.15
            }
            
            overall_complexity = sum(
                complexity_components[factor] * weights[factor]
                for factor in weights
            )
            
            # Calculate escalation probability
            escalation_probability = self._calculate_escalation_probability(
                overall_complexity, complexity_components, context
            )
            
            # Generate predictions
            predictions = self._generate_predictions(
                overall_complexity, complexity_components, context
            )
            
            # Store scoring data
            scoring_record = self._store_complexity_scoring(
                scoring_data, complexity_components, overall_complexity,
                escalation_probability, predictions
            )
            
            return {
                'success': True,
                'complexity_score': overall_complexity,
                'escalation_probability': escalation_probability,
                'complexity_components': complexity_components,
                'predictions': predictions,
                'scoring_id': scoring_record.score_id if scoring_record else None
            }
            
        except Exception as e:
            logger.error(f"Error calculating complexity score: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'complexity_score': 0.0,
                'escalation_probability': 0.0
            }
    
    def _calculate_linguistic_complexity(self, message: str) -> float:
        """Calculate linguistic complexity of message"""
        if not message:
            return 0.0
        
        factors = {
            'message_length': min(len(message) / 200, 1.0),
            'word_count': min(len(message.split()) / 50, 1.0),
            'sentence_count': min(message.count('.') + message.count('!') + message.count('?'), 5) / 5,
            'question_density': min(message.count('?') / max(len(message.split()), 1), 1.0),
            'punctuation_density': min(len([c for c in message if c in '.,!?;:']) / max(len(message), 1), 1.0)
        }
        
        # Check for complex sentence structures
        complex_structures = ['parce que', 'cependant', 'néanmoins', 'toutefois', 'en revanche']
        factors['complex_structures'] = sum(1 for struct in complex_structures if struct in message.lower()) / 5
        
        return sum(factors.values()) / len(factors)
    
    def _calculate_technical_complexity(self, message: str, context: Dict[str, Any]) -> float:
        """Calculate technical complexity based on service type and technical terms"""
        message_lower = message.lower()
        service_type = context.get('service_type', '')
        
        # Base complexity by service type
        service_base_complexity = {
            'plomberie': 0.7,
            'électricité': 0.8,
            'électroménager': 0.6,
            'nettoyage': 0.3,
            'jardinage': 0.4
        }
        
        base_complexity = service_base_complexity.get(service_type, 0.5)
        
        # Count technical terms
        technical_terms = self.technical_patterns.get(service_type, [])
        technical_count = sum(1 for term in technical_terms if term in message_lower)
        
        # Check complexity level indicators
        complexity_multiplier = 1.0
        for level, indicators in self.complexity_levels.items():
            if any(indicator in message_lower for indicator in indicators):
                if level == 'simple':
                    complexity_multiplier = 0.8
                elif level == 'medium':
                    complexity_multiplier = 1.0
                elif level == 'complex':
                    complexity_multiplier = 1.3
                elif level == 'expert':
                    complexity_multiplier = 1.6
                break
        
        # Calculate final technical complexity
        technical_score = base_complexity * complexity_multiplier
        technical_score += min(technical_count / 5, 0.3)  # Boost for technical terms
        
        return min(technical_score, 1.0)
    
    def _calculate_behavioral_complexity(self, conversation_history: List[Dict]) -> float:
        """Calculate behavioral complexity from conversation patterns"""
        if not conversation_history:
            return 0.0
        
        factors = {
            'conversation_length': min(len(conversation_history) / 15, 1.0),
            'message_frequency': self._calculate_message_frequency(conversation_history),
            'topic_coherence': self._calculate_topic_coherence(conversation_history),
            'repetition_level': self._calculate_repetition_level(conversation_history),
            'clarification_requests': self._count_clarification_requests(conversation_history)
        }
        
        return sum(factors.values()) / len(factors)
    
    def _calculate_emotional_complexity(self, message: str, conversation_history: List[Dict]) -> float:
        """Calculate emotional complexity and stress indicators"""
        message_lower = message.lower()
        
        # Current message emotional indicators
        emotion_scores = {}
        for emotion, indicators in self.emotional_complexity.items():
            score = sum(1 for indicator in indicators if indicator in message_lower)
            emotion_scores[emotion] = min(score / 3, 1.0)
        
        # Historical emotional trend
        emotional_trend = self._calculate_emotional_trend(conversation_history)
        
        # Calculate overall emotional complexity
        current_emotion = sum(emotion_scores.values()) / len(emotion_scores)
        
        return min((current_emotion + emotional_trend) / 2, 1.0)
    
    def _calculate_contextual_complexity(self, context: Dict[str, Any]) -> float:
        """Calculate contextual complexity based on request context"""
        factors = {
            'urgency_level': self._urgency_to_score(context.get('urgency_level', 'normal')),
            'zone_complexity': self._zone_to_complexity(context.get('zone', '')),
            'time_of_day': self._time_to_complexity(datetime.now().hour),
            'user_history': self._user_history_complexity(context.get('user_id', ''))
        }
        
        return sum(factors.values()) / len(factors)
    
    def _calculate_escalation_probability(self, overall_complexity: float,
                                       complexity_components: Dict[str, float],
                                       context: Dict[str, Any]) -> float:
        """Calculate probability of escalation based on complexity"""
        # Base probability from overall complexity
        base_probability = overall_complexity * 0.6
        
        # Boost factors
        boosts = 0.0
        
        # High emotional complexity boost
        if complexity_components['emotional'] > 0.7:
            boosts += 0.2
        
        # High technical complexity boost
        if complexity_components['technical'] > 0.8:
            boosts += 0.15
        
        # High behavioral complexity boost
        if complexity_components['behavioral'] > 0.8:
            boosts += 0.1
        
        # Urgency boost
        if context.get('urgency_level') == 'urgent':
            boosts += 0.15
        
        escalation_probability = base_probability + boosts
        
        return min(escalation_probability, 1.0)
    
    def _generate_predictions(self, overall_complexity: float,
                            complexity_components: Dict[str, float],
                            context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate predictions based on complexity analysis"""
        # Predict resolution time
        base_resolution_time = 15  # minutes
        
        if overall_complexity < 0.3:
            predicted_time = base_resolution_time
        elif overall_complexity < 0.6:
            predicted_time = base_resolution_time * 2
        elif overall_complexity < 0.8:
            predicted_time = base_resolution_time * 3
        else:
            predicted_time = base_resolution_time * 4
        
        # Predict escalation type
        escalation_type = 'none'
        if overall_complexity > 0.7:
            if complexity_components['emotional'] > 0.8:
                escalation_type = 'emotional'
            elif complexity_components['technical'] > 0.8:
                escalation_type = 'technical'
            elif complexity_components['behavioral'] > 0.8:
                escalation_type = 'behavioral'
            else:
                escalation_type = 'general'
        
        # Suggest action
        if overall_complexity < 0.4:
            suggested_action = 'continue_conversation'
        elif overall_complexity < 0.7:
            suggested_action = 'provide_additional_support'
        else:
            suggested_action = 'consider_escalation'
        
        return {
            'predicted_resolution_time': predicted_time,
            'predicted_escalation_type': escalation_type,
            'suggested_action': suggested_action,
            'confidence_score': min(overall_complexity + 0.2, 1.0)
        }
    
    def _calculate_message_frequency(self, history: List[Dict]) -> float:
        """Calculate message frequency as complexity indicator"""
        if len(history) < 2:
            return 0.0
        
        timestamps = [entry.get('timestamp', datetime.now()) for entry in history]
        
        # Calculate average time between messages
        intervals = []
        for i in range(1, len(timestamps)):
            if isinstance(timestamps[i], str):
                ts1 = datetime.fromisoformat(timestamps[i].replace('Z', '+00:00'))
            else:
                ts1 = timestamps[i]
            
            if isinstance(timestamps[i-1], str):
                ts2 = datetime.fromisoformat(timestamps[i-1].replace('Z', '+00:00'))
            else:
                ts2 = timestamps[i-1]
            
            interval = abs((ts1 - ts2).total_seconds())
            intervals.append(interval)
        
        if not intervals:
            return 0.0
        
        avg_interval = sum(intervals) / len(intervals)
        
        # High frequency (low intervals) indicates complexity
        if avg_interval < 30:  # Less than 30 seconds
            return 0.9
        elif avg_interval < 60:  # Less than 1 minute
            return 0.6
        elif avg_interval < 120:  # Less than 2 minutes
            return 0.3
        else:
            return 0.1
    
    def _calculate_topic_coherence(self, history: List[Dict]) -> float:
        """Calculate topic coherence as complexity indicator"""
        if len(history) < 2:
            return 0.0
        
        # Simple topic coherence based on keyword overlap
        messages = [entry.get('message', '') for entry in history]
        
        coherence_scores = []
        for i in range(1, len(messages)):
            words1 = set(messages[i-1].lower().split())
            words2 = set(messages[i].lower().split())
            
            if words1 and words2:
                overlap = len(words1.intersection(words2))
                union = len(words1.union(words2))
                coherence = overlap / union if union > 0 else 0
                coherence_scores.append(coherence)
        
        if not coherence_scores:
            return 0.0
        
        avg_coherence = sum(coherence_scores) / len(coherence_scores)
        
        # Low coherence indicates complexity
        return 1.0 - avg_coherence
    
    def _calculate_repetition_level(self, history: List[Dict]) -> float:
        """Calculate repetition level as complexity indicator"""
        if len(history) < 2:
            return 0.0
        
        messages = [entry.get('message', '').lower() for entry in history]
        
        # Count similar messages
        repetitions = 0
        for i in range(len(messages)):
            for j in range(i + 1, len(messages)):
                similarity = self._calculate_similarity(messages[i], messages[j])
                if similarity > 0.6:
                    repetitions += 1
        
        return min(repetitions / 5, 1.0)
    
    def _count_clarification_requests(self, history: List[Dict]) -> float:
        """Count clarification requests as complexity indicator"""
        clarification_patterns = [
            'que voulez-vous dire', 'pouvez-vous expliquer', 'je ne comprends pas',
            'clarifier', 'préciser', 'détailler', 'comment', 'pourquoi', 'où exactement'
        ]
        
        clarifications = 0
        for entry in history:
            message = entry.get('message', '').lower()
            for pattern in clarification_patterns:
                if pattern in message:
                    clarifications += 1
                    break
        
        return min(clarifications / 10, 1.0)
    
    def _calculate_emotional_trend(self, history: List[Dict]) -> float:
        """Calculate emotional trend over conversation"""
        if not history:
            return 0.0
        
        emotion_scores = []
        for entry in history:
            message = entry.get('message', '').lower()
            
            # Count emotional indicators
            emotion_count = 0
            for indicators in self.emotional_complexity.values():
                emotion_count += sum(1 for indicator in indicators if indicator in message)
            
            emotion_scores.append(emotion_count)
        
        if len(emotion_scores) < 2:
            return 0.0
        
        # Calculate trend (increasing emotion = higher complexity)
        trend = (emotion_scores[-1] - emotion_scores[0]) / len(emotion_scores)
        
        return min(max(trend, 0) / 5, 1.0)
    
    def _urgency_to_score(self, urgency_level: str) -> float:
        """Convert urgency level to complexity score"""
        urgency_scores = {
            'low': 0.2,
            'normal': 0.4,
            'high': 0.7,
            'urgent': 0.9
        }
        
        return urgency_scores.get(urgency_level, 0.4)
    
    def _zone_to_complexity(self, zone: str) -> float:
        """Convert zone to complexity score"""
        # Some zones might have more complex service requirements
        zone_complexity = {
            'Bonamoussadi': 0.5,
            'Akwa': 0.7,
            'Deido': 0.6,
            'Makepe': 0.5,
            'Bonapriso': 0.8
        }
        
        return zone_complexity.get(zone, 0.5)
    
    def _time_to_complexity(self, hour: int) -> float:
        """Convert time of day to complexity score"""
        # Late night/early morning requests might be more complex
        if 22 <= hour or hour <= 6:
            return 0.8
        elif 18 <= hour <= 21:
            return 0.6
        else:
            return 0.4
    
    def _user_history_complexity(self, user_id: str) -> float:
        """Calculate user history complexity"""
        if not user_id:
            return 0.5
        
        # Get user's recent escalations
        recent_escalations = self.db.query(EscalationDetectionLog).filter(
            and_(
                EscalationDetectionLog.user_id == user_id,
                EscalationDetectionLog.timestamp >= datetime.utcnow() - timedelta(days=30),
                EscalationDetectionLog.escalation_triggered == True
            )
        ).count()
        
        # Users with recent escalations might have higher complexity
        return min(recent_escalations / 5, 1.0)
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _store_complexity_scoring(self, scoring_data: Dict[str, Any],
                                complexity_components: Dict[str, float],
                                overall_complexity: float, escalation_probability: float,
                                predictions: Dict[str, Any]) -> Optional[ComplexityScoring]:
        """Store complexity scoring in database"""
        try:
            scoring_record = ComplexityScoring(
                score_id=f"complexity_{uuid.uuid4().hex[:12]}",
                user_id=scoring_data.get('user_id', ''),
                session_id=scoring_data.get('session_id', ''),
                request_id=scoring_data.get('request_id', ''),
                conversation_length=scoring_data.get('conversation_length', 0),
                service_type=scoring_data.get('service_type', ''),
                overall_complexity=overall_complexity,
                escalation_probability=escalation_probability,
                predicted_resolution_time=predictions.get('predicted_resolution_time'),
                predicted_escalation_type=predictions.get('predicted_escalation_type'),
                suggested_action=predictions.get('suggested_action'),
                confidence_score=predictions.get('confidence_score', 0.0),
                scoring_metadata={
                    'complexity_components': complexity_components,
                    'predictions': predictions,
                    'message_content': scoring_data.get('message_content', '')
                }
            )
            
            self.db.add(scoring_record)
            self.db.commit()
            
            return scoring_record
            
        except Exception as e:
            logger.error(f"Error storing complexity scoring: {str(e)}")
            self.db.rollback()
            return None
    
    def get_complexity_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get complexity scoring analytics"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get scoring statistics
            total_scores = self.db.query(ComplexityScoring).filter(
                ComplexityScoring.created_at >= start_date
            ).count()
            
            # Average complexity by service type
            service_complexity = self.db.query(
                ComplexityScoring.service_type,
                func.avg(ComplexityScoring.overall_complexity).label('avg_complexity')
            ).filter(
                ComplexityScoring.created_at >= start_date
            ).group_by(ComplexityScoring.service_type).all()
            
            # Escalation prediction accuracy
            accurate_predictions = self.db.query(ComplexityScoring).filter(
                and_(
                    ComplexityScoring.created_at >= start_date,
                    ComplexityScoring.model_accuracy.isnot(None),
                    ComplexityScoring.model_accuracy > 0.7
                )
            ).count()
            
            prediction_accuracy = accurate_predictions / max(total_scores, 1)
            
            return {
                'success': True,
                'period_days': days,
                'analytics': {
                    'total_scores': total_scores,
                    'service_complexity': dict(service_complexity),
                    'prediction_accuracy': prediction_accuracy,
                    'average_complexity': self.db.query(
                        func.avg(ComplexityScoring.overall_complexity)
                    ).filter(
                        ComplexityScoring.created_at >= start_date
                    ).scalar() or 0.0
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting complexity analytics: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }