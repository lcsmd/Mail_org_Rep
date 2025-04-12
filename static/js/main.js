/**
 * Main JavaScript file for the AI-Enhanced Email Management System
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Feather icons
    feather.replace();
    
    // Enable tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Enable popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-resize textareas
    const textAreas = document.querySelectorAll('textarea.auto-resize');
    textAreas.forEach(textArea => {
        textArea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
        
        // Initial resize
        textArea.dispatchEvent(new Event('input'));
    });
    
    // Handle collapsible email threads
    const threadToggles = document.querySelectorAll('.thread-toggle');
    threadToggles.forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            const threadId = this.getAttribute('data-thread-id');
            const threadEmails = document.querySelector(`.thread-emails[data-thread-id="${threadId}"]`);
            
            if (threadEmails) {
                if (threadEmails.classList.contains('show')) {
                    threadEmails.classList.remove('show');
                    this.querySelector('i').classList.remove('feather-chevron-up');
                    this.querySelector('i').classList.add('feather-chevron-down');
                } else {
                    threadEmails.classList.add('show');
                    this.querySelector('i').classList.remove('feather-chevron-down');
                    this.querySelector('i').classList.add('feather-chevron-up');
                }
            }
        });
    });
    
    // Handle email iframe height adjustments
    const emailIframes = document.querySelectorAll('.email-iframe');
    emailIframes.forEach(iframe => {
        iframe.onload = function() {
            adjustIframeHeight(iframe);
        };
    });
    
    // Resize email iframes when window is resized
    window.addEventListener('resize', function() {
        emailIframes.forEach(iframe => {
            adjustIframeHeight(iframe);
        });
    });
    
    // Check for auto-sync setting and refresh emails if needed
    if (window.location.pathname === '/' || window.location.pathname === '/index') {
        const autoSyncEnabled = localStorage.getItem('autoSyncEnabled');
        if (autoSyncEnabled === 'true') {
            const lastSync = localStorage.getItem('lastSync');
            const now = new Date().getTime();
            
            // Only auto-sync if last sync was more than 30 minutes ago or never
            if (!lastSync || (now - parseInt(lastSync)) > 30 * 60 * 1000) {
                const refreshButton = document.getElementById('refreshEmails');
                if (refreshButton) {
                    // Set a small delay to allow the page to load first
                    setTimeout(() => {
                        refreshButton.click();
                        localStorage.setItem('lastSync', now.toString());
                    }, 1000);
                }
            }
        }
    }
});

/**
 * Adjust the height of an email iframe to fit its content
 * @param {HTMLIFrameElement} iframe - The iframe element to adjust
 */
function adjustIframeHeight(iframe) {
    try {
        const doc = iframe.contentDocument || iframe.contentWindow.document;
        const height = doc.body.scrollHeight;
        iframe.style.height = (height + 20) + 'px'; // Add a bit of padding
    } catch (e) {
        console.error('Error adjusting iframe height:', e);
    }
}

/**
 * Show a notification toast
 * @param {string} message - The message to display
 * @param {string} type - The type of notification (success, error, warning, info)
 */
function showNotification(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer');
    
    if (!toastContainer) {
        // Create toast container if it doesn't exist
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(container);
    }
    
    // Create toast element
    const toastId = 'toast-' + Date.now();
    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center text-white bg-${type}`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    toastEl.id = toastId;
    
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    document.getElementById('toastContainer').appendChild(toastEl);
    
    // Initialize and show the toast
    const toast = new bootstrap.Toast(toastEl, {
        autohide: true,
        delay: 5000
    });
    toast.show();
    
    // Remove toast from DOM after it's hidden
    toastEl.addEventListener('hidden.bs.toast', function () {
        document.getElementById(toastId).remove();
    });
}
