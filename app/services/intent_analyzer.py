"""
Intent Analyzer for Djobea AI
Analyzes user messages to understand intentions naturally without exposing system complexity
"""

import re
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from anthropic import Anthropic

from app.config import get_settings
from app.services.ai_service import AIService
from loguru import logger

settings = get_settings()


class IntentAnalyzer:
    """
    Analyzes user intentions from natural language messages
    Provides context-aware intent detection for seamless conversations
    """
    
    def __init__(self):
        self.ai_service = AIService()
        
        # Cameroon-specific patterns and expressions
        self.cameroon_patterns = {
            "urgency_indicators": [
                "urgent", "emergency", "immediate", "tout de suite", "maintenant",
                "y a le feu", "grave", "catastrophe", "problème grave",
                "ça déborde", "water don enter house", "light don cut",
                "eau waka", "problème serious"
            ],
            "service_types": {
                "plomberie": [
                    "plomberie", "plumber", "eau", "water", "fuite", "leak", "wc", "toilette",
                    "robinet", "tap", "tuyau", "pipe", "douche", "shower", "lavabo", "sink",
                    "eau waka", "water no dey flow", "toilette don block", "pipe don burst",
                    "eau don finish", "robinet don spoil"
                ],
                "électricité": [
                    "électricité", "electric", "électrique", "courant", "light", "current",
                    "panne", "blackout", "interrupteur", "switch", "prise", "socket",
                    "courant a jump", "light don go", "no light", "electric don cut",
                    "switch don spoil", "socket no dey work"
                ],
                "réparation électroménager": [
                    "électroménager", "appliance", "frigo", "fridge", "réfrigérateur", "refrigerator",
                    "machine", "washing", "lave-linge", "four", "oven", "micro-onde", "microwave",
                    "frigo don spoil", "machine no dey work", "oven don bad", "AC don die",
                    "ventilateur", "fan", "climatiseur", "air condition"
                ]
            },
            "location_patterns": [
                "bonamoussadi", "bonassama", "douala", "littoral", "cameroun",
                "près de", "near", "côté", "around", "derrière", "behind",
                "devant", "front", "à côté de", "next to"
            ],
            "status_requests": [
                "statut", "status", "où en est", "comment ça avance", "nouvelles",
                "ma demande", "my request", "qu'est-ce qui se passe",
                "na how far", "how far", "wetin happen", "update"
            ],
            "cancellation_requests": [
                "annuler", "cancel", "arrêter", "stop", "plus besoin", "don't need",
                "changer d'avis", "changed mind", "i no want again", "forget am"
            ],
            "request_management": [
                "voir mes demandes", "mes demandes", "my requests", "show requests",
                "mes commandes", "my orders", "voir commandes", "show orders",
                "voir ma demande", "my request", "check my request", "voir commande",
                "vérifier demande", "check request", "what did i request", "qu'est-ce que j'ai demandé"
            ],
            "modification_requests": [
                "modifier", "modify", "changer", "change", "corriger", "correct",
                "ajuster", "adjust", "update", "mettre à jour", "edit", "éditer",
                "je veux changer", "i want to change", "peut-on modifier", "can we modify"
            ]
        }
    
    async def analyze_intent(
        self, 
        message: str, 
        conversation_history: List[Dict[str, Any]] = None,
        current_phase: str = None
    ) -> Dict[str, Any]:
        """
        Analyze user message to determine intent and extract relevant information
        Uses AI + pattern matching for robust intent detection
        """
        
        try:
            # Quick pattern-based analysis for common intents
            quick_analysis = self._quick_pattern_analysis(message)
            
            # AI-powered deep analysis for complex cases
            ai_analysis = await self._ai_intent_analysis(message, conversation_history, current_phase)
            
            # Combine results
            combined_analysis = self._combine_analyses(quick_analysis, ai_analysis, message)
            
            # Add confidence scoring
            combined_analysis["confidence"] = self._calculate_confidence(
                quick_analysis, ai_analysis, message
            )
            
            logger.info(f"Intent analysis result: {combined_analysis}")
            return combined_analysis
            
        except Exception as e:
            logger.error(f"Error in intent analysis: {e}")
            return self._fallback_analysis(message)
    
    def _quick_pattern_analysis(self, message: str) -> Dict[str, Any]:
        """Fast pattern-based intent detection for common cases"""
        
        message_lower = message.lower()
        
        # Check for status requests
        if any(pattern in message_lower for pattern in self.cameroon_patterns["status_requests"]):
            return {
                "primary_intent": "status_inquiry",
                "confidence": 0.9,
                "method": "pattern_matching"
            }
        
        # Check for request management
        if any(pattern in message_lower for pattern in self.cameroon_patterns["request_management"]):
            return {
                "primary_intent": "view_my_requests",
                "confidence": 0.9,
                "method": "pattern_matching"
            }
        
        # Check for modification requests
        if any(pattern in message_lower for pattern in self.cameroon_patterns["modification_requests"]):
            return {
                "primary_intent": "modify_request",
                "confidence": 0.9,
                "method": "pattern_matching"
            }
        
        # Check for cancellation requests
        if any(pattern in message_lower for pattern in self.cameroon_patterns["cancellation_requests"]):
            return {
                "primary_intent": "cancel_request",
                "confidence": 0.9,
                "method": "pattern_matching"
            }
        
        # Check for emergency indicators
        urgency_score = sum(
            1 for pattern in self.cameroon_patterns["urgency_indicators"]
            if pattern in message_lower
        )
        
        if urgency_score >= 2:  # Multiple urgency indicators
            return {
                "primary_intent": "emergency",
                "urgency_level": "high",
                "confidence": 0.85,
                "method": "pattern_matching"
            }
        
        # Check for service type mentions
        detected_services = []
        for service_type, patterns in self.cameroon_patterns["service_types"].items():
            if any(pattern in message_lower for pattern in patterns):
                detected_services.append(service_type)
        
        if detected_services:
            return {
                "primary_intent": "new_service_request",
                "detected_services": detected_services,
                "confidence": 0.7,
                "method": "pattern_matching"
            }
        
        return {
            "primary_intent": "general_inquiry",
            "confidence": 0.3,
            "method": "pattern_matching"
        }
    
    async def _ai_intent_analysis(
        self, 
        message: str, 
        conversation_history: List[Dict[str, Any]] = None,
        current_phase: str = None
    ) -> Dict[str, Any]:
        """AI-powered intent analysis for complex understanding"""
        
        # Build context
        context = ""
        if conversation_history:
            recent_messages = conversation_history[-3:]  # Last 3 exchanges
            context = "\n".join([
                f"User: {msg.get('content', '')}" if msg.get('sender') == 'user' 
                else f"Assistant: {msg.get('content', '')}"
                for msg in recent_messages
            ])
        
        system_prompt = f"""
        Tu es un analyste d'intentions pour Djobea AI, un service camerounais de mise en relation pour services à domicile.
        
        CONTEXTE CAMEROUNAIS:
        - Services: plomberie, électricité, réparation électroménager
        - Zone: Bonamoussadi, Douala
        - Langues: français, anglais, pidgin english
        
        INTENTIONS POSSIBLES:
        1. new_service_request - Nouvelle demande de service
        2. status_inquiry - Demande de statut
        3. view_my_requests - Voir mes demandes existantes
        4. modify_request - Modification de demande
        5. cancel_request - Demande d'annulation
        6. emergency - Situation d'urgence
        7. continue_previous - Suite d'une conversation
        8. general_inquiry - Question générale
        
        PHASE ACTUELLE: {current_phase or 'unknown'}
        
        CONTEXTE CONVERSATION:
        {context}
        
        Analyse le message et extrais:
        - L'intention principale
        - Les informations de service (type, localisation, description, urgence)
        - Le niveau de confiance
        - Les informations manquantes
        
        Réponds en JSON strict.
        """
        
        user_prompt = f"""
        Message utilisateur: "{message}"
        
        Analyse ce message et fournis un JSON avec:
        {{
            "primary_intent": "intention_principale",
            "secondary_intent": "intention_secondaire_optionnelle",
            "extracted_info": {{
                "service_type": "type_de_service_si_detecte",
                "location": "localisation_si_mentionnee",
                "description": "description_du_probleme",
                "urgency": "niveau_urgence",
                "time_preference": "preference_temporelle"
            }},
            "missing_info": ["champs_manquants"],
            "confidence": 0.0_to_1.0,
            "requires_follow_up": true_or_false,
            "context_clues": ["indices_contextuels"]
        }}
        """
        
        try:
            ai_messages = [
                {"role": "user", "content": user_prompt}
            ]
            
            response = await self.ai_service.generate_response(
                messages=ai_messages,
                system_prompt=system_prompt,
                max_tokens=800,
                temperature=0.3
            )
            
            # Extract JSON from response
            if '```json' in response:
                json_start = response.find('```json') + 7
                json_end = response.find('```', json_start)
                response = response[json_start:json_end].strip()
            elif '{' in response:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                response = response[json_start:json_end]
            
            analysis = json.loads(response)
            analysis["method"] = "ai_analysis"
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in AI intent analysis: {e}")
            return {
                "primary_intent": "general_inquiry",
                "confidence": 0.5,
                "method": "ai_fallback"
            }
    
    def _combine_analyses(
        self, 
        pattern_analysis: Dict[str, Any], 
        ai_analysis: Dict[str, Any], 
        message: str
    ) -> Dict[str, Any]:
        """Combine pattern matching and AI analysis results"""
        
        # Start with AI analysis as base (more comprehensive)
        combined = ai_analysis.copy()
        
        # Override with pattern analysis if it has higher confidence
        if pattern_analysis.get("confidence", 0) > ai_analysis.get("confidence", 0):
            combined.update(pattern_analysis)
        
        # Merge extracted info from both analyses
        pattern_info = pattern_analysis.get("extracted_info", {})
        ai_info = ai_analysis.get("extracted_info", {})
        
        combined_info = {}
        combined_info.update(ai_info)
        combined_info.update({k: v for k, v in pattern_info.items() if v})
        
        combined["extracted_info"] = combined_info
        
        # Enhanced service type detection
        if not combined_info.get("service_type"):
            detected_service = self._detect_service_type_enhanced(message)
            if detected_service:
                combined["extracted_info"]["service_type"] = detected_service
        
        # Enhanced location detection
        if not combined_info.get("location"):
            detected_location = self._detect_location_enhanced(message)
            if detected_location:
                combined["extracted_info"]["location"] = detected_location
        
        # Add analysis metadata
        combined["analysis_methods"] = [
            pattern_analysis.get("method", "unknown"),
            ai_analysis.get("method", "unknown")
        ]
        
        return combined
    
    def _detect_service_type_enhanced(self, message: str) -> Optional[str]:
        """Enhanced service type detection with Cameroon context"""
        
        message_lower = message.lower()
        
        # Score each service type
        service_scores = {}
        
        for service_type, patterns in self.cameroon_patterns["service_types"].items():
            score = 0
            for pattern in patterns:
                if pattern in message_lower:
                    # Weight longer patterns higher
                    score += len(pattern.split())
            
            if score > 0:
                service_scores[service_type] = score
        
        # Return service type with highest score
        if service_scores:
            return max(service_scores.items(), key=lambda x: x[1])[0]
        
        return None
    
    def _detect_location_enhanced(self, message: str) -> Optional[str]:
        """Enhanced location detection for Bonamoussadi area"""
        
        message_lower = message.lower()
        
        # Check for explicit location mentions
        location_indicators = [
            "bonamoussadi", "bonassama", "douala",
            "chez moi", "à la maison", "at home", "for house"
        ]
        
        for indicator in location_indicators:
            if indicator in message_lower:
                if indicator in ["chez moi", "à la maison", "at home", "for house"]:
                    return "Bonamoussadi"  # Default area
                return indicator.title()
        
        # Check for landmark references
        landmarks = [
            "carrefour", "marché", "market", "école", "school",
            "église", "church", "hôpital", "hospital"
        ]
        
        for landmark in landmarks:
            if landmark in message_lower:
                return f"Près de {landmark}, Bonamoussadi"
        
        return None
    
    def _calculate_confidence(
        self, 
        pattern_analysis: Dict[str, Any], 
        ai_analysis: Dict[str, Any], 
        message: str
    ) -> float:
        """Calculate overall confidence score"""
        
        pattern_conf = pattern_analysis.get("confidence", 0)
        ai_conf = ai_analysis.get("confidence", 0)
        
        # If both methods agree on intent, boost confidence
        if (pattern_analysis.get("primary_intent") == ai_analysis.get("primary_intent") and
            pattern_analysis.get("primary_intent") != "general_inquiry"):
            return min(0.95, (pattern_conf + ai_conf) / 2 + 0.2)
        
        # Otherwise, take the higher confidence
        return max(pattern_conf, ai_conf)
    
    def _fallback_analysis(self, message: str) -> Dict[str, Any]:
        """Fallback analysis when all methods fail"""
        
        return {
            "primary_intent": "general_inquiry",
            "extracted_info": {},
            "missing_info": ["service_type", "location", "description"],
            "confidence": 0.3,
            "requires_follow_up": True,
            "method": "fallback"
        }