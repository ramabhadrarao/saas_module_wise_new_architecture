/**
 * Plugin management functionality
 */

// Initialize plugin components
document.addEventListener('DOMContentLoaded', function() {
    // JSON editor validation
    const configEditors = document.querySelectorAll('.json-editor');
    if (configEditors) {
        configEditors.forEach(editor => {
            editor.addEventListener('blur', function() {
                try {
                    JSON.parse(this.value);
                    this.classList.remove('is-invalid');
                    const errorElement = this.nextElementSibling;
                    if (errorElement && errorElement.classList.contains('invalid-feedback')) {
                        errorElement.textContent = '';
                    }
                } catch (e) {
                    this.classList.add('is-invalid');
                    const errorElement = this.nextElementSibling;
                    if (errorElement && errorElement.classList.contains('invalid-feedback')) {
                        errorElement.textContent = 'Invalid JSON: ' + e.message;
                    }
                }
            });
        });
    }
    
    // Plugin activation confirmation
    const activateForms = document.querySelectorAll('.activate-plugin-form');
    if (activateForms) {
        activateForms.forEach(form => {
            form.addEventListener('submit', function(e) {
                if (!confirm('Are you sure you want to activate this plugin?')) {
                    e.preventDefault();
                    return false;
                }
            });
        });
    }
    
    // Plugin deactivation confirmation
    const deactivateForms = document.querySelectorAll('.deactivate-plugin-form');
    if (deactivateForms) {
        deactivateForms.forEach(form => {
            form.addEventListener('submit', function(e) {
                if (!confirm('Are you sure you want to deactivate this plugin? This may disrupt services that depend on it.')) {
                    e.preventDefault();
                    return false;
                }
            });
        });
    }
    
    // Format JSON in config displays
    const configDisplays = document.querySelectorAll('.config-display pre');
    configDisplays.forEach(display => {
        try {
            const content = display.textContent;
            const json = JSON.parse(content);
            display.textContent = JSON.stringify(json, null, 2);
        } catch (e) {
            console.error('Error formatting JSON:', e);
        }
    });
    
    // Plugin install/uninstall API
    const pluginApiButtons = document.querySelectorAll('[data-plugin-api]');
    if (pluginApiButtons) {
        pluginApiButtons.forEach(button => {
            button.addEventListener('click', async function(e) {
                e.preventDefault();
                
                const action = this.dataset.pluginApi;
                const slug = this.dataset.pluginSlug;
                const url = this.dataset.apiUrl;
                const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
                
                if (!url || !csrfToken) {
                    console.error('Missing URL or CSRF token');
                    return;
                }
                
                try {
                    const response = await fetch(url, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': csrfToken
                        },
                        body: JSON.stringify({ action: action })
                    });
                    
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        app.showNotification(data.message, 'success');
                        // Reload after short delay
                        setTimeout(() => {
                            window.location.reload();
                        }, 1000);
                    } else {
                        app.showNotification(data.message, 'danger');
                    }
                } catch (error) {
                    console.error('API Error:', error);
                    app.showNotification('An error occurred while processing your request', 'danger');
                }
            });
        });
    }
});