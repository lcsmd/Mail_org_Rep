/**
 * Email processing related JavaScript functionality
 * for the AI-Enhanced Email Management System
 */

/**
 * Process email attachments for viewing
 * @param {string} emailId - The ID of the email
 * @param {Array} attachments - Array of attachment objects
 */
function processAttachments(emailId, attachments) {
    // Get the container where attachments will be displayed
    const container = document.getElementById(`attachments-${emailId}`);
    if (!container) return;
    
    // Clear any existing content
    container.innerHTML = '';
    
    if (!attachments || attachments.length === 0) {
        container.innerHTML = '<p class="text-muted">No attachments</p>';
        return;
    }
    
    // Create UI for each attachment
    attachments.forEach(attachment => {
        const attachmentEl = document.createElement('div');
        attachmentEl.className = 'attachment-item';
        
        // Determine icon based on file type
        let icon = 'file';
        if (attachment.content_type) {
            if (attachment.content_type.includes('image')) {
                icon = 'image';
            } else if (attachment.content_type.includes('pdf')) {
                icon = 'file-text';
            } else if (attachment.content_type.includes('word') || 
                       attachment.content_type.includes('document')) {
                icon = 'file-text';
            } else if (attachment.content_type.includes('spreadsheet') || 
                       attachment.content_type.includes('excel')) {
                icon = 'grid';
            } else if (attachment.content_type.includes('presentation') || 
                       attachment.content_type.includes('powerpoint')) {
                icon = 'monitor';
            } else if (attachment.content_type.includes('zip') || 
                       attachment.content_type.includes('archive')) {
                icon = 'archive';
            }
        }
        
        attachmentEl.innerHTML = `
            <div class="attachment-preview">
                <i data-feather="${icon}"></i>
            </div>
            <div class="attachment-details">
                <p class="attachment-name">${attachment.filename}</p>
                <p class="attachment-size">${formatFileSize(attachment.size)}</p>
            </div>
            <div class="attachment-actions">
                <a href="/attachments/${attachment.id}/download" class="btn btn-sm btn-outline-primary">
                    <i data-feather="download"></i>
                </a>
            </div>
        `;
        
        container.appendChild(attachmentEl);
    });
    
    // Initialize Feather icons for the new elements
    feather.replace();
}

/**
 * Format a file size in bytes to a human-readable string
 * @param {number} bytes - The file size in bytes
 * @returns {string} Formatted file size (e.g., "2.5 MB")
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    
    return parseFloat((bytes / Math.pow(1024, i)).toFixed(1)) + ' ' + sizes[i];
}

/**
 * Fetch and display thread emails
 * @param {string} threadId - The ID of the thread to fetch
 */
function fetchThreadEmails(threadId) {
    // Get the container for thread emails
    const container = document.getElementById(`thread-${threadId}-emails`);
    if (!container) return;
    
    // Show loading indicator
    container.innerHTML = `
        <div class="text-center p-3">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Loading thread emails...</p>
        </div>
    `;
    
    // Fetch thread emails from the server
    fetch(`/thread/${threadId}/emails`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (!data.emails || data.emails.length === 0) {
                container.innerHTML = '<p class="text-muted">No emails found in this thread.</p>';
                return;
            }
            
            // Create elements for each email in the thread
            let html = '';
            data.emails.forEach(email => {
                html += `
                    <div class="thread-email card mb-3" id="email-${email.id}">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <div>
                                <strong>${email.sender}</strong>
                                <span class="text-muted ms-2">${formatDate(email.date_sent)}</span>
                            </div>
                            <a href="/email/${email.id}" class="btn btn-sm btn-outline-secondary">
                                <i data-feather="external-link"></i> View
                            </a>
                        </div>
                        <div class="card-body">
                            <p class="mb-1"><small>To: ${email.recipients}</small></p>
                            <div class="email-content mt-3">
                                ${email.preview_text}
                            </div>
                            
                            ${email.attachments && email.attachments.length > 0 ? `
                                <div class="email-attachments mt-3">
                                    <strong>Attachments:</strong>
                                    <div id="attachments-${email.id}" class="mt-2 attachment-list">
                                        <!-- Attachments will be inserted here -->
                                    </div>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `;
            });
            
            container.innerHTML = html;
            
            // Initialize Feather icons for the new elements
            feather.replace();
            
            // Process attachments for each email
            data.emails.forEach(email => {
                if (email.attachments && email.attachments.length > 0) {
                    processAttachments(email.id, email.attachments);
                }
            });
        })
        .catch(error => {
            container.innerHTML = `
                <div class="alert alert-danger">
                    <i data-feather="alert-circle"></i> Error loading thread emails: ${error.message}
                </div>
            `;
            feather.replace();
        });
}

/**
 * Format a date string for display
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date string
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

/**
 * Apply an AI-suggested rule
 * @param {Object} rule - The rule object to apply
 * @param {Function} callback - Callback function to execute after applying the rule
 */
function applyAiRule(rule, callback) {
    fetch('/rules/apply', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ rule: rule })
    })
    .then(response => response.json())
    .then(data => {
        if (callback && typeof callback === 'function') {
            callback(data);
        }
    })
    .catch(error => {
        console.error('Error applying rule:', error);
        showNotification('Error applying rule: ' + error.message, 'error');
    });
}

/**
 * Batch categorize emails
 * @param {Array} emailIds - Array of email IDs to categorize
 * @param {Array} categories - Array of category names to apply
 * @param {Function} callback - Callback function to execute after categorization
 */
function categorizeEmails(emailIds, categories, callback) {
    fetch('/emails/categorize', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            email_ids: emailIds,
            categories: categories
        })
    })
    .then(response => response.json())
    .then(data => {
        if (callback && typeof callback === 'function') {
            callback(data);
        }
    })
    .catch(error => {
        console.error('Error categorizing emails:', error);
        showNotification('Error categorizing emails: ' + error.message, 'error');
    });
}

/**
 * Run AI analysis on an email
 * @param {string} emailId - The ID of the email to analyze
 * @param {Function} callback - Callback function to receive the analysis results
 */
function analyzeEmail(emailId, callback) {
    fetch(`/ai/analyze/${emailId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (callback && typeof callback === 'function') {
            callback(data);
        }
    })
    .catch(error => {
        console.error('Error analyzing email:', error);
        showNotification('Error analyzing email: ' + error.message, 'error');
    });
}

// Export functions for use in other scripts
window.EmailProcessor = {
    processAttachments,
    formatFileSize,
    fetchThreadEmails,
    formatDate,
    applyAiRule,
    categorizeEmails,
    analyzeEmail
};
