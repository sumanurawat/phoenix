# Implementation Plan: URL Shortener / Deep Linking Feature (Firestore Based)

This document outlines the step-by-step plan for the Firestore-based URL Shortening feature.
Items marked [x] are considered implemented by the recent updates.
Items marked [F] are considered Future, or out of scope for the current Firestore-based MVP.

## Phase 0: Prerequisites & Setup

1.  **GCP Project & Billing:**
    *   [x] Ensure a GCP project is available and billing is enabled.
    *   [x] Enable necessary APIs: Cloud Run, Secret Manager, Cloud Build, Firestore.
2.  **Firebase Project Setup:**
    *   [x] Confirm Firebase project is set up and integrated with the web app for authentication.
    *   [x] Download Firebase Admin SDK service account credentials (JSON file) and configure `GOOGLE_APPLICATION_CREDENTIALS`.
3.  **[F] Stripe Account Setup:** (Future - For premium subscriptions)
    *   [ ] Set up a Stripe account.
    *   [ ] Create a new Product for subscription.
    *   [ ] Obtain Stripe API Keys and Webhook Signing Secret.
4.  **[F] SendGrid Account Setup:** (Future - For email reports)
    *   [ ] Create a SendGrid account and obtain API Key.
    *   [ ] Configure sender domain/email.
5.  **[F] IPinfo (or similar) Account Setup:** (Future - For detailed analytics)
    *   [ ] Sign up and obtain an API Token.
6.  **Development Environment:**
    *   [x] Ensure local development environment is set up for Flask development.
    *   [x] Set up a way to manage local environment variables (e.g., `.env` file with `python-dotenv`).

## Phase 1: Backend - Database & Core Logic

1.  **Project Structure & Dependencies:**
    *   [x] Update `requirements.txt` with necessary packages:
        *   `firebase-admin` (for Firestore interaction)
        *   (Other existing dependencies like Flask, etc., remain)
    *   [x] Organize code into relevant blueprints/modules (e.g., `deeplink_bp`, `auth_bp`).
2.  **Database Setup (Firestore):**
    *   [x] Firestore is used as the database. No traditional migrations (like Alembic) are needed.
    *   [x] **Collection:** `shortened_links`
    *   [x] **Document ID:** `short_code` (e.g., 6-character unique string)
    *   [x] **Document Structure:**
        *   `original_url`: String (the URL to redirect to)
        *   `user_id`: String (Firebase UID of the creator)
        *   `user_email`: String (Email of the creator)
        *   `created_at`: Timestamp (Server timestamp from Firestore)
        *   `click_count`: Number (Initialized to 0, atomically incremented)
3.  **Authentication & Authorization Utilities:**
    *   [x] Implemented `login_required` decorator for Flask routes, which checks for `user_id` in `session`.
    *   [F] `is_premium_user` helper function (Future - when subscription tiers are added).
4.  **Core URL Shortener Logic - Generation:**
    *   [x] Implement `generate_short_code()`: ensures uniqueness against Firestore `shortened_links` collection and is non-predictable (uses `uuid.uuid4().hex[:6]`).
    *   [x] Basic validation for `original_url` (must start with `http://` or `https://`).
5.  **Core URL Shortener Logic - Redirection & Click Tracking:**
    *   [x] Implement `GET /apps/deeplink/r/<short_code>` endpoint.
    *   [x] Logic for looking up `short_code` in Firestore's `shortened_links` collection.
    *   [x] Logic for atomically incrementing `click_count` in the Firestore document.
    *   [F] Detailed click logging (IP, User-Agent, Referrer) to a separate collection (Future - for advanced analytics).
    *   [F] Integrate IPinfo API call for geolocation enrichment (Future).
    *   [F] Integrate User-Agent parsing for device/OS/browser enrichment (Future).
    *   [x] HTTP 302 redirect to `original_url`.

## Phase 2: Backend - User Flows & External Integrations

1.  **[F] Guest User Flow Implementation:** (Future)
    *   [ ] Implement `POST /deeplink/create_guest` (or similar) for guest users if desired.
        *   May require `guest_email`.
        *   May create `DeepLink` with `max_clicks` (e.g., 10 or 25).
    *   [ ] Logic for `max_clicks` enforcement in redirection logic.
    *   [ ] Trigger email (via SendGrid) to `guest_email` with basic analytics upon expiration (Future).
    *   [ ] Create "Link Expired" page/response (Future).
2.  **[F] Stripe Integration - Subscription Management:** (Future)
    *   [ ] Implement webhook for Stripe events (`checkout.session.completed`, etc.).
    *   [ ] Create route for Stripe Checkout session.
3.  **Authenticated User Flow - Link Creation:**
    *   [x] Implement `POST /apps/deeplink/profile/converter` for authenticated users.
        *   Requires login (uses `user_id` and `user_email` from session).
        *   Creates document in `shortened_links` collection. `click_count` defaults to 0. No `max_clicks` (effectively unlimited for authenticated users for now).
4.  **Authenticated User Flow - Link Management & Basic Analytics:**
    *   [x] `GET /apps/deeplink/profile/my-links` page displays a table of user's created links.
    *   [x] Data fetched from `shortened_links` collection, filtered by `user_id`, ordered by `created_at`.
    *   [x] Displays `original_url`, `short_url_display` (full short URL), `created_at_display`, and `click_count`.
    *   [F] Time-series data for charts (Future).
    *   [F] Geo distribution, Referrer, device/OS/browser breakdowns (Future).
