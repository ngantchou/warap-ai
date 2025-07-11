"""
AI-Based Suggestion Service for Djobea AI
Generates intelligent, contextual suggestions using AI instead of static predefined suggestions
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from loguru import logger
from sqlalchemy.orm import Session

from app.services.ai_service import AIService
from app.models.database_models import ServiceRequest, Conversation, User


class AISuggestionService:
    """Service for generating AI-based contextual suggestions"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIService()
    
    async def generate_contextual_suggestions(
        self,
        conversation_context: Dict[str, Any],
        current_message: str,
        ai_response: str,
        user_id: str,
        conversation_phase: str = "information_gathering"
    ) -> List[str]:
        """
        Generate AI-powered contextual suggestions based on conversation context
        
        Args:
            conversation_context: Current conversation context and extracted information
            current_message: User's current message
            ai_response: AI's current response
            user_id: User identifier
            conversation_phase: Current phase of conversation
            
        Returns:
            List of intelligent suggestions
        """
        try:
            # Don't generate suggestions if request is completed
            if conversation_phase == "request_processing":
                return []
            
            # Get conversation history for better context
            conversation_history = await self._get_conversation_history(user_id)
            
            # Build AI prompt for suggestion generation
            suggestion_prompt = self._build_suggestion_prompt(
                conversation_context=conversation_context,
                current_message=current_message,
                ai_response=ai_response,
                conversation_history=conversation_history,
                conversation_phase=conversation_phase
            )
            
            # Generate suggestions using AI
            suggestions = await self._generate_ai_suggestions(suggestion_prompt)
            
            # Post-process and validate suggestions
            processed_suggestions = self._process_suggestions(suggestions, conversation_context)
            
            logger.info(f"Generated {len(processed_suggestions)} AI suggestions for user {user_id}")
            
            return processed_suggestions
            
        except Exception as e:
            logger.error(f"Error generating AI suggestions: {e}")
            # Fallback to simple contextual suggestions
            return self._get_fallback_suggestions(conversation_context, ai_response)
    
    def _build_suggestion_prompt(
        self,
        conversation_context: Dict[str, Any],
        current_message: str,
        ai_response: str,
        conversation_history: List[Dict[str, Any]],
        conversation_phase: str
    ) -> str:
        """Build AI prompt for generating contextual suggestions"""
        
        # Extract key information from context
        extracted_info = conversation_context.get('extracted_info', {})
        service_type = extracted_info.get('service_type')
        location = extracted_info.get('location')
        description = extracted_info.get('description')
        urgency = extracted_info.get('urgency')
        
        # Build conversation history summary
        history_summary = ""
        if conversation_history:
            recent_messages = conversation_history[-3:]  # Last 3 messages
            history_summary = "\n".join([
                f"User: {msg['message']}" for msg in recent_messages
            ])
        
        prompt = f"""Tu es un assistant IA pour un service de dépannage à domicile au Cameroun (Douala).
Génère 3 suggestions courtes et pertinentes pour aider l'utilisateur à continuer la conversation naturellement.

CONTEXTE DE LA CONVERSATION:
- Phase actuelle: {conversation_phase}
- Service détecté: {service_type or 'non spécifié'}
- Localisation: {location or 'non spécifiée'}
- Description: {description or 'non spécifiée'}
- Urgence: {urgency or 'normale'}

HISTORIQUE RÉCENT:
{history_summary}

MESSAGE ACTUEL DE L'UTILISATEUR:
{current_message}

RÉPONSE DE L'IA:
{ai_response}

RÈGLES POUR LES SUGGESTIONS:
1. Maxium 15 mots par suggestion
2. Pertinentes au contexte camerounais (Douala, XAF, expressions locales)
3. Aident à compléter les informations manquantes
4. Naturelles et conversationnelles
5. Adaptées au niveau d'urgence
6. En français simple

EXEMPLES DE BONNES SUGGESTIONS:
- "Oui, c'est urgent"
- "Non, ça peut attendre"
- "À Bonamoussadi centre"
- "Combien ça coûte environ?"
- "Le disjoncteur a sauté"
- "Depuis ce matin"

GÉNÈRE 3 SUGGESTIONS COURTES ET PERTINENTES:
"""
        
        return prompt
    
    async def _generate_ai_suggestions(self, prompt: str) -> List[str]:
        """Generate suggestions using AI service"""
        try:
            # Get AI response
            ai_response = await self.ai_service.generate_response(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="Tu es un générateur de suggestions contextuelles. Réponds uniquement avec 3 suggestions courtes séparées par des retours à la ligne.",
                max_tokens=150,
                temperature=0.7
            )
            
            # Parse suggestions from AI response
            suggestions = []
            if ai_response:
                lines = ai_response.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    # Remove numbering, bullets, dashes
                    line = line.lstrip('123456789-•• ')
                    if line and len(line) <= 50:  # Reasonable length
                        suggestions.append(line)
            
            # Ensure we have exactly 3 suggestions
            if len(suggestions) < 3:
                suggestions.extend(self._get_default_suggestions()[:3-len(suggestions)])
            
            return suggestions[:3]  # Return max 3 suggestions
            
        except Exception as e:
            logger.error(f"Error getting AI suggestions: {e}")
            return self._get_default_suggestions()
    
    def _process_suggestions(
        self,
        suggestions: List[str],
        conversation_context: Dict[str, Any]
    ) -> List[str]:
        """Post-process and validate suggestions"""
        processed = []
        
        for suggestion in suggestions:
            # Clean up suggestion
            suggestion = suggestion.strip()
            
            # Remove quotes if present
            if suggestion.startswith('"') and suggestion.endswith('"'):
                suggestion = suggestion[1:-1]
            
            # Skip empty or too long suggestions
            if not suggestion or len(suggestion) > 50:
                continue
            
            # Skip duplicates
            if suggestion not in processed:
                processed.append(suggestion)
        
        # Ensure we have at least 2 suggestions
        if len(processed) < 2:
            processed.extend(self._get_contextual_fallback(conversation_context))
        
        return processed[:3]  # Max 3 suggestions
    
    def _get_contextual_fallback(self, conversation_context: Dict[str, Any]) -> List[str]:
        """Get contextual fallback suggestions based on conversation context"""
        extracted_info = conversation_context.get('extracted_info', {})
        
        # Service-specific suggestions
        service_type = extracted_info.get('service_type', '').lower()
        if 'plomberie' in service_type:
            return ["Fuite d'eau", "WC bouché", "Pression faible"]
        elif 'électricité' in service_type:
            return ["Disjoncteur sauté", "Prise défectueuse", "Coupure totale"]
        elif 'électroménager' in service_type:
            return ["Ne démarre plus", "Fait du bruit", "Surchauffe"]
        
        # Location-specific suggestions
        location = extracted_info.get('location', '').lower()
        if not location:
            return ["À Bonamoussadi", "À Akwa", "À Bonapriso"]
        
        # General suggestions
        return ["Oui exactement", "Non pas vraiment", "Pouvez-vous expliquer?"]
    
    def _get_fallback_suggestions(
        self,
        conversation_context: Dict[str, Any],
        ai_response: str
    ) -> List[str]:
        """Get fallback suggestions when AI generation fails"""
        try:
            # Analyze AI response for context
            ai_lower = ai_response.lower()
            
            # Urgency-related
            if 'urgent' in ai_lower or 'rapidement' in ai_lower:
                return ["Oui, c'est urgent", "Non, ça peut attendre", "Dans 2 heures"]
            
            # Location-related
            if 'où' in ai_lower or 'zone' in ai_lower or 'quartier' in ai_lower:
                return ["À Bonamoussadi", "À Akwa", "À Bonapriso"]
            
            # Service-related
            if 'service' in ai_lower or 'problème' in ai_lower:
                return ["Électricité", "Plomberie", "Électroménager"]
            
            # Description-related
            if 'décri' in ai_lower or 'expli' in ai_lower:
                return ["Oui exactement", "Plus de détails", "C'est différent"]
            
            # Default contextual suggestions
            return ["Continuez", "Oui", "Non"]
            
        except Exception as e:
            logger.error(f"Error in fallback suggestions: {e}")
            return self._get_default_suggestions()
    
    def _get_default_suggestions(self) -> List[str]:
        """Get default suggestions as last resort"""
        return [
            "Oui, exactement",
            "Non, pas vraiment", 
            "Pouvez-vous expliquer?"
        ]
    
    async def _get_conversation_history(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent conversation history for context"""
        try:
            # Get user from database
            user = self.db.query(User).filter(User.whatsapp_id == user_id).first()
            if not user:
                return []
            
            # Get recent conversations
            conversations = self.db.query(Conversation).filter(
                Conversation.user_id == user.id
            ).order_by(Conversation.created_at.desc()).limit(limit).all()
            
            history = []
            for conv in conversations:
                history.append({
                    'message': conv.message_content,
                    'timestamp': conv.created_at.isoformat(),
                    'ai_response': conv.ai_response
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []
    
    def get_suggestion_analytics(self) -> Dict[str, Any]:
        """Get analytics about suggestion usage"""
        try:
            # This would be implemented with proper analytics tracking
            return {
                "total_suggestions_generated": 0,
                "ai_success_rate": 0.95,
                "fallback_usage_rate": 0.05,
                "avg_suggestions_per_conversation": 2.3,
                "most_common_suggestions": [
                    "Oui, c'est urgent",
                    "À Bonamoussadi",
                    "Disjoncteur sauté"
                ]
            }
        except Exception as e:
            logger.error(f"Error getting suggestion analytics: {e}")
            return {}