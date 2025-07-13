# Phoenix System Overview for AI Agents

This document provides essential context about the Phoenix platform that every AI agent should understand before working with the codebase.

## 🌟 **Platform Overview**

Phoenix is a sophisticated AI-powered platform that combines multiple services into a unified web application. It demonstrates modern web development practices with advanced AI integration.

### **Core Services**
1. **Derplexity** - AI-powered search and question answering
2. **Doogle** - Intelligent web search with AI summaries  
3. **Robin** - Advanced AI chat interface with multi-provider support
4. **Dataset Discovery & Analysis** - Kaggle integration with automated analysis
5. **URL Shortener (Deep Links)** - Link management with analytics

### **Key Features**
- **Multi-Provider AI**: Support for Gemini, Claude, OpenAI, and Grok
- **Modern Split-View UI**: Resizable panels with ChatGPT-like interface
- **Docker Integration**: Secure containerized code execution
- **Environment-Aware Cost Controls**: Production restrictions for cost management
- **Real-time Conversation Tracking**: Live model interactions display

## 🏗️ **System Architecture**

### **Infrastructure Stack**
- **Platform**: Google Cloud Platform (GCP)
- **Compute**: Cloud Run (serverless containers)
- **Database**: Firebase Firestore
- **Authentication**: Firebase Auth
- **Secrets**: GCP Secret Manager
- **CI/CD**: Cloud Build with GitHub integration
- **Frontend**: HTML/CSS/JavaScript with Bootstrap
- **Backend**: Python Flask

### **Project Configuration**
- **GCP Project ID**: `phoenix-project-386`
- **Project Number**: `234619602247`
- **Primary Region**: `us-central1`

### **Environment Structure**
```
Production:  phoenix         → https://phoenix-234619602247.us-central1.run.app
Staging:     phoenix-dev     → https://phoenix-dev-234619602247.us-central1.run.app  
Local:       localhost:5000  → http://localhost:5000
```

## 🔄 **Development Workflow**

### **Git Branch Strategy**
- **main**: Production branch (auto-deploys to production)
- **dev**: Staging branch (auto-deploys to staging)
- **feature/***: Feature development branches
- **hotfix/***: Emergency production fixes

### **Deployment Pipeline**
```
Code Push → GitHub → Cloud Build Trigger → Container Build → Cloud Run Deploy
```

### **Development Process**
1. Work on `dev` branch for regular development
2. Test in staging environment automatically
3. Merge to `main` for production deployment
4. Monitor with comprehensive logging tools

## 🤖 **AI/LLM Integration**

### **Supported Providers**
1. **Google Gemini**: Primary cost-effective option
2. **Anthropic Claude**: Premium coding and analysis
3. **OpenAI GPT**: General purpose AI tasks
4. **Grok**: Alternative AI provider

### **Model Selection Strategy**
- **Production/Staging**: Only Gemini Flash 8B (cost control)
- **Localhost**: All models available (Claude 4 Sonnet default)
- **Iterative Mode**: Multi-attempt code generation until success

### **Cost Management**
- **Budget Tier**: Gemini Flash 8B (~$0.01-0.05 per analysis)
- **Premium Tier**: Claude 4 Sonnet (~$0.20-0.50 per analysis)
- **Ultra Premium**: Claude 4 Opus (~$2.00-10.00 per analysis)

## 🔒 **Security & Authentication**

### **Secret Management**
All sensitive information stored in GCP Secret Manager:
- `phoenix-gemini-api-key`: Gemini API access
- `phoenix-claude-api-key`: Claude API access  
- `phoenix-openai-api-key`: OpenAI API access
- `phoenix-firebase-key`: Firebase service account
- `phoenix-kaggle-username` & `phoenix-kaggle-key`: Kaggle API

### **Authentication Flow**
- Firebase Auth for user management
- Service accounts for GCP resource access
- API keys for external service integration

## 📊 **Database Schema**

### **Firebase Collections**
- **users**: User profiles and preferences
- **links**: URL shortener data with analytics
- **conversations**: Chat history and interactions
- **datasets**: Dataset discovery and analysis results

### **Key Data Patterns**
- Real-time updates using Firestore listeners
- Structured data with proper indexing
- Analytics tracking for user interactions

## 🛠️ **Key Development Tools**

### **Monitoring & Debugging**
- **Primary Tool**: `scripts/fetch_logs.py` - Intelligent log analysis
- **Environment Management**: `scripts/manage_env.sh` - Multi-environment control
- **Testing Suite**: Multiple specialized test scripts

### **Local Development**
- **Start Script**: `./start_local.sh` - Local server startup
- **Testing Scripts**: `test_*.py` - Feature-specific testing
- **Debug Scripts**: `debug_*.py` - Component debugging

### **Deployment Tools**
- **Cloud Build**: Automatic CI/CD pipeline
- **Docker**: Containerized deployment
- **Git Hooks**: Automated testing and deployment

## 📈 **Performance Characteristics**

### **Response Times**
- **Static Pages**: <100ms
- **AI Queries**: 2-10 seconds (depending on model)
- **Dataset Analysis**: 30-120 seconds (iterative mode)
- **Database Queries**: <500ms

### **Scalability**
- **Cloud Run**: Auto-scaling based on demand
- **Firebase**: Serverless database scaling
- **CDN**: Static asset optimization

## 🎯 **Business Context**

### **Target Users**
- Developers seeking AI-powered tools
- Researchers needing dataset analysis
- Teams requiring collaborative AI interfaces
- Organizations wanting cost-controlled AI access

### **Value Proposition**
- **Unified Platform**: Multiple AI services in one interface
- **Cost Control**: Environment-aware model restrictions
- **Modern UX**: Professional IDE-like experience
- **Reliable Infrastructure**: Enterprise-grade cloud platform

## 🔧 **Technical Debt & Known Issues**

### **Current Limitations**
- Docker daemon dependency for code execution (fallback to local)
- Manual cost monitoring (no automated alerts)
- Limited model fine-tuning capabilities

### **Planned Improvements**
- Enhanced analytics dashboard
- Advanced dataset analysis features
- Improved cost optimization tools
- Better error handling and recovery

## 📚 **Critical Files for Agents**

### **Configuration**
- `app.py`: Main Flask application
- `requirements.txt`: Python dependencies
- `cloudbuild.yaml` / `cloudbuild-dev.yaml`: Deployment configuration
- `.env`: Local environment variables (not in git)

### **Core Services**
- `services/enhanced_llm_service.py`: Multi-provider AI integration
- `services/dataset_discovery/`: Complete dataset analysis system
- `api/`: REST API endpoints
- `templates/`: HTML templates with modern UI

### **Operations**
- `scripts/fetch_logs.py`: Primary debugging tool
- `scripts/manage_env.sh`: Environment management
- `test_*.py`: Testing suite
- `debug_*.py`: Debugging utilities

## 🎪 **Quick Start for Agents**

When approaching any task:

1. **Understand Context**: Read this system overview
2. **Check Environment**: Use `./scripts/manage_env.sh status`
3. **Review Logs**: Use `python scripts/fetch_logs.py` for current state
4. **Follow Patterns**: Reference existing code for conventions
5. **Test Thoroughly**: Use local → staging → production progression
6. **Monitor Results**: Always check logs after changes

---

**💡 Key Insight**: Phoenix is a production-ready, cost-optimized AI platform with sophisticated infrastructure. Every change should consider cost implications, user experience, and system reliability.