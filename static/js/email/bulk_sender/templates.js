// static/js/email/bulk_sender/templates.js

// Global helper functions (can be moved to a shared utility file if many JS files need them)
window.showError = function(message) {
    const resultsArea = $('#results-area .card-body'); // Assuming resultsArea is the card-body
    resultsArea.html(`<div class="alert alert-danger" role="alert">${message}</div>`);
    $('#results-area').show();
};

window.showSuccess = function(message) {
    const resultsArea = $('#results-area .card-body');
    resultsArea.html(`<div class="alert alert-success" role="alert">${message}</div>`);
    $('#results-area').show();
};

// Function to load templates from API
window.getTemplates = function() {
    return $.get('/api/email/templates')
        .then(function(response) {
            if (response.success) {
                return response.templates;
            } else {
                throw new Error(response.message || 'Failed to fetch templates');
            }
        });
};

// Function to get template content by ID (used by main.js for preview)
window.getTemplateContentById = function(templateId) {
    return $.get(`/api/email/templates/${templateId}`)
        .then(function(response) {
            if (response.success) {
                return response.content;
            } else {
                throw new Error(response.message || 'Failed to fetch template content');
            }
        });
};

// Function to get template preview with sample data
window.getTemplatePreview = function(templateId, sampleData = {}) {
    return $.ajax({
        url: `/api/email/templates/${templateId}/preview`,
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(sampleData)
    })
    .then(function(response) {
        if (response.success) {
            return response.preview_html;
        } else {
            throw new Error(response.message || 'Failed to get template preview');
        }
    });
};

// Function to load and display templates in the table
window.loadTemplates = function() {
    const $templatesTableBody = $('#templates-table tbody');
    $templatesTableBody.empty(); // Clear existing rows

    window.getTemplates()
        .then(templates => {
            if (templates && templates.length > 0) {
                templates.forEach(template => {
                    // Assuming template object has id, name, subject, last_updated
                    // Note: The current API only returns id and name. Subject and last_updated need to be added to backend.
                    const row = `
                        <tr>
                            <td>${template.name}</td>
                            <td>${template.subject || 'N/A'}</td> 
                            <td>${template.last_updated || 'N/A'}</td>
                            <td>
                                <button class="btn btn-sm btn-info edit-template" data-id="${template.id}">Edit</button>
                                <button class="btn btn-sm btn-danger delete-template" data-id="${template.id}">Delete</button>
                            </td>
                        </tr>
                    `;
                    $templatesTableBody.append(row);
                });
            } else {
                $templatesTableBody.append('<tr><td colspan="4">No templates found.</td></tr>');
            }
        })
        .catch(error => {
            console.error('Error loading templates for table:', error);
            $templatesTableBody.append(`<tr><td colspan="4" class="text-danger">Error loading templates: ${error.message}</td></tr>`);
        });
};

// Function to update the template preview in the editor modal
window.updatePreview = function() {
    const templateId = $('#template-id').val();
    const templateBodyContent = $('#template-body').html(); // Get content from contenteditable div
    const $previewArea = $('#templateEditorModal #template-preview');

    if (!templateBodyContent) {
        $previewArea.html('<p class="text-muted">Enter content to preview</p>');
        return;
    }

    // For preview, we can directly render the contenteditable HTML with some dummy data
    // Or, if we want to use the backend Jinja2 rendering, we'd send it to /preview API
    // For simplicity, let's just display the raw HTML for now, or use the backend API if templateId exists
    if (templateId) {
        window.getTemplatePreview(templateId, { /* sample data */ })
            .then(htmlContent => {
                $previewArea.html(htmlContent);
            })
            .catch(error => {
                console.error('Error updating preview:', error);
                $previewArea.html(`<p class="text-danger">Error previewing: ${error.message}</p>`);
            });
    } else {
        // If it's a new template, just show the raw HTML
        $previewArea.html(templateBodyContent);
    }
};

