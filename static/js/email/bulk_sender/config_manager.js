// static/js/email/bulk_sender/config_manager.js

$(document).ready(function() {
    const $bulkEmailForm = $('#bulk-email-form');
    const $emailSubject = $('#email-subject');
    const $emailTemplateSelect = $('#email-template');
    const $emailColumnName = $('#email-column-name'); // This element is dynamically added
    const $attachmentColumnName = $('#attachment-column-name');
    const $attachmentsBaseFolder = $('#attachments-base-folder');
    const $startIndex = $('#start-index');
    const $endIndex = $('#end-index');
    const $previewBeforeSend = $('#preview-before-send');

    // Helper to show messages (assuming window.showSuccess and window.showError exist)
    function showSuccess(message) {
        if (typeof window.showSuccess === 'function') {
            window.showSuccess(message);
        } else {
            alert('Success: ' + message);
        }
    }

    function showError(message) {
        if (typeof window.showError === 'function') {
            window.showError(message);
        } else {
            alert('Error: ' + message);
        }
    }

    // --- Save Config Functionality ---
    $('#save-config-btn').on('click', function() {
        const configData = {
            email_subject: $emailSubject.val(),
            template_id: $emailTemplateSelect.val(),
            email_column_name: $emailColumnName.val(), // Get current value if element exists
            attachment_column_name: $attachmentColumnName.val(),
            attachments_base_folder: $attachmentsBaseFolder.val(),
            start_index: $startIndex.val(),
            end_index: $endIndex.val(),
            preview_before_send: $previewBeforeSend.prop('checked')
        };

        $.ajax({
            url: '/api/email/save-bulk-config',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(configData),
            success: function(response) {
                if (response.success) {
                    showSuccess(response.message);
                } else {
                    showError(response.message);
                }
            },
            error: function(xhr) {
                const errorMsg = xhr.responseJSON?.message || 'Failed to save configuration.';
                showError(`Error saving config: ${errorMsg}`);
            }
        });
    });

    // --- Load Config Functionality ---
    $('#load-config-btn').on('click', function() {
        $.ajax({
            url: '/api/email/load-bulk-config',
            type: 'GET',
            success: function(response) {
                if (response.success && response.config) {
                    const config = response.config;
                    $emailSubject.val(config.email_subject || '');
                    $emailTemplateSelect.val(config.template_id || '');
                    
                    // Handle dynamic element for email_column_name
                    // This might need to be set after Excel headers are loaded,
                    // so we'll just try to set it if it exists.
                    // A more robust solution would involve re-triggering header extraction
                    // or ensuring the select is populated before setting.
                    if ($emailColumnName.length) {
                        $emailColumnName.val(config.email_column_name || '');
                    }

                    $attachmentColumnName.val(config.attachment_column_name || '');
                    $attachmentsBaseFolder.val(config.attachments_base_folder || '');
                    $startIndex.val(config.start_index || '1');
                    $endIndex.val(config.end_index || '');
                    $previewBeforeSend.prop('checked', config.preview_before_send || false);

                    showSuccess(response.message);
                    
                    // Trigger change event for template select to update preview
                    $emailTemplateSelect.trigger('change');

                } else {
                    showError(response.message || 'Failed to load configuration.');
                }
            },
            error: function(xhr) {
                const errorMsg = xhr.responseJSON?.message || 'Failed to load configuration.';
                showError(`Error loading config: ${errorMsg}`);
            }
        });
    });
});
