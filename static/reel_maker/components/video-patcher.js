/**
 * Reel Maker Video Element Patcher
 * 
 * Patches video elements created by React to use the signed URL fetching system.
 * This works with the minified React bundle without needing to rebuild.
 */

(function() {
    'use strict';

    console.log('[VideoPatcher] Initializing...');

    // Extract projectId and clipPath from the video src URL
    function parseVideoSrc(src) {
        // Expected format: /api/reel/projects/{projectId}/clips/{clipPath}
        const match = src.match(/\/api\/reel\/projects\/([^/]+)\/clips\/(.+?)(?:#|$)/);
        if (match) {
            return {
                projectId: match[1],
                clipPath: decodeURIComponent(match[2].replace(/#.*$/, '')) // Remove fragment and decode
            };
        }
        return null;
    }

    // Patch a single video element
    function patchVideoElement(video) {
        // Skip if already patched
        if (video.dataset.patched === 'true') {
            return;
        }

        const source = video.querySelector('source');
        const srcElement = source || video;
        const originalSrc = srcElement.getAttribute('src');

        if (!originalSrc || !originalSrc.includes('/api/reel/projects/')) {
            return;
        }

        console.log('[VideoPatcher] Patching video element:', originalSrc);

        const parsed = parseVideoSrc(originalSrc);
        if (!parsed) {
            console.warn('[VideoPatcher] Could not parse video src:', originalSrc);
            return;
        }

        // Add data attributes for the video-url-helper
        video.dataset.projectId = parsed.projectId;
        video.dataset.clipPath = parsed.clipPath;
        video.dataset.patched = 'true';

        // Clear the src to prevent 401 errors
        if (source) {
            source.removeAttribute('src');
        } else {
            video.removeAttribute('src');
        }

        // Initialize with signed URL
        if (window.ReelMakerVideoHelper) {
            window.ReelMakerVideoHelper.initializeVideoElement(video, parsed.projectId, parsed.clipPath);
        } else {
            console.error('[VideoPatcher] ReelMakerVideoHelper not loaded!');
        }
    }

    // Patch all video elements
    function patchAllVideos() {
        const videos = document.querySelectorAll('video');
        let patchedCount = 0;

        videos.forEach(video => {
            if (video.dataset.patched !== 'true') {
                patchVideoElement(video);
                patchedCount++;
            }
        });

        if (patchedCount > 0) {
            console.log(`[VideoPatcher] Patched ${patchedCount} video elements`);
        }
    }

    // Watch for new video elements added by React
    const observer = new MutationObserver((mutations) => {
        let hasNewVideos = false;

        mutations.forEach(mutation => {
            mutation.addedNodes.forEach(node => {
                if (node.nodeType === 1) { // Element node
                    if (node.tagName === 'VIDEO') {
                        hasNewVideos = true;
                        patchVideoElement(node);
                    } else if (node.querySelector) {
                        const videos = node.querySelectorAll('video');
                        if (videos.length > 0) {
                            hasNewVideos = true;
                            videos.forEach(patchVideoElement);
                        }
                    }
                }
            });
        });

        if (hasNewVideos) {
            console.log('[VideoPatcher] Detected new video elements');
        }
    });

    // Start observing
    if (document.body) {
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        console.log('[VideoPatcher] Observer started');
    } else {
        document.addEventListener('DOMContentLoaded', () => {
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
            console.log('[VideoPatcher] Observer started (after DOMContentLoaded)');
        });
    }

    // Initial patch
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', patchAllVideos);
    } else {
        patchAllVideos();
    }

    // Periodic check (in case mutations are missed)
    setInterval(patchAllVideos, 2000);

    console.log('[VideoPatcher] Initialized');
})();
