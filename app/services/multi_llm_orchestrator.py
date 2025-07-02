"""
Multi-LLM Orchestration Service for Djobea AI
Intelligent routing and coordination of Claude, Gemini, and GPT-4 for optimal conversation handling
"""

import os
import json
import asyncio
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import logging

# AI Service Imports
import anthropic
from anthropic import Anthropic
from google import genai
from google.genai import types
import openai
from openai import OpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class LLMProvider(Enum):
    """Available LLM providers"""
    CLAUDE = "claude"
    GEMINI = "gemini"
    GPT4 = "gpt4"

class TaskType(Enum):
    """Types of AI tasks for intelligent routing"""
    CONVERSATION_ANALYSIS = "conversation_analysis"
    IMAGE_PROCESSING = "image_processing"
    COMPLEX_PROBLEM_SOLVING = "complex_problem_solving"
    EMOTION_DETECTION = "emotion_detection"
    PROVIDER_MATCHING = "provider_matching"
    CREATIVE_RESPONSES = "creative_responses"
    INTENT_EXTRACTION = "intent_extraction"
    ENTITY_EXTRACTION = "entity_extraction"
    RESPONSE_GENERATION = "response_generation"

@dataclass
class ConversationContext:
    """Comprehensive conversation context for multi-LLM processing"""
    user_id: str
    phone_number: str
    message: str
    conversation_history: List[Dict[str, Any]]
    current_state: str
    user_profile: Optional[Dict[str, Any]] = None
    detected_emotions: Optional[List[str]] = None
    extracted_entities: Optional[Dict[str, Any]] = None
    confidence_scores: Optional[Dict[str, float]] = None
    complexity_score: float = 0.0
    requires_multimodal: bool = False

@dataclass
class ProcessingResult:
    """Result from LLM processing"""
    response: str
    confidence: float
    extracted_data: Optional[Dict[str, Any]] = None
    system_actions: Optional[List[str]] = None
    next_steps: Optional[List[str]] = None
    emotional_context: Optional[Dict[str, Any]] = None
    provider: LLMProvider = LLMProvider.CLAUDE

