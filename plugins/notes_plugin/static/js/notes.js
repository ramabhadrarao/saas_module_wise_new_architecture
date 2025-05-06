/**
 * Notes Plugin JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // Auto-resize textareas
    const textareas = document.querySelectorAll('textarea[name="content"]');
    if (textareas) {
        textareas.forEach(textarea => {
            const minHeight = parseInt(getComputedStyle(textarea).height);
            
            // Function to resize textarea based on content
            const resize = () => {
                textarea.style.height = 'auto';
                textarea.style.height = Math.max(minHeight, textarea.scrollHeight) + 'px';
            };
            
            // Initial resize
            resize();
            
            // Resize on input
            textarea.addEventListener('input', resize);
        });
    }
    
    // Category input with autocomplete
    const categoryInput = document.querySelector('input[name="category"]');
    if (categoryInput && window.Tagify) {
        // If Tagify library is available (you'd need to add this to your base template)
        new Tagify(categoryInput, {
            maxTags: 1,
            dropdown: {
                enabled: 0
            }
        });
    }
    
    // Handle note filtering
    const categorySelect = document.querySelector('select[name="category"]');
    const archivedCheckbox = document.querySelector('input[name="archived"]');
    
    if (categorySelect) {
        categorySelect.addEventListener('change', function() {
            this.form.submit();
        });
    }
    
    if (archivedCheckbox) {
        archivedCheckbox.addEventListener('change', function() {
            this.form.submit();
        });
    }
});