/**
 * Authentication functionality
 */

// Initialize authentication components
document.addEventListener('DOMContentLoaded', function() {
    // Password strength meter
    const passwordInputs = document.querySelectorAll('input[name="password"], input[name="new_password"]');
    if (passwordInputs) {
        passwordInputs.forEach(input => {
            input.addEventListener('input', function() {
                const password = this.value;
                const strengthMeter = this.nextElementSibling;
                
                if (strengthMeter && strengthMeter.classList.contains('password-strength')) {
                    // Calculate password strength
                    let strength = 0;
                    
                    // Length check
                    if (password.length >= 8) strength += 1;
                    
                    // Complexity checks
                    if (/[a-z]/.test(password)) strength += 1;
                    if (/[A-Z]/.test(password)) strength += 1;
                    if (/[0-9]/.test(password)) strength += 1;
                    if (/[^a-zA-Z0-9]/.test(password)) strength += 1;
                    
                    // Update strength meter
                    const strengthBar = strengthMeter.querySelector('.progress-bar');
                    if (strengthBar) {
                        // Set width and color based on strength
                        strengthBar.style.width = (strength * 20) + '%';
                        
                        if (strength <= 2) {
                            strengthBar.className = 'progress-bar bg-danger';
                            strengthMeter.setAttribute('data-strength', 'Weak');
                        } else if (strength <= 3) {
                            strengthBar.className = 'progress-bar bg-warning';
                            strengthMeter.setAttribute('data-strength', 'Medium');
                        } else {
                            strengthBar.className = 'progress-bar bg-success';
                            strengthMeter.setAttribute('data-strength', 'Strong');
                        }
                    }
                }
            });
        });
    }
    
    // Form validation for user creation/editing
    const userForms = document.querySelectorAll('form[action*="/auth/users/"]');
    if (userForms) {
        userForms.forEach(form => {
            form.addEventListener('submit', function(e) {
                const passwordInput = this.querySelector('input[name="password"], input[name="new_password"]');
                const confirmInput = this.querySelector('input[name="confirm_password"]');
                
                if (passwordInput && confirmInput && passwordInput.value !== confirmInput.value) {
                    e.preventDefault();
                    alert('Passwords do not match');
                    passwordInput.focus();
                    return false;
                }
            });
        });
    }
    
    // Role permission toggles
    const permissionGroups = document.querySelectorAll('.permission-group');
    if (permissionGroups) {
        permissionGroups.forEach(group => {
            const groupToggle = group.querySelector('.permission-group-toggle');
            if (groupToggle) {
                groupToggle.addEventListener('change', function() {
                    const isChecked = this.checked;
                    const permissions = group.querySelectorAll('.permission-item input[type="checkbox"]');
                    
                    permissions.forEach(permission => {
                        permission.checked = isChecked;
                    });
                });
            }
            
            // Update group toggle when individual permissions change
            const permissionItems = group.querySelectorAll('.permission-item input[type="checkbox"]');
            permissionItems.forEach(item => {
                item.addEventListener('change', function() {
                    const groupToggle = group.querySelector('.permission-group-toggle');
                    const allPermissions = group.querySelectorAll('.permission-item input[type="checkbox"]');
                    const checkedPermissions = group.querySelectorAll('.permission-item input[type="checkbox"]:checked');
                    
                    if (groupToggle) {
                        if (checkedPermissions.length === 0) {
                            groupToggle.checked = false;
                            groupToggle.indeterminate = false;
                        } else if (checkedPermissions.length === allPermissions.length) {
                            groupToggle.checked = true;
                            groupToggle.indeterminate = false;
                        } else {
                            groupToggle.checked = false;
                            groupToggle.indeterminate = true;
                        }
                    }
                });
            });
        });
    }
});