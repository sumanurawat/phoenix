# Phoenix - AI Platform

A collection of intelligent AI-powered tools showcasing modern approaches to natural language processing, search, and news aggregation.

## Explore the Platform

Visit the live application at: https://phoenix-234619602247.us-central1.run.app

## Featured Projects

### Derplexity
An advanced conversational AI interface powered by Google's Gemini. Derplexity provides natural and intuitive dialogues, allowing users to interact with cutting-edge language models through a clean, user-friendly interface. Perfect for brainstorming, research assistance, or simply engaging in thought-provoking conversations.

### Doogle
An intelligent search engine that leverages AI to deliver precise, contextually relevant results. Unlike traditional search engines that rely solely on keyword matching, Doogle understands the semantic meaning behind your queries, providing more accurate and useful results for complex questions and research needs.

### Robin
A smart news aggregator that curates personalized real-time updates on topics that matter to you. Robin scans thousands of news sources to deliver the most relevant and timely information, all presented in a clean, distraction-free interface. Stay informed without the noise.

### URL Shortener / Deep Linking
A robust URL shortening service that allows authenticated users to create, manage, and track short links for any URL.

**Current Implementation Status:**
- ✅ **Authentication Required**: All users must log in to create/manage links
- ✅ **Universal URL Support**: Supports any valid HTTP/HTTPS URL (not just YouTube)
- ✅ **Link Management Dashboard**: View, copy, and delete your links at `/apps/deeplink/profile/links`
- ✅ **Click Tracking**: Real-time click counting for all short links
- ✅ **Firestore Storage**: Scalable data persistence
- ✅ **Mobile-Friendly**: Responsive design for all devices

**Technology**: 
- Backend: Flask with Firebase Firestore
- Frontend: Bootstrap 5 with responsive design
- Authentication: Firebase Authentication integration

**Usage**:
- **Access**: Click "URL Shortener" on homepage → Login/Signup → Create & manage links
- **Create Links**: Enter any URL in the dashboard to generate a short link
- **Manage Links**: View all your links with click counts and creation dates
- **Share**: Copy short links in format `yourdomain.com/apps/deeplink/r/<short_code>`

**User Flow**:
1. User clicks "URL Shortener" on homepage
2. If not logged in → redirected to login/signup
3. After authentication → redirected to link management dashboard
4. Create, view, and manage all short links in one place

## Technology Stack

- Backend: Flask (Python)
- AI Models: Google Gemini (latest models), Claude, Grok
- Database: Firebase Firestore
- Authentication: Firebase Auth
- Frontend: Bootstrap 5, React (Reel Maker)
- Deployment: Google Cloud Run

## 🚀 Quick Start - Local Development

### Single Command (Builds Everything)
```bash
./start_local.sh
```

This script automatically:
- ✅ Builds React frontend (Reel Maker feature)
- ✅ Starts Flask backend on port 8080
- ✅ Serves complete application

**Access**: http://localhost:8080

### Development Mode (Hot Reload)
```bash
./start_dev_mode.sh
```

For active frontend development with instant React updates.

**Documentation**: See [RUNNING_THE_APP.md](RUNNING_THE_APP.md) for detailed startup options.

## 🎬 Reel Maker Feature

Create AI-powered video reels using Google's Veo. Features include:
- Project-based video management
- JSON prompt editing for scenes
- Real-time generation progress
- GCS-backed video storage

**Setup**: [REEL_MAKER_SETUP.md](REEL_MAKER_SETUP.md)  
**Quick Reference**: [REEL_MAKER_QUICK_REFERENCE.md](REEL_MAKER_QUICK_REFERENCE.md)  
**Access**: http://localhost:8080/reel-maker
- Frontend: HTML5, CSS3, JavaScript
- AI Integration: Google Gemini, custom NLP models
- Database: Firebase Firestore (for features like URL Shortener)
- Deployment: Google Cloud Run

## Setup and Local Development

### Prerequisites
- Python 3.8+
- Google Cloud SDK (for some deployment tasks)
- Access to a Firebase project

### Firebase Setup

This project uses Firebase Firestore for data storage for features like the URL Shortener, and Firebase Authentication.

1.  **Service Account Credentials:**
    *   Download your Firebase service account JSON key file from the Firebase console (Project settings -> Service accounts -> Generate new private key).
    *   Save this file securely in a location not accessible by your web server directly, e.g., outside your project directory or in a secure credentials folder. **Do not commit it to your repository.**
2.  **Environment Variable:**
    *   Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to the absolute path of this JSON key file.
      For Linux/macOS:
      ```bash
      export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/serviceAccountKey.json"
      ```
      For Windows (PowerShell):
      ```powershell
      $env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\your\serviceAccountKey.json"
      ```
    *   The application (specifically the `firebase-admin` SDK) uses this environment variable to authenticate with Firebase services.
    *   For local development, you can set this in your shell, or use a `.env` file with `python-dotenv` (ensure `.env` is in `.gitignore`).
    *   For deployment (e.g., on Cloud Run), you will need to configure this environment variable in your service's settings. Refer to your hosting provider's documentation for setting environment variables.

### General Local Setup
1. Clone the repository.
2. Create a virtual environment: `python -m venv venv`
3. Activate it: `source venv/bin/activate` (Linux/macOS) or `venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Set necessary environment variables (like `GOOGLE_APPLICATION_CREDENTIALS`, Flask specific variables if any).
6. Run the application: `flask run` or `gunicorn app:app` (for production-like environment).

## About the Developer

Created by [Sumanu Rawat](https://github.com/sumanurawat). Connect on [LinkedIn](https://www.linkedin.com/in/sumanurawat/).