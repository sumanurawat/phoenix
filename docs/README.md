# 📚 Phoenix Documentation

## Essential Documentation

### 🚀 Start Here
- **[Consolidated Workflow](CONSOLIDATED_WORKFLOW.md)** - Complete development workflow and commands
- **[Quick Reference](QUICK_REFERENCE.md)** - Daily commands cheat sheet
- **[Daily Workflow Checklist](DAILY_WORKFLOW_CHECKLIST.md)** - Development checklist

### 🏗️ System Design
- **[Development Workflow Guide](DEVELOPMENT_WORKFLOW_GUIDE.md)** - Detailed workflow documentation
- **[Deeplink System Design](DEEPLINK_SYSTEM_DESIGN.md)** - URL shortening architecture

### 🔧 Operations
- **[Log Fetching Usage](LOG_FETCHING_USAGE.md)** - Enhanced log monitoring tools
- **[Manual Testing Plan](MANUAL_TESTING_PLAN.md)** - Testing procedures

## 🔗 Key Resources

### Environment URLs
- **Local Development**: `http://localhost:5000`
- **Staging**: `https://phoenix-dev-234619602247.us-central1.run.app`
- **Production**: `https://phoenix-234619602247.us-central1.run.app`

### Essential Commands
```bash
# Environment status
./scripts/manage_env.sh status

# Deploy to staging
git push origin dev

# Deploy to production  
git checkout main && git merge dev && git push origin main

# Check logs
./scripts/manage_env.sh logs staging --hours 2
./scripts/manage_env.sh logs production --hours 1
```

### Cloud Console Links
- **Cloud Build**: https://console.cloud.google.com/cloud-build/builds?project=phoenix-project-386
- **Cloud Run**: https://console.cloud.google.com/run?project=phoenix-project-386
- **Logs**: https://console.cloud.google.com/logs?project=phoenix-project-386

## 📅 Document Maintenance

### When to Update Documentation
- ✅ When adding new features that affect workflow
- ✅ When changing deployment processes
- ✅ When adding new tools or scripts
- ✅ When discovering new troubleshooting procedures
- ✅ When team processes change

### How to Update
1. Edit the relevant markdown files
2. Update this index if adding new documents
3. Test any command examples provided
4. Commit documentation changes with descriptive messages

## 🎯 Documentation Standards

### File Naming
- Use UPPER_CASE for document names
- Use descriptive names that indicate content
- Include file extensions (.md for markdown)

### Content Structure
- Start with a clear title and purpose
- Use emoji for visual organization 📚
- Include table of contents for longer documents
- Provide code examples with proper syntax highlighting
- Include troubleshooting sections where applicable

### Code Examples
- Always test commands before documenting
- Include expected output where helpful
- Use consistent formatting and indentation
- Provide context for when to use each command

---

*This documentation suite provides everything needed for effective Phoenix development. Start with the Quick Reference for immediate needs, then dive into the comprehensive guides for deeper understanding.*
