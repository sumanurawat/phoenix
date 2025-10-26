# Phoenix Infrastructure Provisioning

Production-grade infrastructure-as-code scripts for the Phoenix AI Social Platform.

## Directory Structure

```
infrastructure/
├── README.md                    # This file
├── gcp/                         # Google Cloud Platform resources
│   ├── redis-memorystore.sh    # Redis for job queue (Phase 3)
│   ├── cloud-run-services.sh   # Cloud Run deployment configs
│   └── secret-manager.sh       # Secret management utilities
└── monitoring/                  # Monitoring and alerting configs
    ├── dashboards/             # GCP Monitoring dashboards
    └── alerts/                 # Alert policies
```

## Usage

### Phase 3: Video Generation Infrastructure

**1. Provision Redis for Job Queue:**
```bash
chmod +x infrastructure/gcp/redis-memorystore.sh
./infrastructure/gcp/redis-memorystore.sh
```

**2. Store Credentials in Secret Manager:**
```bash
# Follow the "Next Steps" output from the Redis provisioning script
```

**3. Deploy Services:**
```bash
gcloud builds submit --config cloudbuild.yaml .
```

## Cost Tracking

All resources are labeled with:
- `app=phoenix` - Application identifier
- `service=<name>` - Service type (cache, worker, api, etc.)
- `env=<env>` - Environment (prod, staging, dev)
- `phase=<num>` - Development phase for tracking feature costs

### View Costs by Phase

**Phase 3 Infrastructure Costs:**
```bash
# Navigate to GCP Billing Reports and filter:
# labels.app = "phoenix"
# labels.phase = "3"
```

### Expected Monthly Costs

| Resource | Specification | Monthly Cost |
|----------|--------------|--------------|
| Redis (Memorystore) | 1GB BASIC | ~$40 |
| Cloud Run (Worker) | 1 min instance, 4GB RAM | ~$20 |
| Cloud Run (API) | Auto-scale, 1GB RAM | ~$10 |
| Vertex AI (Veo) | Per-video | ~$0.32/video |
| Cloud Storage (Temp) | Temporary video files | ~$0.01 |
| Cloudflare R2 | Video storage | $0.28/10K videos |

**Total Infrastructure:** ~$70/month + $0.32/video

## Best Practices

1. **Always run provisioning scripts from project root**
2. **Review cost estimates before provisioning**
3. **Check for existing resources to avoid duplicates**
4. **Store all credentials in Secret Manager, never in code**
5. **Use labels consistently for cost tracking**
6. **Test in staging environment first**

## Security

- All scripts require explicit confirmation for destructive operations
- Service account permissions follow principle of least privilege
- Secrets are never logged or exposed in output
- All resources use private networking where possible

## Monitoring

After provisioning, set up monitoring:

1. **Cloud Monitoring Dashboard**: `infrastructure/monitoring/dashboards/`
2. **Alert Policies**: `infrastructure/monitoring/alerts/`
3. **Log-based Metrics**: Defined in deployment configs

## Rollback

To deprovision resources:

```bash
# Redis
gcloud redis instances delete phoenix-cache-prod --region=us-central1

# Cloud Run services
gcloud run services delete phoenix-video-worker --region=us-central1
```

## Support

For issues or questions:
- Check GCP Cloud Logging: `gcloud run services logs read <service-name>`
- Review provisioning logs in this directory
- Consult Phase 3 implementation plan: `PHASE_3_IMPLEMENTATION_PLAN.md`
