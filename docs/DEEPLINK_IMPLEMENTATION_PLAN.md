# Implementation Plan: Deep Linking Feature

This document outlines the step-by-step plan for developing and deploying the Deep Linking feature.

## Phase 0: Prerequisites & Setup

1.  **GCP Project & Billing:**
    *   [ ] Ensure a GCP project is available and billing is enabled.
    *   [ ] Enable necessary APIs: Cloud Run, Cloud SQL, Secret Manager, Cloud Build.
2.  **Firebase Project Setup:**
    *   [ ] Confirm Firebase project is set up and integrated with the web app for authentication.
    *   [ ] Download Firebase Admin SDK service account credentials (JSON file).
3.  **Stripe Account Setup:**
    *   [ ] Set up a Stripe account.
    *   [ ] Create a new Product for the $5/month subscription.
    *   [ ] Create a Price for that Product.
    *   [ ] Obtain Stripe API Keys (Publishable Key, Secret Key).
    *   [ ] Obtain Webhook Signing Secret for endpoint verification.
4.  **SendGrid Account Setup:**
    *   [ ] Create a SendGrid account.
    *   [ ] Obtain a SendGrid API Key.
    *   [ ] Configure and verify a sender domain/email address.
5.  **IPinfo (or similar) Account Setup:**
    *   [ ] Sign up for an IPinfo account (or chosen alternative).
    *   [ ] Obtain an API Token.
6.  **Development Environment:**
    *   [ ] Ensure local development environment is set up for Flask development.
    *   [ ] Install PostgreSQL locally or configure access to a dev Cloud SQL instance.
    *   [ ] Set up a way to manage local environment variables (e.g., `.env` file with `python-dotenv`).

## Phase 1: Backend - Database & Core Logic

1.  **Project Structure & Dependencies:**
    *   [ ] Update `requirements.txt` with new packages:
        *   `SQLAlchemy`, `psycopg2-binary` (or `pg8000` for Cloud SQL Connector)
        *   `alembic` (for database migrations)
        *   `firebase-admin`
        *   `stripe`
        *   `sendgrid`
        *   `ipinfo` (or library for chosen IP geo service)
        *   `python-dateutil` (for parsing timestamps if needed)
        *   `user-agents` (for parsing User-Agent strings)
    *   [ ] Organize code into relevant blueprints/modules (e.g., `deeplink`, `auth`, `subscription`).
2.  **Database Setup (SQLAlchemy & Alembic):**
    *   [ ] Configure SQLAlchemy to connect to PostgreSQL (Cloud SQL).
    *   [ ] Define SQLAlchemy models for `UserSubscription`, `DeepLink`, `LinkClick` as per the System Design.
    *   [ ] Initialize Alembic for database migrations.
    *   [ ] Create initial migration script for the new tables and their schemas.
    *   [ ] Apply migrations to development and (later) production databases.
3.  **Authentication & Authorization Utilities:**
    *   [ ] Implement middleware or decorator to verify Firebase ID tokens from `Authorization` header.
    *   [ ] Create helper function `is_premium_user(firebase_uid)` that checks `UserSubscription` table for active status.
4.  **Core Deep Link Logic - Generation:**
    *   [ ] Implement `generate_short_code()`: ensures uniqueness and non-predictability.
    *   [ ] Develop logic to validate `original_url`.
5.  **Core Deep Link Logic - Redirection & Click Tracking:**
    *   [ ] Implement `GET /<short_code>` endpoint.
    *   [ ] Logic for looking up `short_code`.
    *   [ ] Logic for logging clicks to `link_clicks` (timestamp, IP, User-Agent, Referrer).
    *   [ ] Integrate IPinfo API call for geolocation enrichment (consider async or error handling for timeouts).
    *   [ ] Integrate User-Agent parsing library (e.g., `user-agents`) for device/OS/browser enrichment.
    *   [ ] Logic for incrementing `click_count` in `deeplinks`.
    *   [ ] HTTP 302 redirect.

## Phase 2: Backend - User Flows & External Integrations

