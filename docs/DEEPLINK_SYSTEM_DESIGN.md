# System Design Document: Deep Linking Feature

## 1. Architectural Overview

**Note: This document originally described a planned PostgreSQL + Stripe architecture. The current implementation uses Firebase Firestore with authentication-required access. See Section 1.1 for current implementation details.**

The Deep Linking feature will be integrated into the existing Phoenix Flask web application, hosted on Google Cloud Run. It leverages Firebase for authentication and Google Cloud SQL (PostgreSQL) for persistent storage. Stripe handles subscriptions, SendGrid manages email delivery, and IPinfo (or a similar service) enriches click data with geolocation. Chart.js will be used for client-side rendering of analytics visualizations.

## 1.1 Current Implementation Architecture (Updated June 2025)

**Current Tech Stack:**
- **Flask Web Application**: Deployed on Google Cloud Run
- **Firebase Firestore**: Primary database for link storage (not PostgreSQL)
- **Firebase Authentication**: User authentication (email/password + Google OAuth)
- **Bootstrap 5**: Frontend UI framework
- **No Premium Subscriptions**: All features free for authenticated users

**Current Components:**

1. **Flask Application:**
   - Single unified dashboard at `/apps/deeplink/profile/links`
   - Authentication-required access for all URL shortening
   - Real-time click tracking with Firestore updates

2. **Firebase Firestore Database:**
   - Collection: `shortened_links`
   - Document structure: `{user_id, user_email, original_url, click_count, created_at}`
   - User data isolation via `user_id` field

3. **Authentication Flow:**
   - Homepage → Login check → Redirect to login if needed
   - Post-auth redirect to link management dashboard
   - Support for `next` parameter in login/signup flows

4. **Removed Features:**
   - Guest user access (authentication now required)
   - YouTube-specific converter (consolidated to general URL shortener)
   - Separate creator/management interfaces (unified dashboard)

**Current Data Flow (Redirect):**
1. User clicks short link (`/apps/deeplink/r/<short_code>`)
2. Flask app queries Firestore for `short_code`
3. If found: increment click count, redirect to original URL
4. If not found: return 404 error

## 1.2 Planned Architecture (Future Implementation)

**Core Components:**

1.  **Flask Web Application (on GCP Cloud Run):**
    *   Handles all HTTP requests.
    *   Serves Jinja2 templates for the UI (link generator, dashboard).
    *   Contains business logic for link creation, redirection, and analytics processing.
    *   Exposes API endpoints for Stripe webhooks and potentially future client-side applications.
    *   Scales automatically based on load via Cloud Run.

2.  **Google Cloud SQL (PostgreSQL):**
    *   Primary relational database for storing:
        *   User subscription information.
        *   Deep link metadata (original URL, short code, owner, creation/expiration details).
        *   Detailed click analytics for each link.
    *   Accessed securely by the Flask application (e.g., via Cloud SQL Proxy or Python Connector).

3.  **Firebase Authentication:**
    *   Handles user registration, login (email/password, Google OAuth), and identity management.
    *   The Flask backend verifies Firebase ID tokens to authenticate users and authorize access to protected resources/features.

4.  **Stripe:**
    *   Manages the $5/month premium subscription.
    *   Provides Stripe Checkout for a secure payment process.
    *   Sends webhooks to the Flask application to notify about subscription events (creation, renewal, cancellation, payment failure).

5.  **SendGrid:**
    *   Handles transactional email delivery:
        *   Analytics reports to guest users upon link expiration.
        *   Periodic performance reports to premium users.
        *   Potentially other notifications (e.g., subscription status changes).

6.  **IPinfo (or similar IP Geolocation API):**
    *   Used to enrich click data by converting IP addresses into geographic information (country, region, city) and potentially ISP/organization details.
    *   Called by the Flask backend when a click is processed.

