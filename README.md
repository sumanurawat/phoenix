# Friedmomo - Where Prompts Become Creation

**🌐 Live at: [friedmomo.com](https://friedmomo.com)**

## The Future of Work is Already Here

In a world where AI transforms ideas into reality in seconds, **prompts are the new currency of creativity**. Friedmomo is your gateway to this future—a social platform where anyone can become a creator with just their imagination.

### Why Friedmomo?

**The prompt revolution is happening now.** While others are still figuring out how to use AI, Friedmomo users are already:
- 🎨 **Creating stunning images** powered by Google's Imagen 3 (1 token)
- 🎬 **Generating professional videos** with Veo 3.1 AI (50 tokens)
- 🌍 **Sharing their creations** with a vibrant community
- 💬 **Engaging with fellow creators** through likes and comments
- ⚡ **Iterating rapidly** with an affordable token-based economy

**This is your chance to join the party early.** Before AI-generated content becomes mainstream, before everyone is doing it—stake your claim as a pioneer in the prompt-driven creator economy.

## What Makes Friedmomo Different?

### 1. **Democratized AI Access**
No expensive subscriptions. No complex APIs. Just buy tokens and create:
- **$10 = 1,000 tokens** = 1,000 images OR 22 videos
- **Free tier: 100 tokens** to start experimenting immediately
- Pay only for what you use

### 2. **Social-First Platform**
Your creations deserve an audience:
- Public gallery showcasing the best AI-generated content
- Like, comment, and discover trending creations
- User profiles to build your creator brand
- Community-driven inspiration

### 3. **Production-Quality Results**
Powered by Google's cutting-edge AI:
- **Imagen 3**: State-of-the-art image generation
- **Veo 3.1**: Professional-grade video synthesis
- Instant image results, videos in 2-5 minutes
- Direct integration with Google's latest models

### 4. **Built for Speed**
- **Cloud Run Jobs** architecture for scalable, async generation
- Real-time progress tracking
- Cloudflare R2 storage for lightning-fast delivery
- Single-instance sessions (no auto-scaling issues)

## The Prompt Economy is Here

**Why wait?** Every day you delay is a day someone else is building their portfolio, refining their prompting skills, and establishing themselves in the AI creator space.

- **Content creators**: Generate unique visuals for your brand
- **Marketers**: Test hundreds of concepts in minutes
- **Artists**: Explore new creative directions
- **Entrepreneurs**: Build visual assets without hiring designers
- **Hobbyists**: Turn your wildest ideas into reality

**The barrier to entry has never been lower. The opportunity has never been bigger.**

## How It Works

1. **Sign up** with Google OAuth (30 seconds)
2. **Get 100 free tokens** to start creating immediately
3. **Enter a prompt** for an image or video
4. **Watch the magic happen** as AI brings your vision to life
5. **Share publicly** and engage with the community

## Technology Stack

**Modern, scalable, production-ready:**

- **Backend**: Flask (Python) with service-oriented architecture
- **AI Models**: Google Imagen 3 (images), Veo 3.1 (videos)
- **Database**: Firebase Firestore for real-time data
- **Authentication**: Firebase Auth with Google OAuth
- **Storage**: Cloudflare R2 for media delivery
- **Infrastructure**: Google Cloud Run + Cloud Run Jobs
- **Frontend**: React SPA deployed at friedmomo.com
- **Payments**: Stripe integration for token purchases

## 🚀 Local Development

### Quick Start
```bash
./start_local.sh
```

This script automatically:
- ✅ Sets up Python virtual environment
- ✅ Installs dependencies
- ✅ Starts Flask backend on port 8080
- ✅ Serves the complete API

**Access Backend**: http://localhost:8080

### Frontend Development
The React frontend is located in `frontend/soho/` and deploys separately to friedmomo.com.

**Documentation**: See [SOHO_ARCHITECTURE.md](SOHO_ARCHITECTURE.md) for detailed architecture

## Core Features

### 🎨 Image Generation (1 token)
- Powered by Google Imagen 3
- Instant results
- High-quality, prompt-accurate images
- Perfect for rapid ideation

### 🎬 Video Generation (50 tokens)
- Powered by Google Veo 3.1
- 2-5 minute processing time
- Professional-grade output
- Real-time progress tracking

### 💰 Token Economy
- **Free tier**: 100 tokens on signup
- **Affordable pricing**: $10 = 1,000 tokens
- Pay-as-you-go model
- Stripe payment integration

### 🌍 Social Platform
- Public gallery of creations
- Like and comment system
- User profiles and portfolios
- Discover trending content
- Build your creator reputation

### 🔐 Authentication
- Google OAuth integration
- Secure session management
- User-specific content tracking

## Prerequisites for Development

- Python 3.8+
- Google Cloud SDK (for deployment)
- Firebase project with Admin SDK credentials
- Environment variables configured (see `.env.example`)

### Firebase Setup

1. **Service Account Credentials:**
   - Download Firebase service account JSON from Firebase Console
   - Save as `firebase-credentials.json` (excluded from git)
   
2. **Environment Variables:**
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="./firebase-credentials.json"
   ```

3. **Required API Keys:**
   - `GEMINI_API_KEY` - Google Gemini for AI features
   - `FIREBASE_API_KEY` - Firebase authentication
   - `STRIPE_SECRET_KEY` - Payment processing
   - See `.env.example` for complete list

### Installation
1. Clone the repository
2. Create virtual environment: `python -m venv venv`
3. Activate: `source venv/bin/activate` (macOS/Linux)
4. Install dependencies: `pip install -r requirements.txt`
5. Configure environment variables
6. Run: `./start_local.sh`

## Join the Prompt Revolution

**🚀 Start creating now: [friedmomo.com](https://friedmomo.com)**

The future belongs to those who master the art of prompting. Every great creator started somewhere—why not start here, today?

- **100 free tokens** to experiment
- **No credit card required** to start
- **Join a growing community** of AI creators
- **Build your portfolio** before the masses arrive

## Architecture Highlights

- **Cloud Run Jobs**: Scalable async processing for video generation
- **Firestore**: Real-time database for creations, users, and social features
- **R2 Storage**: Fast, cost-effective media delivery
- **Single-instance sessions**: Optimized for Cloud Run free tier
- **Service-oriented design**: Clean separation of concerns
- **Blueprint-based routing**: Modular Flask architecture

**Read More**: 
- [SOHO_ARCHITECTURE.md](SOHO_ARCHITECTURE.md) - System design
- [IMAGE_VS_VIDEO_EXPLAINED.md](IMAGE_VS_VIDEO_EXPLAINED.md) - Feature comparison
- [TOKEN_ECONOMY_QUICK_REFERENCE.md](TOKEN_ECONOMY_QUICK_REFERENCE.md) - Pricing details

## Contributing

This is a production application serving real users. For significant changes, please open an issue first to discuss the proposed modifications.

## About

**Friedmomo** - Empowering creativity through AI-generated content.

Created by [Sumanu Rawat](https://github.com/sumanurawat) | Connect on [LinkedIn](https://www.linkedin.com/in/sumanurawat/)

---

*"The best time to start creating with AI was yesterday. The second best time is now."*