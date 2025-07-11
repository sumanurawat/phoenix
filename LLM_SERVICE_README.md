# 🚀 Unified LLM Service

A single, comprehensive service for calling any LLM provider (Gemini, OpenAI, Anthropic, Grok, etc.) with one consistent API.

## 🎯 What This Solves

You wanted:
- ✅ **Single service** for all LLM calls
- ✅ **Model name** as argument to pick the right provider  
- ✅ **Automatic API key management** based on configuration
- ✅ **No more confusion** between GCP Gemini vs AI Studio Gemini
- ✅ **One source** for all LLM interactions

## 🏗️ What's Been Built

### Core Files
- `services/unified_llm_service.py` - Main unified service
- `services/llm_migration_guide.py` - Migration utilities & compatibility layer
- `test_unified_llm.py` - Test script and interactive demo
- `requirements_llm.txt` - Additional dependencies
- `.env.llm.example` - Configuration template

### Features
- **Multi-Provider Support**: Gemini (GCP + AI Studio), OpenAI, Anthropic, Grok
- **Automatic Provider Selection**: Based on model name
- **Streaming Support**: Real-time responses across all providers
- **Usage Tracking**: Monitor costs and token usage
- **Fallback Mechanisms**: Automatic retry with different models
- **Backward Compatibility**: Drop-in replacement for existing service

## ⚡ Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements_llm.txt
```

### 2. Configure API Keys
Copy `.env.llm.example` to your `.env` file and add your API keys:

```bash
# At minimum, configure one of these:
GCP_PROJECT_ID=your-gcp-project-id              # For Gemini via GCP
GEMINI_API_KEY=your-gemini-api-key               # For Gemini via AI Studio  
OPENAI_API_KEY=sk-your-openai-api-key           # For OpenAI models
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key     # For Claude models
```

### 3. Test Everything
```bash
python test_unified_llm.py
```

### 4. Start Using

**Option A: New Unified Interface (Recommended)**
```python
from services.unified_llm_service import UnifiedLLMService

llm = UnifiedLLMService()

# Use any model with the same interface
response = llm.generate("Hello", "gemini-2.0-flash")
response = llm.generate("Hello", "gpt-4") 
response = llm.generate("Hello", "claude-3-sonnet")

# Streaming works across all providers
for chunk in llm.stream("Tell me a story", "gemini-2.0-flash"):
    print(chunk, end="")
```

**Option B: Drop-in Replacement**
```python
# Replace your existing import:
# from services.llm_service import LLMService

# With this:
from services.llm_migration_guide import LegacyLLMServiceWrapper as LLMService

# Everything else works exactly the same!
llm = LLMService()
response = llm.generate_content("Hello world")
```

## 🎮 Interactive Demo

Run the test script and choose option 2 for an interactive demo:

```bash
python test_unified_llm.py
```

Commands in demo:
- `!models` - List available models
- `!model gpt-4` - Switch to different model
- `!stream tell me a joke` - Stream response
- `!stats` - Show usage statistics

## 🔧 Model Support

The service automatically routes to the correct provider based on model name:

| Model | Provider | Notes |
|-------|----------|-------|
| `gemini-2.0-flash` | Gemini GCP | Recommended for production |
| `gemini-1.5-pro` | Gemini GCP | Advanced reasoning |
| `gpt-4` | OpenAI | Latest GPT-4 |
| `gpt-4-turbo` | OpenAI | Faster GPT-4 |
| `claude-3-sonnet` | Anthropic | Balanced Claude model |
| `claude-3-opus` | Anthropic | Most capable Claude |
| `grok-beta` | Grok | X.AI's model |

## 🔄 Migration Guide

### Current State ➜ New State

**Before:** Multiple different LLM clients, confusion about which API to use
```python
import google.generativeai as genai
import openai
# Different interfaces, different error handling, different configs
```

**After:** Single unified interface
```python
from services.unified_llm_service import UnifiedLLMService
llm = UnifiedLLMService()
# Same interface for all providers
```

### For Your Existing Code

Your existing `chat_service.py` and API routes will work unchanged if you use the compatibility wrapper:

```python
# In chat_service.py, replace:
# from services.llm_service import LLMService

