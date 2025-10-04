/* global window, document */

(function () {
  if (window.JobProgressMonitor) {
    return;
  }

  const STATUS_CLASS_MAP = {
    VALIDATION: 'jp-status-validation',
    PREPARATION: 'jp-status-preparation',
    ANALYSIS: 'jp-status-analysis',
    STITCHING: 'jp-status-stitching',
    SUCCESS: 'jp-status-success',
    ERROR: 'jp-status-error',
    PROCESSING: 'jp-status-processing',
  };

  const STAGE_CLASS_MAP = {
    VALIDATION: 'jp-stage-validation',
    PREPARATION: 'jp-stage-preparation',
    ANALYSIS: 'jp-stage-analysis',
    STITCHING: 'jp-stage-stitching',
    ERROR: 'jp-stage-error',
  };

  const DEFAULT_REFRESH_MS = 3500;
  const RETRY_BACKOFF_MS = [3000, 5000, 8000, 13000];

  function formatTimestamp(iso) {
    if (!iso) {
      return '—';
    }
    try {
      const date = new Date(iso);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch (err) {
      return iso;
    }
  }

  function createElement(tag, className, textContent) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (textContent) el.textContent = textContent;
    return el;
  }

  class JobProgressMonitor {
    constructor({ container, fetchProgress, autoStart = true, pollInterval = DEFAULT_REFRESH_MS }) {
      this.container = container;
      this.fetchProgress = fetchProgress;
      this.pollInterval = pollInterval;
      this.retryIndex = 0;
      this.timer = null;
      this.lastUpdateAt = null;
      this.buildSkeleton();
      if (autoStart) {
        this.start();
      }
    }

    buildSkeleton() {
      this.container.classList.add('job-progress-monitor');

      const header = createElement('div', 'jp-progress-header');
      const title = createElement('div', 'jp-progress-title');
      const icon = createElement('i', 'bi bi-hurricane');
      const label = createElement('span');
      label.textContent = 'Compilation Progress';
      title.appendChild(icon);
      title.appendChild(label);

      this.statusBadge = createElement('div', 'jp-status-badge jp-status-processing');
      this.statusBadge.innerHTML = '<i class="bi bi-lightning-charge-fill"></i><span>Initializing</span>';

      header.appendChild(title);
      header.appendChild(this.statusBadge);

      const barWrapper = createElement('div', 'jp-progress-bar-wrapper');
      this.progressBar = createElement('div', 'jp-progress-bar');
      this.progressBar.textContent = '0%';
      barWrapper.appendChild(this.progressBar);

      this.logContainer = createElement('div', 'jp-log-container jp-empty');

      this.container.innerHTML = '';
      this.container.appendChild(header);
      this.container.appendChild(barWrapper);
      this.container.appendChild(this.logContainer);
    }

    updateStatus(status) {
      const normalized = (status || '').toUpperCase();
      const badgeClass = STATUS_CLASS_MAP[normalized] || STATUS_CLASS_MAP.PROCESSING;
      Object.values(STATUS_CLASS_MAP).forEach((className) => {
        this.statusBadge.classList.remove(className);
      });
      this.statusBadge.classList.add(badgeClass);

      const badgeLabel = normalized ? normalized.replace('_', ' ') : 'Processing';
      const icon = normalized === 'SUCCESS' ? 'bi-check-circle-fill' : normalized === 'ERROR' ? 'bi-exclamation-triangle-fill' : 'bi-lightning-charge-fill';
      this.statusBadge.innerHTML = `<i class="bi ${icon}"></i><span>${badgeLabel}</span>`;
    }

    updateProgress(value) {
      const clamped = Math.min(100, Math.max(0, value || 0));
      this.progressBar.style.width = `${clamped}%`;
      this.progressBar.textContent = `${Math.round(clamped)}%`;
    }

    renderLogs(logs = []) {
      this.logContainer.classList.toggle('jp-empty', logs.length === 0);
      if (logs.length === 0) {
        this.logContainer.innerHTML = '';
        return;
      }

      const fragment = document.createDocumentFragment();
      logs.forEach((entry) => {
        const stageClass = STAGE_CLASS_MAP[entry.stage?.toUpperCase?.()] || STAGE_CLASS_MAP.VALIDATION;
        const logEl = createElement('div', `jp-log-entry ${stageClass}`);

        const top = createElement('div', 'jp-log-top');
        const stage = createElement('div', 'jp-log-stage', (entry.stage || 'Stage').replace('_', ' '));
        const time = createElement('div', 'jp-log-time', formatTimestamp(entry.timestamp));
        top.appendChild(stage);
        top.appendChild(time);

        const message = createElement('div', 'jp-log-message', entry.message || 'Pending update…');

        logEl.appendChild(top);
        logEl.appendChild(message);

        if (entry.metrics && Object.keys(entry.metrics).length > 0) {
          const metricsWrap = createElement('div', 'jp-log-metrics');
          Object.entries(entry.metrics).forEach(([key, val]) => {
            const chip = createElement('span', 'jp-metric-chip');
            chip.innerHTML = `<i class="bi bi-activity"></i>${key}: <strong>${val}</strong>`;
            metricsWrap.appendChild(chip);
          });
          logEl.appendChild(metricsWrap);
        }

        fragment.prepend(logEl);
      });

      this.logContainer.innerHTML = '';
      this.logContainer.appendChild(fragment);
    }

    async poll() {
      try {
        const payload = await this.fetchProgress();
        const { progress = 0, status = 'PROCESSING', logs = [] } = payload || {};
        this.lastUpdateAt = Date.now();
        this.retryIndex = 0;

        this.updateStatus(status);
        this.updateProgress(progress);
        this.renderLogs(Array.isArray(logs) ? logs : []);

        if (status === 'SUCCESS' || status === 'ERROR') {
          this.stop();
          return;
        }
      } catch (err) {
        this.retryIndex = Math.min(this.retryIndex + 1, RETRY_BACKOFF_MS.length - 1);
        const delay = RETRY_BACKOFF_MS[this.retryIndex];
        this.statusBadge.innerHTML = `<i class="bi bi-exclamation-triangle"></i><span>Retrying in ${(delay / 1000).toFixed(0)}s</span>`;
        this.updateStatus('PROCESSING');
        this.scheduleNext(delay);
        return;
      }

      this.scheduleNext(this.pollInterval);
    }

    scheduleNext(delay) {
      this.stopTimer();
      this.timer = window.setTimeout(() => this.poll(), delay);
    }

    stopTimer() {
      if (this.timer) {
        window.clearTimeout(this.timer);
        this.timer = null;
      }
    }

    start() {
      this.stopTimer();
      this.poll();
    }

    stop() {
      this.stopTimer();
    }
  }

  window.JobProgressMonitor = JobProgressMonitor;
})();
