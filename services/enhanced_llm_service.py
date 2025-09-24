"""
Enhanced LLM Service with multi-provider support (Gemini + Claude + Grok)
Supports model selection and provider switching for analysis tasks.
"""
import time
import logging
from typing import List, Dict, Any, Optional
from enum import Enum

# Gemini imports
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

# Claude imports (will install if needed)
try:
    import anthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False
    logging.warning("Claude API not available. Run: pip install anthropic")

# Grok imports (OpenAI-compatible API)
try:
    import openai
    GROK_AVAILABLE = True
except ImportError:
    GROK_AVAILABLE = False
    logging.warning("Grok API not available. Run: pip install openai")

from config.settings import GEMINI_API_KEY, CLAUDE_API_KEY, GROK_API_KEY, OPENAI_API_KEY, MAX_RETRIES, RETRY_DELAY
from config.gemini_models import GEMINI_MODELS, get_model_info
from config.openai_models import OpenAIModels, get_openai_model_info
from services.utils import format_chat_history, handle_api_error

logger = logging.getLogger(__name__)


class ModelProvider(Enum):
    """Available LLM providers."""
    GEMINI = "gemini"
    CLAUDE = "claude"
    GROK = "grok"
    OPENAI = "openai"


class ModelInfo:
    """
    Model information and pricing comparison across providers.
    
    PRICING COMPARISON (per 1M tokens as of 2025):
    
    === ULTRA-PREMIUM TIER ($$$$ - $15+ input) ===
    Claude 4 Opus:     $15.00 input / $75.00 output  🏆 World's best coding model
    Claude 3 Opus:     $15.00 input / $75.00 output  📚 Legacy premium
    Grok 4:            $3.00 input / $15.00 output   🚀 xAI flagship with real-time search
    GPT-4 Turbo:       $10.00 input / $30.00 output  🤖 OpenAI flagship
    
    === PREMIUM TIER ($$$ - $3-10 input) ===
    Claude 4 Sonnet:   $3.00 input / $15.00 output   ⭐ Best balance (RECOMMENDED)
    Claude 3.5 Sonnet: $3.00 input / $15.00 output   💪 Proven reliable
    Gemini 2.5 Pro:    $3.50 input / $10.50 output   🧠 Google's flagship
    Gemini 1.5 Pro:    $3.50 input / $10.50 output   📖 Large context
    GPT-4o:            $5.00 input / $15.00 output    🔥 OpenAI multimodal
    
    === PRODUCTION TIER ($$ - $0.5-3 input) ===
    Grok 2-1212:       $2.00 input / $10.00 output   ⚡ xAI production model
    GPT-4o mini:       $0.15 input / $0.60 output    ⚡ OpenAI efficient
    
    === EFFICIENT TIER ($ - $0.1-0.5 input) ===
    Claude 3.5 Haiku:  $0.25 input / $1.25 output    💰 Fast & affordable
    
    === BUDGET TIER (¢ - <$0.1 input) ===
    Gemini 2.5 Flash:  $0.075 input / $0.30 output   🚀 Google fast
    Gemini 1.5 Flash:  $0.075 input / $0.30 output   ⚡ Reliable budget
    Gemini 1.5 Flash 8B: $0.0375 input / $0.15 output 💸 Ultra-budget
    GPT-3.5 Turbo:     $0.50 input / $1.50 output    📱 OpenAI legacy
    
    KEY INSIGHTS:
    💡 Gemini offers the best budget options (Flash models)
    💡 Claude 4 Sonnet offers best premium balance 
    💡 Claude 4 Opus is unmatched for complex coding
    💡 Grok 4 provides real-time search & competitive premium pricing
    💡 Grok 2-1212 is well-positioned in production tier
    💡 OpenAI GPT-4o mini is competitive in mid-tier
    💡 Context windows: Claude/Gemini (200K+) > Grok (256K) > OpenAI (128K)
    """
    
    # Gemini models (Google - Best budget options)
    GEMINI_MODELS = {
        "gemini-2.5-pro": {"name": "Gemini 2.5 Pro", "cost": "High", "performance": "Highest"},
        "gemini-2.5-flash": {"name": "Gemini 2.5 Flash", "cost": "Low", "performance": "High"},
        "gemini-1.5-pro": {"name": "Gemini 1.5 Pro", "cost": "Medium", "performance": "High"},
        "gemini-1.5-flash": {"name": "Gemini 1.5 Flash", "cost": "Low", "performance": "Good"},
        "gemini-1.5-flash-8b": {"name": "Gemini 1.5 Flash 8B", "cost": "Very Low", "performance": "Medium"},
    }
    
    # Claude models (Anthropic - Best coding & reasoning)
    CLAUDE_MODELS = {
        "claude-opus-4-20250514": {"name": "Claude 4 Opus", "cost": "Very High", "performance": "Highest"},
        "claude-sonnet-4-20250514": {"name": "Claude 4 Sonnet", "cost": "High", "performance": "Highest"},
        "claude-3-5-sonnet-20241022": {"name": "Claude 3.5 Sonnet", "cost": "Medium", "performance": "High"},
        "claude-3-5-haiku-20241022": {"name": "Claude 3.5 Haiku", "cost": "Low", "performance": "Good"},
        "claude-3-opus-20240229": {"name": "Claude 3 Opus", "cost": "High", "performance": "High"},
    }
    
    # Grok models (xAI - Real-time search & competitive pricing)
    GROK_MODELS = {
        "grok-4": {"name": "Grok 4", "cost": "High", "performance": "Highest"},
        "grok-2-1212": {"name": "Grok 2-1212", "cost": "Medium", "performance": "High"},
        "grok-2-vision-1212": {"name": "Grok 2 Vision-1212", "cost": "Medium", "performance": "High"},
        "grok-beta": {"name": "Grok Beta", "cost": "High", "performance": "High"},
        "grok-vision-beta": {"name": "Grok Vision Beta", "cost": "High", "performance": "High"},
    }
    
    # OpenAI models (ChatGPT - Mature API with good pricing)
    OPENAI_MODELS = {
        "gpt-4o-mini": {"name": "GPT-4o Mini (Ultra-budget)", "cost": "Very Low", "performance": "High"},
        "gpt-4o": {"name": "GPT-4o (Flagship)", "cost": "Medium", "performance": "Highest"},
        "gpt-4-turbo": {"name": "GPT-4 Turbo (Premium)", "cost": "High", "performance": "Highest"},
        "gpt-3.5-turbo": {"name": "GPT-3.5 Turbo (Budget)", "cost": "Low", "performance": "Medium"},
    }


