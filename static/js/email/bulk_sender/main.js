$(document).ready(function() {
    // Load templates for dropdown
    function loadDynamicTemplates() {
        $.get('/api/email/templates')
            .done(function(templates) {
                const $select = $('#email-template');
                $select.empty().append('<option value="">-- Chọn mẫu email --</option>');
                templates.forEach(function(template) {
                    $select.append(`<option value="${template.id}">${template.name}</option>`);
                });
            })
            .fail(function() {
                $('#email-template').html('<option value="">(Lỗi tải danh sách mẫu)</option>');
            });
    }

    // Load Excel headers when file selected
    $('#excel-file').on('change', function(e) {
        const file = e.target.files[0];
        if (!file) return;
        const formData = new FormData();
        formData.append('file', file);
        $.ajax({
            url: '/api/email/extract-headers',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(res) {
                if (res.success && res.headers) {
                    $('#excel-headers-block').html('<b>Các biến từ Excel:</b> ' + res.headers.map(h=>`<code>{{${h}}}</code>`).join(' '));
                } else {
                    $('#excel-headers-block').html('<span class="text-danger">Không đọc được biến từ file Excel!</span>');
                }
            },
            error: function() {
                $('#excel-headers-block').html('<span class="text-danger">Lỗi khi đọc file Excel!</span>');
            }
        });
    });

    // Preview template with sample data
    $('#preview-template-btn').on('click', function() {
        const templateId = $('#email-template').val();
        if (!templateId) {
            $('#template-preview-block').hide();
            return;
        }
        // Lấy sample data từ biến Excel nếu có
        let sampleData = {};
        const headersHtml = $('#excel-headers-block').text();
        if (headersHtml) {
            const matches = headersHtml.match(/\{\{(.*?)\}\}/g);
            if (matches) {
                matches.forEach(m => {
                    const key = m.replace(/\{|\}/g, '').trim();
                    sampleData[key] = 'Demo';
                });
            }
        }
        $.ajax({
            url: `/api/email/templates/${templateId}/preview`,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ data: sampleData }),
            success: function(res) {
                $('#template-preview').html(res.html || '<i>Không có nội dung</i>');
                $('#template-preview-block').show();
            },
            error: function() {
                $('#template-preview').html('<span class="text-danger">Lỗi khi xem trước mẫu!</span>');
                $('#template-preview-block').show();
            }
        });
    });

    // Gửi bulk email qua API động
    $('#bulk-email-form').on('submit', function(e) {
        e.preventDefault();
        $('#email-loading-indicator').show();
        $('#email-status-messages').html('');

        // Lấy dữ liệu form
        const templateId = $('#email-template').val();
        const excelFile = $('#excel-file')[0].files[0];
        const attachmentsFolder = $('#attachments-folder').val();
        const startIndex = $('#start-index').val();
        const endIndex = $('#end-index').val();

        if (!templateId || !excelFile) {
            $('#email-status-messages').html('<div class="alert alert-danger">Vui lòng chọn mẫu email và file Excel!</div>');
            $('#email-loading-indicator').hide();
            return;
        }

        // Chuẩn bị form data
        const formData = new FormData();
        formData.append('template_id', templateId);
        formData.append('excel_file', excelFile);
        formData.append('attachments_folder', attachmentsFolder);
        if (startIndex) formData.append('start_index', startIndex);
        if (endIndex) formData.append('end_index', endIndex);

        // Gửi request tới API
        $.ajax({
            url: '/api/email/send-bulk',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(res) {
                $('#email-loading-indicator').hide();
                if (res.success) {
                    $('#email-status-messages').html('<div class="alert alert-success">Đã gửi email thành công!<br>' + (res.message || '') + '</div>');
                } else {
                    $('#email-status-messages').html('<div class="alert alert-danger">Lỗi gửi email: ' + (res.message || 'Không rõ lỗi') + '</div>');
                }
            },
            error: function(xhr) {
                $('#email-loading-indicator').hide();
                $('#email-status-messages').html('<div class="alert alert-danger">Lỗi hệ thống khi gửi email!</div>');
            }
        });
    });

    // On page load, fetch templates
    loadDynamicTemplates();
});