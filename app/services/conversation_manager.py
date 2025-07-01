"""
Djobea AI Conversation Manager - Sprint 2
Handles intelligent conversation understanding and information extraction
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
import re
from dataclasses import dataclass
from anthropic import Anthropic
from app.config import get_settings
from loguru import logger
settings = get_settings()

@dataclass
class RequestInfo:
    """Structured information extracted from conversation"""
    service_type: Optional[str] = None  # plomberie, électricité, réparation électroménager
    location: Optional[str] = None      # address in Bonamoussadi
    description: Optional[str] = None   # problem details
    urgency: Optional[str] = None       # urgent, cet après-midi, demain, etc.
    confidence_score: float = 0.0       # extraction confidence

    def is_complete(self) -> bool:
        """Check if all required information is present"""
        return all([
            self.service_type,
            self.location,
            self.description,
            self.urgency
        ])

    def missing_fields(self) -> List[str]:
        """Get list of missing required fields"""
        missing = []
        if not self.service_type: missing.append("service_type")
        if not self.location: missing.append("location")
        if not self.description: missing.append("description") 
        if not self.urgency: missing.append("urgency")
        return missing


class DjobeaConversationManager:
    """
    LangChain-inspired conversation manager for Djobea AI
    Handles multi-turn conversations and intelligent extraction
    """
    
    def __init__(self):
        """Initialize conversation manager with Claude API"""
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.claude_model
        self.conversation_memory: Dict[str, List[Dict]] = {}
        
        # Comprehensive Cameroon-specific expressions
        self.local_expressions = {
            # Electrical issues
            "courant a jump": "panne électrique",
            "light don go": "coupure électricité", 
            "no current": "pas d'électricité",
            "current no dey": "pas d'électricité",
            
            # Water issues
            "coule-coule": "fuite d'eau",
            "wata no dey comot": "pas d'eau",
            "pipe don burst": "canalisation cassée",
            "water no dey flow": "pas d'eau",
            
            # General expressions
            "don spoil": "cassé",
            "no dey work": "ne marche pas",
            "i want make": "je veux que"
        }
        
    def process_message(self, user_id: str, message: str) -> Tuple[str, RequestInfo]:
        """
        Process incoming message and return response with extracted info
        
        Args:
            user_id: WhatsApp user identifier
            message: User message content
            
        Returns:
            Tuple of (bot_response, extracted_request_info)
        """
        try:
            # Normalize message for better understanding
            normalized_message = self._normalize_message(message)
            
            # Get conversation history
            history = self.conversation_memory.get(user_id, [])
            
            # Add current message to history
            history.append({
                "role": "user",
                "content": normalized_message,
                "timestamp": datetime.now().isoformat()
            })
            
            # Extract request information
            request_info = self.extract_request_info(history)
            
            # Generate appropriate response
            response = self.generate_response(history, request_info)
            
            # Add bot response to history
            history.append({
                "role": "assistant", 
                "content": response,
                "timestamp": datetime.now().isoformat()
            })
            
            # Update memory
            self.conversation_memory[user_id] = history[-10:]  # Keep last 10 messages
            
            logger.info(f"Processed message for user {user_id}, confidence: {request_info.confidence_score}")
            
            return response, request_info
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return self._get_error_response(), RequestInfo()
    
    def extract_request_info(self, conversation_history: List[Dict]) -> RequestInfo:
        """
        Extract service request information from conversation using Claude
        
        Args:
            conversation_history: List of conversation messages
            
        Returns:
            RequestInfo object with extracted data
        """
        try:
            # Build conversation context
            context = self._build_conversation_context(conversation_history)
            
            extraction_prompt = f"""
Tu es un assistant expert pour extraire des informations de demandes de services à domicile au Cameroun.

CONTEXTE: Djobea AI connecte les clients aux prestataires à Douala (quartier Bonamoussadi).

SERVICES DISPONIBLES:
- plomberie (robinet, tuyaux, WC, douche, évacuation)
- électricité (prises, câbles, disjoncteur, éclairage, "courant")
- réparation électroménager (frigo, machine à laver, climatiseur, TV)

CONVERSATION:
{context}

EXPRESSIONS LOCALES À COMPRENDRE:
- "courant a jump" = panne électrique
- "coule-coule" = fuite d'eau  
- "no current" = pas d'électricité
- "wata no dey comot" = pas d'eau
- "light don go" = coupure électricité

TÂCHE: Extrais ces 4 informations OBLIGATOIRES au format JSON:
{{
    "service_type": "plomberie|électricité|réparation électroménager|null",
    "location": "adresse précise à Bonamoussadi ou null",
    "description": "description détaillée du problème ou null", 
    "urgency": "urgent|cet après-midi|demain|cette semaine|null",
    "confidence_score": 0.0-1.0
}}

