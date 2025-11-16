# AI Agent Documentation Hub

This directory contains documentation specifically designed for AI agents working with the Phoenix codebase. These documents provide structured, actionable information that enables agents to understand context, execute tasks, and navigate the system effectively.

## 📋 **Quick Agent Reference**

### **Immediate Actions Available**
- 🔍 **Log Analysis**: Use `python scripts/fetch_logs.py` for production debugging
- 🚀 **Deployment**: Check `docs/ai-agents/deployment-procedures.md` 
- 🧪 **Testing**: Reference `docs/ai-agents/testing-procedures.md`
- 🛠️ **Development**: Follow `docs/ai-agents/development-patterns.md`

### **Key System Context**
- **Platform**: Multi-service AI platform (Derplexity, Doogle, Robin, Video Generation)
- **Infrastructure**: GCP Cloud Run + Firebase + Docker
- **AI Integration**: Multi-provider LLM support (Gemini, Claude, OpenAI)
- **Development Model**: Staging (dev branch) → Production (main branch)

## 📁 **Agent Documentation Structure**

### **Core Agent Guides**
1. **[System Overview](./system-overview.md)** - Essential platform knowledge
2. **[Common Operations](./common-operations.md)** - Frequently needed procedures  
3. **[Deployment Procedures](./deployment-procedures.md)** - How to deploy and monitor
4. **[Testing Procedures](./testing-procedures.md)** - Testing patterns and scripts
5. **[Development Patterns](./development-patterns.md)** - Coding conventions and practices
6. **[Troubleshooting Guide](./troubleshooting-guide.md)** - Problem resolution procedures

### **Specialized Knowledge**
7. **[Feature Implementation](./feature-implementation.md)** - How features are built
8. **[Database Operations](./database-operations.md)** - Data management procedures
9. **[API Reference](./api-reference.md)** - Key endpoints and usage
10. **[Security Protocols](./security-protocols.md)** - Security practices and secrets management

## 🎯 **Agent Usage Patterns**

### **For Code Analysis Tasks**
```
1. Read system-overview.md for context
2. Check development-patterns.md for conventions
3. Review specific feature docs in ../features/
4. Apply patterns from common-operations.md
```

### **For Deployment Tasks**
```
1. Check deployment-procedures.md
2. Use scripts/fetch_logs.py for monitoring
3. Follow troubleshooting-guide.md if issues arise
4. Reference security-protocols.md for secrets
```

### **For Feature Development**
```
1. Review feature-implementation.md patterns
2. Check database-operations.md for data changes
3. Follow testing-procedures.md for validation
4. Use development-patterns.md for code style
```

### **For Debugging Tasks**
```
1. Start with troubleshooting-guide.md
2. Use python scripts/fetch_logs.py --hours 24 --severity ERROR
3. Check common-operations.md for related procedures
4. Reference api-reference.md for endpoint behavior
```

## 🔧 **Essential Commands for Agents**

### **Log Analysis** (Most Important!)
```bash
# Fetch recent production errors
python scripts/fetch_logs.py --environment production --hours 6 --severity ERROR

# Search for specific issues  
python scripts/fetch_logs.py --search "video" --hours 12

# Get staging logs with full analysis
python scripts/fetch_logs.py --environment staging --hours 2 --save-json
```

### **Environment Management**
```bash
# Check all environments status
./scripts/manage_env.sh status

# Deploy to staging
git push origin dev

# Deploy to production  
git push origin main

# Monitor deployment
./scripts/manage_env.sh logs production --hours 1
```

### **Local Development**
```bash
# Start local server
./start_local.sh

# Test AI services
python test_enhanced_llm.py

# Debug specific features
python debug_enhanced_llm.py
```

### **Testing & Validation**
```bash
# Test Docker fallback
python test_docker_fallback.py

# Test enhanced LLM service
python test_enhanced_llm.py
```

## 🧠 **Context Management for Agents**

### **Always Remember These Key Facts**
1. **Environment URLs**:
   - Production: https://phoenix-234619602247.us-central1.run.app
   - Staging: https://phoenix-dev-234619602247.us-central1.run.app
   - Local: http://localhost:5000

2. **GCP Project**: phoenix-project-386

3. **Key Services**:
   - Cloud Run (application hosting)
   - Firebase (authentication + database)
   - Secret Manager (API keys)
   - Cloud Build (CI/CD)

4. **Cost Management**:
   - Production: Only Gemini Flash 8B (cost-effective)
   - Localhost: All models available (Claude 4, etc.)

5. **Architecture Pattern**: Modern split-view UI with resizable panels

## 📊 **Agent Performance Metrics**

When working with this codebase, agents should track:
- **Task Completion Time**: How quickly operations complete
- **Error Resolution Rate**: Success in fixing issues
- **Code Quality**: Following established patterns
- **Documentation Usage**: Referencing appropriate guides

## 🔄 **Feedback Loop**

If you discover missing information or unclear procedures:
1. Note the gap in documentation
2. Suggest improvements in commit messages
3. Update relevant agent docs when adding features
4. Maintain this README as the authoritative agent guide

---

**💡 Pro Tip**: Start every task by reading the relevant agent guide. The log fetching script (`scripts/fetch_logs.py`) is your best friend for debugging - it provides intelligent analysis and specific recommendations!