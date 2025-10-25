/**
 * Image Generator Frontend Logic
 * Handles image generation, preview, download, and history
 */

(function() {
    'use strict';

    // State management
    let currentImage = null;
    let csrfToken = null;

    // DOM elements
    const promptInput = document.getElementById('promptInput');
    const charCount = document.getElementById('charCount');
    const generateBtn = document.getElementById('generateBtn');
    const downloadBtn = document.getElementById('downloadBtn');
    const publishBtn = document.getElementById('publishBtn');
    const discardBtn = document.getElementById('discardBtn');
    const refreshHistoryBtn = document.getElementById('refreshHistoryBtn');

    // State containers
    const placeholderState = document.getElementById('placeholderState');
    const loadingState = document.getElementById('loadingState');
    const imagePreviewState = document.getElementById('imagePreviewState');
    const errorState = document.getElementById('errorState');

    // Image elements
    const generatedImage = document.getElementById('generatedImage');
    const imageId = document.getElementById('imageId');
    const genTime = document.getElementById('genTime');
    const usedPrompt = document.getElementById('usedPrompt');
    const errorMessage = document.getElementById('errorMessage');

    // History
    const historyContainer = document.getElementById('historyContainer');

    /**
     * Initialize the application
     */
    function init() {
        console.log('Initializing Image Generator...');
        
        // Get CSRF token from meta tag or header
        csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || 
                    document.querySelector('[name="X-CSRF-Token"]')?.content;
        
        if (!csrfToken) {
            console.warn('CSRF token not found - API calls may fail');
        }

        // Setup event listeners
        setupEventListeners();
        
        // Load history
        loadHistory();
        
        console.log('Image Generator initialized');
    }

    /**
     * Setup all event listeners
     */
    function setupEventListeners() {
        // Prompt character counter
        promptInput.addEventListener('input', () => {
            const length = promptInput.value.length;
            charCount.textContent = length;
            
            // Visual feedback for character limits
            if (length > 4500) {
                charCount.classList.add('text-warning');
            } else {
                charCount.classList.remove('text-warning');
            }
        });

        // Generate button
        generateBtn.addEventListener('click', handleGenerate);

        // Action buttons
        downloadBtn.addEventListener('click', handleDownload);
        publishBtn.addEventListener('click', handlePublish);
        discardBtn.addEventListener('click', handleDiscard);

        // History refresh
        refreshHistoryBtn.addEventListener('click', loadHistory);

        // Enter key to generate (with Ctrl/Cmd modifier)
        promptInput.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                handleGenerate();
            }
        });
    }

    /**
     * Handle image generation
     */
    async function handleGenerate() {
        const prompt = promptInput.value.trim();

        // Validation
        if (!prompt) {
            showError('Please enter a prompt');
            return;
        }

        if (prompt.length < 3) {
            showError('Prompt is too short (minimum 3 characters)');
            return;
        }

        // Show loading state
        showLoadingState();
        generateBtn.disabled = true;

        console.log('Generating image with prompt:', prompt);

        try {
            const response = await fetch('/api/image/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': csrfToken
                },
                body: JSON.stringify({
                    prompt: prompt,
                    save_to_firestore: true
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            if (!data.success) {
                throw new Error(data.error || 'Generation failed');
            }

            console.log('Image generated successfully:', data);

            // Store current image data
            currentImage = data.image;

            // Display the image
            displayImage(data.image);

            // Reload history
            loadHistory();

        } catch (error) {
            console.error('Generation error:', error);
            showError(error.message || 'Failed to generate image. Please try again.');
        } finally {
            generateBtn.disabled = false;
        }
    }

    /**
     * Display generated image
     */
    function displayImage(imageData) {
        console.log('Displaying image:', imageData);

        // Update image source
        generatedImage.src = imageData.image_url;
        
        // Update metadata
        imageId.textContent = imageData.image_id.substring(0, 8) + '...';
        genTime.textContent = `${imageData.generation_time_seconds.toFixed(2)}s`;
        usedPrompt.textContent = imageData.prompt;

        // Show preview state
        showPreviewState();
    }

    /**
     * Handle image download
     */
    async function handleDownload() {
        if (!currentImage) {
            console.error('No image to download');
            return;
        }

        console.log('Downloading image:', currentImage.image_id);

        try {
            // Create download link
            const link = document.createElement('a');
            link.href = currentImage.image_url;
            link.download = `phoenix-image-${currentImage.image_id}.png`;
            
            // Trigger download
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            console.log('Download initiated');

            // Show success feedback
            const originalText = downloadBtn.innerHTML;
            downloadBtn.innerHTML = '<i class="fas fa-check"></i> Downloaded!';
            downloadBtn.classList.add('btn-success');
            
            setTimeout(() => {
                downloadBtn.innerHTML = originalText;
                downloadBtn.classList.remove('btn-success');
            }, 2000);

        } catch (error) {
            console.error('Download error:', error);
            showError('Failed to download image');
        }
    }

    /**
     * Handle publish (placeholder for future implementation)
     */
    function handlePublish() {
        if (!currentImage) return;
        
        // TODO: Implement publish to social media
        alert('Publish feature coming soon!\n\nThis will allow you to:\n- Post to Instagram\n- Share to other platforms\n- Add captions and hashtags');
    }

    /**
     * Handle discard
     */
    function handleDiscard() {
        if (!currentImage) return;

        // Confirm discard
        if (confirm('Are you sure you want to discard this image?')) {
            console.log('Discarding image:', currentImage.image_id);
            
            currentImage = null;
            showPlaceholderState();
            
            // Optional: Clear prompt
            // promptInput.value = '';
            // charCount.textContent = '0';
        }
    }

    /**
     * Load image history
     */
    async function loadHistory() {
        console.log('Loading image history...');

        try {
            const response = await fetch('/api/image/history?limit=6');
            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || 'Failed to load history');
            }

            console.log('History loaded:', data.images.length, 'images');

            displayHistory(data.images);

        } catch (error) {
            console.error('History load error:', error);
            historyContainer.innerHTML = `
                <p class="text-danger text-center py-3 mb-0">
                    <i class="fas fa-exclamation-circle"></i> 
                    Failed to load history
                </p>
            `;
        }
    }

    /**
     * Display image history
     */
    function displayHistory(images) {
        if (!images || images.length === 0) {
            historyContainer.innerHTML = `
                <p class="text-muted text-center py-3 mb-0">
                    <i class="fas fa-info-circle"></i> 
                    No generations yet. Create your first image!
                </p>
            `;
            return;
        }

        // Create grid of thumbnails
        const grid = document.createElement('div');
        grid.className = 'row g-3';

        images.forEach(img => {
            const col = document.createElement('div');
            col.className = 'col-6 col-md-4 col-lg-2';
            
            col.innerHTML = `
                <div class="card bg-dark border-secondary h-100" style="cursor: pointer;">
                    <img src="${img.image_url}" class="card-img-top" alt="Generated image" 
                         style="aspect-ratio: 9/16; object-fit: cover;">
                    <div class="card-body p-2">
                        <p class="small text-muted mb-0 text-truncate" title="${img.prompt}">
                            ${img.prompt.substring(0, 30)}...
                        </p>
                        <small class="text-muted">${img.generation_time_seconds.toFixed(1)}s</small>
                    </div>
                </div>
            `;

            // Click to preview
            col.addEventListener('click', () => {
                currentImage = img;
                displayImage(img);
                
                // Scroll to top
                window.scrollTo({ top: 0, behavior: 'smooth' });
            });

            grid.appendChild(col);
        });

        historyContainer.innerHTML = '';
        historyContainer.appendChild(grid);
    }

    /**
     * State management functions
     */
    function showPlaceholderState() {
        placeholderState.style.display = 'block';
        loadingState.style.display = 'none';
        imagePreviewState.style.display = 'none';
        errorState.style.display = 'none';
    }

    function showLoadingState() {
        placeholderState.style.display = 'none';
        loadingState.style.display = 'block';
        imagePreviewState.style.display = 'none';
        errorState.style.display = 'none';
    }

    function showPreviewState() {
        placeholderState.style.display = 'none';
        loadingState.style.display = 'none';
        imagePreviewState.style.display = 'block';
        errorState.style.display = 'none';
    }

    function showError(message) {
        console.error('Showing error:', message);
        
        errorMessage.textContent = message;
        errorState.style.display = 'block';
        
        placeholderState.style.display = 'none';
        loadingState.style.display = 'none';
        imagePreviewState.style.display = 'none';

        // Auto-hide error after 5 seconds
        setTimeout(() => {
            errorState.style.display = 'none';
            showPlaceholderState();
        }, 5000);
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