// Function to update available variables in the editor modal
window.updateAvailableVariables = function(variables) {
    const $availableVariables = $('#available-variables');
    $availableVariables.empty();
    if (variables && variables.length > 0) {
        variables.forEach(v => {
            $availableVariables.append(`<span class="badge bg-secondary me-1 mb-1">{{${v}}}</span>`);
        });
    } else {
        $availableVariables.html('<p class="text-muted">Variables will appear here when you upload an Excel file</p>');
    }
};


$(document).ready(function() {
    // Handle new template button
    $('#new-template-btn').on('click', function() {
        $('#template-form')[0].reset();
        $('#template-id').val('');
        $('#template-name').val(''); // Clear name for new template
        $('#template-subject').val(''); // Clear subject for new template
        $('#template-body').html('<p>Enter your email template here...</p>');
        window.updateAvailableVariables([]); // Clear variables for new template
        $('#templateEditorModalLabel').text('Create New Template'); // Update modal title
        $('#save-template').text('Create Template'); // Update button text
        $('#templateEditorModal').modal('show');
    });
    
    // Handle edit template
    $(document).on('click', '.edit-template', function() {
        const templateId = $(this).data('id');
        
        window.getTemplateContentById(templateId) // Use the global function
            .then(function(content) {
                $('#template-id').val(templateId);
                $('#template-name').val(templateId.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())); // Convert ID back to readable name
                $('#template-subject').val(''); // Subject is not returned by current API, needs to be added
                $('#template-body').html(content);
                // currentVariables = template.variables || []; // Variables not returned by API
                window.updateAvailableVariables([]); // Clear for now
                window.updatePreview(); // Update preview in modal
                $('#templateEditorModalLabel').text('Edit Template'); // Update modal title
                $('#save-template').text('Save Changes'); // Update button text
                $('#templateEditorModal').modal('show');
            })
            .catch(function(error) {
                window.showError(`Failed to load template: ${error.message}`);
            });
    });
    
    // Handle delete template
    $(document).on('click', '.delete-template', function() {
        if (!confirm('Are you sure you want to delete this template?')) return;
        
        const templateId = $(this).data('id');
        
        $.ajax({
            url: `/api/email/templates/${templateId}`,
            type: 'DELETE',
            success: function(response) {
                if (response.success) {
                    window.showSuccess(response.message);
                    window.loadTemplates(); // Reload templates after deletion
                } else {
                    window.showError(response.message);
                }
            },
            error: function(xhr) {
                const error = xhr.responseJSON?.message || 'Error deleting template';
                window.showError(error);
            }
        });
    });
    
    // Handle refresh preview in editor modal
    $('#refresh-preview').on('click', function() {
        window.updatePreview();
    });
    
    // Handle save template (create/update)
    $('#save-template').on('click', function() {
        const templateId = $('#template-id').val();
        const templateName = $('#template-name').val().trim();
        const templateSubject = $('#template-subject').val().trim(); // Get subject
        const templateContent = $('#template-body').html(); // Get content from contenteditable div

        if (!templateName || !templateContent) {
            window.showError('Template name and content cannot be empty.');
            return;
        }

        const data = {
            name: templateName,
            subject: templateSubject, // Include subject
            content: templateContent
        };

        let url = '/api/email/templates';
        let type = 'POST';

        if (templateId) { // If templateId exists, it's an update
            url = `/api/email/templates/${templateId}`;
            type = 'PUT';
        }

        $.ajax({
            url: url,
            type: type,
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: function(response) {
                if (response.success) {
                    window.showSuccess(response.message);
                    $('#templateEditorModal').modal('hide');
                    window.loadTemplates(); // Reload templates after save
                } else {
                    window.showError(response.message);
                }
            },
            error: function(xhr) {
                const error = xhr.responseJSON?.message || 'Error saving template';
                window.showError(error);
            }
        });
    });

    // Initial load of templates when the Templates tab is shown
    $('a[data-bs-toggle="tab"]').on('shown.bs.tab', function (e) {
        if ($(e.target).attr('id') === 'templates-tab') {
            window.loadTemplates();
        }
    });

    // Initial load of templates for the select dropdown on page load
    // This is handled by main.js, but ensure loadTemplates is called if needed here too
    // window.loadTemplates(); // This would load for the table, not the select dropdown
});
