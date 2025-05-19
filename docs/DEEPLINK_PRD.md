# Product Requirements Document: Deep Linking Feature

## 1. Introduction

### 1.1. Overview
The Phoenix platform is introducing a Deep Linking feature. This service will function as an advanced URL shortener, allowing users to convert long web addresses into concise, trackable links. These "deep links" are easier to share across various platforms and provide valuable analytics on click-through engagement. The feature will be available to both unauthenticated (guest) users with certain limitations and authenticated, subscribed (premium) users with enhanced capabilities and no hard limits.

### 1.2. Problem Statement
Content creators, marketers, and general users often face challenges with:
*   Sharing long, cumbersome URLs, especially on platforms with character limits or where aesthetics matter.
*   Tracking the engagement and performance of shared links to understand audience interaction.
*   Gathering insights like click origins, geographic distribution, and device types for links they distribute.
*   Managing multiple short links and their associated analytics over time.

### 1.3. Proposed Solution
A robust Deep Linking service integrated into the Phoenix platform that will:
*   Generate unique, short, and non-predictable links for any given original URL.
*   Provide detailed click analytics, including timestamps, IP-derived geolocation, user-agent information (device, browser, platform), and referrer data.
*   Offer a freemium model:
    *   **Guest Tier:** Quick link generation with an email requirement, a 10-click limit per link, and an email report upon link expiration.
    *   **Premium Tier ($5/month):** For subscribed users, offering unlimited link generation, persistent link storage, no click-based expiration, a comprehensive analytics dashboard, and regular email reports.
*   Seamlessly integrate with existing Firebase Authentication and leverage GCP infrastructure (Cloud Run, Cloud SQL for PostgreSQL).

### 1.4. Goals
*   **Enable Easy Link Sharing:** Allow users to generate short, professional-looking deep links from any original URL.
*   **Track Engagement:** Provide comprehensive analytics for each generated link to help users understand audience engagement.
*   **Drive User Acquisition and Conversion:** Offer a valuable free tier to attract users and showcase the feature's utility, encouraging upgrades to the premium subscription.
*   **Enhance User Value:** Provide a powerful tool for subscribed content creators to manage and analyze their promotional efforts.
*   **Seamless Integration:** Integrate the deep link generator smoothly into the existing platform’s workflow and UI (Jinja2 templates).
*   **Reliability and Security:** Ensure the service is highly available, redirects links with minimal latency, and securely stores all user and link data with appropriate retention policies.
*   **Scalability:** Design the system to handle growth in users and link creations/clicks.

## 2. User Personas

### 2.1. Guest User (Unauthenticated)
*   **Description:** An internet user, potential customer, or content creator trying out the tool without logging in.
*   **Needs & Goals:**
    *   Quickly shorten a URL for one-off sharing.
    *   Receive basic feedback on link performance (up to 10 clicks).
    *   Willing to provide an email address for this free service.
*   **Motivations:** Convenience, curiosity, testing the service before committing.
*   **Frustrations:** Complicated sign-up processes for simple tasks, links that expire too quickly without notice, lack of basic performance data.

### 2.2. Premium Content Creator (Authenticated & Subscribed)
*   **Description:** A registered Phoenix platform user with an active $5/month subscription (e.g., blogger, YouTuber, social media marketer, small business owner).
*   **Needs & Goals:**
    *   Regularly create and manage multiple short links for their content.
    *   Access detailed, long-term analytics for all their links (clicks, geo, referrer, device).
    *   Have links that do not expire based on click counts.
    *   View link performance in an easy-to-understand dashboard with visualisations (graphs).
    *   Receive periodic email reports on link activity.
*   **Motivations:** Optimizing content distribution, understanding audience behavior, professional link presentation, centralizing link management.
*   **Frustrations:** Services with limited analytics, unreliable link redirection, cumbersome link management interfaces, unexpected link expirations.

### 2.3. Platform Administrator (Internal)
*   **Description:** Internal team member responsible for maintaining the platform.
*   **Needs & Goals:**
    *   Monitor overall usage of the deep linking feature.
    *   Identify and mitigate potential abuse (e.g., spam link generation).
    *   Ensure the system is performing reliably.
*   **(Note: End-user features are not directly built for this persona, but system design should allow for admin oversight.)**

## 3. User Flows

