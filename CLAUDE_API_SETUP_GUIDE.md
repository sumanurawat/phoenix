# Claude API Setup Guide

## Overview
This guide documents how Claude API integration was added to the Phoenix platform for both local development and production deployment.

## Setup Complete ✅

### 1. Local Development (.env file)
- ✅ Added `CLAUDE_API_KEY` to `.env` file
- ✅ API key works for local testing and development

### 2. Production (GCP Secret Manager)
- ✅ Created secret `phoenix-claude-api-key` in GCP Secret Manager
- ✅ Granted access to `phoenix-service-account@phoenix-project-386.iam.gserviceaccount.com`
- ✅ Updated `cloudbuild.yaml` to include Claude API key in deployment

### 3. Code Integration
- ✅ Enhanced LLM Service supports both Gemini and Claude
- ✅ Model selection UI on analysis page
- ✅ Iterative coding agent works with both providers
- ✅ Cost tracking for both APIs

## Available Claude Models

### Claude 4 Models (Latest 2025):
- `claude-opus-4-20250514` - **World's Best Coding Model**, highest quality ($$$$)
- `claude-sonnet-4-20250514` - **Latest & Best Balance**, excellent for most tasks ($$$)

### Claude 3.5 Models (Proven & Reliable):
- `claude-3-5-sonnet-20241022` - High quality, established model ($$)
- `claude-3-5-haiku-20241022` - Fast and cost-effective ($)

### Claude 3 Models (Legacy):
- `claude-3-opus-20240229` - Premium legacy model ($$$)

## Configuration Files Updated

### 1. `.env` (Local Development)
```bash
CLAUDE_API_KEY=sk-ant-api03-[REDACTED_FOR_SECURITY]
```

### 2. `cloudbuild.yaml` (Production Deployment)
```yaml
- '--update-secrets'
- 'GEMINI_API_KEY=phoenix-gemini-api-key:latest,SECRET_KEY=phoenix-secret-key:latest,GOOGLE_API_KEY=phoenix-google-api-key:latest,GOOGLE_SEARCH_ENGINE_ID=phoenix-search-engine-id:latest,NEWSDATA_API_KEY=phoenix-newsdata-api-key:latest,KAGGLE_USERNAME=phoenix-kaggle-username:latest,KAGGLE_KEY=phoenix-kaggle-key:latest,CLAUDE_API_KEY=phoenix-claude-api-key:latest'
```

### 3. `requirements.txt` (Dependencies)
```bash
anthropic==0.40.0  # For Claude API integration (analysis)
matplotlib==3.8.2  # For data visualization in analysis
seaborn==0.13.0  # For statistical data visualization
numpy==1.26.2  # For numerical computing in analysis
```

## How to Use

### 1. Local Development
```bash
# Test the enhanced LLM service
python test_enhanced_llm.py

# Start local server
./start_local.sh
```

### 2. Production Deployment
```bash
# Deploy with Claude API support
gcloud builds submit --config cloudbuild.yaml
```

### 3. Model Selection in UI
1. Go to dataset analysis page
2. **NEW**: Provider defaults to "Anthropic Claude" (localhost) 🚀
3. **NEW**: Model defaults to **Claude 4 Sonnet** (best balance) ⭐
4. Iterative mode enabled by default for best results
5. Max iterations set to 5 (balanced)

**🆕 Localhost Defaults (Updated):**
- **Provider**: Anthropic Claude (was Gemini)
- **Model**: Claude 4 Sonnet (was Gemini 2.5 Flash)
- **Cost**: ~$0.20-0.50 per analysis (was ~$0.01-0.05)
- **Quality**: World-class coding model 🏆

**Model Recommendations:**
- **For Budget**: Switch to Gemini Flash (40x cheaper)
- **For Production**: Keep Claude 4 Sonnet (best balance) ⭐ **DEFAULT**
- **For Premium**: Upgrade to Claude 4 Opus (ultimate coding)

## GCP Secret Manager Commands

### View all secrets:
```bash
gcloud secrets list --project=phoenix-project-386
```

### View Claude secret specifically:
```bash
gcloud secrets describe phoenix-claude-api-key --project=phoenix-project-386
```

### Update Claude secret (if needed):
```bash
echo -n "NEW_API_KEY" | gcloud secrets versions add phoenix-claude-api-key --data-file=- --project=phoenix-project-386
```

## Cost Estimates & Model Comparison

> **📊 For complete pricing comparison with Gemini and OpenAI models, see:** [AI_MODEL_PRICING_COMPARISON.md](./AI_MODEL_PRICING_COMPARISON.md)

### Claude vs. Competitors Quick Comparison:

**🏆 Premium Tier** (Best Quality):
- **Claude 4 Sonnet**: $3.00/$15.00 per 1M ⭐ **Best Balance**
- **Gemini 2.5 Pro**: $3.50/$10.50 per 1M (cheaper output!)
- **GPT-4o**: $5.00/$15.00 per 1M (more expensive)

**💰 Budget Tier** (Best Value):
- **Claude 3.5 Haiku**: $0.25/$1.25 per 1M
- **Gemini 2.5 Flash**: $0.075/$0.30 per 1M (3x cheaper!)
- **GPT-4o Mini**: $0.15/$0.60 per 1M

**💎 Ultra-Premium** (Best Capability):
- **Claude 4 Opus**: $15.00/$75.00 per 1M 🏆 World's best coding
- **GPT-4 Turbo**: $10.00/$30.00 per 1M (cheaper alternative)

### Iterative Mode Cost Impact:
- **Claude 4 Sonnet** (5 iterations): ~$0.20-0.50 per analysis ⭐ **Recommended**
- **Claude 4 Opus** (5 iterations): ~$2.00-10.00 per analysis 💎 **Premium**
- **Claude 3.5 Haiku** (5 iterations): ~$0.05-0.20 per analysis 💰 **Budget**
- **Gemini 2.5 Flash** (5 iterations): ~$0.01-0.05 per analysis 🎯 **Ultra-Budget**

### Key Insights:
💡 **For Budget**: Gemini Flash models are 40-80x cheaper than Claude  
💡 **For Quality**: Claude 4 Sonnet offers best premium balance  
💡 **For Coding**: Claude 4 Opus is unmatched but very expensive  
💡 **For Production**: Claude 4 Sonnet recommended despite higher cost

## Testing

### Local Testing:
```bash
# Test both Gemini and Claude APIs
python test_enhanced_llm.py
```

### Production Testing:
1. Deploy the application
2. Go to dataset analysis page
3. Select Claude provider and model
4. Run analysis on iris dataset
5. Verify iterative mode works

## Security Notes
- ✅ API key stored securely in GCP Secret Manager
- ✅ Service account has minimal required permissions
- ✅ API key not exposed in logs (truncated display)
- ✅ Local .env file for development only

## Troubleshooting

### "Claude API not available" Error:
```bash
# Install Claude API library
pip install anthropic==0.40.0
```

### "Claude API key not found" Error:
- **Local**: Check `.env` file has `CLAUDE_API_KEY` set
- **Production**: Check secret exists in GCP Secret Manager

### Permission Errors in Production:
```bash
# Grant service account access to secret
gcloud secrets add-iam-policy-binding phoenix-claude-api-key \
    --member="serviceAccount:phoenix-service-account@phoenix-project-386.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project=phoenix-project-386
```

## Next Steps
1. ✅ Claude API fully integrated and tested
2. ✅ Model selection UI implemented
3. ✅ Iterative coding agent working
4. ✅ Production deployment configured
5. 🎯 Ready for user testing and feedback

The Claude API integration is now complete and ready for production use!