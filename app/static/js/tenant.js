/**
 * Tenant Management functionality
 */

// Initialize tenant management components
document.addEventListener('DOMContentLoaded', function() {
    // Handle tenant deletion confirmation
    const deleteForms = document.querySelectorAll('.delete-form');
    if (deleteForms) {
        deleteForms.forEach(form => {
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                const message = this.dataset.confirm || 'Are you sure you want to delete this tenant?';
                
                if (confirm(message)) {
                    this.submit();
                }
            });
        });
    }
    
    // Form validation for tenant creation/editing
    const tenantForms = document.querySelectorAll('form[action*="/tenant/"]');
    if (tenantForms) {
        tenantForms.forEach(form => {
            form.addEventListener('submit', function(e) {
                const nameInput = this.querySelector('input[name="name"]');
                const emailInput = this.querySelector('input[name="owner_email"]');
                
                if (nameInput && !nameInput.value.trim()) {
                    e.preventDefault();
                    alert('Tenant name is required');
                    nameInput.focus();
                    return false;
                }
                
                if (emailInput && emailInput.value.trim() && !isValidEmail(emailInput.value.trim())) {
                    e.preventDefault();
                    alert('Please enter a valid email address');
                    emailInput.focus();
                    return false;
                }
            });
        });
    }
    
    // Domain validation for tenant domains
    const domainInput = document.querySelector('input[name="domain"]');
    if (domainInput) {
        domainInput.addEventListener('blur', function() {
            const value = this.value.trim();
            if (value && !isValidDomain(value)) {
                this.classList.add('is-invalid');
                const feedback = document.createElement('div');
                feedback.className = 'invalid-feedback';
                feedback.textContent = 'Please enter a valid domain (e.g., example.com)';
                
                // Remove any existing feedback
                const existingFeedback = this.nextElementSibling;
                if (existingFeedback && existingFeedback.classList.contains('invalid-feedback')) {
                    existingFeedback.remove();
                }
                
                this.parentNode.appendChild(feedback);
            } else {
                this.classList.remove('is-invalid');
                const existingFeedback = this.nextElementSibling;
                if (existingFeedback && existingFeedback.classList.contains('invalid-feedback')) {
                    existingFeedback.remove();
                }
            }
        });
    }
    
    // Helper function to validate email
    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
    
    // Helper function to validate domain
    function isValidDomain(domain) {
        const domainRegex = /^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9](?:\.[a-zA-Z]{2,})+$/;
        return domainRegex.test(domain);
    }
    
    // Initialize quota charts if present on the page
    initializeQuotaCharts();
});

// Initialize quota charts
function initializeQuotaCharts() {
    // Check if we're on the quota page
    const quotaContainer = document.querySelector('.tenant-quota-charts');
    if (!quotaContainer) return;
    
    // Get tenant data from the page
    const usersPercentage = parseInt(quotaContainer.dataset.usersPercentage || '0');
    const storagePercentage = parseInt(quotaContainer.dataset.storagePercentage || '0');
    
    // Create user quota chart
    createRadialChart('users-chart', usersPercentage, '#206bc4');
    
    // Create storage quota chart
    createRadialChart('storage-chart', storagePercentage, '#4299e1');
}

// Create a radial progress chart
function createRadialChart(elementId, percentage, color) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    // Simple SVG-based radial progress chart
    const size = 120;
    const strokeWidth = 8;
    const radius = (size - strokeWidth) / 2;
    const circumference = radius * 2 * Math.PI;
    const offset = circumference - (percentage / 100) * circumference;
    
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', size);
    svg.setAttribute('height', size);
    svg.setAttribute('viewBox', `0 0 ${size} ${size}`);
    
    // Background circle
    const bgCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    bgCircle.setAttribute('cx', size / 2);
    bgCircle.setAttribute('cy', size / 2);
    bgCircle.setAttribute('r', radius);
    bgCircle.setAttribute('fill', 'none');
    bgCircle.setAttribute('stroke', '#e6e7e9');
    bgCircle.setAttribute('stroke-width', strokeWidth);
    
    // Progress circle
    const progressCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    progressCircle.setAttribute('cx', size / 2);
    progressCircle.setAttribute('cy', size / 2);
    progressCircle.setAttribute('r', radius);
    progressCircle.setAttribute('fill', 'none');
    progressCircle.setAttribute('stroke', color);
    progressCircle.setAttribute('stroke-width', strokeWidth);
    progressCircle.setAttribute('stroke-dasharray', circumference);
    progressCircle.setAttribute('stroke-dashoffset', offset);
    progressCircle.setAttribute('transform', `rotate(-90 ${size / 2} ${size / 2})`);
    
    // Percentage text
    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('x', size / 2);
    text.setAttribute('y', size / 2 + 5); // Center vertically
    text.setAttribute('text-anchor', 'middle');
    text.setAttribute('font-size', '20px');
    text.setAttribute('font-weight', 'bold');
    text.setAttribute('fill', '#1e293b');
    text.textContent = `${percentage}%`;
    
    // Append elements to SVG
    svg.appendChild(bgCircle);
    svg.appendChild(progressCircle);
    svg.appendChild(text);
    
    // Clear element and append SVG
    element.innerHTML = '';
    element.appendChild(svg);
}