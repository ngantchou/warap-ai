"""
Enhanced Agent-LLM Communication System
Improves conversation flow with better error handling, structured responses, and context management
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
from loguru import logger

from app.config import get_settings
from app.services.ai_service import AIService
from app.utils.conversation_state import ConversationState

settings = get_settings()


class CommunicationQuality(Enum):
    """Communication quality levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


@dataclass
class AgentMessage:
    """Structured agent message to LLM"""
    user_message: str
    conversation_context: Dict[str, Any]
    user_data: Dict[str, Any]
    system_state: Dict[str, Any]
    urgency_level: str = "normal"
    language: str = "french"
    cultural_context: str = "cameroon"
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class LLMResponse:
    """Structured LLM response"""
    response_text: str
    intent_confidence: float
    extracted_data: Dict[str, Any]
    next_actions: List[str]
    conversation_state: str
    error_indicators: List[str]
    quality_score: float
    response_type: str = "natural_response"
    follow_up_needed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CommunicationMetrics:
    """Metrics for communication quality tracking"""
    total_exchanges: int = 0
    successful_extractions: int = 0
    failed_extractions: int = 0
    average_confidence: float = 0.0
    response_time_ms: int = 0
    error_count: int = 0
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now()


class EnhancedAgentLLMCommunicator:
    """Enhanced communication system between Agent and LLM"""
    
    def __init__(self):
        self.ai_service = AIService()
        self.metrics = CommunicationMetrics()
        self.conversation_cache = {}
        self.error_patterns = []
        self.improvement_suggestions = []
        
    async def process_conversation_with_llm(
        self, 
        agent_message: AgentMessage,
        conversation_state: ConversationState
    ) -> LLMResponse:
        """Process conversation with enhanced error handling and structured responses"""
        
        start_time = datetime.now()
        
        try:
            # Prepare structured prompt for LLM
            structured_prompt = self._build_structured_prompt(agent_message, conversation_state)
            
            # Send to LLM with retry logic
            llm_response = await self._send_to_llm_with_retry(structured_prompt)
            
            # Parse and validate response
            parsed_response = self._parse_llm_response(llm_response)
            
            # Quality assessment
            quality_score = self._assess_response_quality(parsed_response, agent_message)
            parsed_response.quality_score = quality_score
            
            # Update metrics
            self._update_metrics(parsed_response, start_time)
            
            # Log for improvement analysis
            await self._log_communication_analytics(agent_message, parsed_response)
            
            return parsed_response
            
        except Exception as e:
            logger.error(f"Enhanced communication error: {e}")
            return await self._generate_fallback_response(agent_message, str(e))
    
    def _build_structured_prompt(
        self, 
        agent_message: AgentMessage,
        conversation_state: ConversationState
    ) -> str:
        """Build structured prompt for better LLM understanding"""
        
        # Get dynamic services and zones
        services_info = self._get_dynamic_services_info()
        zones_info = self._get_dynamic_zones_info()
        
        prompt = f"""
AGENT-LLM COMMUNICATION PROTOCOL
================================

CONVERSATION CONTEXT:
- User Message: "{agent_message.user_message}"
- Language: {agent_message.language}
- Cultural Context: {agent_message.cultural_context}
- Urgency Level: {agent_message.urgency_level}
- Conversation Phase: {conversation_state.current_phase}

USER DATA:
- User ID: {agent_message.user_data.get('user_id', 'unknown')}
- Phone: {agent_message.user_data.get('phone', 'unknown')}
- Location History: {agent_message.user_data.get('location_history', [])}
- Service History: {agent_message.user_data.get('service_history', [])}

SYSTEM STATE:
- Available Services: {services_info}
- Coverage Zones: {zones_info}
- Current Request Status: {agent_message.system_state.get('current_request_status', 'none')}
- Provider Availability: {agent_message.system_state.get('provider_availability', 'unknown')}

PREVIOUS CONTEXT:
{json.dumps(agent_message.conversation_context, indent=2)}

INSTRUCTIONS:
1. Analyze the user's intent with high confidence
2. Extract ALL relevant information (service_type, location, description, urgency)
3. Provide a natural, culturally appropriate response in French
4. Indicate next conversation actions needed
5. Assess confidence level (0.0-1.0)

RESPONSE FORMAT (JSON):
{{
    "response_text": "Natural French response to user",
    "intent_confidence": 0.95,
    "extracted_data": {{
        "service_type": "service type or null",
        "location": "location or null",
        "description": "problem description or null",
        "urgency": "normal/urgent/emergency or null"
    }},
    "next_actions": ["continue_conversation", "create_request", "gather_info"],
    "conversation_state": "gathering_info/request_ready/completed",
    "error_indicators": [],
    "follow_up_needed": false
}}

CRITICAL: Always respond with valid JSON matching the exact format above.
"""
        
        return prompt
    
    async def _send_to_llm_with_retry(self, prompt: str, max_retries: int = 3) -> str:
        """Send prompt to LLM with retry logic"""
        
        for attempt in range(max_retries):
            try:
                response = await self.ai_service.generate_response(
                    prompt=prompt,
                    max_tokens=800,
                    temperature=0.1  # Lower temperature for more consistent responses
                )
                
                if response and len(response.strip()) > 0:
                    return response
                    
            except Exception as e:
                logger.warning(f"LLM communication attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
        
        raise Exception("All LLM communication attempts failed")
    
    def _parse_llm_response(self, llm_response: str) -> LLMResponse:
        """Parse LLM response into structured format"""
        
        try:
            # Extract JSON from response
            response_data = self._extract_json_from_response(llm_response)
            
            return LLMResponse(
                response_text=response_data.get('response_text', ''),
                intent_confidence=float(response_data.get('intent_confidence', 0.0)),
                extracted_data=response_data.get('extracted_data', {}),
                next_actions=response_data.get('next_actions', []),
                conversation_state=response_data.get('conversation_state', 'unknown'),
                error_indicators=response_data.get('error_indicators', []),
                quality_score=0.0,  # Will be calculated later
                follow_up_needed=response_data.get('follow_up_needed', False)
            )
            
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            logger.debug(f"Raw LLM response: {llm_response}")
            
            # Return a basic fallback response
            return LLMResponse(
                response_text="Je comprends votre demande. Pouvez-vous me donner plus de détails ?",
                intent_confidence=0.3,
                extracted_data={},
                next_actions=["continue_conversation"],
                conversation_state="gathering_info",
                error_indicators=["parsing_error"],
                quality_score=0.2,
                follow_up_needed=True
            )
    
    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """Extract JSON from LLM response, handling various formats"""
        
        # Try to find JSON block
        import re
        
        # Look for JSON in code blocks
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        # Look for JSON without code blocks
        json_match = re.search(r'(\{.*?\})', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        
        # If no JSON found, try to parse the entire response
        response_clean = response.strip()
        if response_clean.startswith('{') and response_clean.endswith('}'):
            return json.loads(response_clean)
        
        raise ValueError("No valid JSON found in response")
    
    def _assess_response_quality(self, response: LLMResponse, agent_message: AgentMessage) -> float:
        """Assess response quality for continuous improvement"""
        
        quality_score = 0.0
        
        # Check response completeness
        if response.response_text and len(response.response_text) > 10:
            quality_score += 0.2
        
        # Check intent confidence
        if response.intent_confidence > 0.8:
            quality_score += 0.3
        elif response.intent_confidence > 0.6:
            quality_score += 0.2
        elif response.intent_confidence > 0.4:
            quality_score += 0.1
        
        # Check data extraction
        extracted_fields = sum(1 for v in response.extracted_data.values() if v is not None)
        if extracted_fields > 0:
            quality_score += 0.2 * min(extracted_fields / 4, 1.0)
        
        # Check action clarity
        if response.next_actions and len(response.next_actions) > 0:
            quality_score += 0.1
        
        # Check error indicators
        if not response.error_indicators:
            quality_score += 0.1
        
        # Check cultural appropriateness for Cameroon context
        if any(word in response.response_text.lower() for word in ['bonjour', 'bonsoir', 'merci', 'problème']):
            quality_score += 0.1
        
        return min(quality_score, 1.0)
    
    def _update_metrics(self, response: LLMResponse, start_time: datetime):
        """Update communication metrics"""
        
        self.metrics.total_exchanges += 1
        self.metrics.response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        if response.extracted_data and any(v is not None for v in response.extracted_data.values()):
            self.metrics.successful_extractions += 1
        else:
            self.metrics.failed_extractions += 1
        
        if response.error_indicators:
            self.metrics.error_count += 1
        
        # Update average confidence
        total_confidence = (self.metrics.average_confidence * (self.metrics.total_exchanges - 1) + 
                           response.intent_confidence)
        self.metrics.average_confidence = total_confidence / self.metrics.total_exchanges
        
        self.metrics.last_updated = datetime.now()
    
    async def _log_communication_analytics(self, agent_message: AgentMessage, response: LLMResponse):
        """Log communication for analytics and improvement"""
        
        analytics_data = {
            'timestamp': datetime.now().isoformat(),
            'user_message_length': len(agent_message.user_message),
            'response_length': len(response.response_text),
            'intent_confidence': response.intent_confidence,
            'quality_score': response.quality_score,
            'response_time_ms': self.metrics.response_time_ms,
            'extracted_fields': len([v for v in response.extracted_data.values() if v is not None]),
            'error_count': len(response.error_indicators),
            'urgency_level': agent_message.urgency_level,
            'language': agent_message.language
        }
        
        logger.info(f"Communication analytics: {analytics_data}")
    
    async def _generate_fallback_response(self, agent_message: AgentMessage, error_message: str) -> LLMResponse:
        """Generate fallback response when communication fails"""
        
        fallback_responses = [
            "Je comprends votre demande. Pouvez-vous me donner plus de détails sur votre problème ?",
            "D'accord, je vais vous aider. Pouvez-vous me préciser le type de service dont vous avez besoin ?",
            "Parfait, je suis là pour vous aider. Décrivez-moi votre situation plus en détail.",
            "Je vois que vous avez besoin d'aide. Pouvez-vous me dire où vous vous trouvez et quel est le problème ?"
        ]
        
        return LLMResponse(
            response_text=fallback_responses[hash(agent_message.user_message) % len(fallback_responses)],
            intent_confidence=0.5,
            extracted_data={},
            next_actions=["continue_conversation"],
            conversation_state="gathering_info",
            error_indicators=["fallback_response", error_message],
            quality_score=0.3,
            follow_up_needed=True
        )
    
    def _get_dynamic_services_info(self) -> Dict[str, Any]:
        """Get dynamic services information"""
        return {
            "plomberie": {"price_range": "5000-15000 XAF", "available": True},
            "electricite": {"price_range": "3000-10000 XAF", "available": True},
            "electromenager": {"price_range": "2000-8000 XAF", "available": True}
        }
    
    def _get_dynamic_zones_info(self) -> Dict[str, Any]:
        """Get dynamic zones information"""
        return {
            "douala": {"available": True, "response_time": "15-30 min"},
            "bonamoussadi": {"available": True, "response_time": "10-25 min"},
            "akwa": {"available": True, "response_time": "20-35 min"}
        }
    
    def get_communication_metrics(self) -> Dict[str, Any]:
        """Get current communication metrics"""
        return {
            "total_exchanges": self.metrics.total_exchanges,
            "success_rate": (self.metrics.successful_extractions / max(self.metrics.total_exchanges, 1)) * 100,
            "average_confidence": self.metrics.average_confidence,
            "average_response_time_ms": self.metrics.response_time_ms,
            "error_rate": (self.metrics.error_count / max(self.metrics.total_exchanges, 1)) * 100,
            "last_updated": self.metrics.last_updated.isoformat() if self.metrics.last_updated else None
        }
    
    def get_improvement_suggestions(self) -> List[str]:
        """Get suggestions for improving communication"""
        suggestions = []
        
        success_rate = (self.metrics.successful_extractions / max(self.metrics.total_exchanges, 1)) * 100
        
        if success_rate < 70:
            suggestions.append("Consider improving prompt structure for better data extraction")
        
        if self.metrics.average_confidence < 0.7:
            suggestions.append("Add more context to prompts to improve intent confidence")
        
        if self.metrics.response_time_ms > 5000:
            suggestions.append("Optimize LLM calls to reduce response time")
        
        if (self.metrics.error_count / max(self.metrics.total_exchanges, 1)) > 0.1:
            suggestions.append("Implement better error handling and retry logic")
        
        return suggestions