7.  **Chart.js:**
    *   A JavaScript library used on the client-side (in the premium user's browser) to render interactive charts and graphs for the analytics dashboard. Data is supplied by the Flask backend via Jinja2 templates.

**High-Level Data Flow (Redirect):**
1.  User clicks a short link (`yourphoenixapp.com/shortcode`).
2.  Request hits the Flask app on Cloud Run.
3.  Flask app parses `shortcode`.
4.  Queries Cloud SQL for the `shortcode` to find the original URL and link status.
5.  If link is active:
    *   Logs click details (timestamp, IP, User-Agent, Referrer) to Cloud SQL.
    *   Optionally, calls IPinfo API to get geo-data for the IP and stores it.
    *   Updates click count for the link.
    *   If guest link reaches 10 clicks, marks as expired and queues/sends email report via SendGrid.
    *   Responds with an HTTP 302 redirect to the original URL.
6.  If link is expired or not found, serves an appropriate error/info page.

## 2. Database Schema

The primary database will be PostgreSQL hosted on GCP Cloud SQL.

### 2.1. Table: `users` (Existing or Assumed)
This table is assumed to exist for Firebase authenticated users, storing at least the Firebase UID. If not, `user_subscriptions` will directly use `firebase_uid`.
*   `firebase_uid` (VARCHAR, PK): Firebase User ID.
*   `email` (VARCHAR, UNIQUE, NOT NULL): User's email.
*   `created_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
*   ... (other user-specific fields)

### 2.2. Table: `user_subscriptions`
Stores information about user subscriptions managed by Stripe.
*   `id` (SERIAL, PK)
*   `firebase_uid` (VARCHAR, FK to `users.firebase_uid`, UNIQUE, NOT NULL): Links to the user.
*   `stripe_customer_id` (VARCHAR, UNIQUE, NOT NULL): Stripe's ID for the customer.
*   `stripe_subscription_id` (VARCHAR, UNIQUE, NOT NULL): Stripe's ID for the subscription.
*   `plan_id` (VARCHAR, NOT NULL): Identifier for the subscribed plan (e.g., "premium_monthly_5usd").
*   `status` (VARCHAR, NOT NULL): Subscription status (e.g., "active", "canceled", "past_due", "incomplete").
*   `current_period_start` (TIMESTAMP): Start of the current billing period.
*   `current_period_end` (TIMESTAMP): End of the current billing period (when next renewal/expiration occurs).
*   `cancel_at_period_end` (BOOLEAN, DEFAULT FALSE): True if the subscription is set to cancel at period end.
*   `created_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
*   `updated_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)

**Indexes:** `firebase_uid`, `stripe_customer_id`, `stripe_subscription_id`.

### 2.3. Table: `deeplinks`
Stores metadata for each generated short link.
*   `id` (SERIAL, PK)
*   `short_code` (VARCHAR(12), UNIQUE, NOT NULL): The unique short identifier for the link (e.g., "aB1xYz").
*   `original_url` (TEXT, NOT NULL): The destination URL.
*   `firebase_uid` (VARCHAR, FK to `users.firebase_uid`, NULLABLE): Owner of the link if created by an authenticated user. NULL for guest links.
*   `guest_email` (VARCHAR, NULLABLE): Email address provided by a guest user for their link.
*   `created_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP)
*   `expires_at` (TIMESTAMP, NULLABLE): For future time-based expiration; not used for click-based expiry.
*   `max_clicks` (INTEGER, NULLABLE): Click limit for the link (e.g., 10 for guests, NULL for premium).
*   `click_count` (INTEGER, DEFAULT 0, NOT NULL): Current number of clicks.
*   `is_active` (BOOLEAN, DEFAULT TRUE, NOT NULL): Whether the link is currently active. Set to FALSE upon expiration or manual deactivation.
*   `last_clicked_at` (TIMESTAMP, NULLABLE): Timestamp of the most recent click.

**Indexes:** `short_code` (unique), `firebase_uid`, `guest_email`, `created_at`.

### 2.4. Table: `link_clicks`
Stores detailed information for each click event.
*   `id` (BIGSERIAL, PK)
*   `deeplink_id` (INTEGER, FK to `deeplinks.id` ON DELETE CASCADE, NOT NULL): Links to the `deeplinks` table.
*   `clicked_at` (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP, NOT NULL)
*   `ip_address` (VARCHAR(45)): IP address of the clicker (supports IPv4 and IPv6).
*   `user_agent` (TEXT): User-Agent string from the clicker's browser.
*   `referrer_url` (TEXT, NULLABLE): The HTTP referrer.
*   `geo_country` (VARCHAR(100), NULLABLE): Country derived from IP address.
*   `geo_region` (VARCHAR(100), NULLABLE): Region/State derived from IP address.
*   `geo_city` (VARCHAR(100), NULLABLE): City derived from IP address.
*   `device_type` (VARCHAR(50), NULLABLE): e.g., "Desktop", "Mobile", "Tablet".
*   `os_family` (VARCHAR(50), NULLABLE): e.g., "Windows", "macOS", "Linux", "Android", "iOS".
*   `browser_family` (VARCHAR(50), NULLABLE): e.g., "Chrome", "Firefox", "Safari", "Edge".

**Indexes:** `deeplink_id`, `clicked_at`, `geo_country`.
**(Note: This table can grow very large. Consider partitioning by `clicked_at` or `deeplink_id` in the future if performance degrades.)**

