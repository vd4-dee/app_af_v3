# Kế hoạch Nâng cấp Tính năng Bulk Email Linh hoạt

**Ngày tạo:** 21 tháng 5 năm 2025
**Người tạo:** Gemini AI
**Mục tiêu:** Xây dựng lại tính năng `bulk_mail` để hỗ trợ template email tùy chỉnh và ánh xạ biến động từ file Excel, đáp ứng cả Frontend (FE) và Backend (BE).

## I. Hiện trạng và Mục tiêu

* **Hiện trạng:**
    * Hệ thống đang sử dụng các file `api.py`, `logic_email.py`, `routes_email.py` và `bulk_email.html`.
    * Việc đọc dữ liệu từ Excel và sử dụng template còn cứng nhắc, các biến được định nghĩa trước.
    * Thư mục template (`TEMPLATE_FOLDER` trong `api.py`) đang trỏ đến `static/email_templates` và cơ chế load template trong `routes_email.py` (hàm `load_email_templates`) còn đơn giản, đọc từ thư mục 'file' cố định.
* **Mục tiêu:**
    1.  Người dùng có thể upload file Excel với bất kỳ cột dữ liệu nào.
    2.  Người dùng có thể tạo/upload/chọn template HTML với các biến (placeholders) tương ứng với tên cột trong file Excel.
    3.  Hệ thống tự động thay thế các biến trong template bằng dữ liệu từ Excel cho từng email.
    4.  Cung cấp giao diện quản lý template (CRUD).
    5.  Cải thiện trải nghiệm người dùng với việc hiển thị biến và xem trước email.
    6.  Tổ chức lại cấu trúc dự án theo hướng module hóa và dễ bảo trì.

## II. Định dạng Template Đề xuất

* Sử dụng cú pháp dấu ngoặc kép: `{{ten_bien_trong_excel}}`.
    * Ví dụ: `Kính gửi {{HoVaTen}}, thông báo về đơn hàng {{MaDonHang}} của bạn.`
* Áp dụng cho cả nội dung email (body) và tiêu đề email (subject).

## III. Cấu trúc Thư mục Đề xuất (Đã thống nhất)

your_flask_project_root/
├── app/                                # Thư mục chính của ứng dụng Flask
│   ├── init.py                     # Khởi tạo app, đăng ký Blueprints, cấu hình cơ bản
│   ├── static/                         # CSS, JavaScript, Images
│   │   ├── css/
│   │   │   └── style.css
│   │   ├── js/
│   │   │   └── main.js                 # JS chung
│   │   │   └── bulk_email.js           # JS cho trang bulk email
│   │   └── images/
│   ├── templates/                      # Templates HTML chung (base.html, layouts)
│   │   ├── base.html
│   │   └── errors/
│   │       ├── 404.html
│   │       └── 500.html
│   ├── modules/                        # Nơi chứa các module tính năng
│   │   └── email/                      # Module Email
│   │       ├── init.py             # Khởi tạo Blueprint cho module email
│   │       ├── routes.py               # Routes cho giao diện người dùng (trang bulk_email.html)
│   │       ├── api_routes.py           # Routes cho các API (gửi mail, quản lý template)
│   │       ├── logic.py                # Logic nghiệp vụ chính (xử lý Excel, render template, gửi mail)
│   │       ├── models.py               # (Tùy chọn) Nếu dùng DB cho template, logs
│   │       ├── forms.py                # (Tùy chọn) Nếu dùng Flask-WTF
│   │       └── templates/              # Templates HTML riêng của module email
│   │           └── email/
│   │               ├── bulk_email.html
│   │               └── manage_templates.html # (Tùy chọn) Trang quản lý templates
│   ├── utils/                          # Các hàm tiện ích dùng chung
│   │   ├── file_helpers.py             # Ví dụ: allowed_file
│   │   └── security.py
│   └── config.py                       # Cấu hình ứng dụng
│
├── instance/                           # Cấu hình riêng tư, nhạy cảm
│   └── config.py
│
├── uploads/                            # Lưu file Excel do người dùng tải lên
│   └── .gitkeep
│
├── logs/                               # Lưu file log của ứng dụng
│   └── .gitkeep
│
├── email_templates_storage/            # Lưu các file HTML template do người dùng tạo/upload
│   └── .gitkeep
│
├── tests/                              # Thư mục chứa các bài test
│
├── venv/                               # Môi trường ảo
├── requirements.txt                    # Các thư viện Python cần thiết
├── run.py                              # Script để chạy ứng dụng
└── .gitignore                          # Các file/thư mục bỏ qua khi commit Git


