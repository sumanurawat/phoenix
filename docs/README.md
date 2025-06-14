# 📚 Phoenix Documentation Index

This directory contains comprehensive documentation for the Phoenix application development workflow and staging environment setup.

## 📖 Documentation Overview

### 🚀 Getting Started
- **[Quick Reference](QUICK_REFERENCE.md)** - Essential commands and URLs for daily use
- **[Daily Workflow Checklist](DAILY_WORKFLOW_CHECKLIST.md)** - Step-by-step checklist for daily development tasks

### 🏗️ Comprehensive Guides
- **[Development Workflow Guide](DEVELOPMENT_WORKFLOW_GUIDE.md)** - Complete guide to development workflow, staging setup, and best practices
- **[Staging Technical Configuration](STAGING_TECHNICAL_CONFIG.md)** - Detailed technical configuration of staging environment

### 📋 Setup Documentation
- **[Staging Setup Complete](STAGING_SETUP_COMPLETE.md)** - Summary of completed staging environment setup
- **[Staging Environment Guide](STAGING_ENVIRONMENT_GUIDE.md)** - Original staging environment setup guide

### 🔧 Tool-Specific Guides
- **[Log Fetching Usage](LOG_FETCHING_USAGE.md)** - How to use the enhanced log fetching tools
- **[Log Fetching Guide](LOG_FETCHING_GUIDE.md)** - Original log fetching setup guide

### 🎯 Feature Documentation
- **[Deeplink Implementation Plan](DEEPLINK_IMPLEMENTATION_PLAN.md)** - URL shortening feature implementation
- **[Deeplink PRD](DEEPLINK_PRD.md)** - Product requirements for URL shortening
- **[Deeplink System Design](DEEPLINK_SYSTEM_DESIGN.md)** - Technical design for URL shortening
- **[Manual Testing Plan](MANUAL_TESTING_PLAN.md)** - Testing procedures for features

## 🗂️ Documentation Categories

### For Daily Development
1. [Quick Reference](QUICK_REFERENCE.md) - Your daily commands cheat sheet
2. [Daily Workflow Checklist](DAILY_WORKFLOW_CHECKLIST.md) - Ensure you don't miss important steps

### For Understanding the System
1. [Development Workflow Guide](DEVELOPMENT_WORKFLOW_GUIDE.md) - Complete workflow and best practices
2. [Staging Technical Configuration](STAGING_TECHNICAL_CONFIG.md) - Technical details of the setup

### For Troubleshooting
1. [Development Workflow Guide](DEVELOPMENT_WORKFLOW_GUIDE.md#troubleshooting) - Common issues and solutions
2. [Log Fetching Usage](LOG_FETCHING_USAGE.md) - How to investigate issues with logs

### For New Team Members
1. [Staging Setup Complete](STAGING_SETUP_COMPLETE.md) - Overview of the current setup
2. [Development Workflow Guide](DEVELOPMENT_WORKFLOW_GUIDE.md) - Complete onboarding guide
3. [Quick Reference](QUICK_REFERENCE.md) - Essential commands to get started

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
