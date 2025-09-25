# Phoenix AI Usage Policies

This document defines the usage limits and access policies for different membership tiers.

## Membership Tiers

### FREE Tier
**Target Audience**: Individual users, trial users, students
**Price**: $0/month

#### Daily Limits
- Chat messages: 5 per day
- Search queries: 10 per day  
- Document uploads: 2 per day
- News searches: 5 per day
- Dataset searches: 5 per day
- URL shortening: 10 URLs per day
- Video generation: 0 (premium only)
- AI summaries: 0 (premium only)

#### Model Access
- Basic models only: `gemini-1.0-pro`, `gpt-3.5-turbo`
- No access to premium models

#### Features
- Basic chat functionality
- Basic search capabilities
- URL shortening (limited)
- Read-only analytics

### PREMIUM Tier  
**Target Audience**: Power users, professionals, small businesses
**Price**: $5/month

#### Daily Limits
- Chat messages: Unlimited
- Search queries: Unlimited
- Document uploads: Unlimited  
- News searches: Unlimited
- Dataset searches: Unlimited
- URL shortening: Unlimited
- Video generation: 10 per day
- Dataset analysis: 5 per day
- AI summaries: Unlimited

#### Model Access
- All available models including:
  - `gpt-4o-mini`, `gpt-4`
  - `claude-3-opus`, `claude-3-sonnet`, `claude-3-haiku`
  - `gemini-1.5-pro`, `gemini-1.5-flash`
  - `grok-beta`

#### Features
- All free tier features
- Video generation
- AI-powered summaries  
- Advanced dataset analysis
- Code generation
- Premium model access
- Advanced analytics
- Priority support

### ENTERPRISE Tier (Future)
**Target Audience**: Large organizations, teams
**Price**: Custom pricing

#### Limits
- Custom limits based on contract
- Bulk usage allowances
- Team management features

## Rate Limiting Strategy

### Time Windows
- **Daily limits**: Reset at midnight UTC
- **Concurrent limits**: Maximum simultaneous requests per user
- **Burst limits**: Short-term allowances for brief spikes

### Reset Policies
- Daily counters reset at 00:00 UTC
- Monthly counters reset on subscription billing date
- Failed requests don't count toward limits
- Cached responses don't count toward limits

### Fallback Behavior
- **Model fallback**: Premium models gracefully degrade to free models when limits reached
- **Feature fallback**: Advanced features show upgrade prompts when unavailable
- **Soft limits**: Warnings at 80% usage, hard blocks at 100%

## Cost-Based Restrictions

### High-Cost Features (Premium Only)
1. **Video Generation**: Expensive GPU compute
2. **Premium AI Models**: Higher API costs (GPT-4, Claude Opus)
3. **Dataset Analysis**: Compute-intensive operations
4. **Bulk Operations**: Batch processing capabilities

### Resource Management
- Timeout limits for long-running operations
- Queue management for expensive operations
- Auto-scaling considerations for premium features

## Monitoring and Compliance

### Usage Tracking
- Real-time usage counters in Firestore
- Daily/monthly aggregation reports
- Feature-specific analytics

### Enforcement
- Pre-request limit checking
- Post-request usage increment
- Graceful degradation when limits exceeded
- Clear messaging about limit status

### Abuse Prevention
- IP-based rate limiting for unauthenticated endpoints
- Anomaly detection for unusual usage patterns
- Account suspension procedures for policy violations

## Policy Rationale

### Free Tier Justification
- Allows meaningful evaluation of platform capabilities
- Balances user acquisition with cost management
- Provides clear upgrade incentives

### Premium Tier Benefits
- Removes friction for productive users
- Unlocks high-value, cost-intensive features
- Provides sustainable revenue model

### Upgrade Triggers
- Hitting daily limits consistently
- Requesting premium model access
- Needing advanced analytics or bulk operations
- Requiring priority support

## Implementation Notes

### Configuration Management
- Limits stored in centralized feature registry
- Runtime configuration updates without deployment
- A/B testing capabilities for limit experiments

### User Experience
- Proactive limit notifications at 80% usage
- Clear upgrade paths when limits reached
- Grace periods for new premium subscribers

### Business Metrics
- Conversion tracking from free to premium
- Feature utilization analysis
- Cost per user calculations
- Churn analysis by usage patterns