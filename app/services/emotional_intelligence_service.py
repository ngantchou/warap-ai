"""
Emotional Intelligence Service for Djobea AI
Handles emotional analysis, cultural adaptation, and empathetic responses
"""

import json
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
from loguru import logger

from app.models.database_models import User, Conversation, ServiceRequest
from app.models.cultural_models import (
    EmotionalProfile, ConversationEmotion, CulturalContext, 
    EmotionalResponse, CulturalSensitivityRule, CulturalCalendar
)
from app.services.ai_service import AIService
from app.config import get_settings


class EmotionalIntelligenceService:
    """Service for emotional analysis and culturally-aware responses"""
    
    def __init__(self, ai_service: AIService):
        self.ai_service = ai_service
        self.settings = get_settings()
        
        # Emotional indicators
        self.stress_indicators = [
            "urgent", "pressé", "vite", "rapide", "emergency", "urgence",
            "help", "aide", "problème grave", "serious problem", "pas le temps",
            "maintenant", "immédiatement", "right now", "tout de suite"
        ]
        
        self.frustration_indicators = [
            "énervé", "frustrated", "angry", "fâché", "disappointed", "déçu",
            "tired", "fatigué", "fed up", "marre", "enough", "assez"
        ]
        
        self.excitement_indicators = [
            "excited", "content", "happy", "heureux", "great", "super",
            "excellent", "parfait", "amazing", "incroyable", "wonderful"
        ]
        
        # Cultural expressions database
        self.cultural_expressions = {
            "douala": {
                "greetings": {
                    "morning": ["Bonjour", "Good morning", "Comment tu as dormi?"],
                    "afternoon": ["Bon après-midi", "Good afternoon", "Comment ça va?"],
                    "evening": ["Bonsoir", "Good evening", "Tu es rentré?"]
                },
                "expressions": {
                    "encouragement": ["Courage mon frère", "Tu peux le faire", "On est ensemble"],
                    "empathy": ["Je comprends ta situation", "C'est dur vraiment", "On va t'aider"],
                    "celebration": ["Félicitations!", "Tu as bien fait!", "C'est formidable!"]
                },
                "respect_phrases": {
                    "elder": ["Monsieur", "Madame", "Papa", "Maman"],
                    "authority": ["Chef", "Patron", "Docteur", "Professeur"]
                }
            }
        }

    async def analyze_conversation_emotion(
        self, 
        db: Session, 
        conversation_id: int, 
        message: str, 
        user_id: int
    ) -> ConversationEmotion:
        """Analyze emotional content of a conversation message"""
        
        try:
            # Get user's cultural context
            user = db.query(User).filter(User.id == user_id).first()
            emotional_profile = db.query(EmotionalProfile).filter(
                EmotionalProfile.user_id == user_id
            ).first()
            
            # Prepare analysis prompt
            analysis_prompt = f"""
            Analyze the emotional content of this WhatsApp message from a user in Cameroon:
            
            Message: "{message}"
            
            Consider:
            1. Primary emotion (joy, fear, anger, sadness, surprise, neutral)
            2. Emotional intensity (0.0 to 1.0)
            3. Sentiment score (-1.0 to 1.0)
            4. Urgency level (true/false)
            5. Stress indicators
            6. Politeness level (0.0 to 1.0)
            7. Cultural expressions used
            8. Recommended response tone
            9. Required empathy level
            
            Return analysis as JSON with these fields:
            {{
                "primary_emotion": "emotion_name",
                "emotion_intensity": 0.0,
                "sentiment_score": 0.0,
                "urgency_detected": false,
                "stress_indicators": ["indicator1", "indicator2"],
                "politeness_level": 0.0,
                "cultural_expressions": ["expression1"],
                "respect_markers": ["marker1"],
                "community_references": ["reference1"],
                "recommended_tone": "tone_name",
                "empathy_level": "low/medium/high",
                "cultural_sensitivity_needed": "low/medium/high"
            }}
            """
            
            # Get AI analysis
            ai_response = await self.ai_service.analyze_message(analysis_prompt)
            
            try:
                emotion_data = json.loads(ai_response)
            except json.JSONDecodeError:
                # Fallback analysis
                emotion_data = self._fallback_emotion_analysis(message)
            
            # Create conversation emotion record
            conversation_emotion = ConversationEmotion(
                conversation_id=conversation_id,
                user_id=user_id,
                primary_emotion=emotion_data.get("primary_emotion", "neutral"),
                emotion_intensity=float(emotion_data.get("emotion_intensity", 0.5)),
                secondary_emotions=emotion_data.get("secondary_emotions", []),
                sentiment_score=float(emotion_data.get("sentiment_score", 0.0)),
                confidence_level=float(emotion_data.get("confidence_level", 0.7)),
                urgency_detected=bool(emotion_data.get("urgency_detected", False)),
                stress_indicators=emotion_data.get("stress_indicators", []),
                politeness_level=float(emotion_data.get("politeness_level", 0.5)),
                cultural_expressions_used=emotion_data.get("cultural_expressions", []),
                respect_markers=emotion_data.get("respect_markers", []),
                community_references=emotion_data.get("community_references", []),
                recommended_tone=emotion_data.get("recommended_tone", "respectful"),
                empathy_level=emotion_data.get("empathy_level", "medium"),
                cultural_sensitivity_needed=emotion_data.get("cultural_sensitivity_needed", "medium"),
                ai_model_version=self.settings.claude_model
            )
            
            db.add(conversation_emotion)
            db.commit()
            db.refresh(conversation_emotion)
            
            # Update user's emotional profile
            await self._update_emotional_profile(db, user_id, conversation_emotion)
            
            return conversation_emotion
            
        except Exception as e:
            logger.error(f"Error analyzing conversation emotion: {e}")
            # Return default emotion analysis
            return self._create_default_emotion_analysis(db, conversation_id, user_id)

    async def generate_emotionally_aware_response(
        self,
        db: Session,
        user_id: int,
        situation: str,
        service_request: Optional[ServiceRequest] = None,
        conversation_emotion: Optional[ConversationEmotion] = None
    ) -> str:
        """Generate culturally and emotionally appropriate response"""
        
        try:
            # Get user's emotional profile and cultural context
            emotional_profile = db.query(EmotionalProfile).filter(
                EmotionalProfile.user_id == user_id
            ).first()
            
            if not emotional_profile:
                emotional_profile = await self._create_default_emotional_profile(db, user_id)
            
            cultural_context = None
            if emotional_profile.cultural_context_id:
                cultural_context = db.query(CulturalContext).filter(
                    CulturalContext.id == emotional_profile.cultural_context_id
                ).first()
            
            # Determine response characteristics
            response_tone = self._determine_response_tone(conversation_emotion, emotional_profile)
            empathy_level = self._determine_empathy_level(conversation_emotion, emotional_profile)
            cultural_sensitivity = self._determine_cultural_sensitivity(cultural_context, emotional_profile)
            
            # Check for existing response template
            existing_response = db.query(EmotionalResponse).filter(
                EmotionalResponse.trigger_situation == situation,
                EmotionalResponse.language == emotional_profile.language_preference,
                EmotionalResponse.formality_level == response_tone
            ).first()
            
            if existing_response:
                response = self._personalize_response_template(
                    existing_response.response_template,
                    emotional_profile,
                    cultural_context,
                    service_request
                )
                
                # Update usage statistics
                existing_response.usage_count += 1
                existing_response.last_used = datetime.now(timezone.utc)
                db.commit()
                
                return response
            
            # Generate new response using AI
            response_prompt = f"""
            Generate an emotionally intelligent and culturally appropriate WhatsApp response for a user in Cameroon (Douala region).
            
            Situation: {situation}
            User's emotional state: {conversation_emotion.primary_emotion if conversation_emotion else 'neutral'}
            Recommended tone: {response_tone}
            Empathy level: {empathy_level}
            Cultural sensitivity: {cultural_sensitivity}
            Language preference: {emotional_profile.language_preference}
            
            Cultural context:
            - Location: Douala, Cameroon
            - Respect for community and elders
            - Mix of French/English/local expressions
            - Business customs and politeness
            
            Requirements:
            1. Use appropriate cultural expressions and greetings
            2. Match the emotional tone to the user's state
            3. Include empathy and understanding
            4. Use WhatsApp-appropriate formatting with emojis
            5. Keep response concise but warm
            6. Include next steps or helpful guidance
            
            Generate a response that feels natural and culturally authentic.
            """
            
            ai_response = await self.ai_service.generate_response(response_prompt)
            
            # Apply cultural sensitivity filters
            filtered_response = await self._apply_cultural_sensitivity_filters(
                db, ai_response, cultural_context
            )
            
            # Store new response template for future use
            await self._store_response_template(
                db, situation, filtered_response, response_tone, 
                emotional_profile.language_preference, empathy_level
            )
            
            return filtered_response
            
        except Exception as e:
            logger.error(f"Error generating emotionally aware response: {e}")
            return self._get_fallback_response(situation, emotional_profile.language_preference if emotional_profile else "français")

    async def detect_emergency_situation(
        self,
        message: str,
        conversation_emotion: Optional[ConversationEmotion] = None
    ) -> bool:
        """Detect if the situation requires emergency response"""
        
        emergency_keywords = [
            "emergency", "urgence", "danger", "fire", "feu", "flood", "inondation",
            "accident", "blessé", "injured", "hospital", "hôpital", "police",
            "ambulance", "help", "aide", "secours", "rescue"
        ]
        
        # Check for emergency keywords
        message_lower = message.lower()
        has_emergency_keywords = any(keyword in message_lower for keyword in emergency_keywords)
        
        # Check emotional indicators
        high_urgency = False
        if conversation_emotion:
            high_urgency = (
                conversation_emotion.urgency_detected and
                conversation_emotion.emotion_intensity > 0.8 and
                conversation_emotion.primary_emotion in ["fear", "panic", "distress"]
            )
        
        return has_emergency_keywords or high_urgency

    async def generate_celebration_message(
        self,
        db: Session,
        user_id: int,
        achievement: str,
        service_request: Optional[ServiceRequest] = None
    ) -> str:
        """Generate celebration and encouragement message"""
        
        emotional_profile = db.query(EmotionalProfile).filter(
            EmotionalProfile.user_id == user_id
        ).first()
        
        if not emotional_profile or not emotional_profile.celebrates_small_wins:
            return ""
        
        celebration_templates = {
            "français": [
                "🎉 Félicitations ! {achievement}",
                "👏 Bravo ! {achievement}",
                "✨ Excellent ! {achievement}",
                "🌟 Très bien ! {achievement}"
            ],
            "english": [
                "🎉 Congratulations! {achievement}",
                "👏 Well done! {achievement}",
                "✨ Excellent! {achievement}",
                "🌟 Great job! {achievement}"
            ]
        }
        
        language = emotional_profile.language_preference
        templates = celebration_templates.get(language, celebration_templates["français"])
        
        import random
        template = random.choice(templates)
        
        return template.format(achievement=achievement)

    async def adapt_message_for_cultural_context(
        self,
        db: Session,
        message: str,
        user_id: int,
        cultural_context: Optional[CulturalContext] = None
    ) -> str:
        """Adapt message for cultural context and sensitivity"""
        
        if not cultural_context:
            emotional_profile = db.query(EmotionalProfile).filter(
                EmotionalProfile.user_id == user_id
            ).first()
            
            if emotional_profile and emotional_profile.cultural_context_id:
                cultural_context = db.query(CulturalContext).filter(
                    CulturalContext.id == emotional_profile.cultural_context_id
                ).first()
        
        if not cultural_context:
            return message
        
        # Apply cultural adaptations
        adapted_message = message
        
        # Add appropriate greetings based on time
        current_hour = datetime.now().hour
        if current_hour < 12:
            greeting_time = "morning"
        elif current_hour < 18:
            greeting_time = "afternoon"
        else:
            greeting_time = "evening"
        
        # Get regional expressions
        region_expressions = self.cultural_expressions.get(
            cultural_context.region.lower(), 
            self.cultural_expressions["douala"]
        )
        
        # Apply cultural sensitivity rules
        sensitivity_rules = db.query(CulturalSensitivityRule).filter(
            CulturalSensitivityRule.is_active == True
        ).all()
        
        for rule in sensitivity_rules:
            if rule.applicable_regions and cultural_context.region not in rule.applicable_regions:
                continue
                
            # Apply prohibited words filter
            if rule.prohibited_words:
                for word in rule.prohibited_words:
                    if word.lower() in adapted_message.lower():
                        # Replace with alternative if available
                        if rule.alternative_suggestions:
                            adapted_message = adapted_message.replace(
                                word, 
                                rule.alternative_suggestions[0]
                            )
        
        return adapted_message

    def _fallback_emotion_analysis(self, message: str) -> Dict[str, Any]:
        """Fallback emotion analysis when AI fails"""
        
        message_lower = message.lower()
        
        # Detect stress indicators
        stress_found = any(indicator in message_lower for indicator in self.stress_indicators)
        frustration_found = any(indicator in message_lower for indicator in self.frustration_indicators)
        excitement_found = any(indicator in message_lower for indicator in self.excitement_indicators)
        
        if stress_found:
            primary_emotion = "stress"
            intensity = 0.8
            sentiment = -0.3
        elif frustration_found:
            primary_emotion = "frustration"
            intensity = 0.7
            sentiment = -0.5
        elif excitement_found:
            primary_emotion = "joy"
            intensity = 0.8
            sentiment = 0.7
        else:
            primary_emotion = "neutral"
            intensity = 0.5
            sentiment = 0.0
        
        return {
            "primary_emotion": primary_emotion,
            "emotion_intensity": intensity,
            "sentiment_score": sentiment,
            "urgency_detected": stress_found,
            "stress_indicators": [ind for ind in self.stress_indicators if ind in message_lower],
            "politeness_level": 0.6,
            "cultural_expressions": [],
            "respect_markers": [],
            "community_references": [],
            "recommended_tone": "empathetic" if sentiment < 0 else "respectful",
            "empathy_level": "high" if sentiment < -0.3 else "medium",
            "cultural_sensitivity_needed": "medium"
        }

    def _create_default_emotion_analysis(
        self, 
        db: Session, 
        conversation_id: int, 
        user_id: int
    ) -> ConversationEmotion:
        """Create default emotion analysis"""
        
        conversation_emotion = ConversationEmotion(
            conversation_id=conversation_id,
            user_id=user_id,
            primary_emotion="neutral",
            emotion_intensity=0.5,
            sentiment_score=0.0,
            confidence_level=0.3,
            urgency_detected=False,
            stress_indicators=[],
            politeness_level=0.6,
            cultural_expressions_used=[],
            respect_markers=[],
            community_references=[],
            recommended_tone="respectful",
            empathy_level="medium",
            cultural_sensitivity_needed="medium",
            ai_model_version=self.settings.claude_model
        )
        
        db.add(conversation_emotion)
        db.commit()
        db.refresh(conversation_emotion)
        
        return conversation_emotion

    async def _update_emotional_profile(
        self,
        db: Session,
        user_id: int,
        conversation_emotion: ConversationEmotion
    ) -> None:
        """Update user's emotional profile based on conversation"""
        
        emotional_profile = db.query(EmotionalProfile).filter(
            EmotionalProfile.user_id == user_id
        ).first()
        
        if not emotional_profile:
            emotional_profile = await self._create_default_emotional_profile(db, user_id)
        
        # Update current mood and levels
        emotional_profile.current_mood = conversation_emotion.primary_emotion
        emotional_profile.stress_level = min(1.0, max(0.0, 
            emotional_profile.stress_level * 0.8 + conversation_emotion.emotion_intensity * 0.2
            if conversation_emotion.primary_emotion == "stress" else emotional_profile.stress_level * 0.9
        ))
        
        emotional_profile.frustration_level = min(1.0, max(0.0,
            emotional_profile.frustration_level * 0.8 + conversation_emotion.emotion_intensity * 0.2
            if conversation_emotion.primary_emotion == "frustration" else emotional_profile.frustration_level * 0.9
        ))
        
        emotional_profile.satisfaction_level = min(1.0, max(0.0,
            emotional_profile.satisfaction_level * 0.8 + conversation_emotion.sentiment_score * 0.2
        ))
        
        # Update preferred tone based on conversation
        if conversation_emotion.recommended_tone:
            emotional_profile.preferred_tone = conversation_emotion.recommended_tone
        
        emotional_profile.last_analysis = datetime.now(timezone.utc)
        emotional_profile.updated_at = datetime.now(timezone.utc)
        
        db.commit()

    async def _create_default_emotional_profile(
        self,
        db: Session,
        user_id: int
    ) -> EmotionalProfile:
        """Create default emotional profile for user"""
        
        # Get default cultural context for Douala
        cultural_context = db.query(CulturalContext).filter(
            CulturalContext.region == "Douala"
        ).first()
        
        emotional_profile = EmotionalProfile(
            user_id=user_id,
            current_mood="neutral",
            stress_level=0.0,
            frustration_level=0.0,
            satisfaction_level=0.5,
            preferred_tone="respectful",
            response_style="empathetic",
            cultural_sensitivity="high",
            cultural_context_id=cultural_context.id if cultural_context else None,
            language_preference="français",
            celebrates_small_wins=True,
            appreciates_encouragement=True,
            values_community_feedback=True
        )
        
        db.add(emotional_profile)
        db.commit()
        db.refresh(emotional_profile)
        
        return emotional_profile

    def _determine_response_tone(
        self,
        conversation_emotion: Optional[ConversationEmotion],
        emotional_profile: EmotionalProfile
    ) -> str:
        """Determine appropriate response tone"""
        
        if not conversation_emotion:
            return emotional_profile.preferred_tone
        
        if conversation_emotion.urgency_detected:
            return "urgent"
        elif conversation_emotion.primary_emotion in ["frustration", "anger"]:
            return "calming"
        elif conversation_emotion.primary_emotion in ["joy", "excitement"]:
            return "celebratory"
        elif conversation_emotion.primary_emotion in ["fear", "anxiety"]:
            return "reassuring"
        else:
            return emotional_profile.preferred_tone

    def _determine_empathy_level(
        self,
        conversation_emotion: Optional[ConversationEmotion],
        emotional_profile: EmotionalProfile
    ) -> str:
        """Determine required empathy level"""
        
        if not conversation_emotion:
            return "medium"
        
        if conversation_emotion.sentiment_score < -0.5:
            return "high"
        elif conversation_emotion.emotion_intensity > 0.7:
            return "high"
        elif conversation_emotion.primary_emotion in ["frustration", "sadness", "fear"]:
            return "high"
        else:
            return "medium"

    def _determine_cultural_sensitivity(
        self,
        cultural_context: Optional[CulturalContext],
        emotional_profile: EmotionalProfile
    ) -> str:
        """Determine required cultural sensitivity level"""
        
        if not cultural_context:
            return emotional_profile.cultural_sensitivity
        
        # Higher sensitivity for certain regions or contexts
        if cultural_context.respect_hierarchy:
            return "high"
        elif cultural_context.religious_considerations:
            return "high"
        else:
            return emotional_profile.cultural_sensitivity

    def _personalize_response_template(
        self,
        template: str,
        emotional_profile: EmotionalProfile,
        cultural_context: Optional[CulturalContext],
        service_request: Optional[ServiceRequest]
    ) -> str:
        """Personalize response template with user-specific information"""
        
        personalized = template
        
        # Add cultural expressions if available
        if cultural_context and cultural_context.common_expressions:
            import random
            expression = random.choice(cultural_context.common_expressions)
            personalized = f"{expression} {personalized}"
        
        # Add service-specific information
        if service_request:
            personalized = personalized.replace("{service_type}", service_request.service_type or "service")
            personalized = personalized.replace("{location}", service_request.location or "votre quartier")
        
        return personalized

    async def _apply_cultural_sensitivity_filters(
        self,
        db: Session,
        message: str,
        cultural_context: Optional[CulturalContext]
    ) -> str:
        """Apply cultural sensitivity filters to message"""
        
        if not cultural_context:
            return message
        
        # Get active sensitivity rules
        rules = db.query(CulturalSensitivityRule).filter(
            CulturalSensitivityRule.is_active == True
        ).all()
        
        filtered_message = message
        
        for rule in rules:
            # Check if rule applies to this context
            if rule.applicable_regions and cultural_context.region not in rule.applicable_regions:
                continue
            
            # Apply prohibited words filter
            if rule.prohibited_words:
                for word in rule.prohibited_words:
                    if word.lower() in filtered_message.lower():
                        if rule.alternative_suggestions:
                            filtered_message = filtered_message.replace(
                                word, rule.alternative_suggestions[0]
                            )
        
        return filtered_message

    async def _store_response_template(
        self,
        db: Session,
        situation: str,
        response: str,
        tone: str,
        language: str,
        empathy_level: str
    ) -> None:
        """Store response template for future use"""
        
        try:
            emotional_response = EmotionalResponse(
                trigger_situation=situation,
                response_template=response,
                tone=tone,
                language=language,
                empathy_level=empathy_level,
                formality_level=tone,
                urgency_level="routine",
                created_by="AI",
                usage_count=1,
                last_used=datetime.now(timezone.utc)
            )
            
            db.add(emotional_response)
            db.commit()
            
        except Exception as e:
            logger.error(f"Error storing response template: {e}")

    def _get_fallback_response(self, situation: str, language: str) -> str:
        """Get fallback response when AI fails"""
        
        fallback_responses = {
            "français": {
                "service_request": "Merci pour votre demande. Nous allons vous aider rapidement. 🙏",
                "emergency": "Nous comprenons l'urgence de votre situation. Nous vous contactons immédiatement. 🚨",
                "success": "Félicitations ! Nous sommes contents de votre satisfaction. 🎉",
                "default": "Merci pour votre message. Nous vous répondrons bientôt. 😊"
            },
            "english": {
                "service_request": "Thank you for your request. We will help you quickly. 🙏",
                "emergency": "We understand the urgency of your situation. We are contacting you immediately. 🚨",
                "success": "Congratulations! We are happy with your satisfaction. 🎉",
                "default": "Thank you for your message. We will respond soon. 😊"
            }
        }
        
        responses = fallback_responses.get(language, fallback_responses["français"])
        return responses.get(situation, responses["default"])