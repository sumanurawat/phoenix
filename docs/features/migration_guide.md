# Feature Gating Migration Guide

This guide explains how to use, rollback, and extend the new centralized feature gating system in Phoenix AI.

## Quick Start

### Enable the New System

1. Set the environment variable:
   ```bash
   export FEATURE_GATING_V2_ENABLED=true
   ```
   Or in your `.env` file:
   ```
   FEATURE_GATING_V2_ENABLED=true
   ```

2. Restart your application
3. All routes will now use the new feature gating system

### Rollback to Legacy System

If you need to rollback immediately:

1. Set the environment variable:
   ```bash
   export FEATURE_GATING_V2_ENABLED=false
   ```

2. Restart your application
3. All routes will revert to the legacy decorators

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Route         │    │ Feature         │    │ Feature         │
│   Decorator     │───▶│ Registry        │───▶│ Registry        │
│                 │    │ Service         │    │ (Config)        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                        ┌─────────────────┐
                        │ Usage Tracker   │
                        │ (Firestore)     │
                        └─────────────────┘
```

## Adding New Features

### 1. Define the Feature

Add to `config/feature_registry.py`:

```python
'new_feature': FeatureDefinition(
    feature_id='new_feature',
    name='New Feature',
    description='Description of the new feature',
    category=FeatureCategory.CORE,
    minimum_tier=MembershipTier.PREMIUM,
    tier_limits={
        MembershipTier.PREMIUM: [UsageLimit(LimitType.DAILY, 10)]
    }
)
```

### 2. Apply to Routes

```python
from services.feature_gating import feature_required

@app.route('/api/new-feature', methods=['POST'])
@feature_required('new_feature')
def new_feature_endpoint():
    return jsonify({'success': True})
```

### 3. Update Frontend

```html
<!-- Template -->
{{ feature_button('new_feature', 'Use New Feature') }}

<!-- JavaScript -->
<script>
if (FeatureGate.canAccess('new_feature')) {
    // Enable feature UI
}
</script>
```

## Available Decorators

### `@feature_required(feature_id, *, check_limits=True, model_param=None)`
Main decorator for feature access control.

```python
# Basic usage
@feature_required('chat_basic')
def chat_api():
    pass

# Without usage limits (for info endpoints)
@feature_required('chat_basic', check_limits=False)
def get_chat_models():
    pass

# With model validation
@feature_required('chat_basic', model_param='model')
def chat_with_model():
    pass
```

### `@tier_required(minimum_tier)`
Require minimum subscription tier.

```python
from config.feature_registry import MembershipTier

@tier_required(MembershipTier.PREMIUM)
def premium_only_feature():
    pass
```

### `@model_required(model_group)`
Enforce model access restrictions.

```python
@model_required('premium')
def use_premium_model():
    pass
```

## Template Macros

### Basic Usage

```html
{% from '_feature_macros.html' import 
    feature_button, 
    feature_section, 
    model_selector, 
    tier_badge 
%}

<!-- Feature-gated button -->
{{ feature_button('video_generation', 'Create Video', class='btn btn-primary') }}

<!-- Model selector (automatically filtered) -->
{{ model_selector(name='chat_model', id='model-select') }}

<!-- Tier indicator -->
<p>Your plan: {{ tier_badge() }}</p>

<!-- Feature section with fallback -->
{% call feature_section('premium_analytics') %}
    <div>Premium analytics content here</div>
{% endcall %}
```

### Advanced Usage

```html
<!-- Upgrade prompt card -->
{{ upgrade_prompt_card(
    'video_generation',
    'Video Generation',
    'Create AI-powered videos from text prompts',
    ['Unlimited video generation', 'HD quality', 'Custom durations']
) }}

<!-- Usage indicator -->
{{ usage_indicator('chat_basic') }}

<!-- Premium banner -->
{{ premium_banner() }}
```

## JavaScript API

### Basic Usage

```javascript
// Check feature access
if (FeatureGate.canAccess('video_generation')) {
    enableVideoUI();
}

// Get feature status with limits
const status = FeatureGate.getStatus('chat_basic');
console.log(`Usage: ${status.usage.current}/${status.usage.limit}`);

// Show upgrade prompt
FeatureGate.showUpgrade('premium_feature', 'Custom message');

// Get available models
const models = window.featureGatekeeper.getAvailableModels();
```

### Event Handling

```javascript
// Listen for subscription changes
document.addEventListener('subscription-updated', () => {
    FeatureGate.refresh();
});

