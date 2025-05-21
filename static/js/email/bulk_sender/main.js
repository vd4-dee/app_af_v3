// static/js/email/bulk_sender/main.js

document.addEventListener('DOMContentLoaded', function() {
    const bulkEmailForm = document.getElementById('bulk-email-form');
    const excelFileImport = document.getElementById('excel-file-import'); // Nút "Chọn File Excel" tùy chỉnh
    const excelFileInput = document.getElementById('excel-file'); // Input file thực sự
    const excelFileNameDisplay = document.getElementById('excel-file-name');
    const emailTemplateSelect = document.getElementById('email-template');
    const previewTemplateButton = document.getElementById('preview-template');
    const templatePreviewArea = document.getElementById('template-preview-area');
    const columnMappingArea = document.getElementById('column-mapping-area');
    const resultsArea = document.getElementById('results-area');
    const loadingIndicator = document.getElementById('loading-indicator'); // Thêm spinner/loading

    // --- Load Email Templates ---
    function loadDynamicTemplates() {
        // templates.js có thể đã được load và có hàm getTemplates()
        if (typeof getTemplates === 'function') {
            getTemplates() // Hàm này từ templates.js gọi API /api/email/templates
                .then(templates => {
                    emailTemplateSelect.innerHTML = '<option value="">-- Chọn mẫu email --</option>';
                    if (templates && templates.length > 0) {
                        templates.forEach(template => {
                            const option = document.createElement('option');
                            option.value = template.id; // Giả sử template có id
                            option.textContent = template.name; // Và name
                            emailTemplateSelect.appendChild(option);
                        });
                    } else {
                        emailTemplateSelect.innerHTML = '<option value="">-- Không có mẫu nào --</option>';
                    }
                })
                .catch(error => {
                    console.error('Lỗi tải danh sách mẫu email:', error);
                    emailTemplateSelect.innerHTML = '<option value="">-- Lỗi tải mẫu --</option>';
                    resultsArea.innerHTML = `<p class="text-danger">Không thể tải danh sách mẫu email. Vui lòng thử lại.</p>`;
                });
        } else {
            console.warn('Hàm getTemplates không tồn tại. Kiểm tra file templates.js');
            resultsArea.innerHTML = `<p class="text-warning">Chức năng tải mẫu email động chưa sẵn sàng.</p>`;
        }
    }

    // --- Handle Excel File Input and Header Extraction ---
    if (excelFileImport && excelFileInput) {
        excelFileImport.addEventListener('click', function() {
            excelFileInput.click(); // Kích hoạt input file ẩn
        });

        excelFileInput.addEventListener('change', function() {
            if (excelFileInput.files.length > 0) {
                const file = excelFileInput.files[0];
                excelFileNameDisplay.textContent = file.name; // Hiển thị tên file
                extractHeaders(file);
            } else {
                excelFileNameDisplay.textContent = 'Chưa chọn file nào';
                columnMappingArea.innerHTML = ''; // Xóa mapping nếu không có file
            }
        });
    }

    function extractHeaders(file) {
        const formData = new FormData();
        formData.append('excel_file', file);
        showLoading(true, "Đang đọc tiêu đề Excel...");

        fetch('/api/email/get-excel-headers', {
            method: 'POST',
            body: formData,
            // headers: { 'Authorization': 'Bearer ' + localStorage.getItem('access_token') } // Nếu có auth
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.message || `Lỗi ${response.status}`) });
            }
            return response.json();
        })
        .then(data => {
            showLoading(false);
            if (data.success && data.headers) {
                displayColumnMappingUI(data.headers);
            } else {
                resultsArea.innerHTML = `<p class="text-danger">Lỗi lấy tiêu đề từ Excel: ${data.message || 'Không rõ lỗi'}</p>`;
                columnMappingArea.innerHTML = '';
            }
        })
        .catch(error => {
            showLoading(false);
            console.error('Lỗi khi lấy tiêu đề Excel:', error);
            resultsArea.innerHTML = `<p class="text-danger">Lỗi khi xử lý file Excel: ${error.message}. Vui lòng kiểm tra định dạng file.</p>`;
            columnMappingArea.innerHTML = '';
        });
    }

    function displayColumnMappingUI(headers) {
        // Hiển thị UI cho người dùng chọn cột email, cột đính kèm, etc.
        // Ví dụ đơn giản: chỉ cần chọn cột chứa email
        let html = `<div class="mb-3">
                        <label for="email-column-name" class="form-label">Cột chứa địa chỉ Email:</label>
                        <select id="email-column-name" class="form-select">`;
        headers.forEach(header => {
            // Tự động chọn cột có tên 'email' hoặc 'mail' nếu có
            const selected = (header.toLowerCase() === 'email' || header.toLowerCase() === 'mail') ? 'selected' : '';
            html += `<option value="${header}" ${selected}>${header}</option>`;
        });
        html += `</select>
                </div>`;
        // Thêm các input khác tại đây nếu cần (ví dụ: cột tên, cột file đính kèm)
        columnMappingArea.innerHTML = html;
    }


    // --- Preview Template ---
    if (previewTemplateButton) {
        previewTemplateButton.addEventListener('click', function() {
            const templateId = emailTemplateSelect.value;
            if (!templateId) {
                alert('Vui lòng chọn một mẫu email để xem trước.');
                return;
            }
            showLoading(true, "Đang tải xem trước...");
            // Gọi API từ templates.js để lấy nội dung xem trước
            if (typeof getTemplatePreview === 'function') {
                getTemplatePreview(templateId, { /* sample data if needed */ })
                    .then(htmlContent => {
                        showLoading(false);
                        // Hiển thị nội dung HTML trong một iframe hoặc div an toàn
                        templatePreviewArea.innerHTML = `<iframe srcdoc="${htmlContent.replace(/"/g, '&quot;')}" style="width:100%; height:300px; border:1px solid #ccc;"></iframe>`;
                    })
                    .catch(error => {
                        showLoading(false);
                        console.error('Lỗi xem trước mẫu:', error);
                        templatePreviewArea.innerHTML = `<p class="text-danger">Không thể tải xem trước: ${error.message}</p>`;
                    });
            } else {
                showLoading(false);
                templatePreviewArea.innerHTML = `<p class="text-warning">Chức năng xem trước chưa sẵn sàng.</p>`;
            }
        });
    }


    // --- Handle Form Submission ---
    if (bulkEmailForm) {
        bulkEmailForm.addEventListener('submit', function(event) {
            event.preventDefault();
            resultsArea.innerHTML = ''; // Xóa kết quả cũ
            showLoading(true, "Đang xử lý gửi email...");

            const formData = new FormData();
            const excelFile = excelFileInput.files[0];
            const emailSubject = document.getElementById('email-subject').value;
            const templateId = emailTemplateSelect.value;
            
            // Các trường mới cho backend thống nhất
            const emailColumn = document.getElementById('email-column-name') ? document.getElementById('email-column-name').value : 'email'; // Lấy từ UI mapping hoặc mặc định
            const attachmentColumn = document.getElementById('attachment-column-name') ? document.getElementById('attachment-column-name').value : '';
            const attachmentsBaseFolder = document.getElementById('attachments-base-folder') ? document.getElementById('attachments-base-folder').value : '';
            const startIndex = document.getElementById('start-index') ? document.getElementById('start-index').value : '1'; // Mặc định gửi từ dòng 1 (sau header)
            const endIndex = document.getElementById('end-index') ? document.getElementById('end-index').value : '';


            if (!excelFile) {
                alert('Vui lòng chọn file Excel.');
                showLoading(false);
                return;
            }
            if (!emailSubject) {
                alert('Vui lòng nhập chủ đề email.');
                showLoading(false);
                return;
            }
            if (!templateId) {
                alert('Vui lòng chọn một mẫu email.');
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

            fetch('/api/email/send-bulk', {
                method: 'POST',
                body: formData,
                // headers: { 'Authorization': 'Bearer ' + localStorage.getItem('access_token') } // Nếu có auth
            })
            .then(response => {
                if (!response.ok) { // Nếu server trả về lỗi (4xx, 5xx)
                    return response.json().then(errData => {
                        throw new Error(errData.message || `Lỗi ${response.status} từ server.`);
                    });
                }
                return response.json();
            })
            .then(data => {
                showLoading(false);
                console.log('Phản hồi từ server:', data);
                let messageHtml = `<div class="alert alert-${data.success ? 'info' : 'danger'}" role="alert">${data.message || 'Hoàn thành xử lý.'}</div>`;
                
                if (data.log_file) {
                    messageHtml += `<p><a href="/api/email/download-log/${data.log_file}" target="_blank" class="btn btn-secondary btn-sm">
                                        <i class="fas fa-download"></i> Tải File Log (${data.log_file})
                                   </a></p>`;
                }

                if (data.results && Array.isArray(data.results)) {
                    messageHtml += '<h4>Chi tiết gửi email:</h4>';
                    messageHtml += `<div class="table-responsive" style="max-height: 400px; overflow-y: auto;">
                                        <table class="table table-striped table-hover table-sm">
                                            <thead class="table-light sticky-top">
                                                <tr>
                                                    <th>Hàng Excel</th>
                                                    <th>Email</th>
                                                    <th>Trạng thái</th>
                                                    <th>Thông báo</th>
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
                resultsArea.innerHTML = messageHtml;
            })
            .catch(error => {
                showLoading(false);
                console.error('Lỗi khi gửi email hàng loạt:', error);
                resultsArea.innerHTML = `<div class="alert alert-danger" role="alert">
                                            <strong>Lỗi nghiêm trọng:</strong> ${error.message || 'Không thể kết nối tới server hoặc có lỗi không xác định.'}
                                         </div>`;
            });
        });
    }

    // --- Helper function for loading indicator ---
    function showLoading(isLoading, message = "Đang tải...") {
        if (loadingIndicator) {
            const loadingMessage = loadingIndicator.querySelector('.loading-message');
            if (loadingMessage) {
                loadingMessage.textContent = message;
            }
            loadingIndicator.style.display = isLoading ? 'flex' : 'none';
        }
    }

    // --- Initial Load ---
    loadDynamicTemplates(); // Tải danh sách mẫu email khi trang được tải

    // Có thể bạn muốn gọi hàm `loadAvailablePlaceholders()` từ `templates.js` nếu có để hiển thị các placeholder có sẵn.
    if (typeof loadAvailablePlaceholders === 'function') {
         loadAvailablePlaceholders();
    }
});