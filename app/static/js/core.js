/**
 * Core functionality for Multi-Tenant SaaS Platform
 */

// Helper function to show notifications
function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show`;
    notification.setAttribute('role', 'alert');
    
    notification.innerHTML = `
        ${message}
        <a href="#" class="btn-close" data-bs-dismiss="alert" aria-label="close"></a>
    `;
    
    // Add to notification container
    const container = document.querySelector('.container-xl');
    if (container) {
        container.insertBefore(notification, container.firstChild);
    }
    
    // Auto dismiss after 5 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 150);
    }, 5000);
}

// CSRF token handling for AJAX requests
function setupCSRF() {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    if (csrfToken) {
        // Add CSRF token to all AJAX requests
        const originalOpen = XMLHttpRequest.prototype.open;
        XMLHttpRequest.prototype.open = function() {
            originalOpen.apply(this, arguments);
            this.setRequestHeader('X-CSRFToken', csrfToken);
        };
        
        // Also handle fetch API
        const originalFetch = window.fetch;
        window.fetch = function(resource, init) {
            if (init && init.method && ['POST', 'PUT', 'DELETE', 'PATCH'].includes(init.method.toUpperCase())) {
                init = init || {};
                init.headers = init.headers || {};
                
                if (!(init.headers instanceof Headers)) {
                    init.headers['X-CSRFToken'] = csrfToken;
                } else {
                    init.headers.append('X-CSRFToken', csrfToken);
                }
            }
            
            return originalFetch.call(this, resource, init);
        };
    }
}

// Initialize on document ready
document.addEventListener('DOMContentLoaded', function() {
    // Setup CSRF protection for AJAX
    setupCSRF();
    
    // Enable tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Enable popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Add current year to footers
    document.querySelectorAll('.current-year').forEach(el => {
        el.textContent = new Date().getFullYear();
    });
    
    console.log('Core infrastructure module initialized');
});

// Utility function for API requests
async function apiRequest(url, method = 'GET', data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    };
    
    if (data && (method !== 'GET' && method !== 'HEAD')) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(url, options);
        const responseData = await response.json();
        
        if (!response.ok) {
            throw new Error(responseData.message || 'API request failed');
        }
        
        return responseData;
    } catch (error) {
        console.error('API Request Error:', error);
        showNotification(error.message, 'danger');
        throw error;
    }
}

// Export utility functions
window.app = {
    showNotification,
    apiRequest
};