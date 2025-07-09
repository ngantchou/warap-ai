"""
Enhanced Conversation Manager V4 - Complete Multi-turn Dialogue Engine
Integrates all advanced dialogue components for optimized conversation management
"""
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import logging
from datetime import datetime, timedelta
import json

from app.models.conversation_session import ConversationSession
from app.models.action_codes import ActionCode
from app.services.dialogue_flow_manager import DialogueFlowManager, DialogueContext, DialogueState
from app.services.intelligent_collection_service import IntelligentCollectionService, CollectionStrategy
from app.services.interruption_manager import InterruptionManager, InterruptionState, InterruptionType
from app.services.dialogue_optimization_engine import DialogueOptimizationEngine, OptimizationStrategy
from app.services.session_manager import SessionManager
from app.services.ai_service import AIService
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

@dataclass
class ConversationMetrics:
    """Comprehensive conversation metrics"""
    total_turns: int = 0
    information_collected: int = 0
    optimizations_applied: int = 0
    interruptions_handled: int = 0
    efficiency_score: float = 0.0
    user_satisfaction: float = 0.0
    completion_time: float = 0.0

class EnhancedConversationManagerV4:
    """
    Complete multi-turn dialogue engine with advanced optimization
    """
    
    def __init__(self):
        # Core services
        self.dialogue_flow_manager = DialogueFlowManager()
        self.intelligent_collection = IntelligentCollectionService()
        self.interruption_manager = InterruptionManager()
        self.optimization_engine = DialogueOptimizationEngine()
        self.session_manager = SessionManager()
        self.ai_service = AIService()
        
        # State management
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.interruption_states: Dict[str, InterruptionState] = {}
        
        # Performance metrics
        self.metrics = ConversationMetrics()
        
        # Configuration
        self.config = {
            "max_turns_per_session": 10,
            "optimization_threshold": 0.7,
            "interruption_detection_enabled": True,
            "auto_optimization_enabled": True,
            "learning_enabled": True
        }
    
    async def process_message(
        self,
        message: str,
        phone_number: str,
        user_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        Process message with complete multi-turn dialogue engine
        """
        start_time = datetime.now()
        
        try:
            # Get or create session
            session = await self._get_or_create_session(phone_number, user_id, db)
            
            # Get dialogue context
            dialogue_context = await self._get_dialogue_context(session, db)
            
            # Get interruption state
            interruption_state = self._get_interruption_state(phone_number)
            
            # Detect interruptions
            if self.config["interruption_detection_enabled"]:
                interruption = await self.interruption_manager.detect_interruption(
                    message, dialogue_context, interruption_state
                )
                
                if interruption:
                    self.metrics.interruptions_handled += 1
                    return await self._handle_interruption(
                        interruption, dialogue_context, interruption_state, session, db
                    )
            
            # Process normal dialogue turn
            dialogue_result = await self.dialogue_flow_manager.process_dialogue_turn(
                session, message, db
            )
            
            # Apply optimizations if enabled
            if self.config["auto_optimization_enabled"]:
                optimization_result = await self._apply_auto_optimizations(
                    dialogue_context, session, db
                )
                if optimization_result:
                    dialogue_result.update(optimization_result)
                    self.metrics.optimizations_applied += 1
            
            # Update metrics
            self.metrics.total_turns += 1
            self.metrics.information_collected = len(dialogue_context.collected_info)
            
            # Calculate efficiency score
            efficiency = self._calculate_efficiency_score(dialogue_context)
            self.metrics.efficiency_score = efficiency
            
            # Update session
            await self._update_session_context(session, dialogue_context, db)
            
            # Prepare response
            response = {
                "response": dialogue_result["response"],
                "dialogue_state": dialogue_result["dialogue_state"],
                "session_id": session.session_id,
                "collected_info": dialogue_result["collected_info"],
                "missing_info": dialogue_result["missing_info"],
                "completion_progress": dialogue_result["completion_progress"],
                "optimization_score": dialogue_result.get("optimization_score", 0.0),
                "suggested_actions": dialogue_result.get("suggested_actions", []),
                "conversation_metrics": {
                    "total_turns": self.metrics.total_turns,
                    "efficiency_score": self.metrics.efficiency_score,
                    "optimizations_applied": self.metrics.optimizations_applied,
                    "interruptions_handled": self.metrics.interruptions_handled
                }
            }
            
            # Learning from conversation
            if self.config["learning_enabled"]:
                await self._learn_from_interaction(dialogue_context, response, db)
            
            # Calculate completion time
            completion_time = (datetime.now() - start_time).total_seconds()
            response["processing_time"] = completion_time
            
            logger.info(f"Message processed successfully in {completion_time:.2f}s")
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                "response": "Désolé, une erreur technique s'est produite. Pouvez-vous reformuler votre demande ?",
                "dialogue_state": "error",
                "session_id": session.session_id if 'session' in locals() else None,
                "error": str(e),
                "processing_time": (datetime.now() - start_time).total_seconds()
            }
    
    async def _get_or_create_session(
        self,
        phone_number: str,
        user_id: int,
        db: Session
    ) -> ConversationSession:
        """Get or create conversation session"""
        from app.models.database_models import User, ConversationSession
        
        # Find or create user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(
                whatsapp_id=f"whatsapp_{phone_number}",
                phone_number=phone_number,
                name=f"User {phone_number}"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Check for existing active session
        active_session = db.query(ConversationSession).filter(
            ConversationSession.user_id == user.id,
            ConversationSession.is_active == True,
            ConversationSession.is_expired == False,
            ConversationSession.expires_at > datetime.now()
        ).first()
        
        if active_session:
            return active_session
        
        # Create new session
        session_id = f"session_{user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        new_session = ConversationSession(
            session_id=session_id,
            user_id=user.id,
            phone_number=phone_number,
            current_state="INITIAL",
            expires_at=datetime.now() + timedelta(hours=2),
            collected_data={},
            session_metadata={},
            conversation_summary={},
            metrics={}
        )
        
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        
        return new_session
    
    async def _get_dialogue_context(
        self,
        session: ConversationSession,
        db: Session
    ) -> DialogueContext:
        """Get dialogue context for session"""
        return await self.dialogue_flow_manager._get_dialogue_context(session, db)
    
    def _get_interruption_state(self, phone_number: str) -> InterruptionState:
        """Get interruption state for phone number"""
        if phone_number not in self.interruption_states:
            self.interruption_states[phone_number] = InterruptionState()
        return self.interruption_states[phone_number]
    
    async def _handle_interruption(
        self,
        interruption,
        dialogue_context: DialogueContext,
        interruption_state: InterruptionState,
        session: ConversationSession,
        db: Session
    ) -> Dict[str, Any]:
        """Handle conversation interruption"""
        logger.info(f"Handling interruption: {interruption.type.value}")
        
        # Handle interruption
        interruption_result = await self.interruption_manager.handle_interruption(
            interruption, dialogue_context, interruption_state, db
        )
        
        # Update session state
        if interruption_result.get("new_state"):
            dialogue_context.current_state = interruption_result["new_state"]
            await self._update_session_context(session, dialogue_context, db)
        
        return {
            "response": interruption_result["response"],
            "dialogue_state": interruption_result["new_state"].value if interruption_result.get("new_state") else dialogue_context.current_state.value,
            "session_id": session.session_id,
            "collected_info": dialogue_context.collected_info,
            "missing_info": dialogue_context.missing_info,
            "completion_progress": self.dialogue_flow_manager._calculate_completion_progress(dialogue_context),
            "interruption_handled": True,
            "interruption_type": interruption.type.value,
            "recovery_actions": interruption_result.get("recovery_actions_executed", [])
        }
    
    async def _apply_auto_optimizations(
        self,
        dialogue_context: DialogueContext,
        session: ConversationSession,
        db: Session
    ) -> Optional[Dict[str, Any]]:
        """Apply automatic optimizations"""
        # Analyze conversation patterns
        conversation_pattern = await self.optimization_engine.analyze_conversation_patterns(
            dialogue_context, dialogue_context.conversation_history
        )
        
        # Classify user type
        user_type = await self.optimization_engine.classify_user_type(
            conversation_pattern, dialogue_context
        )
        
        # Generate optimization recommendations
        recommendations = await self.optimization_engine.generate_optimization_recommendations(
            dialogue_context, conversation_pattern, user_type
        )
        
        # Apply best recommendation if confidence is high enough
        if recommendations and recommendations[0].confidence >= self.config["optimization_threshold"]:
            best_recommendation = recommendations[0]
            
            optimization_result = await self.optimization_engine.apply_optimization(
                best_recommendation, dialogue_context, user_type
            )
            
            return {
                "optimization_applied": True,
                "optimization_strategy": best_recommendation.strategy.value,
                "optimization_confidence": best_recommendation.confidence,
                "expected_turn_reduction": best_recommendation.expected_turn_reduction,
                "optimization_details": optimization_result
            }
        
        return None
    
    def _calculate_efficiency_score(self, dialogue_context: DialogueContext) -> float:
        """Calculate conversation efficiency score"""
        if not dialogue_context.conversation_history:
            return 0.0
        
        # Factors: information density, turn efficiency, completion progress
        total_turns = len(dialogue_context.conversation_history)
        info_collected = len(dialogue_context.collected_info)
        
        # Information density (info per turn)
        info_density = info_collected / total_turns if total_turns > 0 else 0
        
        # Completion progress
        completion_progress = self.dialogue_flow_manager._calculate_completion_progress(dialogue_context) / 100
        
        # Turn efficiency (progress per turn)
        turn_efficiency = completion_progress / total_turns if total_turns > 0 else 0
        
        # Combined efficiency score
        efficiency_score = (info_density * 0.4 + turn_efficiency * 0.4 + completion_progress * 0.2)
        
        return min(max(efficiency_score, 0.0), 1.0)
    
    async def _update_session_context(
        self,
        session: ConversationSession,
        dialogue_context: DialogueContext,
        db: Session
    ) -> None:
        """Update session with dialogue context"""
        await self.dialogue_flow_manager._save_dialogue_context(session, dialogue_context, db)
    
    async def _learn_from_interaction(
        self,
        dialogue_context: DialogueContext,
        response: Dict[str, Any],
        db: Session
    ) -> None:
        """Learn from conversation interaction"""
        # Create optimization metrics
        from app.services.dialogue_optimization_engine import OptimizationMetrics
        
        optimization_metrics = OptimizationMetrics(
            original_estimated_turns=5,  # Default estimate
            optimized_estimated_turns=max(5 - response.get("optimizations_applied", 0), 1),
            actual_turns=self.metrics.total_turns,
            information_density=self.metrics.information_collected / max(self.metrics.total_turns, 1),
            extraction_accuracy=response.get("optimization_score", 0.0),
            user_satisfaction_score=0.8,  # Default for now
            optimization_effectiveness=self.metrics.efficiency_score
        )
        
        # Learn from conversation
        await self.optimization_engine.learn_from_conversation(
            dialogue_context, optimization_metrics
        )
    
    async def get_conversation_analytics(
        self,
        session_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """Get detailed conversation analytics"""
        session = await self.session_manager.get_session(session_id, db)
        if not session:
            return {"error": "Session not found"}
        
        dialogue_context = await self._get_dialogue_context(session, db)
        
        # Get analytics from all components
        dialogue_metrics = await self.dialogue_flow_manager.get_dialogue_metrics()
        collection_metrics = self.intelligent_collection.get_collection_metrics()
        interruption_metrics = self.interruption_manager.get_interruption_metrics()
        optimization_metrics = self.optimization_engine.get_optimization_metrics()
        
        return {
            "session_info": {
                "session_id": session.session_id,
                "created_at": session.created_at.isoformat(),
                "current_state": dialogue_context.current_state.value,
                "completion_progress": self.dialogue_flow_manager._calculate_completion_progress(dialogue_context)
            },
            "dialogue_metrics": dialogue_metrics,
            "collection_metrics": collection_metrics,
            "interruption_metrics": interruption_metrics,
            "optimization_metrics": optimization_metrics,
            "overall_performance": {
                "efficiency_score": self.metrics.efficiency_score,
                "total_turns": self.metrics.total_turns,
                "optimizations_applied": self.metrics.optimizations_applied,
                "interruptions_handled": self.metrics.interruptions_handled
            }
        }
    
    async def test_dialogue_capabilities(
        self,
        phone_number: str,
        test_scenarios: List[Dict[str, Any]],
        db: Session
    ) -> Dict[str, Any]:
        """Test dialogue engine capabilities"""
        test_results = []
        
        for scenario in test_scenarios:
            scenario_name = scenario.get("name", "Unknown")
            messages = scenario.get("messages", [])
            expected_outcome = scenario.get("expected_outcome", {})
            
            logger.info(f"Testing scenario: {scenario_name}")
            
            # Reset session for clean test
            user_id = f"test_user_{phone_number}"
            
            scenario_results = {
                "scenario_name": scenario_name,
                "messages_processed": 0,
                "turns_taken": 0,
                "completion_achieved": False,
                "efficiency_score": 0.0,
                "interruptions_handled": 0,
                "optimizations_applied": 0,
                "final_state": None,
                "collected_info": {},
                "errors": []
            }
            
            try:
                for i, message in enumerate(messages):
                    result = await self.process_message(message, phone_number, user_id, db)
                    
                    scenario_results["messages_processed"] += 1
                    scenario_results["turns_taken"] = result.get("conversation_metrics", {}).get("total_turns", 0)
                    scenario_results["efficiency_score"] = result.get("conversation_metrics", {}).get("efficiency_score", 0.0)
                    scenario_results["interruptions_handled"] = result.get("conversation_metrics", {}).get("interruptions_handled", 0)
                    scenario_results["optimizations_applied"] = result.get("conversation_metrics", {}).get("optimizations_applied", 0)
                    scenario_results["final_state"] = result.get("dialogue_state")
                    scenario_results["collected_info"] = result.get("collected_info", {})
                    
                    if result.get("completion_progress", 0) >= 100:
                        scenario_results["completion_achieved"] = True
                        break
                
                # Check against expected outcome
                if expected_outcome:
                    if expected_outcome.get("should_complete") and not scenario_results["completion_achieved"]:
                        scenario_results["errors"].append("Expected completion but not achieved")
                    
                    if expected_outcome.get("max_turns") and scenario_results["turns_taken"] > expected_outcome["max_turns"]:
                        scenario_results["errors"].append(f"Exceeded max turns: {scenario_results['turns_taken']} > {expected_outcome['max_turns']}")
                
            except Exception as e:
                scenario_results["errors"].append(f"Test error: {str(e)}")
            
            test_results.append(scenario_results)
        
        # Calculate overall test metrics
        successful_tests = sum(1 for result in test_results if not result["errors"])
        total_tests = len(test_results)
        
        return {
            "test_summary": {
                "total_scenarios": total_tests,
                "successful_scenarios": successful_tests,
                "success_rate": successful_tests / total_tests if total_tests > 0 else 0,
                "average_efficiency": sum(r["efficiency_score"] for r in test_results) / total_tests if total_tests > 0 else 0,
                "total_optimizations": sum(r["optimizations_applied"] for r in test_results),
                "total_interruptions": sum(r["interruptions_handled"] for r in test_results)
            },
            "scenario_results": test_results
        }
    
    async def optimize_conversation_flow(
        self,
        phone_number: str,
        db: Session
    ) -> Dict[str, Any]:
        """Manually optimize conversation flow"""
        # Get current session
        session = await self.session_manager.get_user_active_session(phone_number, db)
        if not session:
            return {"error": "No active session found"}
        
        # Get dialogue context
        dialogue_context = await self._get_dialogue_context(session, db)
        
        # Analyze conversation patterns
        conversation_pattern = await self.optimization_engine.analyze_conversation_patterns(
            dialogue_context, dialogue_context.conversation_history
        )
        
        # Classify user type
        user_type = await self.optimization_engine.classify_user_type(
            conversation_pattern, dialogue_context
        )
        
        # Generate optimization recommendations
        recommendations = await self.optimization_engine.generate_optimization_recommendations(
            dialogue_context, conversation_pattern, user_type
        )
        
        # Apply all high-confidence recommendations
        applied_optimizations = []
        for recommendation in recommendations:
            if recommendation.confidence >= 0.8:
                optimization_result = await self.optimization_engine.apply_optimization(
                    recommendation, dialogue_context, user_type
                )
                applied_optimizations.append(optimization_result)
        
        return {
            "user_type": user_type.value,
            "conversation_pattern": {
                "avg_response_length": conversation_pattern.avg_response_length,
                "response_completeness": conversation_pattern.response_completeness,
                "question_answering_rate": conversation_pattern.question_answering_rate,
                "topic_consistency": conversation_pattern.topic_consistency,
                "interruption_frequency": conversation_pattern.interruption_frequency
            },
            "optimization_recommendations": [
                {
                    "strategy": rec.strategy.value,
                    "confidence": rec.confidence,
                    "expected_turn_reduction": rec.expected_turn_reduction,
                    "description": rec.description
                }
                for rec in recommendations
            ],
            "applied_optimizations": applied_optimizations,
            "optimization_count": len(applied_optimizations)
        }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics"""
        return {
            "conversation_metrics": {
                "total_turns": self.metrics.total_turns,
                "information_collected": self.metrics.information_collected,
                "efficiency_score": self.metrics.efficiency_score,
                "completion_time": self.metrics.completion_time
            },
            "optimization_metrics": {
                "optimizations_applied": self.metrics.optimizations_applied,
                "auto_optimization_enabled": self.config["auto_optimization_enabled"],
                "optimization_threshold": self.config["optimization_threshold"]
            },
            "interruption_metrics": {
                "interruptions_handled": self.metrics.interruptions_handled,
                "interruption_detection_enabled": self.config["interruption_detection_enabled"]
            },
            "system_config": self.config,
            "active_sessions": len(self.active_sessions),
            "interruption_states": len(self.interruption_states)
        }
    
    async def reset_conversation(
        self,
        phone_number: str,
        user_id: int,
        db: Session
    ) -> Dict[str, Any]:
        """Reset conversation for testing"""
        # Cancel existing session
        existing_session = await self.session_manager.get_user_active_session(user_id, db)
        if existing_session:
            await self.session_manager.cancel_session(existing_session.session_id, db)
        
        # Clear interruption state
        if phone_number in self.interruption_states:
            del self.interruption_states[phone_number]
        
        # Reset metrics
        self.metrics = ConversationMetrics()
        
        return {
            "conversation_reset": True,
            "phone_number": phone_number,
            "user_id": user_id,
            "message": "Conversation reset successfully. Ready for new interaction."
        }