Si une information n'est pas claire, mets "null". Sois précis sur la localisation dans Bonamoussadi.
"""

            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[{"role": "user", "content": extraction_prompt}]
            )
            
            # Parse JSON response from Claude
            response_text = response.content[0].text if response.content else ""
            extracted_data = json.loads(response_text.strip())
            
            return RequestInfo(
                service_type=extracted_data.get("service_type"),
                location=extracted_data.get("location"),
                description=extracted_data.get("description"),
                urgency=extracted_data.get("urgency"),
                confidence_score=float(extracted_data.get("confidence_score", 0.0))
            )
            
        except Exception as e:
            logger.error(f"Error extracting request info: {str(e)}")
            return RequestInfo()
    
    def generate_response(self, conversation_history: List[Dict], request_info: RequestInfo) -> str:
        """
        Generate contextual response based on conversation and extracted info
        
        Args:
            conversation_history: Conversation messages
            request_info: Currently extracted information
            
        Returns:
            Generated response string
        """
        try:
            if request_info.is_complete():
                return self._generate_confirmation_response(request_info)
            else:
                return self._generate_question_response(conversation_history, request_info)
                
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return self._get_error_response()
    
    def _normalize_message(self, message: str) -> str:
        """Normalize message by handling local expressions and typos"""
        normalized = message.lower().strip()
        
        # Replace local expressions
        for local_expr, standard_expr in self.local_expressions.items():
            normalized = normalized.replace(local_expr, standard_expr)
        
        # Basic typo corrections for common WhatsApp abbreviations
        typo_corrections = {
            "slt": "salut",
            "bjr": "bonjour", 
            "stp": "s'il te plaît",
            "svp": "s'il vous plaît",
            "pb": "problème",
            "qd": "quand",
            "tt": "tout",
            "pr": "pour"
        }
        
        for typo, correction in typo_corrections.items():
            normalized = re.sub(rf'\b{typo}\b', correction, normalized)
        
        return normalized
    
    def _build_conversation_context(self, history: List[Dict]) -> str:
        """Build formatted conversation context for prompts"""
        context_parts = []
        for msg in history[-5:]:  # Last 5 messages for context
            role = "Client" if msg["role"] == "user" else "Assistant"
            context_parts.append(f"{role}: {msg['content']}")
        return "\n".join(context_parts)
    
    def _generate_confirmation_response(self, request_info: RequestInfo) -> str:
        """Generate confirmation message when all info is collected"""
        return f"""Parfait ! J'ai bien compris votre demande :

🔧 **Service** : {request_info.service_type}
📍 **Localisation** : {request_info.location}  
📝 **Problème** : {request_info.description}
⏰ **Délai** : {request_info.urgency}

Je recherche maintenant un prestataire disponible dans votre zone. Vous recevrez une notification dès qu'un professionnel accepte votre demande.

💰 **Commission Djobea** : 15% du montant de la prestation
⏱️ **Temps de réponse** : Généralement sous 30 minutes

Votre demande est en cours de traitement !"""
    
    def _generate_question_response(self, history: List[Dict], request_info: RequestInfo) -> str:
        """Generate question to collect missing information"""
        try:
            context = self._build_conversation_context(history)
            missing_fields = request_info.missing_fields()
            
            current_info = {
                "service_type": request_info.service_type,
                "location": request_info.location,
                "description": request_info.description,
                "urgency": request_info.urgency
            }
            
            question_prompt = f"""
Tu es l'assistant Djobea AI. Tu dois poser UNE question naturelle en français pour obtenir les informations manquantes.

CONVERSATION ACTUELLE:
{context}

INFORMATIONS DÉJÀ OBTENUES:
{json.dumps(current_info, indent=2)}

INFORMATIONS MANQUANTES: {', '.join(missing_fields)}

RÈGLES:
1. Pose UNE seule question claire et naturelle
2. Sois chaleureux et professionnel  
3. Utilise le contexte camerounais (Bonamoussadi, Douala)
4. Si c'est le premier message, commence par saluer
5. Donne des exemples si nécessaire

EXEMPLES DE QUESTIONS SELON CE QUI MANQUE:
- Service manquant: "Quel type de service vous faut-il ? (plomberie, électricité, ou réparation électroménager)"
- Location manquante: "Pouvez-vous me donner votre adresse précise à Bonamoussadi ?"
- Description manquante: "Pouvez-vous me décrire exactement le problème ?"  
- Délai manquant: "Pour quand souhaitez-vous l'intervention ? (urgent, cet après-midi, demain...)"

Génère UNE question appropriée:
"""
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                messages=[{"role": "user", "content": question_prompt}]
            )
            
            return response.content[0].text.strip()
            
        except Exception as e:
            logger.error(f"Error generating question: {str(e)}")
            return "Bonjour ! Comment puis-je vous aider avec vos besoins en plomberie, électricité ou réparation électroménager à Bonamoussadi ?"
    
    def _get_error_response(self) -> str:
        """Fallback response for errors"""
        return """Désolé, j'ai rencontré un problème technique. 

Pouvez-vous me dire :
1. Quel service vous faut-il ? (plomberie, électricité, réparation électroménager)
2. Votre adresse à Bonamoussadi ?
3. Le problème exact ?
4. Pour quand ? (urgent, aujourd'hui, demain...)

Je vous aiderai dès que possible !"""
    
    def get_conversation_history(self, user_id: str) -> List[Dict]:
        """Get conversation history for a user"""
        return self.conversation_memory.get(user_id, [])
    
    def clear_conversation(self, user_id: str) -> None:
        """Clear conversation history for a user"""
        if user_id in self.conversation_memory:
            del self.conversation_memory[user_id]
        logger.info(f"Cleared conversation for user {user_id}")


# Global conversation manager instance
conversation_manager = DjobeaConversationManager()