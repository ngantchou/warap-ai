"""
Proactive Engagement Service for Djobea AI
Manages intelligent follow-ups, state transitions, and proactive client communication
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

from sqlalchemy.orm import Session
from app.database import get_db
from app.models.database_models import User, ServiceRequest, Conversation
from app.services.whatsapp_service import WhatsAppService
from app.services.multi_llm_orchestrator import MultiLLMOrchestrator, ConversationContext
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class EngagementTrigger(Enum):
    """Types of proactive engagement triggers"""
    REQUEST_CREATED = "request_created"
    PROVIDER_ASSIGNED = "provider_assigned"
    AWAITING_RESPONSE = "awaiting_response"
    SERVICE_IN_PROGRESS = "service_in_progress"
    LONG_SILENCE = "long_silence"
    PROVIDER_DELAYED = "provider_delayed"
    PAYMENT_PENDING = "payment_pending"

@dataclass
class EngagementRule:
    """Configuration for proactive engagement triggers"""
    trigger: EngagementTrigger
    delay_seconds: int
    message_template: str
    action_buttons: List[str]
    max_attempts: int = 3
    escalation_delay: int = 1800  # 30 minutes
    conditions: Optional[Dict[str, Any]] = None

@dataclass
class ScheduledEngagement:
    """Scheduled proactive engagement"""
    user_id: str
    phone_number: str
    trigger: EngagementTrigger
    scheduled_time: datetime
    context: Dict[str, Any]
    attempts: int = 0
    completed: bool = False

class ProactiveEngagementService:
    """
    Service for managing proactive client engagement and intelligent follow-ups
    """
    
    def __init__(self):
        self.whatsapp_service = WhatsAppService()
        self.llm_orchestrator = MultiLLMOrchestrator()
        self.setup_engagement_rules()
        self.scheduled_engagements: List[ScheduledEngagement] = []
        self.background_tasks: List[asyncio.Task] = []
        
    def setup_engagement_rules(self):
        """Setup proactive engagement rules and triggers"""
        self.engagement_rules = {
            EngagementTrigger.REQUEST_CREATED: EngagementRule(
                trigger=EngagementTrigger.REQUEST_CREATED,
                delay_seconds=300,  # 5 minutes
                message_template="""
🔍 **Recherche en cours...**

Votre demande de {service_type} à {location} est en traitement.

Je vous notifie dès qu'un prestataire disponible est trouvé ! ⏰

{status_update}
                """,
                action_buttons=[
                    "📊 Voir le statut",
                    "✏️ Modifier ma demande", 
                    "📞 Contact urgence"
                ]
            ),
            
            EngagementTrigger.PROVIDER_ASSIGNED: EngagementRule(
                trigger=EngagementTrigger.PROVIDER_ASSIGNED,
                delay_seconds=900,  # 15 minutes
                message_template="""
✅ **Prestataire trouvé !**

👷‍♂️ **{provider_name}** a accepté votre demande
⭐ Note: {provider_rating}/5 | 📍 Secteur: {provider_location}
📞 Contact: {provider_phone}

Il vous contactera sous peu pour confirmer les détails.

💡 **Estimation**: {estimated_cost} XAF
                """,
                action_buttons=[
                    "👤 Voir profil prestataire",
                    "📞 Contacter maintenant",
                    "📅 Modifier rendez-vous"
                ]
            ),
            
            EngagementTrigger.AWAITING_RESPONSE: EngagementRule(
                trigger=EngagementTrigger.AWAITING_RESPONSE,
                delay_seconds=1800,  # 30 minutes
                message_template="""
❓ **En attente de votre réponse**

J'attends votre retour pour continuer à vous accompagner.

Avez-vous besoin d'aide supplémentaire ? 🤔
                """,
                action_buttons=[
                    "✅ Oui, j'ai besoin d'aide",
                    "👍 Tout va bien",
                    "⏰ Reprendre plus tard"
                ]
            ),
            
            EngagementTrigger.SERVICE_IN_PROGRESS: EngagementRule(
                trigger=EngagementTrigger.SERVICE_IN_PROGRESS,
                delay_seconds=3600,  # 1 hour
                message_template="""
🔧 **Service en cours**

Comment se passe l'intervention de {provider_name} ?

N'hésitez pas à me signaler tout problème ! 📢
                """,
                action_buttons=[
                    "✅ Tout va bien",
                    "⚠️ Il y a un problème",
                    "📞 Contacter support"
                ]
            ),
            
            EngagementTrigger.PROVIDER_DELAYED: EngagementRule(
                trigger=EngagementTrigger.PROVIDER_DELAYED,
                delay_seconds=600,  # 10 minutes
                message_template="""
⏱️ **Délai d'attente dépassé**

