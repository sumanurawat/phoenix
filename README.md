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
A robust URL shortening service that allows authenticated users to create, manage, and track short links. This feature is ideal for sharing cleaner URLs and gaining insights into link performance.
- **Technology**: Utilizes Firebase Firestore for scalable and reliable data persistence of shortened links and their click counts.
- **Usage**:
    - **Create Links**: Authenticated users can generate new short links via the `/apps/deeplink/profile/converter` page.
    - **Manage Links**: View and manage all created short links, including their click counts, on the `/apps/deeplink/profile/my-links` page.
    - **Redirection**: Short links follow the format `yourdomain.com/apps/deeplink/r/<short_code>` and redirect to the original URL, incrementing a click counter.
- **Authentication**: This feature requires users to be logged in.

## Technology Stack

- Backend: Flask (Python)
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