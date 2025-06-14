# Manual Testing Plan for URL Shortener

## Prerequisites
1.  Ensure the Flask application is running locally.
2.  Ensure Firebase Admin SDK is initialized (check app logs for success message like "Firebase Admin SDK initialized successfully.").
3.  Ensure `GOOGLE_APPLICATION_CREDENTIALS` environment variable is correctly set and pointing to a valid Firebase service account key JSON file with Firestore read/write permissions.
4.  You will need to be logged into the application. Use the signup/login functionality. If creating a new user, ensure the authentication flow completes and you are logged in.

## Test Cases

### 1. User Authentication & Access Control
    *   **Test Case 1.1:** Access link creation page (`/apps/deeplink/profile/converter`) without being logged in.
        *   **Expected:** Redirected to the login page (e.g., `/auth/login?next=/apps/deeplink/profile/converter`).
    *   **Test Case 1.2:** Access "My Links" page (`/apps/deeplink/profile/my-links`) without being logged in.
        *   **Expected:** Redirected to the login page (e.g., `/auth/login?next=/apps/deeplink/profile/my-links`).
    *   **Test Case 1.3:** Successfully log in using existing credentials or after signing up.
        *   **Expected:** Able to access your profile page. Subsequently, able to navigate to and view the link creation page (`/apps/deeplink/profile/converter`) and the "My Links" page (`/apps/deeplink/profile/my-links`).

### 2. Link Creation (`/apps/deeplink/profile/converter`)
    *   **Test Case 2.1:** Create a short link with a valid, full URL (e.g., `https://www.google.com/search?q=testing`).
        *   **Steps:** Navigate to the converter page, enter the URL, click "Create Short Link".
        *   **Expected:**
            *   A success message (e.g., "Successfully created your short link!") is displayed.
            *   A short URL is displayed in the format `http://localhost:8080/apps/deeplink/r/xxxxxx` (where `xxxxxx` is the short code).
            *   The original URL submitted is also displayed for confirmation.
        *   **Verification (Firestore):**
            *   Open your Firebase console and navigate to Firestore.
            *   Check the `shortened_links` collection for a new document whose ID is the `xxxxxx` short code.
            *   Verify the document fields: `original_url` matches the input, `user_id` and `user_email` match the logged-in user, `created_at` is a recent timestamp, and `click_count` is `0`.
    *   **Test Case 2.2:** Attempt to create a short link with an empty URL string.
        *   **Steps:** Navigate to the converter page, leave the URL field empty, click "Create Short Link".
        *   **Expected:** An error message like "Please enter a URL to shorten." is displayed. No new link is created in Firestore.
    *   **Test Case 2.3:** Attempt to create a short link with an invalid URL format (e.g., `notaurl`, `www.google.com` without `http://` or `https://`).
        *   **Steps:** Enter an invalid URL, click "Create Short Link".
        *   **Expected:** An error message like "Invalid URL. Please ensure it starts with http:// or https://" is displayed. No new link is created.
    *   **Test Case 2.4:** Create multiple valid short links for different original URLs.
        *   **Expected:** Each link is created successfully. Each has a unique short code. All corresponding documents appear correctly in Firestore.

### 3. Link Redirection & Click Counting (`/apps/deeplink/r/<short_code>`)
    *   **Test Case 3.1:** Access a valid short URL (e.g., one created in Test Case 2.1) by pasting it into a new browser tab or clicking it from the "My Links" page.
        *   **Expected:** The browser redirects to the original long URL (e.g., `https://www.google.com/search?q=testing`).
        *   **Verification (Firestore):** The `click_count` for the corresponding document in the `shortened_links` collection should increment by 1.
    *   **Test Case 3.2:** Access the same short URL multiple times (e.g., 3 more times).
        *   **Expected:** Browser redirects correctly to the original URL each time.
        *   **Verification (Firestore):** The `click_count` in Firestore should accurately reflect the total number of clicks (e.g., if clicked 1 time then 3 more times, total should be 4).
    *   **Test Case 3.3:** Attempt to access an invalid or non-existent short URL (e.g., `/apps/deeplink/r/invalidcode`).
        *   **Expected:** A 404 error page is displayed with a message like "Short link not found or expired."

### 4. "My Links" Page (`/apps/deeplink/profile/my-links`)
    *   **Test Case 4.1:** After creating several links, navigate to the "My Links" page.
        *   **Expected:**
            *   All links created by the currently logged-in user are displayed in a table.
            *   The table includes columns for "Original URL", "Short URL", "Created At", and "Clicks".
            *   The "Short URL" is a clickable link that directs to the ` /apps/deeplink/r/<short_code>` redirector.
            *   The "Original URL" is a clickable link that directs to the actual target URL.
            *   The "Created At" date and time are displayed in a readable format (e.g., YYYY-MM-DD HH:MM UTC).
    *   **Test Case 4.2:** Verify that click counts displayed on the "My Links" page update correctly after short links are accessed (as in Test Cases 3.1, 3.2).
        *   **Steps:** Note current click count, click a short link, refresh "My Links" page.
        *   **Expected:** The "Clicks" column updates to the new total.
    *   **Test Case 4.3:** Use the "Copy" button next to a short URL in the table.
        *   **Expected:** The full short URL (e.g., `http://localhost:8080/apps/deeplink/r/xxxxxx`) is copied to the clipboard. Brief visual feedback (e.g., icon change to a checkmark) is shown on the button.
    *   **Test Case 4.4:** If a user has not created any links, navigate to the "My Links" page.
        *   **Expected:** A message like "You haven't created any short links yet. Why not create one now?" is displayed, with a link to the converter page.
    *   **Test Case 4.5:** Click the "Create New Link" button on the "My Links" page.
        *   **Expected:** User is navigated to the link creation page (`/apps/deeplink/profile/converter`).

### 5. Profile Page Links (`/profile`)
    *   **Test Case 5.1:** Ensure you are logged in. Navigate to your main profile page.
    *   **Steps:** Locate the link/button "My Shortened Links".
        *   **Expected:** Clicking it navigates you to `/apps/deeplink/profile/my-links`.
    *   **Test Case 5.2:** On the profile page, locate the link/button "Create New Short Link".
        *   **Expected:** Clicking it navigates you to `/apps/deeplink/profile/converter`.

### (Optional) Firestore Data Verification
    *   **Test Case 6.1:** (If another user account is available) Log in as User A, create links. Log out. Log in as User B, create links.
        *   **Expected:** User A's "My Links" page only shows links created by User A. User B's "My Links" page only shows links created by User B. Firestore documents should correctly store `user_id` and `user_email` for each link.

### Notes for Testers
*   Clear browser cache/cookies or use incognito mode if testing authentication flows extensively to ensure sessions are handled cleanly.
*   Keep the Firebase Firestore console open to observe real-time data changes for `click_count` and new document creation.
*   Check browser developer console for any frontend errors during interactions.
*   Check Flask application logs for any backend errors or exceptions.
```
