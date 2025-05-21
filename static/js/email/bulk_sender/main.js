// static/js/email/bulk_sender/main.js

$(document).ready(function() {
    const $bulkEmailForm = $('#bulk-email-form');
    const $excelFileImport = $('#excel-file-import');
    const $excelFileInput = $('#excel-file');
    const $excelFileNameDisplay = $('#excel-file-name');
    const $emailTemplateSelect = $('#email-template');
    const $templatePreviewArea = $('#template-preview-area');
    const $columnMappingArea = $('#column-mapping-area');
    const $resultsArea = $('#results-area .card-body'); // Target the card-body for results
    const $resultsCard = $('#results-area'); // The whole card for showing/hiding
    const $loadingIndicator = $('#loading-indicator');
    const $loadingMessage = $loadingIndicator.find('.loading-message');

    // --- Helper function for loading indicator ---
    function showLoading(isLoading, message = "Processing...") {
        if (isLoading) {
            $loadingMessage.text(message);
            $loadingIndicator.show();
            $resultsCard.hide(); // Hide results when loading
        } else {
            $loadingIndicator.hide();
        }
    }

    // --- Load Email Templates ---
    function loadDynamicTemplates() {
        showLoading(true, "Loading email templates...");
        if (typeof window.getTemplates === 'function') {
            window.getTemplates() // Call the global function from templates.js
                .then(templates => {
                    showLoading(false);
                    $emailTemplateSelect.empty().append('<option value="">-- Select an email template --</option>');
                    if (templates && templates.length > 0) {
                        templates.forEach(template => {
                            const option = $('<option></option>')
                                .val(template.id)
                                .text(template.name);
                            $emailTemplateSelect.append(option);
                        });
                    } else {
                        $emailTemplateSelect.append('<option value="">-- No templates found --</option>');
                    }
                })
                .catch(error => {
                    showLoading(false);
                    console.error('Error loading email templates:', error);
                    window.showError(`Could not load email templates: ${error.message}`);
                });
        } else {
            showLoading(false);
            console.warn('getTemplates function not found. Check templates.js');
            window.showError('Email template loading functionality not ready.');
        }
    }

    // --- Handle Excel File Input and Header Extraction ---
    if ($excelFileImport.length && $excelFileInput.length) {
        $excelFileImport.on('click', function() {
            $excelFileInput.click(); // Trigger hidden file input
        });

        $excelFileInput.on('change', function() {
            if (this.files.length > 0) {
                const file = this.files[0];
                $excelFileNameDisplay.text(file.name); // Display file name
                extractHeaders(file);
            } else {
                $excelFileNameDisplay.text('No file chosen');
                $columnMappingArea.empty(); // Clear mapping if no file
            }
        });
    }

    function extractHeaders(file) {
        const formData = new FormData();
        formData.append('excel_file', file);
        showLoading(true, "Reading Excel headers...");

        $.ajax({
            url: '/api/email/get-excel-headers',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(data) {
                showLoading(false);
                if (data.success && data.headers) {
                    displayColumnMappingUI(data.headers);
                } else {
                    window.showError(`Error getting headers from Excel: ${data.message || 'Unknown error'}`);
                    $columnMappingArea.empty();
                }
            },
            error: function(xhr) {
                showLoading(false);
                const error = xhr.responseJSON?.message || `Error ${xhr.status} when processing Excel file.`;
                window.showError(`Error processing Excel file: ${error}. Please check file format.`);
                $columnMappingArea.empty();
            }
        });
    }

    function displayColumnMappingUI(headers) {
        let html = `<div class="mb-3">
                        <label for="email-column-name" class="form-label">Column containing Email Address:</label>
                        <select id="email-column-name" class="form-select">`;
        headers.forEach(header => {
            const selected = (header.toLowerCase() === 'email' || header.toLowerCase() === 'mail') ? 'selected' : '';
            html += `<option value="${header}" ${selected}>${header}</option>`;
        });
        html += `</select>
                </div>`;
        $columnMappingArea.html(html);
    }

    // --- Preview Template ---
    // The preview button is not explicitly defined in bulk_sender.html,
    // but the template-preview-area is there.
    // Let's add a change listener to the template select to trigger preview.
    $emailTemplateSelect.on('change', function() {
        const templateId = $(this).val();
        if (!templateId) {
            $templatePreviewArea.html('<p class="text-muted">Select a template to preview</p>');
            return;
        }
        showLoading(true, "Loading preview...");
        if (typeof window.getTemplatePreview === 'function') {
            window.getTemplatePreview(templateId, { /* sample data if needed */ })
                .then(htmlContent => {
                    showLoading(false);
                    $templatePreviewArea.html(`<iframe srcdoc="${htmlContent.replace(/"/g, '"')}" style="width:100%; height:300px; border:1px solid #ccc;"></iframe>`);
                })
                .catch(error => {
                    showLoading(false);
                    console.error('Error previewing template:', error);
                    $templatePreviewArea.html(`<p class="text-danger">Could not load preview: ${error.message}</p>`);
                });
        } else {
            showLoading(false);
            $templatePreviewArea.html(`<p class="text-warning">Preview functionality not ready.</p>`);
        }
    });

    // --- Handle Form Submission ---
    if ($bulkEmailForm.length) {
        $bulkEmailForm.on('submit', function(event) {
            event.preventDefault();
            $resultsArea.empty(); // Clear old results
            $resultsCard.hide(); // Hide results card initially
            showLoading(true, "Processing email sending...");

            const formData = new FormData();
            const excelFile = $excelFileInput[0].files[0];
            const emailSubject = $('#email-subject').val();
            const templateId = $emailTemplateSelect.val();
            
            const emailColumn = $('#email-column-name').val() || 'email';
            const attachmentColumn = $('#attachment-column-name').val() || '';
            const attachmentsBaseFolder = $('#attachments-base-folder').val() || '';
            const startIndex = $('#start-index').val() || '1';
            const endIndex = $('#end-index').val() || '';

            if (!excelFile) {
                window.showError('Please select an Excel file.');
                showLoading(false);
                return;
            }
            if (!emailSubject) {
                window.showError('Please enter an email subject.');
                showLoading(false);
                return;
            }
            if (!templateId) {
                window.showError('Please select an email template.');
                showLoading(false);
                return;
            }

            formData.append('excel_file', excelFile);
            formData.append('email_subject', emailSubject);
            formData.append('template_id', templateId);
            formData.append('email_column', emailColumn);
            formData.append('attachment_column', attachmentColumn);
            formData.append('attachments_base_folder', attachmentsBaseFolder);
            formData.append('start_index', startIndex);
            formData.append('end_index', endIndex);

            $.ajax({
                url: '/api/email/send-bulk',
                type: 'POST',
                data: formData,
                processData: false,
                contentType: false,
                xhr: function() {
                    const xhr = new window.XMLHttpRequest();
                    // Progress event for upload
                    xhr.upload.addEventListener('progress', function(e) {
                        if (e.lengthComputable) {
                            const percent = Math.round((e.loaded / e.total) * 100);
                            // You can update a progress bar here if you add one
                            // For now, just update loading message
                            $loadingMessage.text(`Uploading: ${percent}%`);
                        }
                    }, false);
                    return xhr;
                },
                success: function(data) {
                    showLoading(false);
                    console.log('Response from server:', data);
                    let messageHtml = `<div class="alert alert-${data.success ? 'info' : 'danger'}" role="alert">${data.message || 'Processing complete.'}</div>`;
                    
                    if (data.log_file) {
                        messageHtml += `<p><a href="/api/email/download-log/${data.log_file}" target="_blank" class="btn btn-secondary btn-sm mt-2">
                                            <i class="bi bi-download"></i> Download Log File (${data.log_file})
                                       </a></p>`;
                    }

                    if (data.results && Array.isArray(data.results)) {
                        messageHtml += '<h4>Email Sending Details:</h4>';
                        messageHtml += `<div class="table-responsive" style="max-height: 400px; overflow-y: auto;">
                                            <table class="table table-striped table-hover table-sm">
                                                <thead class="table-light sticky-top">
                                                    <tr>
                                                        <th>Excel Row</th>
                                                        <th>Email</th>
                                                        <th>Status</th>
                                                        <th>Message</th>
                                                    </tr>
                                                </thead>
                                                <tbody>`;
                        data.results.forEach(res => {
                            const statusClass = res.status === 'success' ? 'text-success' : 'text-danger';
                            messageHtml += `<tr>
                                                <td>${res.row}</td>
                                                <td>${res.email || 'N/A'}</td>
                                                <td class="${statusClass}">${res.status}</td>
                                                <td>${res.message || ''}</td>
                                            </tr>`;
                        });
                        messageHtml += '</tbody></table></div>';
                    }
                    $resultsArea.html(messageHtml);
                    $resultsCard.show(); // Show the results card
                },
                error: function(xhr) {
                    showLoading(false);
                    const error = xhr.responseJSON?.message || 'Could not connect to server or unknown error occurred.';
                    window.showError(`Severe error: ${error}`);
                }
            });
        });
    }

    // --- Initial Load ---
    loadDynamicTemplates(); // Load template list when page loads

    // Load templates for the table when the "Templates" tab is clicked
    $('a[data-bs-toggle="tab"]').on('shown.bs.tab', function (e) {
        if ($(e.target).attr('id') === 'templates-tab') {
            window.loadTemplates(); // Call the global function to load table data
        }
    });
});
