# Phoenix AI Feature Inventory

This document maps all features, API routes, and UI elements to unique feature IDs for the centralized feature gating system.

## Feature Categories

### Chat & Conversations
| Feature ID | Description | Current Protection | Desired Tier | Routes |
|------------|-------------|-------------------|--------------|---------|
| `chat_basic` | Basic chat messages | `@login_required` | FREE (limited) | `/api/chat/message` |
| `chat_document_upload` | Document upload for chat context | `@login_required` | FREE (limited) | `/api/chat/upload-document` |
| `chat_enhanced` | Enhanced chat with conversation management | `@login_required` | FREE (limited) | `/api/conversations/*` |
| `chat_model_selection` | Access to different AI models | None | PREMIUM | `/api/chat/models` |
| `chat_premium_models` | Access to premium models (GPT-4, Claude) | None | PREMIUM | Model selection in chat |

### Search & Doogle
| Feature ID | Description | Current Protection | Desired Tier | Routes |
|------------|-------------|-------------------|--------------|---------|
| `search_basic` | Basic web/news search | None | FREE (limited) | `/api/search/` |
| `search_ai_summary` | AI-powered search summaries | `@csrf_protect` only | PREMIUM | `/api/search/summary` |

### Video Generation
| Feature ID | Description | Current Protection | Desired Tier | Routes |
|------------|-------------|-------------------|--------------|---------|
| `video_generation` | Video generation from prompts | `@login_required` only | PREMIUM | `/api/video/generate` |
| `video_batch_jobs` | Batch video processing | `@login_required` only | PREMIUM | `/api/video/job/*` |

### News & Robin
| Feature ID | Description | Current Protection | Desired Tier | Routes |
|------------|-------------|-------------------|--------------|---------|
| `news_search` | News article search | `@csrf_protect` only | FREE (limited) | `/api/robin/search` |
| `news_content_extraction` | Full article content crawling | `@csrf_protect` only | PREMIUM | `/api/robin/article_content` |
| `news_ai_summary` | AI-powered news summarization | `@csrf_protect` only | PREMIUM | `/api/robin/generate_summary` |

### Dataset Discovery
| Feature ID | Description | Current Protection | Desired Tier | Routes |
|------------|-------------|-------------------|--------------|---------|
| `dataset_search` | Kaggle dataset search | None | FREE (limited) | `/api/dataset/search` |
| `dataset_download` | Dataset download capability | `@csrf_protect` only | PREMIUM | `/api/dataset/download` |
| `dataset_analysis` | AI-powered dataset analysis | `@csrf_protect` only | PREMIUM | `/api/dataset/analyze` |
| `dataset_code_generation` | Code generation for datasets | `@csrf_protect` only | PREMIUM | `/api/dataset/generate-code` |

### URL Shortener & Analytics
| Feature ID | Description | Current Protection | Desired Tier | Routes |
|------------|-------------|-------------------|--------------|---------|
| `url_shortening` | Create short URLs | `@login_required` | FREE (limited) | `/profile/links` |
| `url_analytics` | View link analytics | `@login_required` | PREMIUM | `/profile/links/<code>/analytics` |
| `url_advanced_analytics` | Advanced analytics features | None | PREMIUM | Analytics dashboard |

## Usage Limits by Tier

### Free Tier Limits
- `chat_basic`: 5 messages/day
- `chat_document_upload`: 2 documents/day  
- `chat_enhanced`: 3 conversations/day
- `search_basic`: 10 searches/day
- `news_search`: 5 searches/day
- `dataset_search`: 5 searches/day
- `url_shortening`: 10 URLs/day

### Premium Tier Limits
- Most features: Unlimited or high limits
- `video_generation`: 10 videos/day
- `dataset_analysis`: 5 analyses/day

## Model Access by Tier

### Free Tier Models
- `gemini-1.0-pro`
- `gpt-3.5-turbo`

### Premium Tier Models  
- All free tier models plus:
- `gpt-4o-mini`
- `gpt-4`
- `claude-3-opus`
- `claude-3-sonnet`
- `claude-3-haiku`
- `gemini-1.5-pro`
- `gemini-1.5-flash`
- `grok-beta`

## Missing Protection Analysis

### Routes without proper feature gating:
1. **Video routes** - Only `@login_required`, no usage limits
2. **Robin routes** - Only `@csrf_protect`, no subscription checks
3. **Dataset routes** - Missing authentication on most endpoints
4. **Search summary** - Missing usage limits and tier checks
5. **Model selection** - No tier-based model restrictions

### Priority Migration Order:
1. Video generation (high cost)
2. AI summarization features (resource intensive)
3. Dataset analysis (compute heavy)
4. Advanced analytics (premium feature)
5. Model access control (cost management)