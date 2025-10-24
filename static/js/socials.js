/**
 * Social Media Timeline - Frontend JavaScript
 * Handles account management and timeline display
 */

class SocialsManager {
    constructor() {
        this.accounts = [];
        this.init();
    }
    
    init() {
        console.log('SocialsManager initialized');
        this.bindEvents();
        this.checkOAuthCallback();
        this.loadAccounts();
    }
    
    checkOAuthCallback() {
        // Check for OAuth success/error in URL params
        const urlParams = new URLSearchParams(window.location.search);
        const connected = urlParams.get('connected');
        const username = urlParams.get('username');
        const error = urlParams.get('error');
        const errorMessage = urlParams.get('error_description') || urlParams.get('message');
        
        if (connected) {
            this.showSuccess(`Successfully connected ${connected} account${username ? ` @${username}` : ''}!`);
            // Clean URL
            window.history.replaceState({}, document.title, window.location.pathname);
        } else if (error) {
            this.showError(errorMessage || `Failed to connect account: ${error}`);
            // Clean URL
            window.history.replaceState({}, document.title, window.location.pathname);
        }
    }
    
    bindEvents() {
        // Add account button (empty state)
        const addBtn = document.getElementById('add-account-btn');
        if (addBtn) {
            addBtn.addEventListener('click', () => {
                this.showAddAccountModal();
            });
        }
        
        // Add another account button
        const addAnotherBtn = document.getElementById('add-another-btn');
        if (addAnotherBtn) {
            addAnotherBtn.addEventListener('click', () => {
                this.showAddAccountModal();
            });
        }
        
        // Save account button (will be fully implemented in Phase 3)
        const saveBtn = document.getElementById('save-account-btn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                this.saveAccount();
            });
        }
    }
    
    showAddAccountModal() {
        const modal = new bootstrap.Modal(document.getElementById('addAccountModal'));
        modal.show();
        
        // Add OAuth button listeners
        this.bindOAuthButtons();
    }
    
    bindOAuthButtons() {
        // Instagram OAuth button
        const instagramOAuthBtn = document.getElementById('instagram-oauth-btn');
        if (instagramOAuthBtn) {
            instagramOAuthBtn.replaceWith(instagramOAuthBtn.cloneNode(true));
            const newBtn = document.getElementById('instagram-oauth-btn');
            newBtn.addEventListener('click', () => {
                this.initiateOAuth('instagram');
            });
        }
        
        // Add similar handlers for YouTube and Twitter when implemented
    }
    
    async initiateOAuth(platform) {
        try {
            // Get CSRF token
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
            
            // Request OAuth URL from backend
            const response = await fetch(`/api/socials/connect/${platform}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Close the add account modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('addAccountModal'));
                modal.hide();
                
                // Open OAuth popup or redirect
                const authWindow = window.open(
                    data.authorization_url,
                    `${platform}_oauth`,
                    'width=600,height=700,left=200,top=100'
                );
                
                // Check if popup was blocked
                if (!authWindow || authWindow.closed || typeof authWindow.closed === 'undefined') {
                    // Popup blocked, redirect in same window
                    window.location.href = data.authorization_url;
                } else {
                    // Poll for popup close (OAuth callback will handle the redirect)
                    const pollTimer = setInterval(() => {
                        if (authWindow.closed) {
                            clearInterval(pollTimer);
                            // Reload accounts after OAuth completes
                            this.loadAccounts();
                        }
                    }, 500);
                }
            } else {
                this.showError(data.error || `Failed to connect ${platform}`);
            }
        } catch (error) {
            console.error(`Error initiating ${platform} OAuth:`, error);
            this.showError(`Failed to connect ${platform}. Please try again.`);
        }
    }
    
    async loadAccounts() {
        const emptyState = document.getElementById('empty-state');
        const accountsSection = document.getElementById('accounts-section');
        const loadingState = document.getElementById('loading-state');
        
        try {
            // Show loading
            if (emptyState) emptyState.classList.add('d-none');
            if (accountsSection) accountsSection.classList.add('d-none');
            if (loadingState) loadingState.classList.remove('d-none');
            
            const response = await fetch('/api/socials/accounts');
            const data = await response.json();
            
            // Hide loading
            if (loadingState) loadingState.classList.add('d-none');
            
            if (data.success) {
                this.accounts = data.accounts || [];
                this.renderAccounts();
            } else {
                console.error('Failed to load accounts:', data.error);
                if (emptyState) emptyState.classList.remove('d-none');
            }
        } catch (error) {
            console.error('Error loading accounts:', error);
            if (loadingState) loadingState.classList.add('d-none');
            if (emptyState) emptyState.classList.remove('d-none');
        }
    }
    
    renderAccounts() {
        const emptyState = document.getElementById('empty-state');
        const accountsSection = document.getElementById('accounts-section');
        const accountsList = document.getElementById('accounts-list');
        
        if (this.accounts.length === 0) {
            if (emptyState) emptyState.classList.remove('d-none');
            if (accountsSection) accountsSection.classList.add('d-none');
            return;
        }
        
        if (emptyState) emptyState.classList.add('d-none');
        if (accountsSection) accountsSection.classList.remove('d-none');
        
        if (!accountsList) return;
        
        accountsList.innerHTML = this.accounts.map(account => this.renderAccountCard(account)).join('');
        
        // Bind remove buttons
        this.accounts.forEach(account => {
            const removeBtn = document.getElementById(`remove-${account.id}`);
            if (removeBtn) {
                removeBtn.addEventListener('click', () => {
                    this.removeAccount(account.id);
                });
            }
            
            // Bind sync button
            const syncBtn = document.getElementById(`sync-${account.id}`);
            if (syncBtn) {
                syncBtn.addEventListener('click', () => {
                    this.syncAccount(account.id);
                });
            }
        });
    }
    
    renderAccountCard(account) {
        const platformIcons = {
            instagram: 'fab fa-instagram',
            youtube: 'fab fa-youtube',
            twitter: 'fab fa-twitter'
        };
        
        const platformColors = {
            instagram: 'instagram',
            youtube: 'youtube',
            twitter: 'twitter'
        };
        
        const platformName = account.platform.charAt(0).toUpperCase() + account.platform.slice(1);
        const connectedDate = new Date(account.connected_at._seconds * 1000 || account.connected_at).toLocaleDateString();
        const lastSync = account.last_sync ? 
            new Date(account.last_sync._seconds * 1000 || account.last_sync).toLocaleDateString() : 
            'Never';
        const postsCount = account.posts_count || 0;
        
        return `
            <div class="account-card d-flex justify-content-between align-items-center">
                <div class="d-flex align-items-center">
                    <div class="platform-icon ${platformColors[account.platform]} me-3">
                        <i class="${platformIcons[account.platform]} fa-lg"></i>
                    </div>
                    <div>
                        <h6 class="mb-1">${platformName}</h6>
                        <div class="d-flex align-items-center gap-2">
                            <small class="text-muted">${account.display_name}</small>
                            <span class="badge bg-secondary">${account.account_type}</span>
                        </div>
                        <small class="text-muted">Connected: ${connectedDate}</small>
                        ${postsCount > 0 ? `<br><small class="text-muted">${postsCount} posts · Last sync: ${lastSync}</small>` : ''}
                    </div>
                </div>
                <div class="d-flex align-items-center gap-2">
                    <span class="badge bg-success">Active</span>
                    <button class="btn btn-outline-primary btn-sm" id="sync-${account.id}" title="Sync posts">
                        <i class="fas fa-sync-alt"></i>
                    </button>
                    <button class="btn btn-outline-danger btn-sm" id="remove-${account.id}" title="Remove account">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
    }
    
    async saveAccount() {
        const form = document.getElementById('add-account-form');
        const formData = new FormData(form);
        
        const accountData = {
            platform: formData.get('platform'),
            username: formData.get('username')
        };
        
        // Basic validation
        if (!accountData.platform || !accountData.username) {
            this.showError('Please fill in all fields');
            return;
        }
        
        try {
            // Get CSRF token
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
            
            const response = await fetch('/api/socials/accounts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(accountData)
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('addAccountModal'));
                modal.hide();
                
                // Reset form
                form.reset();
                
                // Reload accounts
                await this.loadAccounts();
                
                this.showSuccess(data.message || 'Account added successfully!');
            } else {
                this.showError(data.error || 'Failed to add account');
            }
        } catch (error) {
            console.error('Error saving account:', error);
            this.showError('Failed to add account. Please try again.');
        }
    }
    
    async removeAccount(accountId) {
        if (!confirm('Are you sure you want to remove this account?')) {
            return;
        }
        
        try {
            // Get CSRF token
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
            
            const response = await fetch(`/api/socials/accounts/${accountId}`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': csrfToken
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Reload accounts
                await this.loadAccounts();
                this.showSuccess('Account removed successfully');
            } else {
                this.showError(data.error || 'Failed to remove account');
            }
        } catch (error) {
            console.error('Error removing account:', error);
            this.showError('Failed to remove account. Please try again.');
        }
    }
    
    async syncAccount(accountId) {
        try {
            const syncBtn = document.getElementById(`sync-${accountId}`);
            const originalIcon = syncBtn ? syncBtn.innerHTML : '';
            
            // Show loading state
            if (syncBtn) {
                syncBtn.disabled = true;
                syncBtn.innerHTML = '<i class="fas fa-sync-alt fa-spin"></i>';
            }
            
            this.showToast('Syncing posts... This may take a few moments', 'info');
            
            // Get CSRF token
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
            
            const response = await fetch(`/api/socials/accounts/${accountId}/sync`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    max_posts: 12  // Fetch last 12 posts
                })
            });
            
            const data = await response.json();
            
            // Restore button state
            if (syncBtn) {
                syncBtn.disabled = false;
                syncBtn.innerHTML = originalIcon;
            }
            
            if (data.success) {
                const postsCount = data.posts_fetched || 0;
                this.showSuccess(`Synced ${postsCount} post${postsCount !== 1 ? 's' : ''} successfully`);
                // Reload accounts to show updated post count
                await this.loadAccounts();
            } else {
                this.showError(data.error || 'Failed to sync posts');
            }
        } catch (error) {
            console.error('Error syncing account:', error);
            this.showError('Failed to sync posts. Please try again.');
            
            // Restore button
            const syncBtn = document.getElementById(`sync-${accountId}`);
            if (syncBtn) {
                syncBtn.disabled = false;
                syncBtn.innerHTML = '<i class="fas fa-sync-alt"></i>';
            }
        }
    }
    
    showSuccess(message) {
        // Create toast notification
        this.showToast(message, 'success');
    }
    
    showError(message) {
        // Create toast notification
        this.showToast(message, 'danger');
    }
    
    showToast(message, type = 'info') {
        // Simple toast notification
        const toastHtml = `
            <div class="toast align-items-center text-white bg-${type} border-0" role="alert" style="position: fixed; top: 20px; right: 20px; z-index: 9999;">
                <div class="d-flex">
                    <div class="toast-body">
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;
        
        const toastContainer = document.createElement('div');
        toastContainer.innerHTML = toastHtml;
        document.body.appendChild(toastContainer);
        
        const toastElement = toastContainer.querySelector('.toast');
        const toast = new bootstrap.Toast(toastElement, { delay: 3000 });
        toast.show();
        
        // Remove from DOM after hidden
        toastElement.addEventListener('hidden.bs.toast', () => {
            document.body.removeChild(toastContainer);
        });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.socialsManager = new SocialsManager();
});
