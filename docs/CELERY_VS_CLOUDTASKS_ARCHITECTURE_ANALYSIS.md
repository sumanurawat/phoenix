# Architectural Decision Record: Migrating Async Tasks from Celery to Cloud Run Jobs

**Date:** 2025-11-07
**Status:** Proposed

## 1. Executive Summary

This document proposes a strategic migration of our asynchronous task processing system from the current Celery/Redis stack to a serverless architecture using **Google Cloud Tasks** and **Cloud Run Jobs**.

The primary drivers for this change are **cost reduction**, **operational simplicity**, and **enhanced scalability**. Our current Celery-based system incurs a fixed monthly cost of **~$43/month** for its underlying Redis and VPC infrastructure, even with zero usage. A migration to Cloud Run Jobs would change this to a pay-per-use model, costing an estimated **$3-$8/month for 1,000 video generations**, representing a **cost reduction of over 80%**.

This move aligns with our existing, successful implementation of `reel-stitching-job` and simplifies our architecture by removing the need for a persistent worker service, a Redis instance, and complex VPC networking.

**Recommendation:** We recommend a phased migration to Cloud Tasks and Cloud Run Jobs, starting with video generation, to improve cost-efficiency and scalability.

---

## 2. Current Architecture: Celery + Redis

Our current system for handling long-running tasks like video and image generation relies on Celery, a popular Python task queue library, with Redis as the message broker.

### 2.1. Data Flow & Components

```mermaid
graph TD
    subgraph User
        A[Browser]
    end

    subgraph Phoenix App (Cloud Run Service)
        B[Flask API: /api/generate/video] --> C{CreationService};
        C --> D[Firestore: Create 'pending' draft];
        C --> E[Celery: send_task()];
    end

    subgraph VPC Network
        E -- Task --> F[Redis Queue (Memorystore)];
        G[Celery Worker (Cloud Run Service)] -- Polls Task --> F;
    end

    G -- Processes Task --> H[Veo/Imagen API];
    H -- Video/Image Data --> G;
    G --> I[Firestore: Update draft to 'completed'];

    A -- Polls for updates --> B;

    style F fill:#F9EBEA,stroke:#C0392B
    style G fill:#D6EAF8,stroke:#2E86C1
```

**Component Breakdown:**

1.  **Flask API (`phoenix` service):**
    -   Receives the user's request at `api.generation_routes.py`.
    -   Calls `services.creation_service.py` to create a "pending" document in the `creations` Firestore collection.
    -   Enqueues a task to Celery/Redis using `celery_app.send_task('jobs.async_video_generation_worker.generate_video_task', ...)`.
    -   Immediately returns a `202 Accepted` response to the user.

2.  **Redis (Google Cloud Memorystore):**
    -   Acts as the "mailbox" or message broker.
    -   The task from the Flask app is stored in a list in Redis.
    -   **Cost:** ~$30/month for a `basic` tier 1GB instance.

3.  **VPC Connector:**
    -   A network bridge that allows our Cloud Run services to access the private IP address of the Redis instance.
    -   **Cost:** ~$8/month.

4.  **Celery Worker (`phoenix-video-worker` service):**
    -   A long-running Cloud Run service with `min-instances=1`.
    -   It maintains a persistent connection to Redis.
    -   When a new task appears in the queue, the worker pulls it and executes the code in `jobs/async_video_generation_worker.py`.
    -   This worker calls the external AI APIs (Veo, Imagen), waits for the result (60-120 seconds), and updates the Firestore document.

### 2.2. Technical Details & Costs

-   **Infrastructure:** 2 Cloud Run Services, 1 Cloud Memorystore for Redis, 1 VPC Connector.
-   **Code:** `celery_app.py`, `run_worker.py`, `jobs/async_*_worker.py`.
-   **Idle Cost:** **~$38/month** (Redis + VPC Connector), regardless of usage.
-   **Scalability:** Limited by the number of concurrent Celery workers and the performance of the single Redis instance. Scaling up workers increases cost and complexity.

