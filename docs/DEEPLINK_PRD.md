# Product Requirements Document: URL Shortener / Deep Linking Feature

## 1. Introduction

### 1.1. Overview
The Phoenix platform offers a URL Shortener (Deep Linking) feature. This service functions as an advanced URL shortener, allowing authenticated users to convert long web addresses into concise, trackable links. These "deep links" are easier to share across various platforms and provide basic analytics on click-through engagement.

### 1.2. Problem Statement
Content creators, marketers, and general users often face challenges with:
*   Sharing long, cumbersome URLs, especially on platforms with character limits or where aesthetics matter.
*   Tracking the engagement and performance of shared links to understand audience interaction.
*   Managing multiple short links and their associated analytics over time.

### 1.3. Proposed Solution
A robust URL Shortening service integrated into the Phoenix platform that will:
*   Generate unique, short, and non-predictable links for any given original URL for authenticated users.
*   Provide click analytics (currently total click count).
*   Leverage existing Firebase Authentication and Firebase Firestore for data persistence.
*   **[Future] Guest Tier:** Quick link generation with limitations (e.g., click limit, email report).
*   **Authenticated User Tier (Current):** For logged-in users, offering link generation, persistent link storage, no click-based expiration (currently), and a management dashboard showing click counts.

### 1.4. Goals
*   **Enable Easy Link Sharing:** Allow authenticated users to generate short, professional-looking links from any original URL.
*   **Track Basic Engagement:** Provide click counts for each generated link.
*   **Enhance User Value:** Provide a useful tool for users to manage and analyze their shared links.
*   **Seamless Integration:** Integrate the URL shortener smoothly into the existing platform’s workflow and UI.
*   **Reliability and Security:** Ensure the service is highly available, redirects links with minimal latency, and securely stores link data.
*   **Scalability:** Design the system (using Firestore) to handle growth in users and link creations/clicks.

## 2. User Personas

### 2.1. [Future] Guest User (Unauthenticated)
*   **Description:** An internet user trying out the tool without logging in.
*   **Needs & Goals:** Quickly shorten a URL for one-off sharing.
*   **(Note: This persona is for future consideration. Current implementation requires authentication.)**

### 2.2. Authenticated User (Current Core User)
*   **Description:** A registered and logged-in Phoenix platform user (e.g., blogger, content creator, general user).
*   **Needs & Goals:**
    *   Regularly create and manage multiple short links for their content or sharing needs.
    *   Access basic analytics for their links (total clicks).
    *   Have links that do not expire based on click counts.
    *   View their links in an easy-to-understand dashboard.
*   **Motivations:** Convenience, professional link presentation, centralizing link management, understanding link popularity.
*   **Frustrations:** Unreliable link redirection, cumbersome link management interfaces.

### 2.3. Platform Administrator (Internal)
*   **Description:** Internal team member responsible for maintaining the platform.
*   **Needs & Goals:** Monitor overall usage, identify potential abuse, ensure system reliability.
*   **(Note: System design should allow for admin oversight.)**

## 3. User Flows

### 3.1. [Future] Guest User: Generating an Ephemeral Link
*   **(This flow is for future consideration and not part of the current implementation.)**

### 3.2. Authenticated User: Generating and Managing Links
1.  **Authentication:** User logs into the Phoenix platform via Firebase Authentication.
2.  **Navigation to "Create New Link":** User navigates to the "Manage / Create New Short Link" page (e.g., via their profile page at `/apps/deeplink/profile/links`).
3.  **Link Creation:**
    *   User enters the original URL on the combined management/creation page. Their email and user ID are known from their session.
    *   System generates a unique short link associated with their account.
    *   The new short URL is displayed on the same page.
4.  **Navigation to "My Links" Dashboard:** User accesses the "Manage / Create New Short Link" page (e.g., via their profile page at `/apps/deeplink/profile/links`), which serves as their dashboard and creation interface.
5.  **Link Management & Analytics Viewing:**
    *   The "Manage / Create New Short Link" page displays a table of all links created by the user, showing the short URL (full, clickable), original URL, creation date, and total click count, alongside the creation form.
    *   User can copy the short URL using a button.
    *   **[Future] Detailed Analytics:** Clicking a link could show more details (geo, referrer, device, charts).
6.  **Redirection & Tracking:** When a user's link is clicked, the platform increments the `click_count` in Firestore and redirects to the original URL.
7.  **[Future] Email Reports:** Periodic email reports summarizing link performance.
8.  **Data Retention:** Link data and click counts are retained as long as the user account is active, or per platform data retention policies.

## 4. Feature Requirements

### 4.1. Core Features (Authenticated Users)
*   **FR1.1: Short Link Generation:**
    *   Ability to input a long URL.
    *   System generates a unique, non-predictable, short alphanumeric code (document ID in Firestore).
    *   The short link is formed by `yourdomain.com/apps/deeplink/r/<short_code>`.
*   **FR1.2: URL Redirection:**
    *   When a short link is accessed, the system redirects the user to the original long URL.
    *   Redirects should be fast and reliable.