5.  **[F] Email Reporting (SendGrid):** (Future)
    *   [ ] Implement guest link expiration email (if guest flow is added).
    *   [ ] Periodic email reports for authenticated users (Future).

## Phase 3: Frontend Development

1.  **[F] Public URL Shortener Page:** (Future - for guest users)
    *   [ ] Create Jinja2 template with form for `original_url` (and `guest_email` if applicable).
    *   [ ] Display generated short link.
2.  **User Profile Page (`templates/profile.html`):**
    *   [x] Updated to include:
        *   Link to "My Shortened Links" (`/apps/deeplink/profile/my-links`).
        *   Link to "Create New Short Link" (`/apps/deeplink/profile/converter`).
3.  **Authenticated User - "My Links" Page (`GET /apps/deeplink/profile/my-links`):**
    *   [x] Created Jinja2 template (`my_links.html`).
    *   [x] Protected route: requires login.
    *   [x] Displays a table of the user's links with `original_url`, `short_url_display`, `created_at_display`, `click_count`.
    *   [x] "Copy to clipboard" button for each short URL.
    *   [F] Integrate Chart.js for visualizing analytics (Future).
4.  **Authenticated User - "Create New Short Link" Page (`GET & POST /apps/deeplink/profile/converter`):**
    *   [x] Created Jinja2 template (`user_deeplink_converter.html`).
    *   [x] Form for `original_url`.
    *   [x] Displays generated short link and "copy" button upon successful submission.
    *   [x] Shows error/success messages.
5.  **[F] Subscription UI:** (Future)
    *   [ ] UI elements for "Upgrade to Premium" linking to Stripe Checkout.
6.  **User Messages & Error Pages:**
    *   [x] Implemented basic error messages on forms.
    *   [x] 404 page for invalid short codes.
    *   [x] Success messages on link creation.

## Phase 4: Testing

1.  **Unit Tests:**
    *   [x] Basic tests for utility functions (e.g., `generate_short_code`, URL validation). (Assuming some level of testing was done for service functions).
    *   [x] Test individual Flask route handlers with mock dependencies (Firestore).
2.  **Integration Tests:**
    *   [x] Test interactions: link creation updates Firestore correctly, redirection increments count.
    *   [x] Test `login_required` decorator.
    *   [F] Test Stripe webhook handling (Future).
    *   [F] Test SendGrid email sending (Future).
3.  **End-to-End (E2E) Testing:**
    *   **[F] Guest User Flow:** (Future)
    *   **Authenticated User Flow:**
        *   [x] Sign up / Log in.
        *   [x] Access "Create New Short Link" page, create links.
        *   [x] Verify links redirect correctly and `click_count` increments.
        *   [x] Access "My Links" page, verify links are listed with correct data.
        *   [x] Test "Copy to clipboard" functionality.
    *   **Edge Cases:**
        *   [x] Invalid URL input during creation.
        *   [x] Accessing non-existent short codes (`/r/<short_code>`).
        *   [F] Concurrent clicks (Future, if high-concurrency is expected).
4.  **Security Testing:**
    *   [x] Basic check for XSS vulnerabilities (ensure `original_url` is properly handled in templates if displayed as link text, but primarily it's an input).
    *   [x] Ensure users can only see their own links on the "My Links" page (due to Firestore query using `user_id`).
    *   [x] Standard Flask CSRF protection should be enabled if not already for forms.

## Phase 5: Deployment & Post-Launch

1.  **Environment Configuration:**
    *   [x] Set up `GOOGLE_APPLICATION_CREDENTIALS` environment variable in Cloud Run for Firebase Admin SDK.
    *   [x] Other necessary environment variables (Flask config, etc.).
2.  **Dockerfile & Cloud Run Configuration:**
    *   [x] Ensure Dockerfile includes `firebase-admin` and other current dependencies.
    *   [x] Configure Cloud Run service settings.
3.  **CI/CD Pipeline:**
    *   [x] Update GitHub Actions (or other CI/CD tool) for build and deployment to Cloud Run.
    *   [ ] No explicit database migration step like Alembic; Firestore schema is managed by application logic.
4.  **Production Deployment:**
    *   [x] Deploy the new version to production.
    *   [x] Monitor logs and system health (GCP Cloud Logging, Monitoring).
5.  **Documentation:**
    *   [x] Update project `README.md` with information about the URL Shortener feature.
    *   [F] Create detailed user-facing help guides or FAQs (Future).
6.  **[F] Data Retention Job:** (Future)
    *   [ ] Consider if data retention/cleanup policies are needed for `shortened_links` collection.
7.  **Monitoring & Alerting:**
    *   [x] Utilize GCP monitoring for Cloud Run and Firestore (error rates, latency, instance counts).
    *   [x] Configure alerts for critical issues.

## Phase 6: Future Iterations (Roadmap from PRD & This Plan)

*   [ ] **Guest User Access:** Limited free tier for creating short links.
*   [ ] **Detailed Analytics:** Geo-location, referrer tracking, device information, time-series charts.
*   [ ] **Premium Subscriptions (Stripe Integration):** For unlocking advanced features or higher limits.
*   [ ] **Custom Short Codes:** Allow users to suggest their own short codes.
*   [ ] **Email Reporting (SendGrid Integration):** For guest link expiration or user analytics summaries.
*   [ ] **API for Link Creation/Management:** For programmatic access.
*   [ ] **QR Code Generation:** For generated short links.
*   [ ] **Advanced Link Editing:** Ability to change original URL for a short code.
*   [ ] Formalize a staging environment setup if not done initially.
*   Gather user feedback and iterate on existing features.