### 2.3. Pros & Cons

| Pros ✅ | Cons ❌ |
| :--- | :--- |
| **Mature Technology:** Celery is a well-known, feature-rich library. | **High Idle Cost:** ~$38/month fixed cost is prohibitive for a startup/prototype. |
| **Rich Features:** Built-in support for retries, rate limiting, and complex workflows. | **Operational Complexity:** Requires managing Redis, VPC networking, and a separate worker service. |
| **Good Local Dev Experience:** `redis-server` can be run locally or via Docker. | **Networking Overhead:** VPC configuration is a common source of errors (as we discovered). |
| **Low Latency (for short tasks):** Worker is always "hot," so task startup is instant. | **Scalability Bottleneck:** All tasks funnel through a single Redis instance. |

---

## 3. Proposed Architecture: Cloud Tasks + Cloud Run Jobs

This proposal replaces the Celery/Redis/Worker stack with a fully serverless, pay-per-use model that leverages Google-managed services. This pattern is already successfully used in our `reel-stitching-job`.

### 3.1. Data Flow & Components

```mermaid
graph TD
    subgraph User
        A[Browser]
    end

    subgraph Phoenix App (Cloud Run Service)
        B[Flask API: /api/generate/video] --> C{CreationService};
        C --> D[Firestore: Create 'pending' draft];
        C --> E[Cloud Tasks: create_task()];
    end

    subgraph Google Cloud Platform (Serverless)
        E -- HTTP Request --> F[Cloud Run Job (New Instance)];
    end

    F -- Processes Task --> G[Veo/Imagen API];
    G -- Video/Image Data --> F;
    F --> H[Firestore: Update draft to 'completed'];

    A -- Polls for updates --> B;

    style F fill:#D5F5E3,stroke:#229954
    style E fill:#E8DAEF,stroke:#884EA0
```

**Component Breakdown:**

1.  **Flask API (`phoenix` service):**
    -   The initial flow is identical: it creates a "pending" draft in Firestore.
    -   Instead of calling Celery, it will call the Google Cloud Tasks API: `tasks_client.create_task(...)`.
    -   The task payload will contain the `creation_id` and other necessary parameters.

2.  **Cloud Tasks:**
    -   A fully-managed, serverless task queue. It receives the task from our API.
    -   It guarantees at-least-once delivery and handles retries automatically.
    -   When it's time to execute, it makes a secure HTTP request to trigger a Cloud Run Job.
    -   **Cost:** Free for the first 1 million tasks per month.

3.  **Cloud Run Job (`video-generation-job`):**
    -   A new, dedicated service for video generation. It is **not** always running.
    -   An instance is created **only** when triggered by Cloud Tasks. It runs, performs its single task, and then shuts down.
    -   The job's code (`jobs/video_generation/main.py`) would read the `creation_id` from the incoming request, perform the generation, and update Firestore.
    -   **Cost:** Pay only for the CPU/memory used during execution (e.g., ~$0.003 per 2-minute video generation).

### 3.2. Technical Details & Costs

-   **Infrastructure:** 1 Cloud Run Service (main app), 1 Cloud Tasks Queue, 2 Cloud Run Jobs (one for video, one for image).
-   **Code:** `jobs/video_generation/main.py` (new), `jobs/image_generation/main.py` (new), and a modified `api/generation_routes.py`.
-   **Idle Cost:** **$0/month**.
-   **Scalability:** Virtually unlimited. If 1,000 users request a video at once, GCP will spin up 1,000 parallel Cloud Run Job instances.

### 3.3. Pros & Cons