*   **FR1.3: Basic Click Tracking:**
    *   For every redirect, the system increments a `click_count` field in Firestore for the specific link.
    *   **[Future] Detailed Click Logging:** Timestamp, IP address, User-Agent, Referrer.
*   **FR1.4: User Interface:**
    *   Clean, intuitive interface for link generation and management on a single page (`/apps/deeplink/profile/links`).
    *   Clear display of the generated short link with an easy way to copy it.
    *   Dashboard for viewing created links is part of this combined page.

### 4.2. [Future] Guest Tier Features
*   **(All features in this section are for future consideration.)**
*   **FR2.1: Anonymous Link Generation.**
*   **FR2.2: Email Requirement for Guests.**
*   **FR2.3: Click Limit & Expiration.**
*   **FR2.4: Email Report on Expiration.**
*   **FR2.5: Data Retention for Guests.**

### 4.3. Authenticated User Features (Current Implementation)
*   **FR3.1: Authenticated Link Generation:**
    *   Links are associated with the logged-in user's account (`user_id`, `user_email`).
*   **FR3.2: Unlimited Links:**
    *   Authenticated users can create an unlimited number of short links (within reasonable system limits).
*   **FR3.3: No Click-Based Expiration:**
    *   Links generated by authenticated users do not currently expire based on click counts.
*   **FR3.4: Persistent Link Storage:**
    *   All generated links and their `click_count` are stored persistently in Firestore.
*   **FR3.5: Combined "Manage & Create Links" Dashboard:**
    *   A dedicated page (`/apps/deeplink/profile/links`) for authenticated users to:
        *   View a list/table of all their created links (short URL, original URL, creation date, total clicks).
        *   Use the form on the same page to create new short links.
        *   Copy short URLs.
*   **FR3.6: [Future] Detailed Analytics & Visualization:**
    *   For each link, display: Total click count (current).
    *   **[Future]:** Click trends over time, geographic distribution, referrers, device breakdown (requires detailed click logging).
*   **FR3.7: [Future] Email Reports:** Periodic email reports.
*   **FR3.8: Data Retention:** Link data and analytics are retained as long as the user account is active or per platform policy.

### 4.4. Authentication
*   **FR4.1: Firebase Authentication:**
    *   Leverage existing Firebase Authentication for user login/signup.
*   **FR4.2: [Future] Stripe Subscription Integration:** For potential premium tiers.
*   **FR4.3: [Future] Subscription Gating:** For potential premium features.

## 5. Business Rules and Constraints

*   **BR1: Short Code Uniqueness:** Each generated short code (Firestore document ID) must be unique.
*   **BR2: Short Code Non-Predictability:** Short codes should be difficult to guess (current `uuid.uuid4().hex[:6]` offers reasonable randomness).
*   **BR3: Original URL Validation:** Basic validation performed on the original URL (starts with http/https).
*   **BR4: [Future] Guest Email Validation.**
*   **BR5: Abuse Prevention:**
    *   Consider rate limiting for link creation if abuse is detected.
*   **BR6: Data Privacy:**
    *   Currently, only `user_id` and `user_email` are stored with the link. IP addresses are not stored per click.
    *   Clearly state data usage in privacy policy.
*   **BR7: [Future] Email Deliverability (SendGrid).**
*   **BR8: Performance:**
    *   Link generation should be near-instantaneous.
    *   Redirects must be very fast.
    *   "My Links" dashboard loading should be reasonably fast.
*   **BR9: [Future] Subscription Status Synchronization.**
*   **BR10: Error Handling:** Graceful handling of errors (e.g., invalid short code, failed link creation) with user-friendly messages.

## 6. Success Metrics
*   Number of links generated by authenticated users.
*   Total clicks processed.
*   "My Links" page views and engagement.
*   System uptime and redirect latency.
*   **[Future]:** Guest-to-authenticated user conversion rate (if guest tier is implemented).
*   **[Future]:** Number of active premium subscribers (if premium tier is implemented).

## 7. Future Roadmap (Post-MVP & Current Implementation)
*   **Guest User Access:** Limited free tier for creating short links.
*   **Detailed Analytics:** Geo-location, referrer tracking, device information, time-series charts for clicks.
*   **Premium Subscription Tiers (Stripe):** For unlocking advanced features or higher limits.
*   **Custom Short Codes/Vanity URLs:** Allow users to suggest their own short codes.
*   **Email Reporting (SendGrid):** For guest link expiration or user analytics summaries.
*   **QR Code Generation:** Generate QR codes for short links.
*   **Link Editing:** Allow editing the destination of an existing short link.
*   **Link Tagging/Organization:** Folders or tags for managing many links.
*   **API Access:** Provide API access for programmatic link creation and analytics retrieval.
*   **Team Accounts/Collaboration.**
*   **Enhanced Abuse Detection.**
*   **A/B Testing for Links.**
*   **Formalize Staging Environment.**