1.  **Guest User Flow Implementation:**
    *   [ ] Implement `POST /deeplink/create` for guest users:
        *   Requires `guest_email`.
        *   Creates `DeepLink` with `max_clicks=10`.
    *   [ ] In `GET /<short_code>`, implement logic for `max_clicks` enforcement:
        *   Set `is_active=FALSE` on `DeepLink` when `click_count` reaches `max_clicks`.
        *   Trigger SendGrid email to `guest_email` with basic analytics summary.
    *   [ ] Create "Link Expired" page/response.
2.  **Stripe Integration - Subscription Management:**
    *   [ ] Implement `POST /webhook/stripe` endpoint:
        *   Verify Stripe webhook signature.
        *   Handle `checkout.session.completed`: Create/update `UserSubscription` entry, associate with `firebase_uid` (from Stripe metadata).
        *   Handle `customer.subscription.updated/deleted`, `invoice.payment_failed`: Update `UserSubscription.status`.
    *   [ ] Create a route (e.g., `GET /subscribe/checkout`) that creates a Stripe Checkout session for the $5/month plan and redirects the user to Stripe.
        *   Include `firebase_uid` in Stripe session metadata.
        *   Set `success_url` and `cancel_url`.
3.  **Premium User Flow - Link Creation:**
    *   [ ] Implement `POST /dashboard/deeplink/create` (for authenticated, premium users):
        *   Requires Firebase token and premium status check.
        *   Creates `DeepLink` associated with `firebase_uid`, `max_clicks=NULL`.
4.  **Premium User Flow - Analytics Data Retrieval:**
    *   [ ] Develop backend logic to query `DeepLink` and `LinkClick` tables to aggregate analytics data for a given premium user or specific link:
        *   Total clicks.
        *   Time-series data for charts.
        *   Geo distribution.
        *   Referrer and device/OS/browser breakdowns.
    *   [ ] Implement `GET /dashboard/deeplink/<deeplink_id>/analytics` API endpoint if client-side fetching is chosen for detailed views, otherwise prepare data in dashboard route.
5.  **Email Reporting (SendGrid):**
    *   [ ] Integrate SendGrid SDK/API for sending emails.
    *   [ ] Implement guest link expiration email (triggered from redirect logic).
    *   [ ] (Later/Optional for MVP) Implement periodic email reports for premium users (e.g., a scheduled task).

## Phase 3: Frontend Development (Jinja2 & Chart.js)

1.  **Public Deep Link Generator Page (`GET /` or `/deeplink-generator`):**
    *   [ ] Create Jinja2 template with form for `original_url` and `guest_email`.
    *   [ ] Display notice about 10-click limit for guest links.
    *   [ ] Display generated short link and "copy" button upon successful submission.
    *   [ ] "Upgrade to Premium" / "Login" prompts.
2.  **User Authentication Profile Update:**
    *   [ ] Remove the Firebase user ID hash display from the existing profile page (`templates/profile.html`).
    *   [ ] Add a tile/link on the profile page for authenticated users to navigate to the "Deep Link Dashboard" (if premium) or "Deep Link Generator" (if not).
3.  **Premium Deep Link Dashboard (`GET /dashboard/deeplinks`):**
    *   [ ] Create Jinja2 template for the dashboard.
    *   [ ] Protected route: requires login and active premium subscription. Redirect/show upgrade prompt if not premium.
    *   [ ] Display a table of the user's `DeepLink` records (short link, original, created date, total clicks).
    *   [ ] Include a form for creating new deep links from the dashboard.
    *   [ ] Integrate Chart.js for visualizing analytics:
        *   Pass aggregated analytics data from Flask backend to the template.
        *   Write JavaScript to initialize Chart.js with the data (e.g., click trends over time).
        *   Implement UI for viewing detailed analytics per link (e.g., on click, show more charts/data).
4.  **Subscription UI:**
    *   [ ] Create UI elements (e.g., "Upgrade to Premium" buttons) that link to the Stripe Checkout route (`GET /subscribe/checkout`).
    *   [ ] Display messages related to subscription status (e.g., on profile or dashboard).
