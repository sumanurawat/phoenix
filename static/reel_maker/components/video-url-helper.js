/**
 * Reel Maker Video URL Helper
 * 
 * Handles fetching signed URLs for video clips from the authenticated API endpoint.
 * This is necessary because <video> tags don't send session cookies by default.
 */

(function() {
    'use strict';

    // Cache for signed URLs (keyed by clip path)
    const signedUrlCache = new Map();
    const CACHE_DURATION_MS = 1.5 * 60 * 60 * 1000; // 1.5 hours (signed URLs expire at 2 hours)

    /**
     * Fetch a signed URL for a given clip path
     * @param {string} projectId - The project ID
     * @param {string} clipPath - The relative path to the clip in GCS
     * @returns {Promise<string>} The signed URL
     */
    async function fetchSignedUrl(projectId, clipPath) {
        const cacheKey = `${projectId}:${clipPath}`;
        
        // Check cache first
        const cached = signedUrlCache.get(cacheKey);
        if (cached && Date.now() - cached.timestamp < CACHE_DURATION_MS) {
            console.log('[VideoURLHelper] Using cached signed URL for', clipPath);
            return cached.url;
        }

        // Fetch new signed URL
        console.log('[VideoURLHelper] Fetching signed URL for', clipPath);
        const response = await fetch(`/api/reel/projects/${projectId}/clips/${clipPath}`, {
            method: 'GET',
            credentials: 'same-origin', // Include session cookies
            headers: {
                'Accept': 'application/json'
            }
        });

        if (!response.ok) {
            // Handle authentication failures specially
            if (response.status === 401) {
                console.error('[VideoURLHelper] Authentication required - session may have expired');
                
                // Try to parse error response
                try {
                    const errorData = await response.json();
                    if (errorData.redirect) {
                        console.error('[VideoURLHelper] Redirecting to login...');
                        // Show user-friendly message before redirecting
                        if (!window.__authAlertShown) {
                            window.__authAlertShown = true;
                            alert('Your session has expired. Please log in again.');
                            window.location.href = errorData.redirect;
                        }
                        throw new Error('Authentication required');
                    }
                } catch (jsonError) {
                    // If not JSON, try text
                    const errorText = await response.text();
                    console.error('[VideoURLHelper] Auth error details:', errorText);
                }
                
                throw new Error('Authentication required - please refresh the page and log in again');
            }
            
            const errorText = await response.text();
            console.error('[VideoURLHelper] Failed to fetch signed URL:', response.status, errorText);
            throw new Error(`Failed to fetch video URL: ${response.status}`);
        }

        const data = await response.json();
        
        if (!data.success || !data.url) {
            console.error('[VideoURLHelper] Invalid response:', data);
            throw new Error(data.error?.message || 'Failed to get video URL');
        }

        // Cache the signed URL
        signedUrlCache.set(cacheKey, {
            url: data.url,
            timestamp: Date.now()
        });

        console.log('[VideoURLHelper] Successfully fetched signed URL for', clipPath);
        return data.url;
    }

    /**
     * Initialize a video element with a signed URL
     * @param {HTMLVideoElement} videoElement - The video element
     * @param {string} projectId - The project ID
     * @param {string} clipPath - The relative path to the clip
     */
    async function initializeVideoElement(videoElement, projectId, clipPath) {
        try {
            // Show loading state
            videoElement.poster = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><text x="50%" y="50%" text-anchor="middle" fill="%23888">Loading...</text></svg>';
            
            const signedUrl = await fetchSignedUrl(projectId, clipPath);
            
            // Set the signed URL on the video source
            const source = videoElement.querySelector('source');
            if (source) {
                source.src = signedUrl + '#t=0.1';
                videoElement.load(); // Reload the video with new source
            } else {
                // If no source element, set directly
                videoElement.src = signedUrl + '#t=0.1';
            }
            
            console.log('[VideoURLHelper] Video element initialized for', clipPath);
        } catch (error) {
            console.error('[VideoURLHelper] Failed to initialize video element:', error);
            videoElement.poster = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><text x="50%" y="50%" text-anchor="middle" fill="%23f00">Failed to load</text></svg>';
        }
    }

    /**
     * Auto-initialize all video elements with data-project-id and data-clip-path attributes
     */
    function autoInitializeVideos() {
        const videos = document.querySelectorAll('video[data-project-id][data-clip-path]');
        console.log(`[VideoURLHelper] Auto-initializing ${videos.length} video elements`);
        
        videos.forEach(video => {
            const projectId = video.dataset.projectId;
            const clipPath = video.dataset.clipPath;
            
            if (!projectId || !clipPath) {
                console.warn('[VideoURLHelper] Video element missing required data attributes', video);
                return;
            }
            
            initializeVideoElement(video, projectId, clipPath);
        });
    }

    // Export to global scope
    window.ReelMakerVideoHelper = {
        fetchSignedUrl,
        initializeVideoElement,
        autoInitializeVideos,
        clearCache: () => signedUrlCache.clear()
    };

    // Auto-initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', autoInitializeVideos);
    } else {
        autoInitializeVideos();
    }

    // Auto-initialize when new content is added (for React/dynamic content)
    const observer = new MutationObserver((mutations) => {
        let hasNewVideos = false;
        mutations.forEach(mutation => {
            mutation.addedNodes.forEach(node => {
                if (node.nodeType === 1) { // Element node
                    if (node.tagName === 'VIDEO' || node.querySelector('video[data-project-id][data-clip-path]')) {
                        hasNewVideos = true;
                    }
                }
            });
        });
        
        if (hasNewVideos) {
            console.log('[VideoURLHelper] Detected new video elements, initializing...');
            setTimeout(autoInitializeVideos, 100); // Small delay to let React finish rendering
        }
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

    console.log('[VideoURLHelper] Initialized');
})();
