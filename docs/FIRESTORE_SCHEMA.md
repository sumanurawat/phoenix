# Firestore Schema Documentation

This document outlines the schema for collections used in Firestore by the Phoenix application.

## `memberships` Collection

This collection stores information about user memberships, their current tier, and details related to their Stripe subscription if applicable.

**Document ID**: `userId` (string, matches the Firebase Authentication user ID)

### Fields

| Field Name              | Data Type          | Nullable | Default | Description                                                                                                | Example Value / Notes                                      | Typically Set By                                       |
|-------------------------|--------------------|----------|---------|------------------------------------------------------------------------------------------------------------|------------------------------------------------------------|--------------------------------------------------------|
| `userId`                | string             | No       | N/A     | The Firebase Authentication user ID. This is also the document ID.                                           | `firebase_auth_user_uid_123`                               | System (upon user creation/first membership action)    |
| `stripeCustomerId`      | string             | Yes      | `null`  | The Stripe Customer ID associated with the user.                                                             | `cus_xxxxxxxxxxxxxx`                                       | Stripe integration (e.g., after first payment/checkout)  |
| `stripeSubscriptionId`  | string             | Yes      | `null`  | The Stripe Subscription ID if the user has an active or past paid subscription.                              | `sub_xxxxxxxxxxxxxx`                                       | Stripe webhooks or subscription creation logic         |
| `currentTier`           | string             | No       | `free`  | The user's current membership tier.                                                                        | `"free"`, `"basic"`, `"premium"`                           | System (default), Stripe webhooks, admin actions       |
| `subscriptionStatus`    | string             | No       | N/A     | The status of the user's Stripe subscription or their general membership status if on a free tier.         | `"active"`, `"inactive"`, `"trialing"`, `"canceled"`, `"past_due"`, `"free_tier"` | Stripe webhooks, system logic for free tier management |
| `subscriptionStartDate` | timestamp          | Yes      | `null`  | The date and time when the current paid subscription period started. Null if on a free tier or no active sub. | Firestore Timestamp                                        | Stripe webhooks                                        |
| `subscriptionEndDate`   | timestamp          | Yes      | `null`  | The date and time when the current subscription period is set to end or next renewal. Null for free tier.    | Firestore Timestamp                                        | Stripe webhooks                                        |
| `lastUpdated`           | timestamp          | No       | N/A     | Firestore server timestamp indicating when the document was last modified.                                   | `FieldValue.serverTimestamp()`                             | Firestore (automatic on write/update)                  |

### Notes

*   The `memberships` collection is crucial for managing user access to different features based on their subscription level.
*   Most fields related to Stripe (`stripeCustomerId`, `stripeSubscriptionId`, `subscriptionStatus`, `subscriptionStartDate`, `subscriptionEndDate`) will primarily be updated via Stripe webhooks to ensure data consistency with Stripe's records.
*   When a user signs up, they might initially not have a document in this collection, or a default "free" tier document can be created for them.

### Schema Reference Script

For a programmatic representation of this schema and example utility functions (like creating a default 'free' tier document for a user for testing), refer to the script:
`scripts/initialize_firestore.py`

This script includes a `document_memberships_schema()` function that prints out the schema details.