### 3.1. Guest User: Generating an Ephemeral Link
1.  **Navigation:** User visits the public "Deep Link Generator" page on the Phoenix website (no login required).
2.  **Input:** User enters the long URL they wish to shorten and their email address into a form. A notice about the 10-click limit and email report is displayed.
3.  **Submission & Generation:** User submits the form. The system validates inputs and generates a unique short link (e.g., `https://yourphoenixapp.com/aB1xYz`).
4.  **Display:** The generated short URL is displayed to the user, along with a "copy" button.
5.  **Sharing & Redirection:** User shares the short link. When clicked, the platform logs the click details and redirects the clicker to the original URL.
6.  **Expiration:** After the 10th redirect, the link is marked as expired. Subsequent clicks will lead to an "expired link" page.
7.  **Email Report:** Upon expiration (after the 10th click), an automated email is sent to the guest user's provided email address. This email contains a summary of the 10 clicks (e.g., total count, timestamps, potentially basic geo/referrer info if implemented for guests) and a call-to-action to subscribe for unlimited links and detailed analytics.
8.  **Data Retention:** Guest link data and associated analytics are stored for 1 year from the link creation date, after which they may be purged.

### 3.2. Premium User: Generating and Managing Persistent Links
1.  **Authentication & Subscription Check:**
    *   User logs into the Phoenix platform via Firebase Authentication.
    *   The system verifies their active $5/month Stripe subscription.
    *   If not subscribed, the user is prompted/guided to subscribe to access premium deep linking features.
2.  **Navigation to Dashboard:** Authenticated and subscribed user accesses the "Deep Links Dashboard" from their account/profile page.
3.  **Link Creation:**
    *   On the dashboard, the user finds an interface to create new links.
    *   User enters the original URL. Their email is known from their account.
    *   System generates a unique short link associated with their account. Premium links do not have a 10-click expiration limit.
    *   The new short URL is displayed and added to their list of links on the dashboard.
4.  **Link Management & Analytics Viewing:**
    *   The dashboard displays a table of all links created by the user, showing the short URL, original URL, creation date, and key metrics like total clicks.
    *   User can click on a specific link (or an "analytics" button next to it) to view detailed analytics.
    *   Detailed analytics view includes:
        *   Total click count.
        *   Timeline graph of clicks (e.g., daily/hourly clicks over a period).
        *   Geographic distribution of clicks (e.g., map or list of countries/cities).
        *   Referrer data (e.g., top referring websites).
        *   Device/platform information (e.g., breakdown by OS, browser, device type).
5.  **Redirection & Tracking:** When a premium user's link is clicked, the platform logs detailed click analytics and redirects to the original URL. Clicks are unlimited.
6.  **Email Reports (Premium):** Premium users receive periodic (e.g., weekly or monthly) email reports summarizing the performance of their links.
7.  **Data Retention:** Premium user link data and analytics are retained indefinitely as long as their subscription is active, or per platform data retention policies.

## 4. Feature Requirements

### 4.1. Core Features (Applicable to All Users)
*   **FR1.1: Short Link Generation:**
    *   Ability to input a long URL.
    *   System generates a unique, non-predictable, short alphanumeric code.
    *   The short link is formed by `yourdomain.com/<short_code>`.
*   **FR1.2: URL Redirection:**
    *   When a short link is accessed, the system redirects the user to the original long URL.
    *   Redirects should be fast and reliable (e.g., HTTP 302 Found).
*   **FR1.3: Basic Click Tracking:**
    *   For every redirect, the system logs:
        *   Timestamp of the click.
        *   IP address of the clicker.
        *   User-Agent string of the clicker's browser/device.
        *   HTTP Referrer (if available).
*   **FR1.4: User Interface:**
    *   Clean, intuitive, and user-friendly interface for link generation.
    *   Clear display of the generated short link with an easy way to copy it.

### 4.2. Guest Tier Features (Unauthenticated Users)
*   **FR2.1: Anonymous Link Generation:**
    *   Users can generate links without logging in.
*   **FR2.2: Email Requirement for Guests:**
    *   Guests must provide a valid email address to generate a link.
    *   Display a notice about the purpose of collecting email (for analytics report).
*   **FR2.3: Click Limit & Expiration:**
    *   Guest-generated links expire after 10 redirects.
    *   After expiration, the link should lead to an "expired link" page, not the original URL.
*   **FR2.4: Email Report on Expiration:**
    *   An automated email is sent to the guest's provided email address once the link expires (after 10 clicks).
    *   The email should contain a summary of the 10 clicks and a call-to-action to subscribe.
*   **FR2.5: Data Retention for Guests:**
    *   Guest link data and associated click analytics are retained for 1 year.

### 4.3. Premium Tier Features (Authenticated & Subscribed Users)
*   **FR3.1: Authenticated Link Generation:**
    *   Links are associated with the logged-in user's account.
*   **FR3.2: Unlimited Links:**
    *   Premium users can create an unlimited number of short links (within reasonable system limits to prevent abuse).
*   **FR3.3: No Click-Based Expiration:**
    *   Links generated by premium users do not expire after a certain number of clicks. They remain active as long as the subscription is active (or per user action).
*   **FR3.4: Persistent Link Storage:**
    *   All generated links and their analytics are stored persistently.