## IV. Kế hoạch Triển khai Chi tiết

### Giai đoạn 1: Tái cấu trúc và Chuẩn bị Backend Cốt lõi

1.  **Thiết lập Cấu trúc Thư mục Mới:**
    * Tạo các thư mục và file `__init__.py` như mô tả ở trên.
    * Tạo file `run.py` cơ bản để khởi chạy ứng dụng.
    * Tạo file `app/config.py` và `instance/config.py`.
        * Trong `app/config.py` (hoặc `app/__init__.py`), định nghĩa các biến:
            * `UPLOAD_FOLDER = os.path.abspath(os.path.join(BASE_DIR, '..', 'uploads'))`
            * `LOG_FOLDER = os.path.abspath(os.path.join(BASE_DIR, '..', 'logs'))`
            * `EMAIL_TEMPLATES_STORAGE_FOLDER = os.path.abspath(os.path.join(BASE_DIR, '..', 'email_templates_storage'))`
            * `(BASE_DIR` là thư mục gốc của `app`)
        * Đảm bảo các thư mục này được tạo khi ứng dụng khởi chạy (trong `create_app` của `app/__init__.py`).

2.  **Chuyển đổi Code Hiện tại vào Cấu trúc Mới:**
    * **`app/__init__.py`**:
        * Viết hàm `create_app()` để khởi tạo Flask app, load config, tạo các thư mục cần thiết.
        * Khởi tạo và đăng ký `email_bp` (Blueprint cho giao diện) và `email_api_bp` (Blueprint cho API) từ module email.
    * **`app/modules/email/__init__.py`**:
        * Định nghĩa `email_bp = Blueprint('email', __name__, template_folder='templates')`.
        * Định nghĩa `email_api_bp = Blueprint('email_api', __name__)`.
        * Import `routes` và `api_routes` của module.
    * **`app/modules/email/logic.py`**:
        * Chuyển toàn bộ nội dung từ `logic_email.py` vào đây.
        * Chuyển hàm `send_bulk_emails_backend` từ `api.py` cũ vào đây, đổi tên nếu cần (ví dụ: `process_and_send_emails`).
        * Hàm `allowed_file` từ `api.py` cũ có thể chuyển vào `app/utils/file_helpers.py`.
    * **`app/modules/email/api_routes.py`**:
        * Chuyển các định nghĩa route API (ví dụ: `/api/email/send-bulk`, `/api/email/logs/<filename>`) từ `api.py` cũ vào đây, sử dụng `email_api_bp`.
        * Route `/api/email/send-bulk` sẽ gọi hàm `process_and_send_emails` từ `app.modules.email.logic`.
    * **`app/modules/email/routes.py`**:
        * Chuyển các định nghĩa route giao diện (ví dụ: `/bulk`) từ `routes_email.py` cũ vào đây, sử dụng `email_bp`.
        * Hàm `load_email_templates` từ `routes_email.py` cũ sẽ được **loại bỏ** ở giai đoạn này và thay thế bằng API quản lý template sau.
    * **`app/modules/email/templates/email/bulk_email.html`**:
        * Chuyển file `bulk_email.html` hiện tại vào đây.
        * Cập nhật `action` của form để trỏ đến route API mới (ví dụ: `{{ url_for('email_api.send_bulk_endpoint_name') }}`).
        * Loại bỏ phần select template HTML tĩnh, sẽ được thay thế sau.

3.  **Cập nhật Logic Backend Chính (trong `app/modules/email/logic.py`):**
    * Sửa hàm `process_and_send_emails` (tên cũ `send_bulk_emails_backend`):
        * **Đầu vào:** Nhận `excel_file_path`, `html_template_content` (nội dung chuỗi của template), `subject_template` (chuỗi tiêu đề có thể chứa biến), `attachments_info` (thông tin file đính kèm), `start_index`, `end_index`.
        * **Đọc Excel:** Sử dụng `pandas` để đọc `excel_file_path`. Lấy danh sách header (`excel_headers = list(df.columns)`).
        * **Xử lý Template với Jinja2:**
            * `from jinja2 import Environment`
            * `env = Environment()`
            * Trong vòng lặp từng dòng của file Excel:
                * `row_data = row.to_dict()`
                * `email_subject_rendered = env.from_string(subject_template).render(row_data)`
                * `email_body_rendered = env.from_string(html_template_content).render(row_data)`
                * Gọi hàm gửi email (ví dụ `send_single_email_outlook` đã có trong `logic_email.py` cũ) với `email_subject_rendered` và `email_body_rendered`.
        * **Xử lý file đính kèm:** Tạm thời giữ nguyên logic cũ nếu có, hoặc lên kế hoạch cải tiến sau (ví dụ: cột `AttachmentPath` trong Excel).
        * **Logging:** Giữ nguyên cơ chế logging hiện tại, đảm bảo ghi log vào `LOG_FOLDER`.

