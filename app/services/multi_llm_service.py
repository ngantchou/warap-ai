"""
Multi-LLM Service with Automatic Fallback
Supports Claude, Gemini, and OpenAI with intelligent switching
"""

import os
import json
import asyncio
from typing import Dict, List, Optional, Any
from loguru import logger
from enum import Enum

# Import AI services
from anthropic import Anthropic
from openai import OpenAI
from google import genai
from google.genai import types

class LLMProvider(Enum):
    """Available LLM providers"""
    CLAUDE = "claude"
    GEMINI = "gemini"
    OPENAI = "openai"

class LLMPriority(Enum):
    """Priority levels for LLM usage"""
    PRIMARY = 1
    SECONDARY = 2
    TERTIARY = 3

class MultiLLMService:
    """Service for managing multiple LLM providers with automatic fallback"""
    
    def __init__(self):
        self.providers = {}
        self.fallback_order = [
            LLMProvider.CLAUDE,
            LLMProvider.GEMINI,
            LLMProvider.OPENAI
        ]
        self.failed_providers = set()
        self.success_counts = {provider: 0 for provider in LLMProvider}
        self.failure_counts = {provider: 0 for provider in LLMProvider}
        
        # Initialize available providers
        self._initialize_providers()
        
    def _initialize_providers(self):
        """Initialize all available LLM providers"""
        
        # Initialize Claude (Anthropic)
        try:
            anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
            if anthropic_key:
                self.providers[LLMProvider.CLAUDE] = Anthropic(api_key=anthropic_key)
                logger.info("Claude (Anthropic) initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Claude: {e}")
            
        # Initialize Gemini (Google)
        try:
            gemini_key = os.environ.get('GEMINI_API_KEY')
            if gemini_key:
                self.providers[LLMProvider.GEMINI] = genai.Client(api_key=gemini_key)
                logger.info("Gemini (Google) initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini: {e}")
            
        # Initialize OpenAI
        try:
            openai_key = os.environ.get('OPENAI_API_KEY')
            if openai_key:
                self.providers[LLMProvider.OPENAI] = OpenAI(api_key=openai_key)
                logger.info("OpenAI initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI: {e}")
            
        logger.info(f"Initialized {len(self.providers)} LLM providers: {list(self.providers.keys())}")
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        preferred_provider: Optional[LLMProvider] = None
    ) -> str:
        """
        Generate response using the best available LLM provider
        
        Args:
            messages: List of conversation messages
            system_prompt: System prompt for the conversation
            max_tokens: Maximum tokens to generate
            temperature: Response randomness
            preferred_provider: Preferred LLM provider (optional)
            
        Returns:
            Generated response text
        """
        
        # Determine provider order
        provider_order = self._get_provider_order(preferred_provider)
        
        last_error = None
        
        for provider in provider_order:
            if provider in self.failed_providers:
                continue
                
            if provider not in self.providers:
                continue
                
            try:
                response = await self._generate_with_provider(
                    provider=provider,
                    messages=messages,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                
                # Success - update counters and return
                self.success_counts[provider] += 1
                if provider in self.failed_providers:
                    self.failed_providers.remove(provider)
                    logger.info(f"Provider {provider.value} recovered from failure")
                
                logger.info(f"Successfully generated response using {provider.value}")
                return response
                
            except Exception as e:
                last_error = e
                self.failure_counts[provider] += 1
                
                # Check if this is a credit/quota error
                if self._is_credit_error(e):
                    logger.error(f"Credit error with {provider.value}: {e}")
                    self.failed_providers.add(provider)
                elif self._is_temporary_error(e):
                    logger.warning(f"Temporary error with {provider.value}: {e}")
                else:
                    logger.error(f"Error with {provider.value}: {e}")
                    self.failed_providers.add(provider)
                
                continue
        
        # All providers failed
        logger.error(f"All LLM providers failed. Last error: {last_error}")
        raise Exception(f"All LLM providers unavailable. Last error: {last_error}")
    
    async def _generate_with_provider(
        self,
        provider: LLMProvider,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """Generate response with specific provider"""
        
        if provider == LLMProvider.CLAUDE:
            return await self._generate_claude(messages, system_prompt, max_tokens, temperature)
        elif provider == LLMProvider.GEMINI:
            return await self._generate_gemini(messages, system_prompt, max_tokens, temperature)
        elif provider == LLMProvider.OPENAI:
            return await self._generate_openai(messages, system_prompt, max_tokens, temperature)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    async def _generate_claude(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """Generate response using Claude (Anthropic)"""
        
        client = self.providers[LLMProvider.CLAUDE]
        
        # Prepare messages for Claude
        claude_messages = []
        for msg in messages:
            claude_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Make the API call
        response = await asyncio.to_thread(
            client.messages.create,
            model="claude-3-5-sonnet-20241022",  # Latest stable model
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt if system_prompt else "You are a helpful assistant.",
            messages=claude_messages
        )
        
        return response.content[0].text
    
    async def _generate_gemini(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """Generate response using Gemini (Google)"""
        
        client = self.providers[LLMProvider.GEMINI]
        
        # Prepare content for Gemini
        contents = []
        if system_prompt:
            contents.append(types.Content(
                role="user",
                parts=[types.Part(text=f"System: {system_prompt}")]
            ))
        
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(types.Content(
                role=role,
                parts=[types.Part(text=msg["content"])]
            ))
        
        # Make the API call
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.0-flash-exp",
            contents=contents,
            config=types.GenerateContentConfig(
                max_output_tokens=max_tokens,
                temperature=temperature
            )
        )
        
        return response.text or ""
    
    async def _generate_openai(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """Generate response using OpenAI"""
        
        client = self.providers[LLMProvider.OPENAI]
        
        # Prepare messages for OpenAI
        openai_messages = []
        if system_prompt:
            openai_messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        for msg in messages:
            openai_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Make the API call
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="gpt-4o",  # Latest GPT-4 model
            messages=openai_messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return response.choices[0].message.content
    
    def _get_provider_order(self, preferred_provider: Optional[LLMProvider] = None) -> List[LLMProvider]:
        """Get provider order based on preference and success rates"""
        
        if preferred_provider and preferred_provider in self.providers:
            # Put preferred provider first
            order = [preferred_provider]
            order.extend([p for p in self.fallback_order if p != preferred_provider])
            return order
        
        # Use default fallback order with success rate consideration
        available_providers = [p for p in self.fallback_order if p in self.providers]
        
        # Sort by success rate (higher is better)
        available_providers.sort(
            key=lambda p: self._get_success_rate(p),
            reverse=True
        )
        
        return available_providers
    
    def _get_success_rate(self, provider: LLMProvider) -> float:
        """Calculate success rate for a provider"""
        total_attempts = self.success_counts[provider] + self.failure_counts[provider]
        if total_attempts == 0:
            return 1.0  # New provider gets benefit of doubt
        return self.success_counts[provider] / total_attempts
    
    def _is_credit_error(self, error: Exception) -> bool:
        """Check if error is related to credits/quota"""
        error_str = str(error).lower()
        credit_keywords = [
            "credit balance",
            "insufficient credits",
            "quota exceeded",
            "billing",
            "payment required",
            "subscription",
            "usage limit"
        ]
        return any(keyword in error_str for keyword in credit_keywords)
    
    def _is_temporary_error(self, error: Exception) -> bool:
        """Check if error is temporary (rate limiting, network, etc.)"""
        error_str = str(error).lower()
        temp_keywords = [
            "rate limit",
            "too many requests",
            "timeout",
            "connection error",
            "server error",
            "503",
            "502",
            "500"
        ]
        return any(keyword in error_str for keyword in temp_keywords)
    
    def get_provider_status(self) -> Dict[str, Any]:
        """Get status of all providers"""
        status = {}
        
        for provider in LLMProvider:
            is_available = provider in self.providers
            is_failed = provider in self.failed_providers
            success_rate = self._get_success_rate(provider)
            
            status[provider.value] = {
                "available": is_available,
                "failed": is_failed,
                "success_count": self.success_counts[provider],
                "failure_count": self.failure_counts[provider],
                "success_rate": success_rate,
                "status": "operational" if is_available and not is_failed else "failed"
            }
        
        return status
    
    def reset_failed_providers(self):
        """Reset failed providers list (for recovery attempts)"""
        self.failed_providers.clear()
        logger.info("Reset failed providers list")
    
    def get_recommended_provider(self) -> Optional[LLMProvider]:
        """Get the currently recommended provider"""
        available_providers = [p for p in self.fallback_order if p in self.providers and p not in self.failed_providers]
        
        if not available_providers:
            return None
        
        # Return provider with highest success rate
        best_provider = max(available_providers, key=lambda p: self._get_success_rate(p))
        return best_provider