*   **FR3.5: Deep Link Dashboard:**
    *   A dedicated dashboard for premium users to:
        *   View a list/table of all their created links (short URL, original URL, creation date, total clicks).
        *   Create new short links.
        *   Access detailed analytics for each link.
*   **FR3.6: Detailed Analytics & Visualization:**
    *   For each link, display:
        *   Total click count.
        *   Click trends over time (e.g., line or bar chart using Chart.js).
        *   Geographic distribution of clicks (e.g., list of top countries/cities, potentially a map view later).
        *   Top referring sources.
        *   Breakdown by device type (Desktop, Mobile, Tablet), Operating System, and Browser.
        *   (Analytics enriched by IPinfo for geolocation and User-Agent parsing for device/platform).
*   **FR3.7: Premium Email Reports:**
    *   Option for periodic (e.g., weekly/monthly) email reports summarizing link performance for all or selected links.
*   **FR3.8: Data Retention for Premium:**
    *   Link data and analytics for premium users are retained for a longer period, ideally as long as the subscription is active or per platform policy.

### 4.4. Authentication & Payment
*   **FR4.1: Firebase Authentication:**
    *   Leverage existing Firebase Authentication for user login/signup.
*   **FR4.2: Stripe Subscription Integration:**
    *   Integrate Stripe for managing the $5/month premium subscription.
    *   Secure checkout process.
    *   Webhook handling for subscription events (created, updated, canceled, payment failed).
*   **FR4.3: Subscription Gating:**
    *   Premium features (dashboard, unlimited links, detailed analytics) are only accessible to users with an active subscription.
    *   Users without an active subscription (or guests) attempting to access premium features should be prompted to subscribe.

## 5. Business Rules and Constraints

*   **BR1: Short Code Uniqueness:** Each generated short code must be unique across the entire system.
*   **BR2: Short Code Non-Predictability:** Short codes should be difficult to guess or enumerate.
*   **BR3: Original URL Validation:** Basic validation should be performed on the original URL to ensure it's a plausible web address (e.g., starts with http/https). Potentially block malicious URL schemes.
*   **BR4: Guest Email Validation:** Basic format validation for guest-provided email addresses.
*   **BR5: Abuse Prevention:**
    *   Consider rate limiting for link creation (especially for guests) to prevent spam.
    *   Monitor for suspicious activity.
*   **BR6: Data Privacy:**
    *   IP addresses should be handled carefully. Anonymization or aggregation might be considered for certain displays if privacy concerns are high, but raw IP is needed for geolocation.
    *   Clearly state data usage in privacy policy.
*   **BR7: Email Deliverability:** Ensure emails (reports, notifications) are sent reliably (via SendGrid) and do not end up in spam folders. Use verified sender domains.
*   **BR8: Performance:**
    *   Link generation should be near-instantaneous (< 1 second).
    *   Redirects must be very fast (< 200ms server-side processing).
    *   Analytics dashboard loading should be reasonably fast (< 3-5 seconds for typical data).
*   **BR9: Subscription Status Synchronization:** The system must accurately reflect the user's current subscription status from Stripe to grant/revoke premium access.
*   **BR10: Error Handling:** Graceful handling of errors (e.g., invalid short code, expired link, failed payment) with user-friendly messages.

## 6. Success Metrics
*   Number of links generated (guest vs. premium).
*   Number of active premium subscribers.
*   Guest-to-premium conversion rate.
*   Total clicks processed.
*   Average click-through rate (if original content context is known).
*   Dashboard engagement (page views, time spent).
*   Email open/click rates for reports.
*   System uptime and redirect latency.

## 7. Future Roadmap (Post-MVP)
*   **Custom Short Codes/Vanity URLs:** Allow premium users to define their own short codes.
*   **Custom Domains:** Allow premium users to use their own domain for short links.
*   **QR Code Generation:** Generate QR codes for short links.
*   **Link Editing:** Allow editing the destination of an existing short link (premium).
*   **Link Tagging/Organization:** Folders or tags for managing many links.
*   **Advanced Analytics Filtering:** More granular date range selection, filtering by geo/referrer/device on the dashboard.
*   **Data Export:** Allow users to export their click data (e.g., CSV).
*   **API Access:** Provide API access for programmatic link creation and analytics retrieval for higher-tier premium users.
*   **Team Accounts/Collaboration:** Features for teams to manage links collectively.
*   **Multiple Subscription Tiers:** Introduce different tiers with varying features and limits.
*   **Staging Environment:** Formalize and regularly use a staging environment for testing new releases.
*   **Enhanced Abuse Detection:** More sophisticated mechanisms for detecting and preventing misuse.
*   **A/B Testing for Links:** Allow creating multiple destination URLs for one short link to test performance.