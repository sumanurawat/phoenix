# 🚀 Phoenix Development Workflow

## Quick Start

### Environment URLs
- **Local**: `http://localhost:5000`
- **Staging**: `https://phoenix-dev-234619602247.us-central1.run.app`
- **Production**: `https://phoenix-234619602247.us-central1.run.app`

### Daily Workflow
```bash
# 1. Start work
git checkout dev && git pull origin dev
./start_local.sh

# 2. Deploy to staging
git add . && git commit -m "feat: your changes"
git push origin dev  # Auto-deploys to staging

# 3. Test staging
./scripts/manage_env.sh open staging
./scripts/manage_env.sh logs staging --hours 1

# 4. Release to production
git checkout main && git merge dev && git push origin main
```

## Environment Configuration

| Environment | Branch | CPU | Memory | Max Instances |
|-------------|--------|-----|---------|---------------|
| Staging     | dev    | 1   | 1Gi     | 5             |
| Production  | main   | 2   | 2Gi     | 100           |

## Essential Commands

### Environment Management
```bash
./scripts/manage_env.sh status    # Check both environments
./scripts/manage_env.sh logs staging --hours 2
./scripts/manage_env.sh logs production --search "error"
```

### Log Monitoring
```bash
python scripts/fetch_logs.py --environment staging
python scripts/fetch_logs.py --environment production --hours 6
```

## Troubleshooting

### Staging Issues
- **Memory errors**: Check if 1Gi is sufficient
- **403 errors**: Verify IAM policy allows public access
- **Build failures**: Check secrets configuration

### Common Fixes
```bash
# Check service status
gcloud run services describe phoenix-dev --region=us-central1

# Fix IAM permissions
gcloud run services add-iam-policy-binding phoenix-dev \
  --member="allUsers" --role="roles/run.invoker"
```

## Best Practices
- ✅ Always test in staging before production
- ✅ Monitor logs after deployments
- ✅ Use feature branches for large changes
- ❌ Don't push directly to main
- ❌ Don't skip staging testing