class EnhancedLLMService:
    """Enhanced LLM service supporting multiple providers."""
    
    def __init__(self, provider: ModelProvider = ModelProvider.GEMINI, model: str = None):
        """Initialize the enhanced LLM service."""
        self.provider = provider
        self.model = model or self._get_default_model(provider)
        self.cost_tracker = {"requests": 0, "estimated_cost": 0.0}
        
        # Initialize APIs
        self._init_gemini()
        self._init_claude()
        self._init_grok()
        self._init_openai()
        
        logger.info(f"🚀 Enhanced LLM Service initialized")
        logger.info(f"📊 Provider: {provider.value}, Model: {self.model}")
    
    def _get_default_model(self, provider: ModelProvider) -> str:
        """Get default model for provider."""
        if provider == ModelProvider.GEMINI:
            return GEMINI_MODELS.HIGH_PERFORMANCE
        elif provider == ModelProvider.CLAUDE:
            return "claude-sonnet-4-20250514"  # Default to Claude 4 Sonnet
        elif provider == ModelProvider.GROK:
            return "grok-2-1212"  # Default to Grok 2-1212 (production model)
        elif provider == ModelProvider.OPENAI:
            return OpenAIModels.PRIMARY  # Default to GPT-4o Mini (cheapest)
        return GEMINI_MODELS.PRIMARY
    
    def _init_gemini(self):
        """Initialize Gemini API."""
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
            logger.info("✅ Gemini API initialized")
        else:
            logger.warning("⚠️ Gemini API key not found")
    
    def _init_claude(self):
        """Initialize Claude API."""
        if not CLAUDE_AVAILABLE:
            logger.warning("⚠️ Claude API library not installed. Run: pip install anthropic")
            self.claude_client = None
        elif not CLAUDE_API_KEY:
            logger.warning("⚠️ Claude API key not found in environment variables")
            self.claude_client = None
        else:
            try:
                self.claude_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
                logger.info(f"✅ Claude API initialized with key: {CLAUDE_API_KEY[:15]}...")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Claude API: {e}")
                self.claude_client = None
    
    def _init_grok(self):
        """Initialize Grok API using direct HTTP client."""
        if not GROK_API_KEY:
            logger.warning("⚠️ Grok API key not found in environment variables")
            self.grok_client = None
        else:
            try:
                # Use httpx directly instead of OpenAI client to avoid compatibility issues
                import httpx
                import json
                
                self.grok_http_client = httpx.Client(
                    base_url="https://api.x.ai/v1",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {GROK_API_KEY}"
                    },
                    timeout=30.0
                )
                
                logger.info("🧪 Testing Grok API connection with direct HTTP...")
                test_payload = {
                    "model": "grok-2-1212",
                    "messages": [{"role": "user", "content": "Hello, respond with just 'OK'"}],
                    "max_tokens": 10,
                    "temperature": 0.1
                }
                
                response = self.grok_http_client.post("/chat/completions", json=test_payload)
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"✅ Grok API test successful: {result['choices'][0]['message']['content']}")
                    self.grok_client = "http_client"  # Use string to indicate we're using HTTP client
                else:
                    logger.error(f"❌ Grok API test failed: {response.status_code} - {response.text}")
                    self.grok_client = None
                    
            except Exception as e:
                logger.error(f"❌ Failed to initialize Grok API: {e}")
                logger.error(f"🔍 Error type: {type(e).__name__}")
                self.grok_client = None
    
    def _init_openai(self):
        """Initialize OpenAI API."""
        if not GROK_AVAILABLE:  # Uses same openai library
            logger.warning("⚠️ OpenAI API library not installed. Run: pip install openai")
            self.openai_client = None
        elif not OPENAI_API_KEY:
            logger.warning("⚠️ OpenAI API key not found in environment variables")
            self.openai_client = None
        else:
            try:
                # Initialize OpenAI client with basic configuration
                self.openai_client = openai.OpenAI(
                    api_key=OPENAI_API_KEY,
                    timeout=30.0
                )
                
                # Test the API connection
                logger.info("🧪 Testing OpenAI API connection...")
                test_model = "gpt-4o-mini"  # Use stable model for testing
                test_params = {
                    "model": test_model,
                    "messages": [{"role": "user", "content": "Hello, respond with just 'OK'"}]
                }
                
                # Use correct parameters based on model
                if test_model.startswith('gpt-5'):
                    test_params["max_completion_tokens"] = 10
                    # GPT-5 only supports default temperature (1.0), don't set it
                else:
                    test_params["max_tokens"] = 10
                    test_params["temperature"] = 0.1
                
                test_response = self.openai_client.chat.completions.create(**test_params)
                
                test_content = test_response.choices[0].message.content
                logger.info(f"✅ OpenAI API test successful: {test_content}")
                logger.info(f"✅ OpenAI API initialized with key: {OPENAI_API_KEY[:15]}...")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize OpenAI API: {e}")
                logger.error(f"🔍 Error type: {type(e).__name__}")
                self.openai_client = None
    
    def switch_model(self, provider: ModelProvider, model: str):
        """Switch to a different model/provider."""
        old_info = f"{self.provider.value}:{self.model}"
        self.provider = provider
        self.model = model
        new_info = f"{provider.value}:{model}"
        logger.info(f"🔄 Switched model: {old_info} → {new_info}")
    
    def generate_text(self, prompt: str, max_retries: int = 3, enable_fallback: bool = True, 
                     enable_thinking: bool = False, thinking_budget: int = 2048) -> Dict[str, Any]:
        """Generate text using the selected provider with automatic fallback."""
        primary_result = None
        
        if self.provider == ModelProvider.GEMINI:
            primary_result = self._generate_with_gemini(prompt, max_retries)
        elif self.provider == ModelProvider.CLAUDE:
            primary_result = self._generate_with_claude(prompt, max_retries, enable_thinking, thinking_budget)
        elif self.provider == ModelProvider.GROK:
            primary_result = self._generate_with_grok(prompt, max_retries)
        elif self.provider == ModelProvider.OPENAI:
            primary_result = self._generate_with_openai(prompt, max_retries)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
        
        # If primary provider succeeded, return result
        if primary_result and primary_result.get("success"):
            return primary_result
        
        # If primary failed and fallback is enabled, try Gemini Flash as backup
        if enable_fallback and self.provider in [ModelProvider.CLAUDE, ModelProvider.GROK, ModelProvider.OPENAI]:
            logger.warning(f"🔄 {self.provider.value} failed, falling back to Gemini 1.5 Flash as backup...")
            return self._fallback_to_gemini(prompt, max_retries, primary_result)
        
        # Return original result if no fallback or fallback not applicable
        return primary_result or {"success": False, "error": "Unknown error occurred"}
    
    def _generate_with_gemini(self, prompt: str, max_retries: int) -> Dict[str, Any]:
        """Generate text using Gemini."""
        logger.info(f"🤖 Generating with Gemini: {self.model}")
        
        for attempt in range(max_retries):
            try:
                model = genai.GenerativeModel(
                    model_name=self.model,
                    generation_config={
                        "temperature": 0.1,  # Lower temperature for code generation
                        "top_p": 0.95,
                        "top_k": 40,
                        "max_output_tokens": 4096,
                    }
                )
                
                start_time = time.time()
                response = model.generate_content(prompt)
                response_time = time.time() - start_time
                
                self._track_cost("gemini", len(prompt), len(response.text))
                
                logger.info(f"✅ Gemini generation successful ({response_time:.2f}s)")
                return {
                    "success": True,
                    "text": response.text,
                    "provider": "gemini",
                    "model": self.model,
                    "response_time": response_time,
                    "cost_info": self.cost_tracker
                }
                
            except Exception as e:
                logger.error(f"❌ Gemini attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return {"success": False, "error": str(e), "provider": "gemini"}
                time.sleep(RETRY_DELAY)
    
    def _generate_with_claude(self, prompt: str, max_retries: int, enable_thinking: bool = False, thinking_budget: int = 2048) -> Dict[str, Any]:
        """Generate text using Claude."""
        if not self.claude_client:
            return {"success": False, "error": "Claude API not available", "provider": "claude"}
        
        logger.info(f"🤖 Generating with Claude: {self.model}")
        
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                
                # Prepare API request parameters
                api_params = {
                    "model": self.model,
                    "max_tokens": 4096,
                    "temperature": 0.1,  # Lower temperature for code generation
                    "messages": [{"role": "user", "content": prompt}]
                }
                
                # Add thinking parameters for Claude 4 models if enabled
                if enable_thinking and self._is_claude_4_model() and thinking_budget >= 1024:
                    api_params["thinking"] = {
                        "type": "enabled",
                        "budget_tokens": min(thinking_budget, 3072)  # Max budget to leave room for response
                    }
                    logger.info(f"🧠 Enabling thinking mode with {thinking_budget} tokens budget")
                
                response = self.claude_client.messages.create(**api_params)
                response_time = time.time() - start_time
                
                # Extract response text and thinking content
                response_text = ""
                thinking_content = ""
                
                for content_block in response.content:
                    if content_block.type == "text":
                        response_text += content_block.text
                    elif content_block.type == "thinking":
                        thinking_content += content_block.content
                
                # Extract token usage from Claude API response
                input_tokens = getattr(response.usage, 'input_tokens', 0)
                output_tokens = getattr(response.usage, 'output_tokens', 0)
                
                self._track_cost("claude", input_tokens, output_tokens)
                
                logger.info(f"✅ Claude generation successful ({response_time:.2f}s)")
                logger.info(f"📊 Token usage: {input_tokens} input + {output_tokens} output = {input_tokens + output_tokens} total")
                if thinking_content:
                    logger.info(f"🧠 Thinking content generated: {len(thinking_content)} characters")
                
                result = {
                    "success": True,
                    "text": response_text,
                    "provider": "claude",
                    "model": self.model,
                    "response_time": response_time,
                    "usage": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": input_tokens + output_tokens
                    },
                    "cost_info": self.cost_tracker
                }
                
                # Add thinking content if available
                if thinking_content:
                    result["thinking"] = thinking_content
                    result["has_thinking"] = True
                
                return result
                
            except Exception as e:
                logger.error(f"❌ Claude attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return {"success": False, "error": str(e), "provider": "claude"}
                time.sleep(RETRY_DELAY)
    
    def _generate_with_grok(self, prompt: str, max_retries: int) -> Dict[str, Any]:
        """Generate text using Grok (xAI) via direct HTTP API."""
        if not self.grok_client or not hasattr(self, 'grok_http_client'):
            return {"success": False, "error": "Grok client not initialized", "provider": "grok"}
        
        logger.info(f"🚀 Generating with Grok: {self.model}")
        
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                
                payload = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,  # Lower temperature for code generation
                    "max_tokens": 4096,
                    "stream": False
                }
                
                response = self.grok_http_client.post("/chat/completions", json=payload)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Extract response text and usage information
                    response_text = result["choices"][0]["message"]["content"]
                    usage = result["usage"]
                    
                    input_tokens = usage["prompt_tokens"]
                    output_tokens = usage["completion_tokens"]
                    
                    self._track_cost("grok", input_tokens, output_tokens)
                    
                    logger.info(f"✅ Grok generation successful ({response_time:.2f}s)")
                    logger.info(f"📊 Token usage: {input_tokens} input + {output_tokens} output = {input_tokens + output_tokens} total")
                    
                    return {
                        "success": True,
                        "text": response_text,
                        "provider": "grok",
                        "model": self.model,
                        "response_time": response_time,
                        "usage": {
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "total_tokens": input_tokens + output_tokens
                        },
                        "cost_info": self.cost_tracker
                    }
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    logger.error(f"❌ Grok attempt {attempt + 1} failed: {error_msg}")
                    if attempt == max_retries - 1:
                        return {"success": False, "error": error_msg, "provider": "grok"}
                
            except Exception as e:
                logger.error(f"❌ Grok attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return {"success": False, "error": str(e), "provider": "grok"}
                
            time.sleep(RETRY_DELAY)
    
    def _generate_with_openai(self, prompt: str, max_retries: int) -> Dict[str, Any]:
        """Generate text using OpenAI API."""
        if not self.openai_client:
            return {"success": False, "error": "OpenAI client not initialized", "provider": "openai"}
        
        logger.info(f"🤖 Generating with OpenAI: {self.model}")
        
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                
                # GPT-5 models use max_completion_tokens instead of max_tokens
                # and only support default temperature (1.0)
                request_params = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}]
                }
                
                # Use correct token parameter based on model
                if self.model.startswith('gpt-5'):
                    request_params["max_completion_tokens"] = 4096
                    # GPT-5 only supports default temperature (1.0), don't set it
                else:
                    request_params["max_tokens"] = 4096
                    request_params["temperature"] = 0.1  # Lower temperature for code generation
                
                response = self.openai_client.chat.completions.create(**request_params)
                
                response_time = time.time() - start_time
                
                # Extract response text and usage information
                response_text = response.choices[0].message.content
                usage = response.usage
                
                input_tokens = usage.prompt_tokens
                output_tokens = usage.completion_tokens
                
                self._track_cost("openai", input_tokens, output_tokens)
                
                logger.info(f"✅ OpenAI generation successful ({response_time:.2f}s)")
                logger.info(f"📊 Token usage: {input_tokens} input + {output_tokens} output = {input_tokens + output_tokens} total")
                
                return {
                    "success": True,
                    "text": response_text,
                    "provider": "openai",
                    "model": self.model,
                    "response_time": response_time,
                    "usage": {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": input_tokens + output_tokens
                    },
                    "cost_info": self.cost_tracker
                }
                
            except Exception as e:
                logger.error(f"❌ OpenAI attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return {"success": False, "error": str(e), "provider": "openai"}
                
            time.sleep(RETRY_DELAY)
    
    def _track_cost(self, provider: str, input_tokens: int, output_tokens: int):
        """Track estimated costs."""
        self.cost_tracker["requests"] += 1
        
        # COMPREHENSIVE PRICING COMPARISON (per 1M tokens as of 2025)
        # All major AI providers included for reference and cost optimization
        model_costs = {
            # === GEMINI MODELS (Google) - BEST BUDGET OPTIONS ===
            # Google's strength: Ultra-affordable Flash models with good performance
            "gemini-2.5-pro": {"input": 3.5, "output": 10.5},    # Premium but cheaper output than Claude
            "gemini-2.5-flash": {"input": 0.075, "output": 0.30}, # 40x cheaper than Claude 4 Sonnet!
            "gemini-1.5-pro": {"input": 3.5, "output": 10.5},     # Large context (2M tokens)
            "gemini-1.5-flash": {"input": 0.075, "output": 0.30},  # Proven budget choice
            "gemini-1.5-flash-8b": {"input": 0.0375, "output": 0.15}, # CHEAPEST option (80x cheaper!)
            
            # === CLAUDE MODELS (Anthropic) - BEST CODING & REASONING ===
            # Anthropic's strength: Superior coding, reasoning, and safety
            
            # Claude 4 (2025) - Latest and greatest
            "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},  # 🏆 World's best coding model
            "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0}, # ⭐ Best balance (RECOMMENDED)
            
            # Claude 3.5 - Proven reliable
            "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0}, # Same price as 4 Sonnet, use 4!
            "claude-3-5-haiku-20241022": {"input": 0.25, "output": 1.25},  # 3x more than Gemini Flash
            
            # Claude 3 - Legacy
            "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},    # Same price as 4 Opus, use 4!
            
            # === GROK MODELS (xAI) - REAL-TIME SEARCH & COMPETITIVE PRICING ===
            # xAI's strength: Real-time search, web access, competitive pricing
            "grok-4": {"input": 3.0, "output": 15.0},             # Premium tier, same as Claude 4 Sonnet
            "grok-2-1212": {"input": 2.0, "output": 10.0},        # Production tier, great value
            "grok-2-vision-1212": {"input": 2.0, "output": 10.0}, # Production tier with vision
            "grok-beta": {"input": 5.0, "output": 15.0},          # Beta model pricing
            "grok-vision-beta": {"input": 5.0, "output": 15.0},   # Beta vision model
            
            # === OPENAI MODELS (ChatGPT) - MATURE API & GOOD MID-TIER ===
            # OpenAI's strength: Multimodal capabilities, mature ecosystem, wide adoption
            "gpt-4-turbo": {"input": 10.0, "output": 30.0},       # Cheaper than Claude Opus
            "gpt-4o": {"input": 5.0, "output": 15.0},             # More expensive than Claude 4 Sonnet
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},       # 2x more than Gemini Flash but great value
            "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},       # 7x more than Gemini Flash
            
            # === COST ANALYSIS INSIGHTS ===
            # 1. For BUDGET: Gemini Flash 8B wins (40-80x cheaper than premium)
            # 2. For BALANCE: Claude 4 Sonnet best quality/price in premium tier
            # 3. For PREMIUM: Claude 4 Opus unmatched for complex coding
            # 4. OpenAI competitive in mid-tier with GPT-4o mini
            # 5. Gemini Pro models have better output pricing than Claude
        }
        
        # Get cost for current model or use default
        if self.model in model_costs:
            rates = model_costs[self.model]
        elif provider == "gemini":
            rates = {"input": 3.5, "output": 10.5}  # Default Gemini Pro pricing
        elif provider == "grok":
            rates = {"input": 2.0, "output": 10.0}  # Default Grok 2-1212 pricing
        elif provider == "openai":
            rates = {"input": 0.15, "output": 0.60}  # Default GPT-4o Mini pricing
        else:
            rates = {"input": 3.0, "output": 15.0}  # Default Claude pricing
        
        # Calculate estimated cost
        estimated_cost = (
            (input_tokens / 1_000_000) * rates["input"] +
            (output_tokens / 1_000_000) * rates["output"]
        )
        self.cost_tracker["estimated_cost"] += estimated_cost
    
    def _fallback_to_gemini(self, prompt: str, max_retries: int, primary_error: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback to Gemini 1.5 Flash when Claude fails."""
        logger.info("🔄 Attempting fallback to Gemini 1.5 Flash...")
        
        try:
            # Temporarily switch to Gemini for fallback
            original_provider = self.provider
            original_model = self.model
            
            # Switch to Gemini Flash (reliable and fast)
            self.provider = ModelProvider.GEMINI
            self.model = "gemini-1.5-flash"
            
            # Initialize Gemini if not already done
            if not hasattr(self, '_gemini_initialized'):
                self._init_gemini()
                self._gemini_initialized = True
            
            # Try Gemini generation
            result = self._generate_with_gemini(prompt, max_retries)
            
            # Restore original settings
            self.provider = original_provider
            self.model = original_model
            
            if result and result.get("success"):
                # Mark as fallback result
                result["fallback_used"] = True
                result["fallback_from"] = f"{original_provider.value}:{original_model}"
                result["primary_error"] = primary_error.get("error", "Unknown error")
                logger.info("✅ Gemini fallback successful!")
                return result
            else:
                logger.error("❌ Gemini fallback also failed")
                return primary_error
                
        except Exception as e:
            logger.error(f"❌ Gemini fallback exception: {e}")
            return primary_error
    
    def get_available_models(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all available models organized by provider."""
        models = {
            "gemini": [
                {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "cost": "High", "performance": "Highest"},
                {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "cost": "Low", "performance": "High"},
                {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "cost": "Medium", "performance": "High"},
                {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "cost": "Low", "performance": "Good"},
                {"id": "gemini-1.5-flash-8b", "name": "Gemini 1.5 Flash 8B", "cost": "Very Low", "performance": "Medium"},
            ]
        }
        
        if CLAUDE_AVAILABLE and CLAUDE_API_KEY:
            models["claude"] = [
                {"id": "claude-opus-4-20250514", "name": "Claude 4 Opus (World's Best Coding Model)", "cost": "Very High", "performance": "Highest"},
                {"id": "claude-sonnet-4-20250514", "name": "Claude 4 Sonnet (Latest, Best Balance)", "cost": "High", "performance": "Highest"},
                {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "cost": "Medium", "performance": "High"},
                {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku", "cost": "Low", "performance": "Good"},
                {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "cost": "High", "performance": "High"},
            ]
        
        if GROK_AVAILABLE and GROK_API_KEY:
            models["grok"] = [
                {"id": "grok-4", "name": "Grok 4 (Real-time Search)", "cost": "High", "performance": "Highest"},
                {"id": "grok-2-1212", "name": "Grok 2-1212 (Production Model)", "cost": "Medium", "performance": "High"},
                {"id": "grok-2-vision-1212", "name": "Grok 2 Vision-1212", "cost": "Medium", "performance": "High"},
                {"id": "grok-beta", "name": "Grok Beta", "cost": "High", "performance": "High"},
                {"id": "grok-vision-beta", "name": "Grok Vision Beta", "cost": "High", "performance": "High"},
            ]
        
        if GROK_AVAILABLE and OPENAI_API_KEY:  # Uses same openai library
            models["openai"] = [
                {"id": "gpt-4o-mini", "name": "GPT-4o Mini (Ultra-budget)", "cost": "Very Low", "performance": "High"},
                {"id": "gpt-4o", "name": "GPT-4o (Flagship)", "cost": "Medium", "performance": "Highest"},
                {"id": "gpt-4-turbo", "name": "GPT-4 Turbo (Premium)", "cost": "High", "performance": "Highest"},
                {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo (Budget)", "cost": "Low", "performance": "Medium"},
            ]
        
        return models
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost tracking summary."""
        return {
            "requests_made": self.cost_tracker["requests"],
            "estimated_cost_usd": round(self.cost_tracker["estimated_cost"], 4),
            "current_provider": self.provider.value,
            "current_model": self.model
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get current model information."""
        return {
            "current_model": self.model,
            "current_provider": self.provider.value,
            "cost_info": self.get_cost_summary(),
            "available_models": self.get_available_models()
        }
    
    def _is_claude_4_model(self) -> bool:
        """Check if current model is a Claude 4 model that supports thinking."""
        claude_4_models = [
            "claude-opus-4-20250514",
            "claude-sonnet-4-20250514"
        ]
        return self.model in claude_4_models