**Data Retention Policy:**
*   For guest links (`deeplinks` where `firebase_uid` is NULL): `deeplinks` and associated `link_clicks` data will be retained for 1 year from `deeplinks.created_at`. A periodic cleanup job will be required.
*   For premium user links: Data is retained as long as the subscription is active or per platform's overall data deletion policies for inactive accounts.

## 3. API Endpoints and URL Routes (Flask)

Base URL: `https://yourphoenixapp.com`

### 3.1. Public Access
*   **`GET /` (or `/deeplink-generator`)**
    *   **Purpose:** Displays the deep link generator page for all users.
    *   **Auth:** None required.
    *   **Response:** HTML page with a form for `original_url` and `guest_email` (if not logged in). Displays terms (10-click limit for guests).

*   **`POST /deeplink/create`**
    *   **Purpose:** Handles creation of a new short link.
    *   **Auth:**
        *   If guest: No token needed. `guest_email` is required in payload.
        *   If authenticated: Firebase ID token required. `guest_email` ignored.
    *   **Request Body (form-data or JSON):**
        *   `original_url` (string, required)
        *   `guest_email` (string, optional, required for guests)
    *   **Behavior:**
        1.  Validate `original_url`.
        2.  If guest, validate `guest_email`.
        3.  Generate unique `short_code`.
        4.  If guest: Create `deeplinks` entry with `max_clicks=10`, `guest_email`.
        5.  If authenticated: Check subscription status via `user_subscriptions`.
            *   If premium: Create `deeplinks` entry with `firebase_uid`, `max_clicks=NULL`.
            *   If not premium (authenticated but not subscribed): Potentially treat as guest (10 clicks, but tied to `firebase_uid`), or disallow/prompt to upgrade. (Decision: For simplicity, authenticated non-subscribed users attempting to create via this public endpoint could be redirected to the subscription page or informed it's a premium feature beyond a very limited trial if any. Or, treat them like guests using their account email). For now, assume this endpoint is primarily for guests or new users; premium users use dashboard.
    *   **Response:**
        *   Success: HTML page displaying the `short_link`, or JSON `{"short_link": "...", "original_url": "..."}`.
        *   Error: HTML error page or JSON error message.

*   **`GET /<short_code>`** (e.g., `/aB1xYz`)
    *   **Purpose:** Redirects a short link to its original URL and logs the click.
    *   **Auth:** None required.
    *   **Behavior:**
        1.  Look up `short_code` in `deeplinks`.
        2.  If not found or `is_active` is false: Return 404 or an "invalid/expired link" page.
        3.  If found and active:
            *   Increment `click_count` in `deeplinks`.
            *   Log click details (IP, User-Agent, Referrer) into `link_clicks`.
            *   (Async or quick sync) Call IPinfo API to get `geo_country`, `geo_region`, `geo_city` and update `link_clicks`.
            *   (Async or quick sync) Parse User-Agent for `device_type`, `os_family`, `browser_family` and update `link_clicks`.
            *   Check if `click_count` >= `max_clicks` (if `max_clicks` is set).
                *   If limit reached: Set `is_active=FALSE`. If `guest_email` exists, trigger email report via SendGrid.
            *   Perform HTTP 302 redirect to `original_url`.
    *   **Response:** HTTP 302 Redirect or HTML error page.

### 3.2. Authenticated Access (Premium Users - Firebase Token Required)
*   **`GET /dashboard/deeplinks`**
    *   **Purpose:** Displays the premium user's deep link management dashboard.
    *   **Auth:** Firebase ID token required. User must have an active premium subscription.
    *   **Behavior:**
        1.  Verify token, get `firebase_uid`.
        2.  Check `user_subscriptions` for active status. If not premium, redirect to upgrade page or show error.
        3.  Fetch all `deeplinks` associated with `firebase_uid`.
        4.  For each link, fetch aggregated analytics (total clicks, recent trends) from `link_clicks`.
    *   **Response:** HTML page (Jinja2 template) rendering the dashboard with link table and analytics charts (data passed to Chart.js).

*   **`POST /dashboard/deeplink/create`**
    *   **Purpose:** Handles creation of a new short link by a premium user from their dashboard.
    *   **Auth:** Firebase ID token required. User must have an active premium subscription.
    *   **Request Body (form-data or JSON):**
        *   `original_url` (string, required)
    *   **Behavior:**
        1.  Verify token, get `firebase_uid`. Confirm premium status.
        2.  Validate `original_url`.
        3.  Generate unique `short_code`.
        4.  Create `deeplinks` entry with `firebase_uid`, `max_clicks=NULL`.
    *   **Response:**
        *   Success: Redirect back to `/dashboard/deeplinks` with a success message, or JSON `{"short_link": "...", "original_url": "..."}` if dashboard handles client-side updates.
        *   Error: Error message on dashboard or JSON error.

*   **`GET /dashboard/deeplink/<deeplink_id>/analytics`**
    *   **Purpose:** Fetches detailed analytics for a specific link owned by the premium user.
    *   **Auth:** Firebase ID token required. User must own the link and be premium.
    *   **Behavior:**
        1.  Verify token, get `firebase_uid`.
        2.  Fetch `deeplink` by `deeplink_id`, ensuring `firebase_uid` matches.
        3.  Query `link_clicks` for detailed click data (time series, geo, referrers, devices).
    *   **Response:** JSON data suitable for rendering detailed charts/tables on the dashboard.
        ```json
        {
          "total_clicks": 1250,
          "clicks_timeseries": [{"date": "2023-10-01", "count": 15}, ...],
          "geo_distribution": [{"country": "US", "count": 500}, {"country": "CA", "count": 100}, ...],
          "referrers": [{"source": "google.com", "count": 300}, ...],
          "devices": [{"type": "Desktop", "count": 700}, {"type": "Mobile", "count": 550}, ...]
        }
        ```

### 3.3. Webhooks
*   **`POST /webhook/stripe`**
    *   **Purpose:** Receives subscription events from Stripe.
    *   **Auth:** Verified by checking Stripe signature in request header.
    *   **Request Body:** Stripe event payload (JSON).
    *   **Behavior:**
        1.  Verify Stripe signature using webhook secret.
        2.  Parse event type (e.g., `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`).
        3.  Update `user_subscriptions` table accordingly (create new entry, update status, period end, etc.).
            *   For `checkout.session.completed`, link Stripe customer to `firebase_uid` (retrieve from session metadata).
    *   **Response:** HTTP 200 to acknowledge receipt to Stripe. Error codes (4xx/5xx) if processing fails.

## 4. Data Flow Scenarios

*   **Guest Link Creation & Expiration:**
    1.  User submits URL + email to `POST /deeplink/create`.
    2.  Flask app validates, generates `short_code`, stores in `deeplinks` (with `guest_email`, `max_clicks=10`).
    3.  User shares link.
    4.  Clicks hit `GET /<short_code>`. Each click updates `deeplinks.click_count` and adds a row to `link_clicks`.
    5.  On 10th click, `deeplinks.is_active` becomes `FALSE`. Flask app triggers SendGrid to email `guest_email` with click summary.
    6.  Subsequent clicks to `GET /<short_code>` show "expired" page.

*   **Premium User Link Creation & Analytics:**
    1.  User logs in (Firebase Auth), navigates to `/dashboard/deeplinks`.
    2.  User submits URL to `POST /dashboard/deeplink/create`.
    3.  Flask app (auth middleware verifies token & premium status) validates, generates `short_code`, stores in `deeplinks` (with `firebase_uid`, `max_clicks=NULL`).
    4.  Link appears on dashboard.
    5.  Clicks on the link are logged in `link_clicks` (with geo/device enrichment). `deeplinks.click_count` updated.
    6.  User views `/dashboard/deeplinks`. Flask app queries `deeplinks` and `link_clicks` to aggregate data for display with Chart.js.
    7.  Periodic task (e.g., Cloud Scheduler job hitting an internal endpoint) queries data and sends summary reports via SendGrid.

*   **Subscription Management:**
    1.  User initiates subscription via a "Upgrade" button, redirected to Stripe Checkout.
    2.  User completes payment on Stripe.
    3.  Stripe sends `checkout.session.completed` event to `POST /webhook/stripe`.
    4.  Flask app verifies webhook, extracts `firebase_uid` (from metadata) and Stripe IDs.
    5.  Creates/updates entry in `user_subscriptions` with `status='active'`.
    6.  User now has premium access.
    7.  If subscription is canceled or payment fails, Stripe sends other webhooks, updating `user_subscriptions.status`. Access to premium features is revoked accordingly.

## 5. External Integrations

*   **Firebase Authentication:**
    *   Frontend uses Firebase JS SDK for login UI.
    *   Backend uses Firebase Admin SDK (Python) to verify ID tokens.
    *   Service account credentials for Admin SDK securely managed in Cloud Run environment.
*   **Stripe:**
    *   Stripe JS (optional, for custom Checkout) or direct redirect to Stripe-hosted Checkout.
    *   Backend uses Stripe Python SDK for creating Checkout sessions and verifying webhook signatures.
    *   Stripe API Key (secret) and Webhook Signing Secret securely managed in Cloud Run environment.
*   **SendGrid:**
    *   Backend uses SendGrid Python SDK or direct API calls.
    *   SendGrid API Key securely managed in Cloud Run environment.
    *   Verified sender domain configured in SendGrid.
*   **IPinfo (or similar):**
    *   Backend makes HTTP API calls to IPinfo.
    *   IPinfo API Token securely managed in Cloud Run environment.
    *   Consider rate limits of the free/paid tier. Cache results for identical IPs within a short window if high volume from same IP.
*   **Chart.js:**
    *   Frontend includes Chart.js library (e.g., from a CDN).
    *   Flask backend provides data to Jinja2 templates, which then passes it to Chart.js for rendering.

## 6. Scalability and Performance

*   **Cloud Run:** Auto-scales stateless Flask application instances. Configure concurrency settings appropriately. Optimize container startup time.
*   **Cloud SQL (PostgreSQL):**
    *   Choose an appropriate instance size. Can be scaled up.
    *   Utilize connection pooling from Flask app (e.g., SQLAlchemy's pool or Cloud SQL Python Connector).
    *   Proper indexing on tables is crucial (see schema).
    *   For `link_clicks`, which can grow very large:
        *   Consider archiving or summarizing old data.
        *   Future: Table partitioning by date range.
        *   Analytic queries on large `link_clicks` table should be optimized.
*   **Redirection (`GET /<short_code>`):**
    *   This is a critical path. Aim for minimal latency.
    *   Database lookup for `short_code` must be fast (indexed).
    *   Offload heavy processing (like detailed IP geolocation or extensive User-Agent parsing) to asynchronous tasks if it adds significant latency. A quick IPinfo lookup might be acceptable.
*   **Caching:**
    *   Short-lived in-memory caching (e.g., LRU cache in Flask app instance) for frequently accessed `short_code` -> `original_url` mappings.
    *   Consider caching aggregated analytics results for dashboards if queries are heavy and data doesn't change hyper-frequently.
*   **Asynchronous Tasks:**
    *   For non-critical path operations like sending email reports or complex analytics data enrichment, consider using a task queue (e.g., Google Cloud Tasks) to offload work from the main request-response cycle.
*   **Database Read Replicas:** If read load becomes an issue on Cloud SQL, read replicas can be used for analytics queries.

## 7. Security Considerations

*   **Authentication & Authorization:**
    *   All authenticated endpoints must rigorously verify Firebase ID tokens.
    *   Authorization checks must ensure users can only access/manage their own data (e.g., a user cannot see another user's links or analytics).
*   **Input Validation:**
    *   Sanitize and validate all user inputs: `original_url` (prevent XSS, SSRF if URL is fetched server-side, check for valid schemes), `guest_email`, `short_code` format.
    *   Protect against SQL injection (use ORM or parameterized queries).
*   **API Key Management:** All API keys and secrets (Firebase, Stripe, SendGrid, IPinfo) must be stored securely as environment variables in Cloud Run (ideally sourced from Google Secret Manager).
*   **Stripe Webhook Security:** Verify Stripe webhook signatures to ensure authenticity.
*   **CSRF Protection:** Use CSRF tokens for all state-changing form submissions if using session-based authentication alongside token auth. Flask-WTF or similar can provide this.
*   **Rate Limiting:** Implement rate limiting on link creation endpoints (`/deeplink/create`, `/dashboard/deeplink/create`) and potentially on the redirect endpoint if abuse is detected (e.g., too many requests for non-existent short codes from one IP).
*   **Short Code Generation:** Ensure `short_code` generation is random enough to prevent enumeration and guessing. Use a sufficiently large character set and length.
*   **HTTPS:** Enforce HTTPS for all communication. Cloud Run typically handles SSL termination.
*   **Data Privacy:** Adhere to data retention policies. Be mindful of PII (IP addresses, emails).

## 8. Deployment and Staging

*   **Deployment:** The Flask application will be containerized (Dockerfile) and deployed to GCP Cloud Run.
*   **CI/CD:** A CI/CD pipeline (e.g., using GitHub Actions) will automate builds and deployments to Cloud Run upon pushes/merges to specified branches.
*   **Environment Variables:** All configuration (API keys, database connection strings) will be managed via environment variables in Cloud Run.
*   **Staging Environment (Future):**
    *   A separate Cloud Run service will be set up for staging, connected to a separate Cloud SQL instance (or schema) and test versions of external services (Stripe test mode, SendGrid sandbox).
    *   The CI/CD pipeline will deploy a `dev` or `staging` branch to this environment for testing before production release.