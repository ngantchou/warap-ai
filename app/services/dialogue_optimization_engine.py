"""
Dialogue Optimization Engine - Advanced conversation efficiency optimization
Reduces turn count, improves extraction efficiency, and personalizes dialogue flow
"""
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime, timedelta
import json
import statistics

from app.services.dialogue_flow_manager import DialogueContext, InformationField, InformationPriority
from app.services.ai_service import AIService
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class OptimizationStrategy(Enum):
    """Optimization strategies"""
    MULTI_FIELD_EXTRACTION = "multi_field_extraction"
    CONTEXT_AWARE_QUESTIONING = "context_aware_questioning"
    PREDICTIVE_COMPLETION = "predictive_completion"
    SMART_SUGGESTIONS = "smart_suggestions"
    ADAPTIVE_FLOW = "adaptive_flow"
    PRIORITY_REORDERING = "priority_reordering"
    CONVERSATION_COMPRESSION = "conversation_compression"

class UserType(Enum):
    """User behavior types for personalization"""
    DETAILED_RESPONDER = "detailed_responder"      # Provides lots of info
    BRIEF_RESPONDER = "brief_responder"            # Gives short answers
    QUESTION_AVOIDER = "question_avoider"          # Tries to avoid questions
    CONTEXT_PROVIDER = "context_provider"          # Gives context naturally
    IMPATIENT_USER = "impatient_user"             # Wants quick service
    METHODICAL_USER = "methodical_user"           # Prefers step-by-step

@dataclass
class OptimizationMetrics:
    """Metrics for optimization tracking"""
    original_estimated_turns: int
    optimized_estimated_turns: int
    actual_turns: int
    information_density: float  # Info per turn
    extraction_accuracy: float
    user_satisfaction_score: float
    optimization_effectiveness: float
    strategies_applied: List[OptimizationStrategy] = field(default_factory=list)

@dataclass
class ConversationPattern:
    """User conversation patterns"""
    avg_response_length: float
    response_completeness: float
    question_answering_rate: float
    topic_consistency: float
    interruption_frequency: float
    preferred_information_order: List[str] = field(default_factory=list)
    response_style: str = "neutral"

@dataclass
class OptimizationRecommendation:
    """Optimization recommendation"""
    strategy: OptimizationStrategy
    confidence: float
    expected_turn_reduction: int
    description: str
    implementation_actions: List[str] = field(default_factory=list)

