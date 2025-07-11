"""
Unified LLM Service - Single interface for all LLM providers
Supports: Gemini (GCP & AI Studio), OpenAI, Anthropic, Grok, and more

This service replaces the need for multiple LLM clients and provides:
- Single API interface for all providers
- Automatic provider selection based on model name
- Configuration-based API key management
- Fallback mechanisms and error handling
- Cost tracking and usage monitoring
- Streaming support across providers
"""

import os
import json
import time
import logging
from typing import Dict, List, Optional, Union, Any, Generator
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
from enum import Enum
from datetime import datetime, timezone

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Core imports
import requests
from google.cloud import aiplatform
import google.generativeai as genai

# Optional imports - will be installed as needed
try:
    import openai
except ImportError:
    openai = None

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    from groq import Groq
except ImportError:
    Groq = None


class LLMProvider(Enum):
    """Supported LLM providers."""
    GEMINI_GCP = "gemini_gcp"
    GEMINI_API = "gemini_api"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROK = "grok"
    OLLAMA = "ollama"


@dataclass
class LLMResponse:
    """Standardized response format for all LLM providers."""
    content: str
    provider: str
    model: str
    usage: Dict[str, int] = None
    cost: float = None
    latency: float = None
    metadata: Dict[str, Any] = None


@dataclass
class LLMConfig:
    """Configuration for LLM providers."""
    # Gemini
    gemini_api_key: Optional[str] = None
    gemini_gcp_project: Optional[str] = None
    gemini_gcp_location: Optional[str] = "us-central1"
    
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_org_id: Optional[str] = None
    
    # Anthropic
    anthropic_api_key: Optional[str] = None
    
    # Grok
    grok_api_key: Optional[str] = None
    
    # Ollama
    ollama_base_url: Optional[str] = "http://localhost:11434"
    
    # General settings
    default_temperature: float = 0.1
    default_max_tokens: int = 2048
    timeout: int = 60
    max_retries: int = 3
    
    @classmethod
    def from_env(cls) -> 'LLMConfig':
        """Load configuration from environment variables."""
        return cls(
            # Gemini - support both new and existing env var names
            gemini_api_key=os.getenv('GEMINI_API_KEY'),  # User's existing config
            gemini_gcp_project=os.getenv('GCP_PROJECT_ID'),
            gemini_gcp_location=os.getenv('GCP_LOCATION', 'us-central1'),
            
            # OpenAI
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            openai_org_id=os.getenv('OPENAI_ORG_ID'),
            
            # Anthropic
            anthropic_api_key=os.getenv('ANTHROPIC_API_KEY'),
            
            # Grok
            grok_api_key=os.getenv('GROK_API_KEY'),
            
            # Ollama
            ollama_base_url=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
            
            # General
            default_temperature=float(os.getenv('LLM_DEFAULT_TEMPERATURE', 0.1)),
            default_max_tokens=int(os.getenv('LLM_DEFAULT_MAX_TOKENS', 2048)),
            timeout=int(os.getenv('LLM_TIMEOUT', 60)),
            max_retries=int(os.getenv('LLM_MAX_RETRIES', 3))
        )


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    @abstractmethod
    def generate(
        self,
        prompt: str,
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response from the LLM."""
        pass
    
    @abstractmethod
    def stream_generate(
        self,
        prompt: str,
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Generator[str, None, None]:
        """Stream response from the LLM."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and configured."""
        pass


class GeminiGCPProvider(BaseLLMProvider):
    """Google Gemini via GCP Vertex AI."""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        if config.gemini_gcp_project:
            aiplatform.init(
                project=config.gemini_gcp_project,
                location=config.gemini_gcp_location
            )
    
    def generate(
        self,
        prompt: str,
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using Gemini via GCP."""
        start_time = time.time()
        
        try:
            from vertexai.generative_models import GenerativeModel
            
            # Initialize model
            vertex_model = GenerativeModel(model)
            
            # Set generation config
            generation_config = {
                "temperature": temperature or self.config.default_temperature,
                "max_output_tokens": max_tokens or self.config.default_max_tokens,
            }
            
            # Generate response
            response = vertex_model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            latency = time.time() - start_time
            
            return LLMResponse(
                content=response.text,
                provider="gemini_gcp",
                model=model,
                latency=latency,
                metadata={"generation_config": generation_config}
            )
            
        except Exception as e:
            self.logger.error(f"Gemini GCP generation failed: {e}")
            raise
    
    def stream_generate(
        self,
        prompt: str,
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Generator[str, None, None]:
        """Stream response using Gemini via GCP."""
        try:
            from vertexai.generative_models import GenerativeModel
            
            vertex_model = GenerativeModel(model)
            
            generation_config = {
                "temperature": temperature or self.config.default_temperature,
                "max_output_tokens": max_tokens or self.config.default_max_tokens,
            }
            
            response = vertex_model.generate_content(
                prompt,
                generation_config=generation_config,
                stream=True
            )
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            self.logger.error(f"Gemini GCP streaming failed: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if Gemini GCP is available."""
        return bool(self.config.gemini_gcp_project)


class GeminiAPIProvider(BaseLLMProvider):
    """Google Gemini via AI Studio API."""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        if config.gemini_api_key:
            genai.configure(api_key=config.gemini_api_key)
    
    def generate(
        self,
        prompt: str,
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using Gemini API."""
        start_time = time.time()
        
        try:
            # Initialize model
            genai_model = genai.GenerativeModel(model)
            
            # Set generation config
            generation_config = genai.types.GenerationConfig(
                temperature=temperature or self.config.default_temperature,
                max_output_tokens=max_tokens or self.config.default_max_tokens,
            )
            
            # Generate response
            response = genai_model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            latency = time.time() - start_time
            
            return LLMResponse(
                content=response.text,
                provider="gemini_api",
                model=model,
                latency=latency,
                usage=getattr(response, 'usage_metadata', None),
                metadata={"generation_config": asdict(generation_config)}
            )
            
        except Exception as e:
            self.logger.error(f"Gemini API generation failed: {e}")
            raise
    
    def stream_generate(
        self,
        prompt: str,
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Generator[str, None, None]:
        """Stream response using Gemini API."""
        try:
            genai_model = genai.GenerativeModel(model)
            
            generation_config = genai.types.GenerationConfig(
                temperature=temperature or self.config.default_temperature,
                max_output_tokens=max_tokens or self.config.default_max_tokens,
            )
            
            response = genai_model.generate_content(
                prompt,
                generation_config=generation_config,
                stream=True
            )
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            self.logger.error(f"Gemini API streaming failed: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if Gemini API is available."""
        return bool(self.config.gemini_api_key)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider for GPT models."""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        if openai and config.openai_api_key:
            try:
                # Initialize OpenAI client with minimal config
                client_kwargs = {"api_key": config.openai_api_key}
                if config.openai_org_id:
                    client_kwargs["organization"] = config.openai_org_id
                self.client = openai.OpenAI(**client_kwargs)
            except Exception as e:
                self.logger.error(f"Failed to initialize OpenAI client: {e}")
                self.client = None
        else:
            self.client = None
    
    def generate(
        self,
        prompt: str,
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using OpenAI."""
        start_time = time.time()
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature or self.config.default_temperature,
                max_tokens=max_tokens or self.config.default_max_tokens,
                **kwargs
            )
            
            latency = time.time() - start_time
            
            return LLMResponse(
                content=response.choices[0].message.content,
                provider="openai",
                model=model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                latency=latency
            )
            
        except Exception as e:
            self.logger.error(f"OpenAI generation failed: {e}")
            raise
    
    def stream_generate(
        self,
        prompt: str,
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Generator[str, None, None]:
        """Stream response using OpenAI."""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature or self.config.default_temperature,
                max_tokens=max_tokens or self.config.default_max_tokens,
                stream=True,
                **kwargs
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            self.logger.error(f"OpenAI streaming failed: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if OpenAI is available."""
        return bool(openai and self.config.openai_api_key and self.client)


class AnthropicProvider(BaseLLMProvider):
    """Anthropic provider for Claude models."""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        if anthropic and config.anthropic_api_key:
            try:
                self.client = anthropic.Anthropic(api_key=config.anthropic_api_key)
            except Exception as e:
                self.logger.error(f"Failed to initialize Anthropic client: {e}")
                self.client = None
        else:
            self.client = None
    
    def generate(
        self,
        prompt: str,
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response using Anthropic."""
        start_time = time.time()
        
        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=max_tokens or self.config.default_max_tokens,
                temperature=temperature or self.config.default_temperature,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
            
            latency = time.time() - start_time
            
            return LLMResponse(
                content=response.content[0].text,
                provider="anthropic",
                model=model,
                usage={
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                },
                latency=latency
            )
            
        except Exception as e:
            self.logger.error(f"Anthropic generation failed: {e}")
            raise
    
    def stream_generate(
        self,
        prompt: str,
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Generator[str, None, None]:
        """Stream response using Anthropic."""
        try:
            with self.client.messages.stream(
                model=model,
                max_tokens=max_tokens or self.config.default_max_tokens,
                temperature=temperature or self.config.default_temperature,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            ) as stream:
                for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            self.logger.error(f"Anthropic streaming failed: {e}")
            raise
    
    def is_available(self) -> bool:
        """Check if Anthropic is available."""
        return bool(anthropic and self.config.anthropic_api_key and self.client)


class UnifiedLLMService:
    """
    Unified LLM Service - Single interface for all LLM providers.
    
    Usage:
        service = UnifiedLLMService()
        
        # Generate with any model
        response = service.generate("Hello", "gemini-2.0-flash")
        response = service.generate("Hello", "gpt-4")
        response = service.generate("Hello", "claude-3-sonnet")
        
        # Stream responses
        for chunk in service.stream("Hello", "gemini-2.0-flash"):
            print(chunk, end="")
    """
    
    # Model to provider mapping
    MODEL_PROVIDERS = {
        # Gemini models - prefer API over GCP for user's setup
        "gemini-2.0-flash": LLMProvider.GEMINI_API,
        "gemini-1.5-flash": LLMProvider.GEMINI_API,
        "gemini-1.5-pro": LLMProvider.GEMINI_API,
        "gemini-2.5-pro-exp": LLMProvider.GEMINI_API,
        
        # OpenAI models
        "gpt-4": LLMProvider.OPENAI,
        "gpt-4-turbo": LLMProvider.OPENAI,
        "gpt-3.5-turbo": LLMProvider.OPENAI,
        "o1-preview": LLMProvider.OPENAI,
        "o1-mini": LLMProvider.OPENAI,
        
        # Anthropic models
        "claude-3-opus": LLMProvider.ANTHROPIC,
        "claude-3-sonnet": LLMProvider.ANTHROPIC,
        "claude-3-haiku": LLMProvider.ANTHROPIC,
        "claude-3-5-sonnet": LLMProvider.ANTHROPIC,
        
        # Grok models
        "grok-beta": LLMProvider.GROK,
        "grok-vision-beta": LLMProvider.GROK,
    }
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize the unified LLM service."""
        self.config = config or LLMConfig.from_env()
        self.logger = logging.getLogger(__name__)
        
        # Initialize providers
        self.providers = {
            LLMProvider.GEMINI_GCP: GeminiGCPProvider(self.config),
            LLMProvider.GEMINI_API: GeminiAPIProvider(self.config),
        }
        
        # Add additional providers if available
        try:
            openai_provider = OpenAIProvider(self.config)
            if openai_provider.is_available():
                self.providers[LLMProvider.OPENAI] = openai_provider
        except Exception as e:
            self.logger.warning(f"OpenAI provider not available: {e}")
            
        try:
            anthropic_provider = AnthropicProvider(self.config)
            if anthropic_provider.is_available():
                self.providers[LLMProvider.ANTHROPIC] = anthropic_provider
        except Exception as e:
            self.logger.warning(f"Anthropic provider not available: {e}")
        
        # Usage tracking
        self.usage_stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "provider_usage": {}
        }
    
    def _get_provider_for_model(self, model: str) -> BaseLLMProvider:
        """Get the appropriate provider for a model."""
        provider_enum = self.MODEL_PROVIDERS.get(model)
        
        if not provider_enum:
            # Try to infer from model name
            if "gemini" in model.lower():
                provider_enum = LLMProvider.GEMINI_GCP
            elif "gpt" in model.lower() or "o1" in model.lower():
                provider_enum = LLMProvider.OPENAI
            elif "claude" in model.lower():
                provider_enum = LLMProvider.ANTHROPIC
            elif "grok" in model.lower():
                provider_enum = LLMProvider.GROK
            else:
                raise ValueError(f"Unknown model: {model}")
        
        provider = self.providers.get(provider_enum)
        if not provider or not provider.is_available():
            # Fallback to Gemini GCP (current default)
            fallback_provider = self.providers[LLMProvider.GEMINI_GCP]
            if fallback_provider.is_available():
                self.logger.warning(f"Provider for {model} not available, using Gemini GCP")
                return fallback_provider
            else:
                raise RuntimeError(f"No available provider for model: {model}")
        
        return provider
    
    def generate(
        self,
        prompt: str,
        model: str = "gemini-2.0-flash",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate response using the specified model.
        
        Args:
            prompt: Input prompt
            model: Model name (e.g., "gemini-2.0-flash", "gpt-4", "claude-3-sonnet")
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific arguments
            
        Returns:
            LLMResponse with content and metadata
        """
        provider = self._get_provider_for_model(model)
        
        try:
            response = provider.generate(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            # Update usage stats
            self._update_usage_stats(response)
            
            return response
            
        except Exception as e:
            self.logger.error(f"Generation failed for model {model}: {e}")
            raise
    
    def stream(
        self,
        prompt: str,
        model: str = "gemini-2.0-flash",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Stream response using the specified model.
        
        Args:
            prompt: Input prompt
            model: Model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific arguments
            
        Yields:
            Chunks of generated text
        """
        provider = self._get_provider_for_model(model)
        
        try:
            for chunk in provider.stream_generate(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            ):
                yield chunk
                
        except Exception as e:
            self.logger.error(f"Streaming failed for model {model}: {e}")
            raise
    
    def list_available_models(self) -> Dict[str, List[str]]:
        """List all available models by provider."""
        available_models = {}
        
        for provider_enum, provider in self.providers.items():
            if provider.is_available():
                provider_name = provider_enum.value
                models = [
                    model for model, prov in self.MODEL_PROVIDERS.items()
                    if prov == provider_enum
                ]
                if models:
                    available_models[provider_name] = models
        
        return available_models
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return self.usage_stats.copy()
    
    def _update_usage_stats(self, response: LLMResponse):
        """Update usage statistics."""
        self.usage_stats["total_requests"] += 1
        
        if response.usage:
            total_tokens = response.usage.get("total_tokens", 0)
            if not total_tokens:
                # For providers that don't have total_tokens
                total_tokens = (
                    response.usage.get("prompt_tokens", 0) +
                    response.usage.get("completion_tokens", 0) +
                    response.usage.get("input_tokens", 0) +
                    response.usage.get("output_tokens", 0)
                )
            self.usage_stats["total_tokens"] += total_tokens
        
        if response.cost:
            self.usage_stats["total_cost"] += response.cost
        
        provider_stats = self.usage_stats["provider_usage"].setdefault(response.provider, {
            "requests": 0,
            "tokens": 0,
            "cost": 0.0
        })
        provider_stats["requests"] += 1
        if response.usage:
            provider_stats["tokens"] += total_tokens
        if response.cost:
            provider_stats["cost"] += response.cost


# Convenience function for backward compatibility
def create_llm_service(config: Optional[LLMConfig] = None) -> UnifiedLLMService:
    """Create a unified LLM service instance."""
    return UnifiedLLMService(config)


# Example usage
if __name__ == "__main__":
    # Initialize service
    service = UnifiedLLMService()
    
    # List available models
    print("Available models:")
    for provider, models in service.list_available_models().items():
        print(f"  {provider}: {', '.join(models)}")
    
    # Test generation
    try:
        response = service.generate("Hello, world!", "gemini-2.0-flash")
        print(f"\nResponse from {response.model} via {response.provider}:")
        print(response.content)
        print(f"Latency: {response.latency:.2f}s")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test streaming
    try:
        print(f"\nStreaming response:")
        for chunk in service.stream("Tell me a short joke", "gemini-2.0-flash"):
            print(chunk, end="")
        print()
    except Exception as e:
        print(f"Streaming error: {e}")
    
    # Show usage stats
    print(f"\nUsage stats: {service.get_usage_stats()}")