# With:  
from services.llm_migration_guide import LegacyLLMServiceWrapper as LLMService
```

## 📊 Usage Tracking

```python
llm = UnifiedLLMService()

# Make some calls
llm.generate("Hello", "gpt-4")
llm.generate("Hi", "claude-3-sonnet") 

# Check usage
stats = llm.get_usage_stats()
print(stats)
# {
#   "total_requests": 2,
#   "total_tokens": 156,
#   "provider_usage": {
#     "openai": {"requests": 1, "tokens": 78},
#     "anthropic": {"requests": 1, "tokens": 78}
#   }
# }
```

## 🏥 Error Handling & Fallbacks

The service includes robust error handling:

1. **Provider Selection**: Automatically chooses the right provider for each model
2. **Fallback Models**: If a model fails, falls back to Gemini GCP (your current default)
3. **Retry Logic**: Automatic retries with exponential backoff
4. **Graceful Degradation**: Service continues working even if some providers are down

## 🔐 API Key Configuration

### Gemini (Recommended)

**Option 1: GCP (Production)**
```bash
# Set up Application Default Credentials
gcloud auth application-default login

# In .env
GCP_PROJECT_ID=your-project-id
```

**Option 2: AI Studio (Development)**  
```bash
# Get key from https://aistudio.google.com/
GEMINI_API_KEY=your-api-key
```

### Other Providers

```bash
# OpenAI: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-key

# Anthropic: https://console.anthropic.com/
ANTHROPIC_API_KEY=sk-ant-your-key

# Grok: https://console.x.ai/
GROK_API_KEY=your-key
```

## 🚀 Benefits

### Before vs After

| Before | After |
|--------|-------|
| ❌ Multiple LLM clients | ✅ Single unified service |
| ❌ Different APIs for each provider | ✅ Same API for all providers |
| ❌ Manual provider selection | ✅ Automatic based on model name |
| ❌ Separate error handling | ✅ Unified error handling |
| ❌ No usage tracking | ✅ Built-in usage tracking |
| ❌ No streaming standardization | ✅ Streaming works everywhere |

### New Capabilities

- 🎯 **Model Flexibility**: Switch between providers instantly
- 📊 **Usage Analytics**: Track costs and usage across providers  
- 🔄 **Streaming**: Real-time responses from any provider
- 🛡️ **Robust Fallbacks**: Never lose service due to one provider issue
- 🎮 **Interactive Testing**: Built-in demo and testing tools

## 🔧 Troubleshooting

### Common Issues

**"No models available"**
- Check your API keys in `.env`
- Run `python test_unified_llm.py` to diagnose

**"Import error"**
- Install dependencies: `pip install -r requirements_llm.txt`
- Check you're in the phoenix project directory

**"Provider not available"**
- Verify API keys are correct
- Check internet connectivity
- Some providers may have geographic restrictions

### Getting Help

1. Run the test script: `python test_unified_llm.py`
2. Check the configuration: Review `.env.llm.example`
3. Test individual providers in the interactive demo

## 🎯 Next Steps

1. **Test the service**: `python test_unified_llm.py`
2. **Update your code**: Use the compatibility wrapper or new interface  
3. **Explore new models**: Try GPT-4, Claude, or other providers
4. **Monitor usage**: Check `service.get_usage_stats()` regularly
5. **Consider costs**: Different providers have different pricing

## 🎉 Success!

You now have a single, unified LLM service that:
- ✅ Supports all major LLM providers
- ✅ Uses model names to automatically select providers
- ✅ Manages API keys through configuration
- ✅ Provides a single interface for all LLM calls
- ✅ Maintains backward compatibility with your existing code

**No more confusion about which API to use - just specify the model name and it works!**