### Giai đoạn 2: Phát triển Tính năng Template Linh hoạt (FE & BE)

1.  **Backend - API Quản lý Template (trong `app/modules/email/api_routes.py` và `logic.py`):**
    * **Logic (trong `app/modules/email/logic.py`):**
        * `save_email_template(template_name, html_content)`: Lưu nội dung HTML vào file trong `EMAIL_TEMPLATES_STORAGE_FOLDER` với tên `template_name.html`.
        * `get_email_template(template_name)`: Đọc nội dung file `template_name.html`.
        * `list_email_templates()`: Liệt kê các file `.html` trong `EMAIL_TEMPLATES_STORAGE_FOLDER`.
        * `update_email_template(template_name, new_html_content)`: Ghi đè file template.
        * `delete_email_template(template_name)`: Xóa file template.
    * **API Endpoints (trong `app/modules/email/api_routes.py`):**
        * `POST /api/email/templates`: Nhận `name` và `html_content`, gọi `save_email_template`.
        * `GET /api/email/templates`: Gọi `list_email_templates`, trả về danh sách tên template.
        * `GET /api/email/templates/<template_name>`: Gọi `get_email_template`.
        * `PUT /api/email/templates/<template_name>`: Nhận `html_content`, gọi `update_email_template`.
        * `DELETE /api/email/templates/<template_name>`: Gọi `delete_email_template`.

2.  **Frontend - Cập nhật Giao diện `bulk_email.html` (trong `app/modules/email/templates/email/bulk_email.html` và `app/static/js/bulk_email.js`):**
    * **Ô nhập Subject:** Thêm trường `<input type="text" id="email-subject" name="email_subject" placeholder="Tiêu đề email (có thể dùng {{bien}})">`.
    * **Chọn/Tạo Template:**
        * **Option 1 (Dropdown chọn template đã lưu):**
            * Dùng JavaScript (`bulk_email.js`) gọi API `GET /api/email/templates` khi trang load.
            * Điền vào `<select id="email-template-select" name="selected_template_name">`.
            * Khi chọn một template, có thể fetch nội dung template (`GET /api/email/templates/<template_name>`) và hiển thị trong một `<textarea readonly>` để xem trước.
        * **Option 2 (Textarea để nhập/dán HTML):**
            * Thêm `<textarea id="html-template-content" name="html_template_content" rows="10" placeholder="Dán nội dung HTML template vào đây..."></textarea>`.
        * **Option 3 (Upload file HTML template):**
            * Thêm `<input type="file" id="html-template-file" name="html_template_file" accept=".html">`.
    * **Logic gửi form (trong `bulk_email.js`):**
        * Khi submit form, `FormData` cần bao gồm:
            * `excel_file`
            * `email_subject` (nội dung từ ô subject)
            * Nếu dùng Option 1: `selected_template_name` (tên template đã chọn). BE sẽ tự load nội dung từ `EMAIL_TEMPLATES_STORAGE_FOLDER`.
            * Nếu dùng Option 2: `html_template_content` (nội dung từ textarea).
            * Nếu dùng Option 3: `html_template_file` (file HTML). BE sẽ đọc nội dung file này.
        * Gửi request AJAX đến `/api/email/send-bulk`.

3.  **Backend - Cập nhật API `/api/email/send-bulk` (trong `app/modules/email/api_routes.py` và `logic.py`):**
    * Nhận thêm `email_subject` từ form.
    * Xác định `html_template_content`:
        * Nếu có `selected_template_name`: Đọc file từ `EMAIL_TEMPLATES_STORAGE_FOLDER` (sử dụng `logic.get_email_template`).
        * Nếu có `html_template_content` (dạng text): Sử dụng trực tiếp.
        * Nếu có `html_template_file` (dạng file upload): Đọc nội dung file.
    * Truyền `html_template_content` và `email_subject` (sau khi đã được xác định) vào hàm `process_and_send_emails` trong `logic.py`.

