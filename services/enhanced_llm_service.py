"""
Enhanced LLM Service with multi-provider support (Gemini + Claude)
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

from config.settings import GEMINI_API_KEY, CLAUDE_API_KEY, MAX_RETRIES, RETRY_DELAY
from config.gemini_models import GEMINI_MODELS, get_model_info
from services.utils import format_chat_history, handle_api_error

logger = logging.getLogger(__name__)


class ModelProvider(Enum):
    """Available LLM providers."""
    GEMINI = "gemini"
    CLAUDE = "claude"


class ModelInfo:
    """
    Model information and pricing comparison across providers.
    
    PRICING COMPARISON (per 1M tokens as of 2025):
    
    === ULTRA-PREMIUM TIER ($$$$ - $15+ input) ===
    Claude 4 Opus:     $15.00 input / $75.00 output  🏆 World's best coding model
    Claude 3 Opus:     $15.00 input / $75.00 output  📚 Legacy premium
    GPT-4 Turbo:       $10.00 input / $30.00 output  🤖 OpenAI flagship
    
    === PREMIUM TIER ($$$ - $3-10 input) ===
    Claude 4 Sonnet:   $3.00 input / $15.00 output   ⭐ Best balance (RECOMMENDED)
    Claude 3.5 Sonnet: $3.00 input / $15.00 output   💪 Proven reliable
    Gemini 2.5 Pro:    $3.50 input / $10.50 output   🧠 Google's flagship
    Gemini 1.5 Pro:    $3.50 input / $10.50 output   📖 Large context
    GPT-4o:            $5.00 input / $15.00 output    🔥 OpenAI multimodal
    
    === PRODUCTION TIER ($$ - $0.5-3 input) ===
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
    💡 OpenAI GPT-4o mini is competitive in mid-tier
    💡 Context windows: Claude/Gemini (200K+) > OpenAI (128K)
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
    
    # OpenAI models (for reference - not implemented yet)
    OPENAI_MODELS = {
        "gpt-4-turbo": {"name": "GPT-4 Turbo", "cost": "High", "performance": "Highest"},
        "gpt-4o": {"name": "GPT-4o", "cost": "High", "performance": "Highest"},
        "gpt-4o-mini": {"name": "GPT-4o Mini", "cost": "Low", "performance": "Good"},
        "gpt-3.5-turbo": {"name": "GPT-3.5 Turbo", "cost": "Low", "performance": "Medium"},
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
        
        logger.info(f"🚀 Enhanced LLM Service initialized")
        logger.info(f"📊 Provider: {provider.value}, Model: {self.model}")
    
    def _get_default_model(self, provider: ModelProvider) -> str:
        """Get default model for provider."""
        if provider == ModelProvider.GEMINI:
            return GEMINI_MODELS.HIGH_PERFORMANCE
        elif provider == ModelProvider.CLAUDE:
            return "claude-sonnet-4-20250514"  # Default to Claude 4 Sonnet
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
    
    def switch_model(self, provider: ModelProvider, model: str):
        """Switch to a different model/provider."""
        old_info = f"{self.provider.value}:{self.model}"
        self.provider = provider
        self.model = model
        new_info = f"{provider.value}:{model}"
        logger.info(f"🔄 Switched model: {old_info} → {new_info}")
    
    def generate_text(self, prompt: str, max_retries: int = 3, enable_fallback: bool = True) -> Dict[str, Any]:
        """Generate text using the selected provider with automatic fallback."""
        primary_result = None
        
        if self.provider == ModelProvider.GEMINI:
            primary_result = self._generate_with_gemini(prompt, max_retries)
        elif self.provider == ModelProvider.CLAUDE:
            primary_result = self._generate_with_claude(prompt, max_retries)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
        
        # If primary provider succeeded, return result
        if primary_result and primary_result.get("success"):
            return primary_result
        
        # If primary failed and fallback is enabled, try Gemini Flash as backup
        if enable_fallback and self.provider == ModelProvider.CLAUDE:
            logger.warning(f"🔄 Claude failed, falling back to Gemini 1.5 Flash as backup...")
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
    
    def _generate_with_claude(self, prompt: str, max_retries: int) -> Dict[str, Any]:
        """Generate text using Claude."""
        if not self.claude_client:
            return {"success": False, "error": "Claude API not available", "provider": "claude"}
        
        logger.info(f"🤖 Generating with Claude: {self.model}")
        
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                response = self.claude_client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    temperature=0.1,  # Lower temperature for code generation
                    messages=[{"role": "user", "content": prompt}]
                )
                response_time = time.time() - start_time
                
                response_text = response.content[0].text
                
                # Extract token usage from Claude API response
                input_tokens = getattr(response.usage, 'input_tokens', 0)
                output_tokens = getattr(response.usage, 'output_tokens', 0)
                
                self._track_cost("claude", input_tokens, output_tokens)
                
                logger.info(f"✅ Claude generation successful ({response_time:.2f}s)")
                logger.info(f"📊 Token usage: {input_tokens} input + {output_tokens} output = {input_tokens + output_tokens} total")
                
                return {
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
                
            except Exception as e:
                logger.error(f"❌ Claude attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return {"success": False, "error": str(e), "provider": "claude"}
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
            
            # === OPENAI MODELS (for reference - could be added later) ===
            # OpenAI's strength: Multimodal capabilities and ecosystem
            "gpt-4-turbo": {"input": 10.0, "output": 30.0},       # Cheaper than Claude Opus
            "gpt-4o": {"input": 5.0, "output": 15.0},             # More expensive than Claude 4 Sonnet
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},       # 2x more than Gemini Flash
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
        
        return models
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost tracking summary."""
        return {
            "requests_made": self.cost_tracker["requests"],
            "estimated_cost_usd": round(self.cost_tracker["estimated_cost"], 4),
            "current_provider": self.provider.value,
            "current_model": self.model
        }