| Pros ✅ | Cons ❌ |
| :--- | :--- |
| **Extremely Cost-Effective:** No idle costs. Pay only for what you use. | **Cold Starts:** Each job has a 2-5 second cold start. (Negligible for a 120s task). |
| **Massively Scalable:** Each task runs in its own isolated container. | **Local Development is Harder:** Cannot run Cloud Tasks/Jobs locally. Requires mocking or deploying to test. |
| **Operational Simplicity:** No Redis, no VPC, no worker service to manage. | **Less Feature-Rich than Celery:** Lacks complex workflow features like task chaining out-of-the-box. |
| **Increased Reliability:** A failing job does not affect the main app or other jobs. | **Potential for "Thundering Herd":** Requires careful rate limiting on downstream APIs (e.g., Veo). |

---

## 4. Comparative Analysis

| Feature | Current (Celery + Redis) | Proposed (Cloud Tasks + Jobs) | **Winner & Why** |
| :--- | :--- | :--- | :--- |
| **Monthly Cost** | **~$43** (fixed + variable) | **~$8** (for 1000 videos) | 🏆 **Cloud Tasks** (80%+ savings) |
| **Scalability** | Moderate (Vertical/Complex) | Massive (Horizontal/Automatic) | 🏆 **Cloud Tasks** (True serverless scaling) |
| **Complexity** | High (3 services + networking) | Low (1 service + serverless jobs) | 🏆 **Cloud Tasks** (Fewer moving parts) |
| **Reliability** | Good (Worker can crash) | Excellent (Jobs are isolated) | 🏆 **Cloud Tasks** (Better fault isolation) |
| **Local Dev** | Easy | Hard | 🏆 **Celery** (Clear winner here) |
| **Latency** | 0ms task startup | 2-5s task startup | 🏆 **Celery** (But irrelevant for our long tasks) |

---

## 5. Phased Migration Plan

We will perform a careful, phased migration to de-risk the process.

**Phase 1: Implement Video Generation with Cloud Tasks (In Parallel)**
1.  **Infrastructure Setup:** Create a new Cloud Tasks queue (`video-jobs-queue`).
2.  **Create Cloud Run Job:** Create and deploy `video-generation-job`, modeling it after the existing `reel-stitching-job`.
3.  **API Modification:** In `api.generation_routes.py`, add logic to dispatch tasks to Cloud Tasks. Use a feature flag or A/B test to route a percentage of traffic to the new system.
4.  **Monitoring:** Create a dashboard to compare the performance, cost, and reliability of both systems side-by-side.

**Phase 2: Migrate Image Generation**
1.  **Create Cloud Run Job:** Create `image-generation-job`. Since image generation is faster, we will analyze if the cold start is acceptable.
2.  **API Modification:** Update the image generation endpoint to use Cloud Tasks.

**Phase 3: Decommission Celery & Redis**
1.  **Ramp Up:** Route 100% of traffic to the new Cloud Tasks system.
2.  **Drain Stop:** Stop the `phoenix-video-worker` service and ensure no tasks are left in the Redis queue.
3.  **Infrastructure Teardown:**
    -   Delete the `phoenix-video-worker` Cloud Run service.
    -   Delete the Cloud Memorystore Redis instance.
    -   Delete the VPC Connector.
4.  **Code Cleanup:** Remove `celery`, `redis`, and `run_worker.py` from the codebase.

---

## 6. Conclusion & Recommendation

The current Celery/Redis architecture, while functional, is an operational and financial burden that is not suitable for our current scale. It was the right choice for a rapid prototype but is now holding us back.

The proposed architecture using **Cloud Tasks and Cloud Run Jobs** is a clear winner. It offers:
-   **Financial Health:** An immediate and significant reduction in monthly cloud spend.
-   **Scalability:** A future-proof system that can handle viral growth without re-architecting.
-   **Simplicity:** A leaner, more maintainable codebase with fewer infrastructure dependencies.

The primary trade-off is a more complex local development workflow, but this is a manageable challenge that is far outweighed by the production benefits.

**We strongly recommend proceeding with the phased migration plan outlined above.**
