/* global window, document, fetch, JobProgressMonitor */

(function () {
  const DATA_ATTR_PROJECT = 'data-project-id';
  const DATA_ATTR_JOB = 'data-job-id';

  function waitForJobId(container) {
    return new Promise((resolve) => {
      const existing = container.getAttribute(DATA_ATTR_JOB);
      if (existing) {
        resolve(existing);
        return;
      }

      const observer = new MutationObserver(() => {
        const val = container.getAttribute(DATA_ATTR_JOB);
        if (val) {
          observer.disconnect();
          resolve(val);
        }
      });
      observer.observe(container, { attributes: true });
    });
  }

  async function initMonitor(container) {
    const projectId = container.getAttribute(DATA_ATTR_PROJECT);
    if (!projectId) {
      // eslint-disable-next-line no-console
      console.warn('[ProgressMonitor] Missing project id, skipping initialization.');
      return;
    }

    const jobId = await waitForJobId(container);
    const endpoint = `/api/reel/projects/${projectId}/jobs/${jobId}/progress`;

    // eslint-disable-next-line no-console
    console.info('[ProgressMonitor] Starting stitching poller', {
      projectId,
      jobId,
      endpoint,
      method: 'GET',
      credentials: 'same-origin',
    });

    const fallback = container.parentElement?.querySelector('.stitch-panel__processing');
    if (fallback) {
      fallback.style.display = 'none';
    }

    const monitor = new window.JobProgressMonitor({
      container,
      fetchProgress: async () => {
        const response = await fetch(endpoint, { credentials: 'same-origin' });
        if (!response.ok) {
          throw new Error(`Failed to load progress (${response.status})`);
        }
        const payload = await response.json();
        // eslint-disable-next-line no-console
        console.debug('[ProgressMonitor] Progress payload', payload);
        return payload;
      },
    });

    return monitor;
  }

  function bootstrap() {
    const container = document.querySelector('#job-progress-monitor-container');
    if (!container) {
      return;
    }

    if (!window.JobProgressMonitor) {
      // eslint-disable-next-line no-console
      console.error('[ProgressMonitor] JobProgressMonitor not found. Ensure JobProgressMonitor.js is loaded.');
      return;
    }

    initMonitor(container).catch((err) => {
      // eslint-disable-next-line no-console
      console.error('[ProgressMonitor] Initialization failed:', err);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootstrap);
  } else {
    bootstrap();
  }
})();
