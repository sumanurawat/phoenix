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

## Technology Stack

- Backend: Flask (Python)
- Frontend: HTML5, CSS3, JavaScript
- AI Integration: Google Gemini, custom NLP models
- Deployment: Google Cloud Run

---

## Deep Linking Service (MVP)

This feature provides a URL shortening service within the Phoenix platform. It allows users to generate shorter, shareable links from long URLs. The service tracks the number of clicks on each short link and includes basic differentiation for guest versus authenticated users, laying the groundwork for future premium features.

### Core Functionality:
*   **Short Link Generation:** Creates a unique, short alphanumeric code for any given valid URL.
*   **Click Tracking:** Records each time a short link is accessed.
*   **User Types:**
    *   **Guest Users:** Can create short links. These links have a usage limit (e.g., 10 clicks) after which they expire. An optional email can be associated with guest links.
    *   **Authenticated Users:** Can create short links without click limitations (as an MVP baseline). User ID is associated with the link.
*   **Redirection:** Handles the redirection from the short link to the original long URL.
*   **Link Expiration:** Guest links expire after a predefined number of clicks. Expired links will no longer redirect to the original URL.
*   **Click Analytics (Basic):** For each click, the service logs the timestamp, IP address, user agent, referrer URL, and attempts to determine the country of origin via IP geolocation.

### Firestore Collections Used:

The service leverages Google Firestore for data persistence.

1.  **`links` Collection:**
    *   **Purpose:** Stores the primary data for each short link created. Each document in this collection represents a unique short link.
    *   **Document ID:** The unique `shortCode` itself.
    *   **Key Fields:**
        *   `originalUrl` (String): The original long URL that the short link redirects to.
        *   `userId` (String, Nullable): The unique ID of the authenticated user who created the link. Null for guest users.
        *   `userEmail` (String, Nullable): The email address provided by a guest user. Null for authenticated users or if no email is provided by a guest.
        *   `type` (String): Indicates the type of link, e.g., "guest" or "authenticated".
        *   `createdAt` (Timestamp): Server timestamp indicating when the link was created.
        *   `clickCount` (Number): The total number of times the short link has been clicked. Atomically incremented.
        *   `lastClickedAt` (Timestamp, Nullable): Server timestamp of the most recent click.
        *   `isExpired` (Boolean): `true` if the link has expired (e.g., due to reaching `maxClicks`), `false` otherwise.
        *   `maxClicks` (Number, Nullable): The maximum number of clicks allowed for this link. Typically set for "guest" links (e.g., 10) and null for "authenticated" links (unlimited for MVP).

2.  **`clicks` Subcollection (nested under each document in the `links` collection):**
    *   **Path:** `links/{shortCode}/clicks/{clickId}`
    *   **Purpose:** Stores details for each individual click event on a specific short link. Each document represents one click.
    *   **Document ID:** Auto-generated unique ID for the click event.
    *   **Key Fields:**
        *   `clickedAt` (Timestamp): Server timestamp indicating when the click occurred.
        *   `ipAddress` (String): The IP address of the client that accessed the link.
        *   `userAgent` (String): The user agent string of the client's browser or device.
        *   `referrerUrl` (String, Nullable): The URL of the page that referred the client to the short link, if available.
        *   `countryCode` (String, Nullable): The two-letter country code (e.g., "US") derived from the IP address via an external geolocation service (ip-api.com). May be null if geolocation fails or is not applicable.

---

## About the Developer

Created by [Sumanu Rawat](https://github.com/sumanurawat). Connect on [LinkedIn](https://www.linkedin.com/in/sumanurawat/).