Le prestataire n'a pas encore répondu.

🔄 Je recherche une alternative pour vous...

**Options disponibles:**
• Attendre encore 10 minutes
• Passer au prestataire suivant
• Reprogrammer pour plus tard
                """,
                action_buttons=[
                    "⏳ Attendre encore",
                    "🔄 Prestataire suivant",
                    "📅 Reprogrammer"
                ]
            ),
            
            EngagementTrigger.PAYMENT_PENDING: EngagementRule(
                trigger=EngagementTrigger.PAYMENT_PENDING,
                delay_seconds=1200,  # 20 minutes
                message_template="""
💳 **Paiement en attente**

Votre service avec {provider_name} est terminé !

💰 **Montant**: {final_amount} XAF
📱 Lien de paiement: {payment_link}

Merci de procéder au règlement pour finaliser. 🙏
                """,
                action_buttons=[
                    "💳 Payer maintenant",
                    "❓ Question sur le montant",
                    "📞 Contacter support"
                ]
            )
        }

    async def schedule_engagement(
        self,
        user_id: str,
        phone_number: str, 
        trigger: EngagementTrigger,
        context: Dict[str, Any],
        custom_delay: Optional[int] = None
    ):
        """Schedule a proactive engagement"""
        try:
            rule = self.engagement_rules.get(trigger)
            if not rule:
                logger.warning(f"No rule found for trigger: {trigger}")
                return
            
            delay = custom_delay or rule.delay_seconds
            scheduled_time = datetime.utcnow() + timedelta(seconds=delay)
            
            engagement = ScheduledEngagement(
                user_id=user_id,
                phone_number=phone_number,
                trigger=trigger,
                scheduled_time=scheduled_time,
                context=context
            )
            
            self.scheduled_engagements.append(engagement)
            
            # Schedule the background task
            task = asyncio.create_task(
                self._execute_scheduled_engagement(engagement)
            )
            self.background_tasks.append(task)
            
            logger.info(f"Scheduled {trigger.value} engagement for user {user_id} at {scheduled_time}")
            
        except Exception as e:
            logger.error(f"Error scheduling engagement: {e}")

    async def _execute_scheduled_engagement(self, engagement: ScheduledEngagement):
        """Execute a scheduled proactive engagement"""
        try:
            # Wait until scheduled time
            now = datetime.utcnow()
            if engagement.scheduled_time > now:
                wait_seconds = (engagement.scheduled_time - now).total_seconds()
                await asyncio.sleep(wait_seconds)
            
            # Check if engagement is still relevant
            if engagement.completed:
                return
            
            # Check conditions if any
            rule = self.engagement_rules[engagement.trigger]
            if rule.conditions and not self._check_conditions(engagement, rule.conditions):
                logger.info(f"Conditions not met for engagement {engagement.trigger.value}")
                return
            
            # Generate personalized message
            message = await self._generate_engagement_message(engagement, rule)
            
            # Send the message
            await self.whatsapp_service.send_message(
                to_phone_number=engagement.phone_number,
                message=message
            )
            
            engagement.attempts += 1
            
            # Schedule retry if needed
            if engagement.attempts < rule.max_attempts:
                retry_engagement = ScheduledEngagement(
                    user_id=engagement.user_id,
                    phone_number=engagement.phone_number,
                    trigger=engagement.trigger,
                    scheduled_time=datetime.utcnow() + timedelta(seconds=rule.escalation_delay),
                    context=engagement.context,
                    attempts=engagement.attempts
                )
                
                task = asyncio.create_task(
                    self._execute_scheduled_engagement(retry_engagement)
                )
                self.background_tasks.append(task)
            
            logger.info(f"Executed proactive engagement: {engagement.trigger.value} for user {engagement.user_id}")
            
        except Exception as e:
            logger.error(f"Error executing engagement: {e}")

    async def _generate_engagement_message(
        self, 
        engagement: ScheduledEngagement, 
        rule: EngagementRule
    ) -> str:
        """Generate personalized engagement message using multi-LLM system"""
        try:
            # Create conversation context for LLM processing
            context = ConversationContext(
                user_id=engagement.user_id,
                phone_number=engagement.phone_number,
                message="[PROACTIVE_ENGAGEMENT]",
                conversation_history=[],
                current_state=engagement.trigger.value.upper(),
                user_profile=engagement.context.get("user_profile"),
                extracted_entities=engagement.context
            )
            
            # Use LLM orchestrator to generate personalized message
            result = await self.llm_orchestrator.process_conversation(context)
            
            # If LLM fails, use template
            if not result.response or result.confidence < 0.6:
                return self._format_template_message(rule.message_template, engagement.context)
            
            # Add action buttons if supported
            formatted_message = result.response
            if rule.action_buttons:
                formatted_message += "\n\n" + self._format_action_buttons(rule.action_buttons)
            
            return formatted_message
            
        except Exception as e:
            logger.error(f"Error generating engagement message: {e}")
            return self._format_template_message(rule.message_template, engagement.context)

    def _format_template_message(self, template: str, context: Dict[str, Any]) -> str:
        """Format template message with context data"""
        try:
            return template.format(**context)
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            return template

    def _format_action_buttons(self, buttons: List[str]) -> str:
        """Format action buttons for WhatsApp"""
        if not buttons:
            return ""
        
        button_text = "**Options disponibles:**\n"
        for i, button in enumerate(buttons, 1):
            button_text += f"{i}. {button}\n"
        
        button_text += "\nTapez le numéro de votre choix ou écrivez votre réponse."
        return button_text

    def _check_conditions(self, engagement: ScheduledEngagement, conditions: Dict[str, Any]) -> bool:
        """Check if engagement conditions are met"""
        try:
            # This would implement condition checking logic
            # For now, return True (always execute)
            return True
        except Exception as e:
            logger.error(f"Error checking conditions: {e}")
            return False

    async def handle_proactive_response(self, user_id: str, message: str, context: Dict[str, Any]) -> bool:
        """Handle user response to proactive engagement"""
        try:
            # Check if this is a response to action buttons
            if message.isdigit():
                button_index = int(message) - 1
                return await self._handle_button_response(user_id, button_index, context)
            
            # Process natural language response
            conversation_context = ConversationContext(
                user_id=user_id,
                phone_number=context.get("phone_number", ""),
                message=message,
                conversation_history=context.get("conversation_history", []),
                current_state=context.get("current_state", "RESPONDING_TO_PROACTIVE")
            )
            
            result = await self.llm_orchestrator.process_conversation(conversation_context)
            
            # Send appropriate response
            await self.whatsapp_service.send_message(
                phone_number=context.get("phone_number", ""),
                message=result.response
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling proactive response: {e}")
            return False

    async def _handle_button_response(self, user_id: str, button_index: int, context: Dict[str, Any]) -> bool:
        """Handle response to action buttons"""
        try:
            # This would implement specific button action logic
            # For now, just acknowledge the response
            response_actions = {
                0: "Merci ! Je note votre préférence et continue le suivi.",
                1: "Parfait ! Je m'occupe de cela immédiatement.",
                2: "Compris ! Je vous recontacte selon vos préférences."
            }
            
            response = response_actions.get(button_index, "Merci pour votre réponse !")
            
            await self.whatsapp_service.send_message(
                phone_number=context.get("phone_number", ""),
                message=response
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling button response: {e}")
            return False

    async def cancel_engagement(self, user_id: str, trigger: EngagementTrigger):
        """Cancel scheduled engagement for user"""
        try:
            for engagement in self.scheduled_engagements:
                if (engagement.user_id == user_id and 
                    engagement.trigger == trigger and 
                    not engagement.completed):
                    engagement.completed = True
                    logger.info(f"Cancelled engagement {trigger.value} for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error cancelling engagement: {e}")

    async def trigger_immediate_engagement(
        self,
        user_id: str,
        phone_number: str,
        trigger: EngagementTrigger,
        context: Dict[str, Any]
    ):
        """Trigger immediate proactive engagement (no delay)"""
        await self.schedule_engagement(
            user_id=user_id,
            phone_number=phone_number,
            trigger=trigger,
            context=context,
            custom_delay=0
        )

    def get_engagement_status(self, user_id: str) -> List[Dict[str, Any]]:
        """Get status of all engagements for a user"""
        try:
            user_engagements = [
                {
                    "trigger": eng.trigger.value,
                    "scheduled_time": eng.scheduled_time.isoformat(),
                    "attempts": eng.attempts,
                    "completed": eng.completed
                }
                for eng in self.scheduled_engagements
                if eng.user_id == user_id
            ]
            
            return user_engagements
            
        except Exception as e:
            logger.error(f"Error getting engagement status: {e}")
            return []

    async def cleanup_completed_engagements(self):
        """Clean up completed engagements and tasks"""
        try:
            # Remove completed engagements
            self.scheduled_engagements = [
                eng for eng in self.scheduled_engagements 
                if not eng.completed
            ]
            
            # Clean up finished tasks
            finished_tasks = [task for task in self.background_tasks if task.done()]
            for task in finished_tasks:
                self.background_tasks.remove(task)
            
            logger.info(f"Cleaned up {len(finished_tasks)} completed tasks")
            
        except Exception as e:
            logger.error(f"Error cleaning up engagements: {e}")

# Global service instance
proactive_engagement_service = ProactiveEngagementService()