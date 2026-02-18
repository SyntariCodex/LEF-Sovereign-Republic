"""
CortexCache (Context Caching Manager)
DEPRECATED: This module was designed for the google.generativeai caching API.

The new google.genai package has a different caching mechanism.
This file is kept for backwards compatibility but returns standard models.

TODO: Investigate and implement caching with the new google.genai API
when the caching feature becomes stable.
"""

import os
import datetime
import logging
import warnings

# Import genai using new package
try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

warnings.warn("cortex_cache.py is deprecated. Use system.llm_router.get_router() instead.", DeprecationWarning, stacklevel=2)

try:
    from system.llm_router import get_router as _get_llm_router
    _LLM_ROUTER = _get_llm_router()
except ImportError:
    _LLM_ROUTER = None

class CacheManager:
    """
    Manages Gemini Context Caching.
    
    NOTE: Caching has been temporarily disabled during google.genai migration.
    This class now returns a simple wrapper that delegates to client.models.generate_content.
    """
    def __init__(self, api_key):
        self.api_key = api_key
        self.client = None
        if self.api_key and GENAI_AVAILABLE:
            self.client = genai.Client(api_key=self.api_key)
            
    def get_cached_model(self, model_name, cache_name, system_instruction, ttl_minutes=10):
        """
        Returns a model-like object that can be used for generation.
        
        NOTE: Caching is temporarily disabled. This returns a wrapper that
        uses direct generation with the system instruction prepended.
        
        Args:
            model_name: The model to use (e.g., 'models/gemini-2.0-flash')
            cache_name: Identifier for the cache (currently unused)
            system_instruction: The system prompt to prepend
            ttl_minutes: Cache TTL (currently unused)
            
        Returns:
            A CachedModelWrapper that mimics the old API
        """
        logging.debug(f"[CACHE] Caching disabled during migration. Using direct generation for: {cache_name}")
        
        # Clean model name (remove 'models/' prefix if present)
        if model_name.startswith('models/'):
            model_name = model_name.replace('models/', '')
            
        return CachedModelWrapper(self.client, model_name, system_instruction)


class CachedModelWrapper:
    """
    A wrapper that mimics the old GenerativeModel interface.
    Prepends system instruction to each call since caching is disabled.
    """
    def __init__(self, client, model_name, system_instruction):
        self.client = client
        self.model_name = model_name
        self.system_instruction = system_instruction
        
    def generate_content(self, prompt):
        """
        Generate content with the system instruction prepended.
        
        Args:
            prompt: The user prompt
            
        Returns:
            Response object with .text attribute
        """
        if not self.client and not _LLM_ROUTER:
            raise ValueError("No client available for generation")
            
        # Combine system instruction with prompt
        full_prompt = f"{self.system_instruction}\n\n{prompt}"
        
        response_text = None
        if _LLM_ROUTER:
            response_text = _LLM_ROUTER.generate(
                prompt=full_prompt, agent_name='CortexCache',
                context_label='CORTEX_CACHE', timeout_seconds=90
            )
        if response_text is None and self.client:
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=full_prompt
                )
                response_text = response.text.strip() if response and response.text else None
            except Exception as _e:
                import logging
                logging.debug(f"Legacy LLM fallback failed: {_e}")
        
        # Return a response-like object for backwards compatibility
        return type('_CachedResponse', (), {'text': response_text})()
