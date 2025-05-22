# filename: config.py
import os

class Config:
    """
    Lớp cấu hình cơ sở cho ứng dụng Flask.
    Các cấu hình cụ thể cho môi trường (Development, Production, Testing)
    có thể kế thừa từ lớp này.
    """
    # Khóa bí mật để bảo vệ session và các dữ liệu nhạy cảm khác
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_very_secret_key_please_change_it'

    # Cấu hình SQLAlchemy (ví dụ sử dụng SQLite)
    # Bạn nên thay thế bằng URI kết nối database thực tế của bạn (PostgreSQL, MySQL, ...)
    # Ví dụ: 'postgresql://user:password@host:port/database'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False # Tắt theo dõi thay đổi đối tượng để tiết kiệm tài nguyên

    # Thư mục lưu trữ template email (sử dụng bởi blueprints/email/api_templates.py)
    # Đảm bảo thư mục này tồn tại hoặc được tạo khi ứng dụng khởi động
    TEMPLATE_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'email_templates_storage')

    # Thư mục upload file Excel cho module email
    # Đảm bảo thư mục này tồn tại hoặc được tạo khi ứng dụng khởi động
    UPLOAD_FOLDER_EXCEL = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'uploads', 'excels')

    # Thư mục lưu log cho module email
    # Đảm bảo thư mục này tồn tại hoặc được tạo khi ứng dụng khởi động
    LOG_FOLDER_EMAIL = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'logs', 'email_module')

    # Cấu hình khác của ứng dụng có thể được thêm vào đây
    # Ví dụ: MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USERNAME, MAIL_PASSWORD cho gửi mail qua SMTP
    # FLASK_ADMIN_SWATCH = 'cerulean' # Theme cho Flask-Admin nếu bạn dùng

    # Cấu hình cho việc cho phép các origin nào có thể truy cập API (CORS)
    # CORS_ALLOWED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"] # Ví dụ cho React dev server

    # Các cấu hình liên quan đến logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()

    # IMPORTANT: Replace 'YOUR_ACTUAL_BASE32_OTP_SECRET_HERE' with a real, securely generated Base32 secret.
    # You can generate one using `pyotp.random_base32()` in a Python console.
    # Example: OTP_SECRET = 'JBSWY3DPEHPK3PXP'
    OTP_SECRET = 'YOUR_ACTUAL_BASE32_OTP_SECRET_HERE'
    DRIVER_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'chromedriver.exe')
    DOWNLOAD_BASE_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'downloads')

    # --- Optional Configuration (UI Defaults) ---
    DEFAULT_EMAIL = os.getenv('DEFAULT_EMAIL', 'khangvd4')
    # Set DEFAULT_PASSWORD environment variable or leave empty for UI input (recommended)
    DEFAULT_PASSWORD = os.getenv('DEFAULT_PASSWORD', 'toiGHEThack@123') # <-- REMOVE or set ENV VAR, avoid hardcoding password

    # --- Other Configuration ---
    # List of report URLs that require region selection
    REGION_REQUIRED_REPORT_URLS = [
        'https://bi.nhathuoclongchau.com.vn/MIS/PHAR/PHARFAF030.aspx'
        # Add other report URLs here if they need region selection
    ]


    # --- Validation and Warnings ---
    if not OTP_SECRET or OTP_SECRET == 'YOUR_ACTUAL_BASE32_OTP_SECRET_HERE':
        print("\n" + "="*60)
        print("== WARNING: OTP_SECRET is using the default example value or is empty! ==")
        print("== Please configure it securely via Environment Variables or other methods. ==")
        print("="*60 + "\n")

    if DEFAULT_PASSWORD and DEFAULT_PASSWORD != '': # Check if password is hardcoded
        print("\n" + "="*60)
        print("== WARNING: DEFAULT_PASSWORD is set in config.py! ==")
        print("== It's highly recommended to use Environment Variables or leave it empty ==")
        print("== for the user to input it in the UI. ==")
        print("="*60 + "\n")

    if not os.path.exists(DRIVER_PATH):
        print(f"\nWARNING: ChromeDriver path does not exist: {DRIVER_PATH}. Automation will likely fail. Check the path or set the CHROMEDRIVER_PATH environment variable.\n")

    if not os.path.exists(DOWNLOAD_BASE_PATH):
        print(f"\nWARNING: Download base path does not exist: {DOWNLOAD_BASE_PATH}. The application will attempt to create it, but please verify the configuration.\n")

    REPORTS = [
        {
            "name": "FAF030",
            "url": "https://bi.nhathuoclongchau.com.vn/MIS/PHAR/PHARFAF030.aspx"
        }
    ]

    # --- Email Module Defaults ---
    DEFAULT_SENDER = DEFAULT_EMAIL
    EMAIL_BATCH_SIZE = int(os.getenv('EMAIL_BATCH_SIZE', '50'))
    EMAIL_PAUSE_SECONDS = int(os.getenv('EMAIL_PAUSE_SECONDS', '5'))
    EMAIL_LOG_PATH = os.getenv('EMAIL_LOG_PATH', os.path.abspath('email_log.csv'))

    # Path for download logs (used by blueprints/download.py)
    LOG_FILE_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'logs', 'download_log.csv')

    # Path for saved configurations (used by blueprints/download.py for config management)
    CONFIG_FILE_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'configs.json')
