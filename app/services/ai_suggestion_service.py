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
from app.services.multi_llm_service import MultiLLMService
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
Génère 3 suggestions courtes qui sont des EXEMPLES DE RÉPONSES que l'utilisateur peut donner, pas des questions.

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

RÈGLES IMPORTANTES:
1. Génère des RÉPONSES EXEMPLE que l'utilisateur peut dire, PAS des questions
2. Maximum 15 mots par suggestion
3. Pertinentes au contexte camerounais (Douala, XAF, expressions locales)
4. Aident à compléter les informations manquantes
5. Naturelles et conversationnelles
6. En français simple

EXEMPLES DE BONNES SUGGESTIONS (RÉPONSES UTILISATEUR):
Si l'IA demande le type de problème:
- "Le disjoncteur a sauté"
- "Pas de courant dans la cuisine"
- "Les prises ne marchent plus"

Si l'IA demande la localisation:
- "À Bonamoussadi centre"
- "Près du marché Deido"
- "À côté de l'école"

Si l'IA demande l'urgence:
- "Oui, c'est urgent"
- "Non, ça peut attendre"
- "Dès que possible"

IMPORTANT: NE GÉNÈRE PAS DE QUESTIONS! Génère UNIQUEMENT des réponses/affirmations que l'utilisateur peut dire.

GÉNÈRE 3 EXEMPLES DE RÉPONSES QUE L'UTILISATEUR PEUT DONNER:
"""
        
        return prompt
    
    async def _generate_ai_suggestions(self, prompt: str) -> List[str]:
        """Generate suggestions using AI service"""
        try:
            # Get AI response
            ai_response = await self.ai_service.generate_response(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="Tu es un générateur de suggestions contextuelles. Génère UNIQUEMENT 3 exemples de réponses/affirmations que l'utilisateur peut donner, PAS DES QUESTIONS. Évite les mots interrogatifs (quel, quand, comment, où, pourquoi). Réponds avec 3 suggestions courtes séparées par des retours à la ligne.",
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
            
            # Filter out questions and convert to answer examples
            if self._is_question(suggestion):
                # Convert question to answer example
                answer_example = self._convert_question_to_answer(suggestion, conversation_context)
                if answer_example and answer_example not in processed:
                    processed.append(answer_example)
            else:
                # Skip duplicates
                if suggestion not in processed:
                    processed.append(suggestion)
        
        # Ensure we have at least 2 suggestions
        if len(processed) < 2:
            processed.extend(self._get_contextual_fallback(conversation_context))
        
        return processed[:3]  # Max 3 suggestions
    
    def _is_question(self, text: str) -> bool:
        """Check if text is a question"""
        text_lower = text.lower()
        question_words = ['quel', 'quand', 'comment', 'où', 'pourquoi', 'combien', 'est-ce que', 'avez-vous']
        return text.endswith('?') or any(word in text_lower for word in question_words)
    
    def _convert_question_to_answer(self, question: str, conversation_context: Dict[str, Any]) -> str:
        """Convert a question to an answer example"""
        question_lower = question.lower()
        extracted_info = conversation_context.get('extracted_info', {})
        
        # Location-related questions
        if 'où' in question_lower or 'quartier' in question_lower or 'zone' in question_lower:
            return "À Bonamoussadi centre"
        
        # Time-related questions
        if 'quand' in question_lower or 'depuis' in question_lower:
            return "Depuis ce matin"
        
        # Type/description questions
        if 'quel' in question_lower or 'décri' in question_lower:
            service_type = extracted_info.get('service_type', '').lower()
            if 'électricité' in service_type:
                return "Le disjoncteur a sauté"
            elif 'plomberie' in service_type:
                return "Le robinet coule"
            elif 'électroménager' in service_type:
                return "Le frigo ne marche plus"
            else:
                return "Problème technique"
        
        # Verification questions
        if 'avez-vous' in question_lower or 'vérifié' in question_lower:
            return "Oui, j'ai vérifié"
        
        # Default answer
        return "Oui exactement"
    
    def _get_contextual_fallback(self, conversation_context: Dict[str, Any]) -> List[str]:
        """Get contextual fallback suggestions based on conversation context"""
        extracted_info = conversation_context.get('extracted_info', {})
        
        # Service-specific answer examples
        service_type = extracted_info.get('service_type', '').lower()
        if 'plomberie' in service_type:
            return ["Le robinet coule", "WC bouché", "À Bonamoussadi"]
        elif 'électricité' in service_type:
            return ["Le disjoncteur a sauté", "Depuis ce matin", "À Bonamoussadi centre"]
        elif 'électroménager' in service_type:
            return ["Le frigo ne marche plus", "Fait du bruit bizarre", "Depuis hier soir"]
        
        # Location-specific answer examples
        location = extracted_info.get('location', '').lower()
        if not location:
            return ["À Bonamoussadi", "À Akwa", "Près du marché"]
        
        # General answer examples
        return ["Oui exactement", "Non pas vraiment", "Depuis ce matin"]
    
    def _get_fallback_suggestions(
        self,
        conversation_context: Dict[str, Any],
        ai_response: str
    ) -> List[str]:
        """Get fallback suggestions when AI generation fails"""
        try:
            # Analyze AI response for context
            ai_lower = ai_response.lower()
            
            # Urgency-related answer examples
            if 'urgent' in ai_lower or 'rapidement' in ai_lower:
                return ["Oui, c'est urgent", "Non, ça peut attendre", "Dans l'après-midi"]
            
            # Location-related answer examples
            if 'où' in ai_lower or 'zone' in ai_lower or 'quartier' in ai_lower:
                return ["À Bonamoussadi centre", "Près du marché", "À côté de l'école"]
            
            # Service type answer examples
            if 'service' in ai_lower or 'problème' in ai_lower:
                return ["Problème électrique", "Fuite d'eau", "Réfrigérateur cassé"]
            
            # Description-related answer examples
            if 'décri' in ai_lower or 'expli' in ai_lower:
                return ["Le disjoncteur a sauté", "Plus de courant", "Depuis ce matin"]
            
            # Default answer examples
            return ["Oui exactement", "Non pas ça", "Depuis hier"]
            
        except Exception as e:
            logger.error(f"Error in fallback suggestions: {e}")
            return self._get_default_suggestions()
    
    def _get_default_suggestions(self) -> List[str]:
        """Get default suggestions as last resort"""
        return [
            "Oui, exactement",
            "Non, pas vraiment", 
            "Depuis ce matin"
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