class MultiLLMOrchestrator:
    """
    Central orchestrator for multi-LLM conversation processing
    Intelligently routes tasks to optimal LLM providers
    """
    
    def __init__(self):
        self.setup_llm_clients()
        self.setup_routing_rules()
        self.setup_conversation_states()
        
    def setup_llm_clients(self):
        """Initialize all LLM clients"""
        try:
            # Claude client
            self.claude_client = Anthropic(api_key=settings.anthropic_api_key)
            
            # Gemini client
            self.gemini_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
            
            # OpenAI client
            self.openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            
            logger.info("Multi-LLM clients initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM clients: {e}")
            raise
    
    def setup_routing_rules(self):
        """Setup intelligent routing rules for task distribution"""
        self.routing_rules = {
            TaskType.CONVERSATION_ANALYSIS: LLMProvider.CLAUDE,
            TaskType.IMAGE_PROCESSING: LLMProvider.GEMINI,
            TaskType.COMPLEX_PROBLEM_SOLVING: LLMProvider.GPT4,
            TaskType.EMOTION_DETECTION: LLMProvider.CLAUDE,
            TaskType.PROVIDER_MATCHING: LLMProvider.GEMINI,
            TaskType.CREATIVE_RESPONSES: LLMProvider.GPT4,
            TaskType.INTENT_EXTRACTION: LLMProvider.CLAUDE,
            TaskType.ENTITY_EXTRACTION: LLMProvider.CLAUDE,
            TaskType.RESPONSE_GENERATION: LLMProvider.CLAUDE  # Default fallback
        }
        
        # Intention-based routing for response generation
        self.intention_routing = {
            "plainte": LLMProvider.CLAUDE,      # Empathy and emotional management
            "urgence": LLMProvider.CLAUDE,      # Emotional intelligence
            "nouvelle_demande": LLMProvider.GEMINI,  # Prediction and matching
            "question_info": LLMProvider.GPT4,       # Creativity and detailed explanation
            "negociation_prix": LLMProvider.GPT4,    # Complex problem solving
            "modification_demande": LLMProvider.GEMINI,  # Smart prediction
            "suivi_statut": LLMProvider.CLAUDE,      # Professional communication
        }
    
    def setup_conversation_states(self):
        """Setup conversation state machine"""
        self.conversation_states = {
            "INITIAL": "Première interaction ou retour utilisateur",
            "COLLECTING_INFO": "Collecte des détails de la demande",
            "CONFIRMING_REQUEST": "Validation des informations collectées",
            "SEARCHING_PROVIDERS": "Recherche de prestataires disponibles",
            "PRESENTING_OPTIONS": "Présentation des options au client",
            "AWAITING_SELECTION": "Attente du choix du client",
            "PROVIDER_ASSIGNED": "Prestataire assigné, attente de prise de contact",
            "SERVICE_IN_PROGRESS": "Service en cours d'exécution",
            "AWAITING_FEEDBACK": "Attente du feedback post-service",
            "COMPLETED": "Cycle terminé avec succès",
            "ESCALATED": "Transfert vers support humain"
        }
        
        # Primary and secondary intentions
        self.primary_intentions = [
            "nouvelle_demande", "modification_demande", "annulation", 
            "suivi_statut", "plainte", "compliment", "question_info",
            "urgence", "negociation_prix", "reprogrammation"
        ]
        
        self.secondary_intentions = [
            "besoin_precision", "confirmation_action", "validation_etape",
            "demande_contact_direct", "evaluation_prestataire"
        ]

    async def process_conversation(self, context: ConversationContext) -> ProcessingResult:
        """
        Main conversation processing pipeline with multi-LLM orchestration
        """
        try:
            logger.info(f"Processing conversation for user {context.user_id}")
            
            # Step 1: Primary analysis with Claude
            primary_analysis = await self.analyze_with_claude(context)
            
            # Step 2: Determine complexity and routing needs
            context.complexity_score = self.calculate_complexity_score(primary_analysis)
            context.extracted_entities = primary_analysis.get("entities", {})
            context.detected_emotions = primary_analysis.get("emotions", [])
            
            # Step 3: Enhanced processing based on complexity
            if context.complexity_score > 0.7 or context.requires_multimodal:
                enhanced_result = await self.process_complex_request(context, primary_analysis)
            else:
                enhanced_result = await self.process_standard_request(context, primary_analysis)
            
            # Step 4: Generate final response
            final_response = await self.generate_final_response(context, enhanced_result)
            
            return final_response
            
        except Exception as e:
            logger.error(f"Error in conversation processing: {e}")
            return self.generate_fallback_response(context)

    async def analyze_with_claude(self, context: ConversationContext) -> Dict[str, Any]:
        """Primary conversation analysis using Claude"""
        try:
            analysis_prompt = f"""
            Analysez ce message WhatsApp d'un client de services à domicile au Cameroun (Douala, Bonamoussadi).

            Message: "{context.message}"
            Historique récent: {json.dumps(context.conversation_history[-3:] if context.conversation_history else [], ensure_ascii=False)}
            État actuel: {context.current_state}

            Extrayez et analysez:

            1. INTENTION PRIMAIRE (choisir une seule):
            {self.primary_intentions}

            2. INTENTION SECONDAIRE (optionnel):
            {self.secondary_intentions}

            3. ENTITÉS CRITIQUES:
            - Service: {{plomberie|électricité|réparation_électroménager|autre}}
            - Urgence: {{immédiat|aujourd'hui|demain|cette_semaine|flexible}}
            - Localisation: secteur précis dans Bonamoussadi
            - Budget: fourchette estimée ou contraintes
            - Contexte_émotionnel: {{calme|frustré|urgent|satisfait|inquiet|confus}}

            4. ÉMOTIONS DÉTECTÉES: Liste des émotions perçues

            5. NIVEAU DE COMPLEXITÉ (0.0-1.0): Évaluez la complexité de la demande

            6. ACTIONS SYSTÈME REQUISES: Actions à effectuer dans la base de données

            Répondez UNIQUEMENT en JSON valide avec ces clés exactes:
            {{
                "intention_primaire": "",
                "intention_secondaire": "",
                "entities": {{}},
                "emotions": [],
                "complexity_score": 0.0,
                "system_actions": [],
                "confidence": 0.0
            }}
            """
            
            response = self.claude_client.messages.create(
                model=settings.claude_model,
                max_tokens=1000,
                messages=[{"role": "user", "content": analysis_prompt}]
            )
            
            # Extract JSON from response
            content = response.content[0].text if hasattr(response.content[0], 'text') else str(response.content[0])
            analysis_result = json.loads(content)
            
            logger.info(f"Claude analysis completed with confidence: {analysis_result.get('confidence', 0.0)}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in Claude analysis: {e}")
            return {
                "intention_primaire": "question_info",
                "entities": {},
                "emotions": ["neutre"],
                "complexity_score": 0.3,
                "system_actions": [],
                "confidence": 0.5
            }

    async def process_complex_request(self, context: ConversationContext, primary_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Process complex requests using multiple LLMs"""
        try:
            # Use Gemini for provider matching and predictions
            gemini_enhancement = await self.enhance_with_gemini(context, primary_analysis)
            
            # Use GPT-4 for complex response generation if needed
            if context.complexity_score > 0.8:
                gpt4_response = await self.generate_with_gpt4(context, {**primary_analysis, **gemini_enhancement})
                return {**primary_analysis, **gemini_enhancement, **gpt4_response}
            
            return {**primary_analysis, **gemini_enhancement}
            
        except Exception as e:
            logger.error(f"Error in complex request processing: {e}")
            return primary_analysis

    async def enhance_with_gemini(self, context: ConversationContext, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance analysis with Gemini for provider matching and predictions"""
        try:
            enhancement_prompt = f"""
            Améliorez cette analyse pour un service à domicile au Cameroun (Douala, Bonamoussadi):

            Analyse initiale: {json.dumps(analysis, ensure_ascii=False)}
            Message: "{context.message}"
            État conversation: {context.current_state}

            Prédisez et optimisez:

            1. MATCHING PRESTATAIRES:
            - Type de prestataire optimal
            - Critères de sélection prioritaires
            - Timing optimal pour intervention

            2. PRÉDICTIONS UTILISATEUR:
            - Probabilité d'acceptation rapide
            - Préférences probables de prix
            - Moment optimal pour recontact

            3. RECOMMANDATIONS SYSTÈME:
            - Prochaines étapes optimales
            - Messages de suivi suggérés
            - Métriques à surveiller

            Répondez en JSON valide:
            {{
                "provider_matching": {{}},
                "user_predictions": {{}},
                "system_recommendations": {{}},
                "enhancement_confidence": 0.0
            }}
            """
            
            response = self.gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=enhancement_prompt
            )
            
            content = response.text or "{}"
            enhancement_result = json.loads(content)
            
            logger.info(f"Gemini enhancement completed")
            return enhancement_result
            
        except Exception as e:
            logger.error(f"Error in Gemini enhancement: {e}")
            return {"provider_matching": {}, "user_predictions": {}, "system_recommendations": {}}

    async def generate_with_gpt4(self, context: ConversationContext, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate complex responses using GPT-4"""
        try:
            # The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # Do not change this unless explicitly requested by the user
            generation_prompt = f"""
            Générez une réponse optimisée pour ce client de services à domicile au Cameroun:

            Analyse complète: {json.dumps(analysis, ensure_ascii=False)}
            Message: "{context.message}"
            Contexte: {context.current_state}

            Créez une réponse qui:
            1. Répond précisément à la demande
            2. Utilise un ton approprié au contexte émotionnel
            3. Propose des options multiples si pertinent
            4. Inclut des éléments culturels camerounais
            5. Optimise pour l'engagement WhatsApp

            Répondez en JSON valide:
            {{
                "response_text": "réponse complète avec emojis et formatage WhatsApp",
                "tone": "empathique|professionnel|rassurant|efficace",
                "options": ["option1", "option2", "option3"],
                "cultural_elements": [],
                "generation_confidence": 0.0
            }}
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": generation_prompt}],
                response_format={"type": "json_object"},
                max_tokens=1000
            )
            
            content = response.choices[0].message.content
            generation_result = json.loads(content)
            
            logger.info(f"GPT-4 generation completed")
            return generation_result
            
        except Exception as e:
            logger.error(f"Error in GPT-4 generation: {e}")
            return {"response_text": "", "tone": "professionnel", "options": []}

    async def process_standard_request(self, context: ConversationContext, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Process standard requests with single LLM"""
        intention = analysis.get("intention_primaire", "question_info")
        
        # Route to appropriate LLM based on intention
        if intention in self.intention_routing:
            provider = self.intention_routing[intention]
            
            if provider == LLMProvider.GEMINI:
                enhancement = await self.enhance_with_gemini(context, analysis)
                return {**analysis, **enhancement}
            elif provider == LLMProvider.GPT4:
                generation = await self.generate_with_gpt4(context, analysis)
                return {**analysis, **generation}
        
        # Default to Claude processing
        return analysis

    async def generate_final_response(self, context: ConversationContext, processing_result: Dict[str, Any]) -> ProcessingResult:
        """Generate the final response based on all processing results"""
        try:
            # If GPT-4 already generated a response, use it
            if "response_text" in processing_result and processing_result["response_text"]:
                return ProcessingResult(
                    response=processing_result["response_text"],
                    confidence=processing_result.get("generation_confidence", 0.8),
                    extracted_data=processing_result,
                    system_actions=processing_result.get("system_actions", []),
                    provider=LLMProvider.GPT4
                )
            
            # Otherwise, generate with Claude
            final_prompt = f"""
            Générez la réponse finale pour ce client WhatsApp au Cameroun:

            Analyse: {json.dumps(processing_result, ensure_ascii=False)}
            Message original: "{context.message}"
            État: {context.current_state}

            Créez une réponse WhatsApp professionnelle et engageante qui:
            - Répond directement à la demande
            - Utilise le bon ton émotionnel
            - Inclut des emojis appropriés
            - Propose des actions claires
            - Respecte la culture camerounaise

            Réponse en français naturel:
            """
            
            response = self.claude_client.messages.create(
                model=settings.claude_model,
                max_tokens=800,
                messages=[{"role": "user", "content": final_prompt}]
            )
            
            content = response.content[0].text if hasattr(response.content[0], 'text') else str(response.content[0])
            
            return ProcessingResult(
                response=content,
                confidence=processing_result.get("confidence", 0.8),
                extracted_data=processing_result,
                system_actions=processing_result.get("system_actions", []),
                emotional_context={
                    "emotions": processing_result.get("emotions", []),
                    "tone": processing_result.get("tone", "professionnel")
                },
                provider=LLMProvider.CLAUDE
            )
            
        except Exception as e:
            logger.error(f"Error generating final response: {e}")
            return self.generate_fallback_response(context)

    def calculate_complexity_score(self, analysis: Dict[str, Any]) -> float:
        """Calculate conversation complexity score"""
        base_score = analysis.get("complexity_score", 0.3)
        
        # Increase complexity for multiple entities
        entities = analysis.get("entities", {})
        if len(entities) > 3:
            base_score += 0.2
        
        # Increase for negative emotions
        emotions = analysis.get("emotions", [])
        negative_emotions = ["frustré", "inquiet", "urgent", "confus"]
        if any(emotion in emotions for emotion in negative_emotions):
            base_score += 0.3
        
        # Increase for complex intentions
        complex_intentions = ["negociation_prix", "modification_demande", "plainte"]
        if analysis.get("intention_primaire") in complex_intentions:
            base_score += 0.2
        
        return min(base_score, 1.0)

    def generate_fallback_response(self, context: ConversationContext) -> ProcessingResult:
        """Generate fallback response when other methods fail"""
        fallback_responses = [
            "Merci pour votre message. Je comprends votre demande et je vais vous aider rapidement. Pouvez-vous me donner plus de détails ?",
            "J'ai bien reçu votre demande. Un conseiller va analyser votre situation et vous répondre sous peu.",
            "Merci de me faire confiance pour vos services à domicile. Je traite votre demande en priorité."
        ]
        
        import random
        response = random.choice(fallback_responses)
        
        return ProcessingResult(
            response=response,
            confidence=0.6,
            system_actions=["LOG_FALLBACK_RESPONSE"],
            provider=LLMProvider.CLAUDE
        )

    async def process_multimodal_content(self, context: ConversationContext, media_content: Any) -> Dict[str, Any]:
        """Process images, videos, or audio content using Gemini"""
        try:
            if not context.requires_multimodal:
                return {}
            
            # Use Gemini for multimodal analysis
            analysis_prompt = f"""
            Analysez ce contenu média envoyé par un client de services à domicile au Cameroun.
            
            Context: {context.message}
            Service demandé: {context.extracted_entities.get('service', 'non spécifié')}
            
            Analysez et décrivez:
            1. Problème identifié
            2. Gravité/urgence (1-5)
            3. Coût estimé en XAF
            4. Recommandations
            
            Répondez en JSON français:
            """
            
            # This would be implemented based on the specific media type
            # For now, return a placeholder structure
            return {
                "media_analysis": {
                    "problems_detected": [],
                    "severity": 3,
                    "estimated_cost": "5000-15000 XAF",
                    "recommendations": []
                }
            }
            
        except Exception as e:
            logger.error(f"Error in multimodal processing: {e}")
            return {}

# Global orchestrator instance
multi_llm_orchestrator = MultiLLMOrchestrator()