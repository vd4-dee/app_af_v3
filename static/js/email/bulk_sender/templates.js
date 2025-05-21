// static/js/email/bulk_sender/templates.js
$(document).ready(function() {
    // Handle new template button
    $('#new-template-btn, #create-template-btn').on('click', function() {
        $('#template-form')[0].reset();
        $('#template-id').val('');
        $('#template-body').html('<p>Enter your email template here...</p>');
        currentVariables = [];
        updateAvailableVariables([]);
        $('#templateEditorModal').modal('show');
    });
    
    // Handle edit template
    $(document).on('click', '.edit-template', function() {
        const templateId = $(this).data('id');
        
        $.get(`/api/email/templates/${templateId}`)
            .done(function(template) {
                $('#template-id').val(template.id);
                $('#template-name').val(template.name);
                $('#template-subject').val(template.subject);
                $('#template-body').html(template.html_content);
                currentVariables = template.variables || [];
                updateAvailableVariables(currentVariables);
                updatePreview();
                $('#templateEditorModal').modal('show');
            })
            .fail(function() {
                showError('Failed to load template');
            });
    });
    
    // Handle delete template
    $(document).on('click', '.delete-template', function() {
        if (!confirm('Are you sure you want to delete this template?')) return;
        
        const templateId = $(this).data('id');
        
        $.ajax({
            url: `/api/email/templates/${templateId}`,
            type: 'DELETE',
            success: function() {
                showSuccess('Template deleted successfully');
                loadTemplates();
            },
            error: function() {
                showError('Failed to delete template');
            }
        });
    });
    
    // Handle refresh preview
    $('#refresh-preview').on('click', function() {
        updatePreview();
    });
    
    // Handle form submission
    $('#bulk-email-form').on('submit', function(e) {
        e.preventDefault();
        
        const templateId = $('#template-select').val();
        const fileInput = document.getElementById('excel-file');
        
        if (!templateId) {
            showError('Please select a template');
            return;
        }
        
        if (!fileInput.files.length) {
            showError('Please upload an Excel file');
            return;
        }
        
        const formData = new FormData();
        formData.append('excel_file', fileInput.files[0]);
        formData.append('template_id', templateId);
        
        // Show loading state
        const $btn = $('#send-emails-btn');
        const originalText = $btn.html();
        $btn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Sending...');
        
        // Show progress bar
        const $progress = $('#progress-container');
        $progress.show().find('.progress-bar').css('width', '0%');
        
        // Clear previous results
        $('#results-card').hide();
        
        // Send request
        $.ajax({
            url: '/api/email/send-bulk',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            xhr: function() {
                const xhr = new window.XMLHttpRequest();
                
                xhr.upload.addEventListener('progress', function(e) {
                    if (e.lengthComputable) {
                        const percent = Math.round((e.loaded / e.total) * 100);
                        $progress.find('.progress-bar').css('width', percent + '%');
                    }
                }, false);
                
                return xhr;
            },
            success: function(response) {
                if (response.success) {
                    showResults(response);
                } else {
                    showError(response.message || 'Error sending emails');
                }
            },
            error: function(xhr) {
                const error = xhr.responseJSON?.message || 'Error sending emails';
                showError(error);
            },
            complete: function() {
                $btn.prop('disabled', false).html(originalText);
            }
        });
    });
    
    // Show results
    function showResults(data) {
        const $resultsCard = $('#results-card');
        const $resultsSummary = $('#results-summary');
        const $resultsDetails = $('#results-details');
        
        // Update summary
        $resultsSummary.html(`
            <div class="alert alert-${data.failure_count > 0 ? 'warning' : 'success'}">
                Processed ${data.details.length} emails. 
                Success: <strong>${data.success_count}</strong>, 
                Failed: <strong>${data.failure_count}</strong>
            </div>
        `);
        
        // Update details
        $resultsDetails.empty();
        const $table = $('<table class="table table-sm">').appendTo($resultsDetails);
        const $thead = $('<thead>').appendTo($table);
        const $tbody = $('<tbody>').appendTo($table);
        
        // Add header
        $thead.append(`
            <tr>
                <th>#</th>
                <th>Status</th>
                <th>Message</th>
            </tr>
        `);
        
        // Add rows
        data.details.forEach(function(detail) {
            const isSuccess = detail.status === 'success';
            $tbody.append(`
                <tr class="${isSuccess ? 'table-success' : 'table-danger'}">
                    <td>${detail.row}</td>
                    <td><span class="badge bg-${isSuccess ? 'success' : 'danger'}">${detail.status}</span></td>
                    <td>${detail.message}</td>
                </tr>
            `);
        });
        
        // Show results card
        $resultsCard.show();
    }
});