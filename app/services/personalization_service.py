"""
Djobea AI Personalization Service
Intelligent user preference learning and adaptive communication system
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from loguru import logger

from app.models.personalization_models import (
    UserPreferences, ServiceHistory, BehavioralPatterns, 
    PreferenceLearningData, ContextualMemory, PersonalizationMetrics
)
from app.models.database_models import User, ServiceRequest, Conversation
from app.services.ai_service import AIService


class PersonalizationService:
    """
    Advanced personalization system with intelligent preference learning
    """
    
    def __init__(self, ai_service: Optional[AIService] = None):
        """Initialize personalization service"""
        self.ai_service = ai_service or AIService()
        self.preference_weights = {
            'communication_style': 0.3,
            'service_patterns': 0.25,
            'provider_preferences': 0.2,
            'timing_patterns': 0.15,
            'contextual_memory': 0.1
        }
    
    async def get_user_preferences(self, db: Session, user_id: int) -> UserPreferences:
        """Get or create user preferences"""
        try:
            preferences = db.query(UserPreferences).filter(
                UserPreferences.user_id == user_id
            ).first()
            
            if not preferences:
                preferences = await self.initialize_user_preferences(db, user_id)
            
            return preferences
            
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            # Return default preferences
            return UserPreferences(user_id=user_id)
    
    async def initialize_user_preferences(self, db: Session, user_id: int) -> UserPreferences:
        """Initialize preferences for new user"""
        try:
            # Get user data for initial preference setup
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Create initial preferences with smart defaults
            preferences = UserPreferences(
                user_id=user_id,
                communication_style="respectful",
                preferred_language="français",
                language_mix_preference={
                    "français": 0.7,
                    "english": 0.2,
                    "pidgin": 0.1
                },
                message_length_preference="medium",
                emoji_usage_preference="moderate",
                response_time_expectations="normal",
                confirmation_level="standard",
                update_frequency_preference="regular",
                preference_confidence=0.1,  # Low confidence initially
                interaction_count=0,
                personalization_enabled=True
            )
            
            db.add(preferences)
            db.commit()
            db.refresh(preferences)
            
            logger.info(f"Initialized preferences for user {user_id}")
            return preferences
            
        except Exception as e:
            logger.error(f"Error initializing user preferences: {e}")
            db.rollback()
            raise
    
    async def learn_from_conversation(
        self, 
        db: Session, 
        user_id: int, 
        conversation: Dict[str, Any],
        response_feedback: Optional[Dict[str, Any]] = None
    ) -> None:
        """Learn preferences from conversation patterns"""
        try:
            # Analyze conversation for preference signals
            learning_signals = await self._extract_preference_signals(
                conversation, response_feedback
            )
            
            # Store learning data
            for signal in learning_signals:
                learning_data = PreferenceLearningData(
                    user_id=user_id,
                    data_source="conversation",
                    interaction_type="message",
                    context_data=conversation,
                    signal_type=signal['type'],
                    signal_strength=signal['strength'],
                    signal_data=signal['data'],
                    preference_category=signal['category'],
                    preference_insight=signal['insight'],
                    confidence_level=signal['confidence']
                )
                db.add(learning_data)
            
            # Update preferences based on signals
            await self._update_preferences_from_signals(db, user_id, learning_signals)
            
            db.commit()
            logger.info(f"Learned from conversation for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error learning from conversation: {e}")
            db.rollback()
    
    async def learn_from_service_completion(
        self, 
        db: Session, 
        user_id: int, 
        service_request: ServiceRequest,
        outcome_data: Dict[str, Any]
    ) -> None:
        """Learn from completed service interactions"""
        try:
            # Create service history record
            service_history = ServiceHistory(
                user_id=user_id,
                service_request_id=service_request.id,
                service_type=service_request.service_type,
                service_description=service_request.description,
                location=service_request.location,
                urgency_level=service_request.urgency,
                provider_id=service_request.provider_id if hasattr(service_request, 'provider_id') else None,
                service_outcome=outcome_data.get('outcome', 'completed'),
                overall_satisfaction=outcome_data.get('satisfaction'),
                provider_rating_given=outcome_data.get('provider_rating'),
                communication_satisfaction=outcome_data.get('communication_satisfaction'),
                cost_satisfaction=outcome_data.get('cost_satisfaction'),
                would_use_again=outcome_data.get('would_use_again'),
                actual_cost=outcome_data.get('actual_cost'),
                total_messages_exchanged=outcome_data.get('message_count', 0)
            )
            
            db.add(service_history)
            
            # Extract learning insights
            insights = await self._analyze_service_outcome(service_request, outcome_data)
            service_history.lessons_learned = insights
            
            # Update behavioral patterns
            await self._update_behavioral_patterns(db, user_id, service_history)
            
            db.commit()
            logger.info(f"Learned from service completion for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error learning from service completion: {e}")
            db.rollback()
    
    async def personalize_message(
        self, 
        db: Session, 
        user_id: int, 
        base_message: str,
        context: Dict[str, Any] = None
    ) -> str:
        """Personalize message based on user preferences"""
        try:
            preferences = await self.get_user_preferences(db, user_id)
            context = context or {}
            
            # Get contextual memory for enhanced personalization
            relevant_memories = await self._get_relevant_memories(db, user_id, context)
            
            # Build personalization context
            personalization_context = {
                'communication_style': preferences.communication_style,
                'preferred_language': preferences.preferred_language,
                'language_mix': preferences.language_mix_preference,
                'message_length': preferences.message_length_preference,
                'emoji_usage': preferences.emoji_usage_preference,
                'confirmation_level': preferences.confirmation_level,
                'memories': relevant_memories,
                'context': context
            }
            
            # Use AI to personalize the message
            personalized_message = await self._apply_ai_personalization(
                base_message, personalization_context
            )
            
            # Track personalization usage
            await self._track_personalization_usage(db, user_id, base_message, personalized_message)
            
            return personalized_message
            
        except Exception as e:
            logger.error(f"Error personalizing message: {e}")
            return base_message  # Fallback to original message
    
    async def get_smart_defaults(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Get smart defaults based on user patterns"""
        try:
            preferences = await self.get_user_preferences(db, user_id)
            patterns = await self._get_behavioral_patterns(db, user_id)
            
            # Get recent service history
            recent_services = db.query(ServiceHistory).filter(
                ServiceHistory.user_id == user_id
            ).order_by(ServiceHistory.created_at.desc()).limit(10).all()
            
            smart_defaults = {
                'typical_location': self._get_most_common_location(recent_services),
                'preferred_time_slots': preferences.preferred_time_slots or [],
                'likely_service_type': self._predict_next_service_type(recent_services, patterns),
                'budget_range': self._estimate_budget_range(recent_services),
                'urgency_preference': patterns.planning_behavior if patterns else 'mixed',
                'communication_preferences': {
                    'style': preferences.communication_style,
                    'language': preferences.preferred_language,
                    'detail_level': preferences.message_length_preference
                }
            }
            
            return smart_defaults
            
        except Exception as e:
            logger.error(f"Error getting smart defaults: {e}")
            return {}
    
    async def predict_user_needs(self, db: Session, user_id: int) -> List[Dict[str, Any]]:
        """Predict future user needs based on patterns"""
        try:
            patterns = await self._get_behavioral_patterns(db, user_id)
            service_history = db.query(ServiceHistory).filter(
                ServiceHistory.user_id == user_id
            ).order_by(ServiceHistory.created_at.desc()).limit(20).all()
            
            predictions = []
            
            # Seasonal pattern predictions
            if patterns and patterns.seasonal_patterns:
                current_month = datetime.now().month
                seasonal_needs = patterns.seasonal_patterns.get(str(current_month), [])
                for need in seasonal_needs:
                    predictions.append({
                        'type': 'seasonal',
                        'service_type': need,
                        'probability': 0.7,
                        'timeframe': 'this_month',
                        'reasoning': 'Based on your seasonal patterns'
                    })
            
            # Maintenance reminders based on previous services
            for service in service_history:
                if service.service_type in ['électricité', 'plomberie']:
                    days_since = (datetime.now() - service.created_at).days
                    if days_since > 180:  # 6 months
                        predictions.append({
                            'type': 'maintenance',
                            'service_type': service.service_type,
                            'probability': 0.5,
                            'timeframe': 'soon',
                            'reasoning': 'Maintenance check recommended'
                        })
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error predicting user needs: {e}")
            return []
    
    async def get_personalization_insights(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Get insights about user personalization effectiveness"""
        try:
            preferences = await self.get_user_preferences(db, user_id)
            patterns = await self._get_behavioral_patterns(db, user_id)
            
            # Get latest metrics
            metrics = db.query(PersonalizationMetrics).filter(
                PersonalizationMetrics.user_id == user_id
            ).order_by(PersonalizationMetrics.created_at.desc()).first()
            
            insights = {
                'learning_progress': preferences.preference_confidence,
                'interaction_count': preferences.interaction_count,
                'personalization_effectiveness': metrics.personalization_accuracy if metrics else 0.0,
                'user_type': patterns.user_type if patterns else 'new_user',
                'communication_style_confidence': self._calculate_style_confidence(preferences),
                'preference_gaps': await self._identify_preference_gaps(db, user_id),
                'recommendations': await self._generate_personalization_recommendations(
                    preferences, patterns
                )
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"Error getting personalization insights: {e}")
            return {}
    
    # Private helper methods
    
    async def _extract_preference_signals(
        self, 
        conversation: Dict[str, Any],
        feedback: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Extract preference signals from conversation"""
        signals = []
        
        try:
            # Analyze message content for language preferences
            message = conversation.get('message', '')
            
            # Language preference signals
            if any(word in message.lower() for word in ['please', 'thank you', 'sir', 'madam']):
                signals.append({
                    'type': 'positive',
                    'strength': 0.7,
                    'data': {'formality_indicator': True},
                    'category': 'communication',
                    'insight': 'User prefers formal communication',
                    'confidence': 0.6
                })
            
            # Urgency pattern signals
            urgent_indicators = ['urgent', 'emergency', 'asap', 'immédiatement', 'vite']
            if any(indicator in message.lower() for indicator in urgent_indicators):
                signals.append({
                    'type': 'preference_indicator',
                    'strength': 0.8,
                    'data': {'urgency_preference': 'high'},
                    'category': 'service',
                    'insight': 'User often requires urgent services',
                    'confidence': 0.7
                })
            
            # Detail preference signals
            if len(message) > 200:
                signals.append({
                    'type': 'preference_indicator',
                    'strength': 0.6,
                    'data': {'detail_preference': 'detailed'},
                    'category': 'communication',
                    'insight': 'User provides detailed information',
                    'confidence': 0.5
                })
            
            # Add feedback-based signals if available
            if feedback:
                if feedback.get('satisfaction', 0) > 4:
                    signals.append({
                        'type': 'positive',
                        'strength': 0.9,
                        'data': {'communication_effective': True},
                        'category': 'communication',
                        'insight': 'Current communication style works well',
                        'confidence': 0.8
                    })
        
        except Exception as e:
            logger.error(f"Error extracting preference signals: {e}")
        
        return signals
    
    async def _update_preferences_from_signals(
        self, 
        db: Session, 
        user_id: int, 
        signals: List[Dict[str, Any]]
    ) -> None:
        """Update user preferences based on learning signals"""
        try:
            preferences = await self.get_user_preferences(db, user_id)
            
            for signal in signals:
                if signal['category'] == 'communication':
                    if 'formality_indicator' in signal['data']:
                        preferences.communication_style = "formal"
                    elif 'detail_preference' in signal['data']:
                        preferences.message_length_preference = signal['data']['detail_preference']
                
                elif signal['category'] == 'service':
                    if 'urgency_preference' in signal['data']:
                        if not preferences.urgency_patterns:
                            preferences.urgency_patterns = {}
                        preferences.urgency_patterns['typical_urgency'] = signal['data']['urgency_preference']
            
            # Update confidence and interaction count
            preferences.interaction_count += 1
            preferences.preference_confidence = min(
                1.0, 
                preferences.preference_confidence + (0.1 * len(signals))
            )
            preferences.last_learning_update = datetime.now()
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error updating preferences from signals: {e}")
            db.rollback()
    
    async def _analyze_service_outcome(
        self, 
        service_request: ServiceRequest, 
        outcome_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze service outcome for learning insights"""
        insights = {}
        
        try:
            # Provider preference insights
            if outcome_data.get('provider_rating', 0) >= 4:
                insights['preferred_provider_attributes'] = {
                    'high_rating_provider': True,
                    'provider_id': service_request.provider_id if hasattr(service_request, 'provider_id') else None
                }
            
            # Communication insights
            if outcome_data.get('communication_satisfaction', 0) >= 4:
                insights['effective_communication_style'] = True
            
            # Service type preferences
            if outcome_data.get('overall_satisfaction', 0) >= 4:
                insights['successful_service_type'] = service_request.service_type
            
            # Timing insights
            insights['service_timing'] = {
                'urgency_level': service_request.urgency,
                'satisfaction_with_timing': outcome_data.get('timing_satisfaction', 3)
            }
        
        except Exception as e:
            logger.error(f"Error analyzing service outcome: {e}")
        
        return insights
    
    async def _update_behavioral_patterns(
        self, 
        db: Session, 
        user_id: int, 
        service_history: ServiceHistory
    ) -> None:
        """Update behavioral patterns based on service history"""
        try:
            patterns = await self._get_behavioral_patterns(db, user_id)
            
            if not patterns:
                patterns = BehavioralPatterns(
                    user_id=user_id,
                    user_type="new_user",
                    activity_level="low",
                    analysis_data_points=0
                )
                db.add(patterns)
            
            # Update service patterns
            if not patterns.most_requested_services:
                patterns.most_requested_services = {}
            
            service_type = service_history.service_type
            current_count = patterns.most_requested_services.get(service_type, 0)
            patterns.most_requested_services[service_type] = current_count + 1
            
            # Update timing patterns
            hour = service_history.created_at.hour
            if not patterns.time_of_day_patterns:
                patterns.time_of_day_patterns = {}
            patterns.time_of_day_patterns[str(hour)] = patterns.time_of_day_patterns.get(str(hour), 0) + 1
            
            # Update user classification
            patterns.analysis_data_points += 1
            if patterns.analysis_data_points >= 10:
                patterns.user_type = "power_user"
            elif patterns.analysis_data_points >= 5:
                patterns.user_type = "regular_user"
            
            patterns.last_pattern_analysis = datetime.now()
            db.commit()
            
        except Exception as e:
            logger.error(f"Error updating behavioral patterns: {e}")
            db.rollback()
    
    async def _get_relevant_memories(
        self, 
        db: Session, 
        user_id: int, 
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get relevant contextual memories for personalization"""
        try:
            # Get recent and important memories
            memories = db.query(ContextualMemory).filter(
                ContextualMemory.user_id == user_id,
                ContextualMemory.importance_score > 0.5
            ).order_by(
                ContextualMemory.importance_score.desc(),
                ContextualMemory.last_accessed.desc()
            ).limit(5).all()
            
            relevant_memories = []
            for memory in memories:
                # Update access frequency
                memory.access_frequency += 1
                memory.last_accessed = datetime.now()
                
                relevant_memories.append({
                    'title': memory.memory_title,
                    'content': memory.memory_content,
                    'emotional_context': memory.emotional_context,
                    'importance': memory.importance_score
                })
            
            db.commit()
            return relevant_memories
            
        except Exception as e:
            logger.error(f"Error getting relevant memories: {e}")
            return []
    
    async def _apply_ai_personalization(
        self, 
        base_message: str, 
        context: Dict[str, Any]
    ) -> str:
        """Apply AI-powered personalization to message"""
        try:
            personalization_prompt = f"""
            Personalize this message for a user with these preferences:
            
            Base message: {base_message}
            
            User preferences:
            - Communication style: {context.get('communication_style', 'respectful')}
            - Preferred language: {context.get('preferred_language', 'français')}
            - Message length preference: {context.get('message_length', 'medium')}
            - Emoji usage: {context.get('emoji_usage', 'moderate')}
            - Confirmation level: {context.get('confirmation_level', 'standard')}
            
            Relevant memories: {context.get('memories', [])}
            
            Instructions:
            1. Adapt the tone and formality to match communication style
            2. Use appropriate language mix if specified
            3. Adjust message length based on preference
            4. Include relevant personal context from memories
            5. Maintain the core message meaning
            6. Use culturally appropriate expressions for Cameroon context
            
            Return only the personalized message.
            """
            
            # For now, return the base message with basic personalization
            # TODO: Implement proper AI personalization when AIService method is available
            return base_message
            
        except Exception as e:
            logger.error(f"Error applying AI personalization: {e}")
            return base_message
    
    async def _get_behavioral_patterns(self, db: Session, user_id: int) -> Optional[BehavioralPatterns]:
        """Get behavioral patterns for user"""
        try:
            return db.query(BehavioralPatterns).filter(
                BehavioralPatterns.user_id == user_id
            ).first()
        except Exception as e:
            logger.error(f"Error getting behavioral patterns: {e}")
            return None
    
    def _get_most_common_location(self, service_history: List[ServiceHistory]) -> Optional[str]:
        """Get most commonly used location"""
        if not service_history:
            return None
        
        location_counts = {}
        for service in service_history:
            location = service.location
            location_counts[location] = location_counts.get(location, 0) + 1
        
        return max(location_counts, key=location_counts.get) if location_counts else None
    
    def _predict_next_service_type(
        self, 
        service_history: List[ServiceHistory], 
        patterns: Optional[BehavioralPatterns]
    ) -> Optional[str]:
        """Predict most likely next service type"""
        if patterns and patterns.most_requested_services:
            return max(patterns.most_requested_services, key=patterns.most_requested_services.get)
        elif service_history:
            service_counts = {}
            for service in service_history:
                service_type = service.service_type
                service_counts[service_type] = service_counts.get(service_type, 0) + 1
            return max(service_counts, key=service_counts.get) if service_counts else None
        return None
    
    def _estimate_budget_range(self, service_history: List[ServiceHistory]) -> Dict[str, float]:
        """Estimate budget range based on history"""
        if not service_history:
            return {}
        
        costs = [s.actual_cost for s in service_history if s.actual_cost]
        if not costs:
            return {}
        
        return {
            'min': min(costs),
            'max': max(costs),
            'average': sum(costs) / len(costs)
        }
    
    def _calculate_style_confidence(self, preferences: UserPreferences) -> float:
        """Calculate confidence in communication style preference"""
        base_confidence = preferences.preference_confidence
        interaction_bonus = min(0.3, preferences.interaction_count * 0.01)
        return min(1.0, base_confidence + interaction_bonus)
    
    async def _identify_preference_gaps(self, db: Session, user_id: int) -> List[str]:
        """Identify areas where we need more preference data"""
        preferences = await self.get_user_preferences(db, user_id)
        gaps = []
        
        if not preferences.typical_locations:
            gaps.append("location_preferences")
        if not preferences.preferred_time_slots:
            gaps.append("timing_preferences")
        if not preferences.budget_preferences:
            gaps.append("budget_preferences")
        if preferences.preference_confidence < 0.5:
            gaps.append("communication_style")
        
        return gaps
    
    async def _generate_personalization_recommendations(
        self, 
        preferences: UserPreferences, 
        patterns: Optional[BehavioralPatterns]
    ) -> List[str]:
        """Generate recommendations for improving personalization"""
        recommendations = []
        
        if preferences.preference_confidence < 0.3:
            recommendations.append("Collect more interaction data to improve personalization")
        
        if preferences.interaction_count < 5:
            recommendations.append("Need more conversations to learn communication preferences")
        
        if not preferences.typical_locations:
            recommendations.append("Learn user's common locations for faster service requests")
        
        if patterns and patterns.user_type == "power_user" and not preferences.budget_preferences:
            recommendations.append("Learn budget preferences for better service matching")
        
        return recommendations
    
    async def _track_personalization_usage(
        self, 
        db: Session, 
        user_id: int, 
        original_message: str, 
        personalized_message: str
    ) -> None:
        """Track usage of personalization for analytics"""
        try:
            # Store the personalization usage for metrics
            learning_data = PreferenceLearningData(
                user_id=user_id,
                data_source="personalization",
                interaction_type="message_adaptation",
                context_data={
                    'original': original_message,
                    'personalized': personalized_message
                },
                signal_type="neutral",
                signal_strength=0.5,
                signal_data={'personalization_applied': True},
                preference_category="communication",
                confidence_level=0.7,
                processed=True
            )
            db.add(learning_data)
            db.commit()
            
        except Exception as e:
            logger.error(f"Error tracking personalization usage: {e}")
            db.rollback()
    
    async def get_smart_suggestions(
        self, 
        db: Session, 
        user_id: int, 
        current_context: Dict[str, Any] = None
    ) -> List[str]:
        """Generate smart suggestions based on user patterns and context"""
        try:
            preferences = await self.get_user_preferences(db, user_id)
            patterns = await self._get_behavioral_patterns(db, user_id)
            context = current_context or {}
            
            suggestions = []
            
            # Time-based suggestions
            current_hour = datetime.now().hour
            if 8 <= current_hour <= 10:
                suggestions.append("Besoin d'une intervention ce matin ?")
            elif 17 <= current_hour <= 19:
                suggestions.append("Intervention prévue pour ce soir ?")
            
            # Pattern-based suggestions
            if patterns:
                most_common_service = patterns.service_patterns.get('most_common')
                if most_common_service:
                    suggestions.append(f"Nouveau problème de {most_common_service} ?")
                
                if patterns.urgency_patterns.get('usually_urgent', False):
                    suggestions.append("Intervention urgente comme d'habitude ?")
                else:
                    suggestions.append("Quand souhaitez-vous l'intervention ?")
            
            # Location-based suggestions
            if preferences.typical_locations:
                common_location = list(preferences.typical_locations.keys())[0]
                suggestions.append(f"C'est toujours à {common_location} ?")
            
            # Service completion reminders
            recent_services = self._get_recent_service_history(db, user_id, days=30)
            if recent_services:
                for service in recent_services:
                    if service.service_type == "plomberie" and service.created_at < (datetime.now() - timedelta(days=90)):
                        suggestions.append("Vérification de plomberie recommandée")
                    elif service.service_type == "électricité" and service.created_at < (datetime.now() - timedelta(days=180)):
                        suggestions.append("Maintenance électrique conseillée")
            
            return suggestions[:3]  # Return top 3 suggestions
            
        except Exception as e:
            logger.error(f"Error generating smart suggestions: {e}")
            return []
    
    async def predict_maintenance_needs(
        self, 
        db: Session, 
        user_id: int
    ) -> List[Dict[str, Any]]:
        """Predict future maintenance needs based on service history"""
        try:
            service_history = self._get_recent_service_history(db, user_id, days=365)
            predictions = []
            
            for service in service_history:
                if service.service_type == "plomberie":
                    # Plumbing typically needs maintenance every 6 months
                    next_maintenance = service.created_at + timedelta(days=180)
                    if next_maintenance <= datetime.now() + timedelta(days=30):
                        predictions.append({
                            'service_type': 'plomberie',
                            'predicted_date': next_maintenance,
                            'reason': 'Maintenance préventive recommandée',
                            'confidence': 0.8
                        })
                
                elif service.service_type == "électricité":
                    # Electrical typically needs maintenance every year
                    next_maintenance = service.created_at + timedelta(days=365)
                    if next_maintenance <= datetime.now() + timedelta(days=30):
                        predictions.append({
                            'service_type': 'électricité',
                            'predicted_date': next_maintenance,
                            'reason': 'Contrôle électrique annuel',
                            'confidence': 0.7
                        })
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error predicting maintenance needs: {e}")
            return []
    
    async def adapt_communication_complexity(
        self, 
        db: Session, 
        user_id: int, 
        message: str, 
        user_comprehension_level: float = None
    ) -> str:
        """Adapt message complexity based on user comprehension patterns"""
        try:
            preferences = await self.get_user_preferences(db, user_id)
            patterns = await self._get_behavioral_patterns(db, user_id)
            
            # Determine complexity level
            if user_comprehension_level:
                complexity = user_comprehension_level
            elif patterns and patterns.interaction_patterns:
                complexity = patterns.interaction_patterns.get('comprehension_level', 0.5)
            else:
                complexity = 0.5  # Default medium complexity
            
            # Adapt message based on complexity
            if complexity < 0.3:  # Simple communication needed
                # Use simpler language and shorter sentences
                simplified_prompt = f"""
                Simplify this message for easy understanding:
                Original: {message}
                
                Use:
                - Simple words only
                - Short sentences  
                - Clear instructions
                - Avoid technical terms
                """
                
                simplified_message = await self.ai_service.process_prompt(simplified_prompt)
                return simplified_message
                
            elif complexity > 0.7:  # Can handle detailed communication
                # Add more technical details and context
                detailed_prompt = f"""
                Enhance this message with more technical detail:
                Original: {message}
                
                Add:
                - Technical context
                - Process explanations
                - Timeline details
                - Comprehensive information
                """
                
                detailed_message = await self.ai_service.process_prompt(detailed_prompt)
                return detailed_message
            
            else:
                # Medium complexity - return original message
                return message
                
        except Exception as e:
            logger.error(f"Error adapting communication complexity: {e}")
            return message
    
    def _get_recent_service_history(
        self, 
        db: Session, 
        user_id: int, 
        days: int = 90
    ) -> List[ServiceHistory]:
        """Get recent service history for a user"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            return db.query(ServiceHistory).filter(
                ServiceHistory.user_id == user_id,
                ServiceHistory.created_at >= cutoff_date
            ).order_by(ServiceHistory.created_at.desc()).all()
        except Exception as e:
            logger.error(f"Error getting service history: {e}")
            return []