// Manually refresh feature data
await FeatureGate.refresh();
```

## Monitoring and Logging

### Log Structure

The system logs structured events:

```json
{
  "level": "INFO",
  "message": "Feature access denied",
  "feature_id": "video_generation",
  "user_id": "user123",
  "reason": "This feature requires premium subscription",
  "route": "video.start_video_batch",
  "ip": "192.168.1.1",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Key Metrics to Monitor

1. **Feature Access Denials**: Track upgrade opportunities
2. **Limit Exceeded Events**: Monitor usage patterns
3. **Model Access Attempts**: Track premium model demand
4. **API Response Times**: Ensure gating doesn't slow requests

### Alerting Recommendations

```yaml
# Example alerting rules
- alert: HighFeatureAccessDenials
  expr: rate(feature_access_denied_total[5m]) > 10
  labels:
    severity: warning
  annotations:
    summary: High rate of feature access denials

- alert: FeatureGatingErrors
  expr: rate(feature_gating_errors_total[5m]) > 1
  labels:
    severity: critical
  annotations:
    summary: Feature gating system errors
```

## Testing

### Unit Tests

```python
from config.feature_registry import MembershipTier
from services.feature_registry_service import FeatureRegistryService

def test_feature_access():
    service = FeatureRegistryService()
    
    # Mock user as free tier
    with patch.object(service, 'get_user_tier', return_value=MembershipTier.FREE):
        can_access, reason = service.can_access_feature('video_generation')
        assert not can_access
        assert 'premium subscription' in reason
```

### Integration Tests

```python
def test_feature_gated_endpoint(client):
    # Test without authentication
    response = client.post('/api/video/generate')
    assert response.status_code == 401
    
    # Test with free user
    with client.session_transaction() as sess:
        sess['user_id'] = 'free_user'
    response = client.post('/api/video/generate')
    assert response.status_code == 403
    
    # Test with premium user
    with client.session_transaction() as sess:
        sess['user_id'] = 'premium_user'
    response = client.post('/api/video/generate')
    assert response.status_code == 200  # or appropriate success code
```

## Troubleshooting

### Common Issues

#### 1. Features Not Loading in Frontend
**Symptoms**: JavaScript errors, features not updating
**Solutions**:
- Check browser console for JavaScript errors
- Verify `/api/user/features` endpoint is accessible
- Ensure `feature_gating.js` is loaded before use

#### 2. Inconsistent Feature Access
**Symptoms**: Backend allows but frontend blocks (or vice versa)
**Solutions**:
- Verify `FEATURE_GATING_V2_ENABLED` is set consistently
- Check feature registry for typos in feature IDs
- Refresh browser cache

#### 3. Usage Limits Not Working
**Symptoms**: Users can exceed limits
**Solutions**:
- Check Firestore connectivity
- Verify StripeService usage tracking
- Look for `increment_usage` call placement

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger('services.feature_gating').setLevel(logging.DEBUG)
logging.getLogger('services.feature_registry_service').setLevel(logging.DEBUG)
```

### Manual Testing

```bash
# Test feature access API
curl -H "Cookie: session=..." http://localhost:8080/api/user/features

# Test feature-gated endpoint
curl -X POST -H "Cookie: session=..." http://localhost:8080/api/video/generate
```

## Performance Considerations

### Caching

- Feature access checks are cached in the user session
- JavaScript client caches for 5 minutes
- Consider Redis for high-traffic deployments

### Database Optimization

- Usage counters use Firestore increment operations
- Daily limits reset automatically by date-based keys
- Consider archiving old usage data

### Load Testing

Test feature gating overhead:

```bash
# Baseline (no gating)
ab -n 1000 -c 10 http://localhost:8080/api/health

# With feature gating
ab -n 1000 -c 10 -H "Cookie: session=..." http://localhost:8080/api/gated-endpoint
```

## Migration Checklist

### Pre-Deployment

- [ ] All features defined in registry
- [ ] Routes updated with conditional decorators
- [ ] Frontend assets deployed
- [ ] Monitoring configured
- [ ] Rollback plan tested

### Deployment

- [ ] Deploy with `FEATURE_GATING_V2_ENABLED=false`
- [ ] Verify legacy system works
- [ ] Enable new system: `FEATURE_GATING_V2_ENABLED=true`
- [ ] Monitor logs for errors
- [ ] Test key user flows

### Post-Deployment

- [ ] Monitor feature access metrics
- [ ] Validate usage limit enforcement
- [ ] Check frontend UI updates
- [ ] Collect user feedback
- [ ] Plan legacy system removal

## Future Enhancements

### Planned Features

1. **A/B Testing**: Feature flag variations for experiments
2. **Time-based Limits**: Hourly/weekly limits beyond daily
3. **Geographic Restrictions**: Region-based feature access
4. **Role-based Access**: Team/organization feature management
5. **Real-time Notifications**: WebSocket updates for limit changes

### Extension Points

```python
# Custom limit types
class CustomLimitType(Enum):
    CONCURRENT_SESSIONS = "concurrent_sessions"
    MONTHLY_CREDITS = "monthly_credits"

# Custom validators
def custom_feature_validator(user_id: str, feature_id: str) -> bool:
    # Custom validation logic
    return True
```

## Support

### Documentation

- Feature Registry: `config/feature_registry.py`
- Service Layer: `services/feature_registry_service.py` 
- Decorators: `services/feature_gating.py`
- Frontend: `static/js/feature_gating.js`
- Templates: `templates/_feature_macros.html`

### Getting Help

1. Check logs for error messages
2. Verify feature definitions in registry
3. Test with minimal reproduction case
4. Review this migration guide
5. Contact development team with specific error details

---

*Last updated: 2024-01-15*
*Version: 1.0.0*