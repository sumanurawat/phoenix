# ✅ Phoenix Development - Daily Workflow Checklist

## 🌅 Starting Your Day

### Initial Setup
- [ ] Check current branch: `git branch`
- [ ] Switch to dev branch: `git checkout dev`
- [ ] Pull latest changes: `git pull origin dev`
- [ ] Check environment status: `./scripts/manage_env.sh status`
- [ ] Start local server: `./start_local.sh`

### Environment Health Check
- [ ] Staging environment accessible: `./scripts/manage_env.sh open staging`
- [ ] No critical errors in staging: `./scripts/manage_env.sh logs staging --hours 12`
- [ ] Production environment stable: `./scripts/manage_env.sh logs production --hours 2`

## 🛠️ Feature Development

### Before Starting New Feature
- [ ] Create feature branch: `git checkout -b feature/your-feature-name`
- [ ] Understand requirements clearly
- [ ] Plan implementation approach
- [ ] Identify test scenarios

### During Development
- [ ] Test locally frequently: `http://localhost:5000`
- [ ] Commit small, logical changes: `git add . && git commit -m "descriptive message"`
- [ ] Test edge cases and error scenarios
- [ ] Ensure existing functionality still works

### Ready for Staging
- [ ] All local tests pass
- [ ] Code reviewed (self-review or peer review)
- [ ] Merge to dev: `git checkout dev && git merge feature/your-feature-name`
- [ ] Push to staging: `git push origin dev`
- [ ] Wait for deployment: Check build status in Cloud Console
- [ ] Verify staging deployment: `./scripts/manage_env.sh status`

## 🧪 Staging Testing

### Functional Testing
- [ ] Test new feature thoroughly in staging
- [ ] Test all existing critical user flows
- [ ] Test authentication and user sessions
- [ ] Test error handling and edge cases
- [ ] Verify performance is acceptable

### Technical Validation
- [ ] Check staging logs for errors: `./scripts/manage_env.sh logs staging --hours 2`
- [ ] No memory issues (SIGKILL errors)
- [ ] No authentication errors
- [ ] No database connection issues
- [ ] Response times acceptable

### User Experience Testing
- [ ] Test on different browsers/devices
- [ ] Verify mobile responsiveness
- [ ] Check loading times
- [ ] Ensure intuitive user flows
- [ ] Test accessibility features

## 🚀 Production Release

### Pre-Release Checklist
- [ ] All staging tests completed successfully
- [ ] No errors in staging logs for past 2 hours
- [ ] Team approval received (if required)
- [ ] Release notes prepared
- [ ] Backup plan identified if rollback needed

### Release Process
- [ ] Switch to main: `git checkout main`
- [ ] Pull latest: `git pull origin main`
- [ ] Merge dev: `git merge dev`
- [ ] Push to production: `git push origin main`
- [ ] Monitor deployment: `./scripts/manage_env.sh status`

### Post-Release Monitoring
- [ ] Check production logs: `./scripts/manage_env.sh logs production --hours 1`
- [ ] Test critical user flows in production
- [ ] Monitor for 30 minutes post-deployment
- [ ] Verify metrics in Cloud Console
- [ ] No performance degradation

## 🆘 Issue Response

### When Staging Issues Found
- [ ] Document the issue clearly
- [ ] Check staging logs: `./scripts/manage_env.sh logs staging --search "error"`
- [ ] Reproduce locally if possible
- [ ] Fix and test locally
- [ ] Re-deploy to staging: `git push origin dev`
- [ ] Re-test in staging

### When Production Issues Found
- [ ] Assess severity and impact
- [ ] Check production logs: `./scripts/manage_env.sh logs production --hours 2`
- [ ] If critical: Consider immediate rollback
- [ ] Document issue and create hotfix branch
- [ ] Implement minimal fix
- [ ] Test locally, then deploy to staging
- [ ] If staging tests pass, deploy to production
- [ ] Monitor closely post-fix

## 🔍 Weekly Maintenance

### Code Quality
- [ ] Review and clean up feature branches
- [ ] Merge completed features to dev
- [ ] Update documentation if needed
- [ ] Review and address technical debt

### Environment Health
- [ ] Check resource usage in Cloud Console
- [ ] Review error patterns in logs over past week
- [ ] Verify both environments are running latest code
- [ ] Clean up old container images if needed

### Performance Review
- [ ] Review response times and performance metrics
- [ ] Check for memory leaks or resource issues
- [ ] Optimize slow queries or endpoints
- [ ] Update dependencies if needed

## 📋 Emergency Procedures

### Production Down
1. [ ] Check service status: `./scripts/manage_env.sh status`
2. [ ] Check recent deployments: `gcloud builds list --limit=5`
3. [ ] Check logs for errors: `./scripts/manage_env.sh logs production --hours 2`
4. [ ] If recent deployment caused issue, consider rollback
5. [ ] Contact team/stakeholders about outage
6. [ ] Document incident and resolution

### Database Issues
1. [ ] Check Firestore console for errors
2. [ ] Verify Firebase Auth is working
3. [ ] Check service account permissions
4. [ ] Test database connectivity from staging
5. [ ] Review recent database operations

### Build/Deployment Failures
1. [ ] Check build logs: `gcloud builds list --limit=3`
2. [ ] Review build configuration files
3. [ ] Check for syntax errors in code
4. [ ] Verify all required files are committed
5. [ ] Re-trigger build if transient failure

## 🎯 Success Metrics

### Daily Goals
- [ ] No production errors for the day
- [ ] All feature development completed as planned
- [ ] Staging environment stable and tested
- [ ] Code quality maintained

### Weekly Goals
- [ ] All planned features released successfully
- [ ] No rollbacks or hotfixes needed
- [ ] Performance metrics stable or improved
- [ ] Technical debt reduced

---

💡 **Pro Tip**: Print this checklist or bookmark it for daily reference. Consistency in following these steps will prevent most issues and ensure smooth deployments!