5.  **User Messages & Error Pages:**
    *   [ ] Create templates for:
        *   Link expiration page.
        *   Invalid short code / 404 page.
        *   General error messages (e.g., failed link creation).
        *   Success messages (e.g., "Link created successfully!").

## Phase 4: Testing

1.  **Unit Tests:**
    *   [ ] Write unit tests for core utility functions (e.g., `generate_short_code`, URL validation, User-Agent parsing).
    *   [ ] Test individual Flask route handlers with mock dependencies (database, external APIs).
2.  **Integration Tests:**
    *   [ ] Test interactions between components (e.g., link creation updates database correctly).
    *   [ ] Test Firebase token verification.
    *   [ ] Test Stripe webhook handling logic (can use Stripe CLI to send mock events).
    *   [ ] Test SendGrid email sending (with a test account or mocked API).
3.  **End-to-End (E2E) Testing:**
    *   **Guest User Flow:**
        *   [ ] Create link as guest.
        *   [ ] Click link < 10 times, verify redirect and click logging.
        *   [ ] Click link >= 10 times, verify expiration and email report.
    *   **Premium User Flow:**
        *   [ ] Sign up / Log in.
        *   [ ] Subscribe via Stripe (test mode).
        *   [ ] Access dashboard, create links.
        *   [ ] Verify links work without 10-click limit.
        *   [ ] Verify analytics display correctly on dashboard.
        *   [ ] Test subscription cancellation flow and access revocation.
    *   **Edge Cases:**
        *   [ ] Invalid URL input.
        *   [ ] Non-existent short codes.
        *   [ ] Concurrent clicks (if feasible to test).
4.  **Security Testing:**
    *   [ ] Check for XSS vulnerabilities (especially with `original_url`).
    *   [ ] Ensure users cannot access/modify other users' data.
    *   [ ] Verify CSRF protection on forms if applicable.

## Phase 5: Deployment & Post-Launch

1.  **Environment Configuration:**
    *   [ ] Set up all necessary environment variables in Cloud Run (API keys, database connection strings, Firebase creds path). Use Secret Manager for sensitive values.
2.  **Dockerfile & Cloud Run Configuration:**
    *   [ ] Ensure Dockerfile is updated with new dependencies and correctly builds the Flask app.
    *   [ ] Configure Cloud Run service settings (memory, CPU, concurrency, connection to Cloud SQL via Proxy/Connector).
3.  **CI/CD Pipeline:**
    *   [ ] Update GitHub Actions (or other CI/CD tool) to:
        *   Build Docker image.
        *   Push to Google Container Registry (GCR) or Artifact Registry.
        *   Deploy to Cloud Run (staging first, then production).
        *   Handle database migrations as part of deployment (carefully).
4.  **Database Migration (Production):**
    *   [ ] Schedule and perform database schema migration on the production Cloud SQL instance.
5.  **Production Deployment:**
    *   [ ] Deploy the new version to production.
    *   [ ] Monitor logs and system health closely post-deployment.
6.  **Documentation:**
    *   [ ] Update project `README.md` with information about the new feature.
    *   [ ] Create user-facing help guides or FAQs for the deep linking feature.
7.  **Data Retention Job:**
    *   [ ] Implement and schedule a periodic job (e.g., Cloud Scheduler + Cloud Function/Cloud Run job) to clean up guest `deeplinks` and `link_clicks` data older than 1 year.
8.  **Monitoring & Alerting:**
    *   [ ] Set up monitoring dashboards in GCP for Cloud Run, Cloud SQL, and API traffic.
    *   [ ] Configure alerts for high error rates, latency spikes, or resource exhaustion.

## Phase 6: Future Iterations (Roadmap from PRD)

*   [ ] Plan and prioritize features from the "Future Roadmap" section of the PRD.
*   [ ] Gather user feedback and iterate on existing features.
*   [ ] Formalize a staging environment setup if not done initially.