class DialogueOptimizationEngine:
    """
    Advanced dialogue optimization engine for efficient conversations
    """
    
    def __init__(self):
        self.ai_service = AIService()
        
        # Optimization strategies
        self.optimization_strategies = self._initialize_optimization_strategies()
        
        # User profile templates
        self.user_type_profiles = self._initialize_user_type_profiles()
        
        # Optimization metrics
        self.metrics = {
            "total_optimizations": 0,
            "successful_optimizations": 0,
            "average_turn_reduction": 0.0,
            "optimization_accuracy": 0.0,
            "user_satisfaction_improvement": 0.0
        }
        
        # Learning data
        self.conversation_history = []
        self.optimization_history = []
    
    def _initialize_optimization_strategies(self) -> Dict[OptimizationStrategy, Dict[str, Any]]:
        """Initialize optimization strategies"""
        return {
            OptimizationStrategy.MULTI_FIELD_EXTRACTION: {
                "description": "Extract multiple information fields from single response",
                "applicable_contexts": ["service_collection", "location_collection", "description_collection"],
                "expected_reduction": 2,
                "confidence_threshold": 0.8,
                "implementation": {
                    "combine_questions": True,
                    "use_context_clues": True,
                    "parallel_validation": True
                }
            },
            
            OptimizationStrategy.CONTEXT_AWARE_QUESTIONING: {
                "description": "Use previous information to ask more targeted questions",
                "applicable_contexts": ["any"],
                "expected_reduction": 1,
                "confidence_threshold": 0.7,
                "implementation": {
                    "reference_previous_info": True,
                    "suggest_likely_answers": True,
                    "skip_redundant_questions": True
                }
            },
            
            OptimizationStrategy.PREDICTIVE_COMPLETION: {
                "description": "Predict likely answers based on patterns",
                "applicable_contexts": ["urgency_collection", "contact_collection"],
                "expected_reduction": 1,
                "confidence_threshold": 0.8,
                "implementation": {
                    "auto_suggest_predictions": True,
                    "confidence_based_completion": True,
                    "user_confirmation": True
                }
            },
            
            OptimizationStrategy.SMART_SUGGESTIONS: {
                "description": "Provide intelligent suggestions to speed up input",
                "applicable_contexts": ["any"],
                "expected_reduction": 1,
                "confidence_threshold": 0.6,
                "implementation": {
                    "contextual_suggestions": True,
                    "one_click_completion": True,
                    "smart_defaults": True
                }
            },
            
            OptimizationStrategy.ADAPTIVE_FLOW: {
                "description": "Adapt conversation flow based on user behavior",
                "applicable_contexts": ["flow_control"],
                "expected_reduction": 2,
                "confidence_threshold": 0.9,
                "implementation": {
                    "skip_unnecessary_steps": True,
                    "reorder_questions": True,
                    "personalize_approach": True
                }
            },
            
            OptimizationStrategy.PRIORITY_REORDERING: {
                "description": "Reorder information collection based on user patterns",
                "applicable_contexts": ["any"],
                "expected_reduction": 1,
                "confidence_threshold": 0.7,
                "implementation": {
                    "analyze_user_preference": True,
                    "dynamic_prioritization": True,
                    "efficient_sequencing": True
                }
            },
            
            OptimizationStrategy.CONVERSATION_COMPRESSION: {
                "description": "Compress multiple conversation turns into fewer exchanges",
                "applicable_contexts": ["any"],
                "expected_reduction": 3,
                "confidence_threshold": 0.8,
                "implementation": {
                    "batch_questions": True,
                    "parallel_processing": True,
                    "smart_bundling": True
                }
            }
        }
    
    def _initialize_user_type_profiles(self) -> Dict[UserType, Dict[str, Any]]:
        """Initialize user type profiles for personalization"""
        return {
            UserType.DETAILED_RESPONDER: {
                "characteristics": {
                    "avg_response_length": 100,
                    "information_density": 0.8,
                    "question_answering_rate": 0.9,
                    "prefers_open_questions": True
                },
                "optimization_preferences": [
                    OptimizationStrategy.MULTI_FIELD_EXTRACTION,
                    OptimizationStrategy.CONVERSATION_COMPRESSION
                ],
                "questioning_style": "open_ended",
                "suggested_approach": "Ask broader questions, extract multiple fields"
            },
            
            UserType.BRIEF_RESPONDER: {
                "characteristics": {
                    "avg_response_length": 20,
                    "information_density": 0.4,
                    "question_answering_rate": 0.7,
                    "prefers_specific_questions": True
                },
                "optimization_preferences": [
                    OptimizationStrategy.SMART_SUGGESTIONS,
                    OptimizationStrategy.PREDICTIVE_COMPLETION
                ],
                "questioning_style": "specific_targeted",
                "suggested_approach": "Use suggestions, predict answers, ask specific questions"
            },
            
            UserType.QUESTION_AVOIDER: {
                "characteristics": {
                    "avg_response_length": 50,
                    "information_density": 0.6,
                    "question_answering_rate": 0.5,
                    "prefers_statements": True
                },
                "optimization_preferences": [
                    OptimizationStrategy.PREDICTIVE_COMPLETION,
                    OptimizationStrategy.CONTEXT_AWARE_QUESTIONING
                ],
                "questioning_style": "indirect",
                "suggested_approach": "Use statements, predict needs, minimize direct questions"
            },
            
            UserType.CONTEXT_PROVIDER: {
                "characteristics": {
                    "avg_response_length": 80,
                    "information_density": 0.7,
                    "question_answering_rate": 0.8,
                    "provides_context_naturally": True
                },
                "optimization_preferences": [
                    OptimizationStrategy.CONTEXT_AWARE_QUESTIONING,
                    OptimizationStrategy.MULTI_FIELD_EXTRACTION
                ],
                "questioning_style": "contextual",
                "suggested_approach": "Build on provided context, extract multiple fields"
            },
            
            UserType.IMPATIENT_USER: {
                "characteristics": {
                    "avg_response_length": 30,
                    "information_density": 0.5,
                    "question_answering_rate": 0.8,
                    "wants_quick_resolution": True
                },
                "optimization_preferences": [
                    OptimizationStrategy.CONVERSATION_COMPRESSION,
                    OptimizationStrategy.SMART_SUGGESTIONS,
                    OptimizationStrategy.PREDICTIVE_COMPLETION
                ],
                "questioning_style": "rapid_fire",
                "suggested_approach": "Compress conversation, use smart defaults, predict answers"
            },
            
            UserType.METHODICAL_USER: {
                "characteristics": {
                    "avg_response_length": 60,
                    "information_density": 0.6,
                    "question_answering_rate": 0.9,
                    "prefers_step_by_step": True
                },
                "optimization_preferences": [
                    OptimizationStrategy.ADAPTIVE_FLOW,
                    OptimizationStrategy.PRIORITY_REORDERING
                ],
                "questioning_style": "sequential",
                "suggested_approach": "Follow logical sequence, adapt flow to preferences"
            }
        }
    
    async def analyze_conversation_patterns(
        self,
        dialogue_context: DialogueContext,
        conversation_history: List[Dict]
    ) -> ConversationPattern:
        """
        Analyze user conversation patterns for optimization
        """
        if not conversation_history:
            return ConversationPattern(
                avg_response_length=50,
                response_completeness=0.5,
                question_answering_rate=0.7,
                topic_consistency=0.8,
                interruption_frequency=0.1
            )
        
        # Calculate metrics
        response_lengths = [len(msg.get("message", "")) for msg in conversation_history if msg.get("message")]
        avg_response_length = statistics.mean(response_lengths) if response_lengths else 50
        
        # Analyze response completeness
        response_completeness = await self._analyze_response_completeness(conversation_history)
        
        # Calculate question answering rate
        question_answering_rate = await self._calculate_question_answering_rate(conversation_history)
        
        # Analyze topic consistency
        topic_consistency = await self._analyze_topic_consistency(conversation_history)
        
        # Calculate interruption frequency
        interruption_frequency = self._calculate_interruption_frequency(conversation_history)
        
        # Determine preferred information order
        preferred_order = await self._determine_preferred_information_order(
            dialogue_context, conversation_history
        )
        
        # Determine response style
        response_style = await self._determine_response_style(conversation_history)
        
        return ConversationPattern(
            avg_response_length=avg_response_length,
            response_completeness=response_completeness,
            question_answering_rate=question_answering_rate,
            topic_consistency=topic_consistency,
            interruption_frequency=interruption_frequency,
            preferred_information_order=preferred_order,
            response_style=response_style
        )
    
    async def _analyze_response_completeness(self, conversation_history: List[Dict]) -> float:
        """Analyze how complete user responses are"""
        completeness_scores = []
        
        for msg in conversation_history:
            message = msg.get("message", "")
            if message:
                # Simple heuristic: longer responses with specific details are more complete
                score = min(len(message) / 100, 1.0)  # Normalize to 0-1
                
                # Boost score for specific keywords
                specific_keywords = ["robinet", "fuite", "panne", "ne marche pas", "cassé", "urgent"]
                for keyword in specific_keywords:
                    if keyword in message.lower():
                        score += 0.1
                
                completeness_scores.append(min(score, 1.0))
        
        return statistics.mean(completeness_scores) if completeness_scores else 0.5
    
    async def _calculate_question_answering_rate(self, conversation_history: List[Dict]) -> float:
        """Calculate how often user directly answers questions"""
        # This would require more sophisticated analysis
        # For now, return a heuristic based on message patterns
        
        answered_questions = 0
        total_questions = 0
        
        for i, msg in enumerate(conversation_history):
            if msg.get("type") == "assistant" and "?" in msg.get("message", ""):
                total_questions += 1
                
                # Check if next user message seems to answer the question
                if i + 1 < len(conversation_history):
                    next_msg = conversation_history[i + 1]
                    if next_msg.get("type") == "user":
                        # Simple heuristic: if response is reasonably long, assume it's an answer
                        if len(next_msg.get("message", "")) > 10:
                            answered_questions += 1
        
        return answered_questions / total_questions if total_questions > 0 else 0.7
    
    async def _analyze_topic_consistency(self, conversation_history: List[Dict]) -> float:
        """Analyze how consistent user is with topic"""
        if len(conversation_history) < 2:
            return 0.8
        
        # Simple heuristic: fewer topic changes = higher consistency
        topic_changes = 0
        current_topic = None
        
        for msg in conversation_history:
            message = msg.get("message", "").lower()
            
            # Detect service type mentions
            if "plomberie" in message or "robinet" in message or "fuite" in message:
                detected_topic = "plomberie"
            elif "électricité" in message or "courant" in message or "lumière" in message:
                detected_topic = "électricité"
            elif "électroménager" in message or "frigo" in message or "machine" in message:
                detected_topic = "électroménager"
            else:
                continue
            
            if current_topic and current_topic != detected_topic:
                topic_changes += 1
            
            current_topic = detected_topic
        
        consistency = 1.0 - (topic_changes / len(conversation_history))
        return max(consistency, 0.0)
    
    def _calculate_interruption_frequency(self, conversation_history: List[Dict]) -> float:
        """Calculate frequency of interruptions"""
        interruption_indicators = ["non", "plutôt", "finalement", "en fait", "annuler", "stop"]
        
        interruptions = 0
        for msg in conversation_history:
            message = msg.get("message", "").lower()
            for indicator in interruption_indicators:
                if indicator in message:
                    interruptions += 1
                    break
        
        return interruptions / len(conversation_history) if conversation_history else 0.1
    
    async def _determine_preferred_information_order(
        self,
        dialogue_context: DialogueContext,
        conversation_history: List[Dict]
    ) -> List[str]:
        """Determine user's preferred information order"""
        # Analyze which information user provides first naturally
        provided_order = []
        
        for msg in conversation_history:
            message = msg.get("message", "").lower()
            
            # Check for service type
            if "plomberie" in message or "électricité" in message or "électroménager" in message:
                if "service_type" not in provided_order:
                    provided_order.append("service_type")
            
            # Check for location
            if "bonamoussadi" in message or "douala" in message or "adresse" in message:
                if "location" not in provided_order:
                    provided_order.append("location")
            
            # Check for description
            if any(word in message for word in ["problème", "panne", "fuite", "cassé", "ne marche pas"]):
                if "description" not in provided_order:
                    provided_order.append("description")
            
            # Check for urgency
            if any(word in message for word in ["urgent", "vite", "rapidement", "maintenant"]):
                if "urgency" not in provided_order:
                    provided_order.append("urgency")
        
        # Fill in missing fields with default order
        default_order = ["service_type", "location", "description", "urgency", "contact_info"]
        for field in default_order:
            if field not in provided_order:
                provided_order.append(field)
        
        return provided_order
    
    async def _determine_response_style(self, conversation_history: List[Dict]) -> str:
        """Determine user's response style"""
        if not conversation_history:
            return "neutral"
        
        # Analyze language patterns
        formal_indicators = ["monsieur", "madame", "s'il vous plaît", "veuillez"]
        casual_indicators = ["salut", "ok", "ouais", "ça va"]
        
        formal_count = 0
        casual_count = 0
        
        for msg in conversation_history:
            message = msg.get("message", "").lower()
            
            for indicator in formal_indicators:
                if indicator in message:
                    formal_count += 1
            
            for indicator in casual_indicators:
                if indicator in message:
                    casual_count += 1
        
        if formal_count > casual_count:
            return "formal"
        elif casual_count > formal_count:
            return "casual"
        else:
            return "neutral"
    
    async def classify_user_type(
        self,
        conversation_pattern: ConversationPattern,
        dialogue_context: DialogueContext
    ) -> UserType:
        """
        Classify user type based on conversation patterns
        """
        # Score each user type based on patterns
        user_type_scores = {}
        
        for user_type, profile in self.user_type_profiles.items():
            score = 0.0
            characteristics = profile["characteristics"]
            
            # Compare response length
            length_diff = abs(conversation_pattern.avg_response_length - characteristics["avg_response_length"])
            length_score = 1.0 - (length_diff / 100)  # Normalize
            score += length_score * 0.3
            
            # Compare information density
            if "information_density" in characteristics:
                density_diff = abs(conversation_pattern.response_completeness - characteristics["information_density"])
                density_score = 1.0 - density_diff
                score += density_score * 0.3
            
            # Compare question answering rate
            if "question_answering_rate" in characteristics:
                qa_diff = abs(conversation_pattern.question_answering_rate - characteristics["question_answering_rate"])
                qa_score = 1.0 - qa_diff
                score += qa_score * 0.2
            
            # Check special characteristics
            if characteristics.get("prefers_open_questions") and conversation_pattern.response_completeness > 0.7:
                score += 0.1
            
            if characteristics.get("prefers_specific_questions") and conversation_pattern.avg_response_length < 30:
                score += 0.1
            
            if characteristics.get("wants_quick_resolution") and conversation_pattern.interruption_frequency < 0.1:
                score += 0.1
            
            user_type_scores[user_type] = max(score, 0.0)
        
        # Return user type with highest score
        best_user_type = max(user_type_scores, key=user_type_scores.get)
        
        logger.info(f"User classified as: {best_user_type.value} (score: {user_type_scores[best_user_type]:.2f})")
        
        return best_user_type
    
    async def generate_optimization_recommendations(
        self,
        dialogue_context: DialogueContext,
        conversation_pattern: ConversationPattern,
        user_type: UserType
    ) -> List[OptimizationRecommendation]:
        """
        Generate optimization recommendations based on analysis
        """
        recommendations = []
        
        # Get user type preferences
        user_profile = self.user_type_profiles[user_type]
        preferred_strategies = user_profile["optimization_preferences"]
        
        # Analyze current conversation state
        missing_fields = dialogue_context.missing_info
        collected_fields = dialogue_context.collected_info
        
        # Generate recommendations for each applicable strategy
        for strategy in preferred_strategies:
            if strategy in self.optimization_strategies:
                strategy_info = self.optimization_strategies[strategy]
                
                # Check if strategy is applicable
                if self._is_strategy_applicable(strategy, dialogue_context, conversation_pattern):
                    
                    # Calculate confidence based on user type match and context
                    confidence = self._calculate_strategy_confidence(
                        strategy, user_type, dialogue_context, conversation_pattern
                    )
                    
                    if confidence >= strategy_info["confidence_threshold"]:
                        recommendations.append(
                            OptimizationRecommendation(
                                strategy=strategy,
                                confidence=confidence,
                                expected_turn_reduction=strategy_info["expected_reduction"],
                                description=strategy_info["description"],
                                implementation_actions=self._generate_implementation_actions(
                                    strategy, dialogue_context, user_type
                                )
                            )
                        )
        
        # Sort by confidence and expected reduction
        recommendations.sort(
            key=lambda x: (x.confidence, x.expected_turn_reduction),
            reverse=True
        )
        
        return recommendations
    
    def _is_strategy_applicable(
        self,
        strategy: OptimizationStrategy,
        dialogue_context: DialogueContext,
        conversation_pattern: ConversationPattern
    ) -> bool:
        """Check if optimization strategy is applicable"""
        strategy_info = self.optimization_strategies[strategy]
        applicable_contexts = strategy_info["applicable_contexts"]
        
        # Check if current context matches applicable contexts
        if "any" in applicable_contexts:
            return True
        
        current_state = dialogue_context.current_state.value
        return any(context in current_state for context in applicable_contexts)
    
    def _calculate_strategy_confidence(
        self,
        strategy: OptimizationStrategy,
        user_type: UserType,
        dialogue_context: DialogueContext,
        conversation_pattern: ConversationPattern
    ) -> float:
        """Calculate confidence score for strategy application"""
        base_confidence = 0.7
        
        # Adjust based on user type compatibility
        user_profile = self.user_type_profiles[user_type]
        if strategy in user_profile["optimization_preferences"]:
            base_confidence += 0.2
        
        # Adjust based on conversation patterns
        if strategy == OptimizationStrategy.MULTI_FIELD_EXTRACTION:
            if conversation_pattern.response_completeness > 0.7:
                base_confidence += 0.1
        
        elif strategy == OptimizationStrategy.PREDICTIVE_COMPLETION:
            if conversation_pattern.topic_consistency > 0.8:
                base_confidence += 0.1
        
        elif strategy == OptimizationStrategy.CONVERSATION_COMPRESSION:
            if conversation_pattern.interruption_frequency < 0.1:
                base_confidence += 0.1
        
        # Adjust based on dialogue context
        completion_progress = len(dialogue_context.collected_info) / 5
        if completion_progress > 0.5:
            base_confidence += 0.1
        
        return min(base_confidence, 1.0)
    
    def _generate_implementation_actions(
        self,
        strategy: OptimizationStrategy,
        dialogue_context: DialogueContext,
        user_type: UserType
    ) -> List[str]:
        """Generate implementation actions for strategy"""
        actions = []
        
        if strategy == OptimizationStrategy.MULTI_FIELD_EXTRACTION:
            actions = [
                "Combine multiple questions in single turn",
                "Use context clues to extract multiple fields",
                "Implement parallel validation"
            ]
        
        elif strategy == OptimizationStrategy.CONTEXT_AWARE_QUESTIONING:
            actions = [
                "Reference previously collected information",
                "Ask targeted questions based on context",
                "Skip redundant information requests"
            ]
        
        elif strategy == OptimizationStrategy.PREDICTIVE_COMPLETION:
            actions = [
                "Predict likely answers based on patterns",
                "Provide auto-suggestions",
                "Implement confidence-based completion"
            ]
        
        elif strategy == OptimizationStrategy.SMART_SUGGESTIONS:
            actions = [
                "Generate contextual suggestions",
                "Implement one-click completion",
                "Use smart defaults"
            ]
        
        elif strategy == OptimizationStrategy.ADAPTIVE_FLOW:
            actions = [
                "Adapt question order to user preferences",
                "Skip unnecessary validation steps",
                "Personalize conversation approach"
            ]
        
        elif strategy == OptimizationStrategy.CONVERSATION_COMPRESSION:
            actions = [
                "Batch multiple questions together",
                "Use parallel information processing",
                "Implement smart question bundling"
            ]
        
        return actions
    
    async def apply_optimization(
        self,
        recommendation: OptimizationRecommendation,
        dialogue_context: DialogueContext,
        user_type: UserType
    ) -> Dict[str, Any]:
        """
        Apply optimization recommendation
        """
        strategy = recommendation.strategy
        
        optimization_result = {
            "strategy_applied": strategy.value,
            "confidence": recommendation.confidence,
            "implementation_actions": recommendation.implementation_actions,
            "modifications": []
        }
        
        # Apply specific optimization
        if strategy == OptimizationStrategy.MULTI_FIELD_EXTRACTION:
            result = await self._apply_multi_field_extraction(dialogue_context, user_type)
            optimization_result["modifications"].append(result)
        
        elif strategy == OptimizationStrategy.CONTEXT_AWARE_QUESTIONING:
            result = await self._apply_context_aware_questioning(dialogue_context, user_type)
            optimization_result["modifications"].append(result)
        
        elif strategy == OptimizationStrategy.PREDICTIVE_COMPLETION:
            result = await self._apply_predictive_completion(dialogue_context, user_type)
            optimization_result["modifications"].append(result)
        
        elif strategy == OptimizationStrategy.SMART_SUGGESTIONS:
            result = await self._apply_smart_suggestions(dialogue_context, user_type)
            optimization_result["modifications"].append(result)
        
        elif strategy == OptimizationStrategy.ADAPTIVE_FLOW:
            result = await self._apply_adaptive_flow(dialogue_context, user_type)
            optimization_result["modifications"].append(result)
        
        elif strategy == OptimizationStrategy.CONVERSATION_COMPRESSION:
            result = await self._apply_conversation_compression(dialogue_context, user_type)
            optimization_result["modifications"].append(result)
        
        # Update metrics
        self.metrics["total_optimizations"] += 1
        
        return optimization_result
    
    async def _apply_multi_field_extraction(
        self,
        dialogue_context: DialogueContext,
        user_type: UserType
    ) -> Dict[str, Any]:
        """Apply multi-field extraction optimization"""
        missing_fields = dialogue_context.missing_info
        
        # Group related fields for combined extraction
        field_groups = [
            ["service_type", "description"],
            ["location", "urgency"],
            ["contact_info"]
        ]
        
        combined_questions = []
        for group in field_groups:
            relevant_fields = [field for field in group if field in missing_fields]
            if len(relevant_fields) > 1:
                combined_questions.append(relevant_fields)
        
        return {
            "modification_type": "multi_field_extraction",
            "combined_questions": combined_questions,
            "expected_turn_reduction": len(combined_questions)
        }
    
    async def _apply_context_aware_questioning(
        self,
        dialogue_context: DialogueContext,
        user_type: UserType
    ) -> Dict[str, Any]:
        """Apply context-aware questioning optimization"""
        collected_info = dialogue_context.collected_info
        missing_fields = dialogue_context.missing_info
        
        context_hints = {}
        for field in missing_fields:
            if field == "description" and "service_type" in collected_info:
                service_type = collected_info["service_type"]
                context_hints[field] = f"Specific to {service_type} problems"
            
            elif field == "urgency" and "description" in collected_info:
                description = collected_info["description"].lower()
                if any(word in description for word in ["fuite", "panne", "ne marche pas"]):
                    context_hints[field] = "Likely urgent based on description"
        
        return {
            "modification_type": "context_aware_questioning",
            "context_hints": context_hints,
            "expected_turn_reduction": len(context_hints)
        }
    
    async def _apply_predictive_completion(
        self,
        dialogue_context: DialogueContext,
        user_type: UserType
    ) -> Dict[str, Any]:
        """Apply predictive completion optimization"""
        collected_info = dialogue_context.collected_info
        missing_fields = dialogue_context.missing_info
        
        predictions = {}
        
        # Predict urgency based on description
        if "urgency" in missing_fields and "description" in collected_info:
            description = collected_info["description"].lower()
            if any(word in description for word in ["fuite", "panne", "ne marche pas"]):
                predictions["urgency"] = "urgent"
            else:
                predictions["urgency"] = "normal"
        
        # Predict contact preference
        if "contact_info" in missing_fields:
            predictions["contact_info"] = "whatsapp_current"
        
        return {
            "modification_type": "predictive_completion",
            "predictions": predictions,
            "expected_turn_reduction": len(predictions)
        }
    
    async def _apply_smart_suggestions(
        self,
        dialogue_context: DialogueContext,
        user_type: UserType
    ) -> Dict[str, Any]:
        """Apply smart suggestions optimization"""
        collected_info = dialogue_context.collected_info
        missing_fields = dialogue_context.missing_info
        
        suggestions = {}
        
        for field in missing_fields:
            if field == "service_type":
                suggestions[field] = ["Plomberie", "Électricité", "Électroménager"]
            
            elif field == "location":
                suggestions[field] = ["Bonamoussadi Village", "Bonamoussadi Carrefour", "Bonamoussadi Ndokoti"]
            
            elif field == "urgency":
                suggestions[field] = ["Urgent", "Aujourd'hui", "Demain", "Cette semaine"]
            
            elif field == "description" and "service_type" in collected_info:
                service_type = collected_info["service_type"]
                if service_type == "plomberie":
                    suggestions[field] = ["Robinet qui fuit", "Toilette bouchée", "Pas d'eau"]
                elif service_type == "électricité":
                    suggestions[field] = ["Panne de courant", "Prise ne marche pas", "Lumière clignote"]
                elif service_type == "électroménager":
                    suggestions[field] = ["Frigo ne refroidit pas", "Machine en panne", "Climatiseur cassé"]
        
        return {
            "modification_type": "smart_suggestions",
            "suggestions": suggestions,
            "expected_turn_reduction": 1
        }
    
    async def _apply_adaptive_flow(
        self,
        dialogue_context: DialogueContext,
        user_type: UserType
    ) -> Dict[str, Any]:
        """Apply adaptive flow optimization"""
        user_profile = self.user_type_profiles[user_type]
        preferred_order = dialogue_context.user_profile.get("preferred_information_order", [])
        
        # Reorder missing fields based on user preferences
        missing_fields = dialogue_context.missing_info
        
        if preferred_order:
            # Use user's preferred order
            reordered_fields = []
            for field in preferred_order:
                if field in missing_fields:
                    reordered_fields.append(field)
            
            # Add any remaining fields
            for field in missing_fields:
                if field not in reordered_fields:
                    reordered_fields.append(field)
        else:
            # Use default order for user type
            if user_type == UserType.IMPATIENT_USER:
                reordered_fields = ["service_type", "urgency", "location", "description", "contact_info"]
            else:
                reordered_fields = missing_fields
        
        return {
            "modification_type": "adaptive_flow",
            "reordered_fields": reordered_fields,
            "user_type": user_type.value,
            "expected_turn_reduction": 1
        }
    
    async def _apply_conversation_compression(
        self,
        dialogue_context: DialogueContext,
        user_type: UserType
    ) -> Dict[str, Any]:
        """Apply conversation compression optimization"""
        missing_fields = dialogue_context.missing_info
        
        # Create compressed question bundles
        if len(missing_fields) >= 3:
            # Create one comprehensive question
            compressed_bundle = {
                "type": "comprehensive_question",
                "fields": missing_fields,
                "approach": "single_comprehensive_message"
            }
            expected_reduction = len(missing_fields) - 1
        
        elif len(missing_fields) == 2:
            # Combine into one question
            compressed_bundle = {
                "type": "dual_question",
                "fields": missing_fields,
                "approach": "combined_question"
            }
            expected_reduction = 1
        
        else:
            # No compression needed
            compressed_bundle = {
                "type": "no_compression",
                "fields": missing_fields,
                "approach": "standard"
            }
            expected_reduction = 0
        
        return {
            "modification_type": "conversation_compression",
            "compressed_bundle": compressed_bundle,
            "expected_turn_reduction": expected_reduction
        }
    
    def get_optimization_metrics(self) -> Dict[str, Any]:
        """Get optimization performance metrics"""
        return {
            "metrics": self.metrics,
            "optimization_strategies": {
                strategy.value: {
                    "description": info["description"],
                    "expected_reduction": info["expected_reduction"],
                    "confidence_threshold": info["confidence_threshold"]
                }
                for strategy, info in self.optimization_strategies.items()
            },
            "user_types": {
                user_type.value: {
                    "characteristics": profile["characteristics"],
                    "preferred_strategies": [s.value for s in profile["optimization_preferences"]],
                    "questioning_style": profile["questioning_style"]
                }
                for user_type, profile in self.user_type_profiles.items()
            }
        }
    
    async def learn_from_conversation(
        self,
        dialogue_context: DialogueContext,
        optimization_metrics: OptimizationMetrics,
        user_feedback: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Learn from conversation outcomes to improve future optimizations
        """
        # Store conversation data for learning
        conversation_data = {
            "timestamp": datetime.now().isoformat(),
            "dialogue_context": dialogue_context.collected_info,
            "optimization_metrics": optimization_metrics,
            "user_feedback": user_feedback,
            "actual_vs_predicted": {
                "estimated_turns": optimization_metrics.original_estimated_turns,
                "actual_turns": optimization_metrics.actual_turns,
                "accuracy": optimization_metrics.optimization_effectiveness
            }
        }
        
        self.conversation_history.append(conversation_data)
        
        # Update metrics
        if optimization_metrics.optimization_effectiveness > 0.7:
            self.metrics["successful_optimizations"] += 1
        
        # Calculate average turn reduction
        turn_reduction = optimization_metrics.original_estimated_turns - optimization_metrics.actual_turns
        self.metrics["average_turn_reduction"] = (
            (self.metrics["average_turn_reduction"] * (self.metrics["total_optimizations"] - 1) + turn_reduction) /
            self.metrics["total_optimizations"]
        )
        
        # Update optimization accuracy
        accuracy = optimization_metrics.optimization_effectiveness
        self.metrics["optimization_accuracy"] = (
            (self.metrics["optimization_accuracy"] * (self.metrics["total_optimizations"] - 1) + accuracy) /
            self.metrics["total_optimizations"]
        )
        
        logger.info(f"Learned from conversation: {turn_reduction} turn reduction, {accuracy:.2f} accuracy")