### Giai đoạn 3: Cải thiện Trải nghiệm Người dùng (FE & BE)

1.  **Backend - API Lấy Headers từ Excel (trong `app/modules/email/api_routes.py` và `logic.py`):**
    * **API Endpoint:** `POST /api/email/get-excel-headers`
        * Nhận file Excel upload tạm thời.
        * **Logic (trong `logic.py`):** Đọc file Excel bằng `pandas`, trả về `list(df.columns)`.
        * Xóa file Excel tạm sau khi đọc.
2.  **Frontend - Hiển thị Biến và Xem trước (trong `bulk_email.html` và `bulk_email.js`):**
    * **Hiển thị biến:**
        * Sau khi người dùng chọn file Excel (`excel-file` input `change` event):
            * Upload file Excel lên API `/api/email/get-excel-headers`.
            * Hiển thị danh sách biến trả về (ví dụ: "Các biến có thể dùng: `{{TenCot1}}`, `{{TenCot2}}`...") gần khu vực nhập template.
    * **Xem trước Template (Cơ bản):**
        * **Backend API:** `POST /api/email/preview-template`
            * Nhận `html_template_content`, `subject_template`, và một dictionary `sample_data` (ví dụ: dữ liệu từ dòng đầu tiên của Excel).
            * **Logic (trong `logic.py`):** Render template và subject với `sample_data` bằng Jinja2. Trả về `rendered_subject` và `rendered_body`.
        * **Frontend:**
            * Sau khi người dùng upload Excel và chọn/nhập template:
            * Lấy dòng dữ liệu đầu tiên từ Excel (có thể cần FE đọc client-side hoặc gọi API lấy dòng đầu).
            * Gọi API `/api/email/preview-template` với nội dung template, subject và sample data.
            * Hiển thị `rendered_body` trong một `<iframe>` hoặc `<div>`. Hiển thị `rendered_subject`.

### Giai đoạn 4: Hoàn thiện và Kiểm thử

1.  **Xử lý Lỗi Chi tiết:**
    * Cả FE và BE cần cung cấp thông báo lỗi rõ ràng (ví dụ: biến không tìm thấy, file sai định dạng, không kết nối được Outlook).
    * Trong Jinja2, có thể dùng `{{ TenBien | default('') }}` để tránh lỗi nếu biến không tồn tại.
2.  **Bảo mật:**
    * Validate kỹ các file upload (định dạng, kích thước).
    * Ngăn chặn Path Traversal khi xử lý tên file (đặc biệt là `template_name` và file đính kèm).
    * Xem xét HTML sanitization nếu người dùng có thể tự do tạo template phức tạp và template đó có thể được hiển thị lại ở đâu đó trên trang.
3.  **Tài liệu hóa:**
    * Hướng dẫn sử dụng cho người dùng cuối (cách tạo file Excel, cách viết template).
    * Tài liệu code cho nhà phát triển.
4.  **Kiểm thử Toàn diện:**
    * Kiểm thử với nhiều loại file Excel, nhiều dạng template.
    * Kiểm thử các trường hợp lỗi.
    * Kiểm thử trên các trình duyệt khác nhau (nếu cần).

## V. Phân công (Ví dụ)

* **Agent A (Backend Developer):**
    * Thực hiện Giai đoạn 1 (Tái cấu trúc Backend).
    * Phát triển API quản lý template (Backend - Giai đoạn 2.1).
    * Cập nhật API `/api/email/send-bulk` (Backend - Giai đoạn 2.3).
    * Phát triển API lấy headers Excel và API preview (Backend - Giai đoạn 3).
* **Agent B (Frontend Developer):**
    * Cập nhật `bulk_email.html` và `bulk_email.js` (Frontend - Giai đoạn 2.2).
    * Tích hợp hiển thị biến và xem trước (Frontend - Giai đoạn 3.2).
* **Cả hai Agent:**
    * Tham gia vào Giai đoạn 4 (Hoàn thiện, Kiểm thử, Tài liệu hóa).
    * Thường xuyên trao đổi để đảm bảo FE và BE tương thích.