# app.py (hoặc có thể là __init__.py trong thư mục gốc ứng dụng của bạn)
import os
import threading
import atexit
import logging
import json
import traceback
import logging.handlers
from datetime import datetime, timezone, timedelta

from flask import (
    Flask, render_template, request, jsonify, Response,
    session, flash, redirect, url_for, current_app, send_from_directory
)
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

# Import extensions đã được khởi tạo (nhưng chưa gắn vào app)
from extensions import db # Giả sử bạn có file extensions.py định nghĩa db = SQLAlchemy()

# Import các hàm xác thực và tiện ích
# (Giả sử auth_google_sheet.py và utils_legacy.py nằm ở thư mục gốc hoặc trong python path)
import auth_google_sheet
from utils_legacy import load_configs as load_legacy_configs, save_configs as save_legacy_configs
# Bạn có thể xem xét việc chuyển utils_legacy vào một package 'utils'

# --- Globals that are truly app-independent or need to be initialized before app ---
# Scheduler có thể được khởi tạo ở đây vì nó không phụ thuộc trực tiếp vào app instance lúc khởi tạo
# nhưng jobstores và executors sẽ được cấu hình trong create_app
scheduler = BackgroundScheduler(
    jobstores={'default': MemoryJobStore()},
    executors={'default': ThreadPoolExecutor(5)}, # Giới hạn số luồng cho scheduler
    job_defaults={'coalesce': False, 'max_instances': 1}
)

# Lock có thể vẫn cần thiết nếu các tác vụ nền truy cập tài nguyên dùng chung
# mà không thể quản lý qua request context.
# Tuy nhiên, hãy cố gắng giảm thiểu việc sử dụng global lock nếu có thể.
global_lock = threading.Lock()

# Trạng thái dùng chung, nên được quản lý cẩn thận hơn, có thể thông qua một service/class
# Hoặc nếu chỉ dùng trong context của request thì không cần global
shared_app_state = {
    "is_automation_running": False,
    "status_messages": []
}


def create_app(config_object_name='config.Config'):
    """
    Application factory function.
    """
    app = Flask(__name__, instance_relative_config=True)

    # Initialize thread lock for thread-safe operations
    app.lock = threading.Lock()
    app.status_messages = []  # Initialize status_messages list
    app.shared_state = shared_app_state # Attach shared_app_state to the app object

    # 1. Load Configuration
    # ---------------------
    app.config.from_object(config_object_name)
    # Bạn có thể load thêm config từ file instance/config.py nếu cần
    # app.config.from_pyfile('production_config.py', silent=True)

    # 2. Initialize Extensions
    # ------------------------
    db.init_app(app) # Gắn SQLAlchemy vào app
    
    # Configure session
    app.config.update(
        SESSION_COOKIE_SECURE=False,  # Set to True in production with HTTPS
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=86400  # 1 day in seconds
    )

    # 3. Initialize Global Objects/State tied to App Context (nếu cần)
    # -------------------------------------------------------------
    app.config['GLOBAL_LOCK'] = global_lock # Nếu các blueprint cần truy cập
    app.config['SHARED_APP_STATE'] = shared_app_state # Cẩn thận khi dùng global state

    # Đường dẫn file configs.json và download_log.csv nên được lấy từ app.config
    # được định nghĩa trong config.py
    # Ví dụ: app.config['LEGACY_CONFIG_FILE_PATH']
    #        app.config['LEGACY_LOG_FILE_PATH']
    # Hiện tại, các hàm utils_legacy đang dùng đường dẫn cố định, cần xem xét lại.

    # 4. Setup Logging
    # ----------------
    # (Bạn có thể cấu hình logging chi tiết hơn ở đây, ví dụ: ghi ra file)
    # 4. Setup Logging
    # ----------------
    if not app.debug and not app.testing:
        log_dir = os.path.join(app.instance_path, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        # Dòng này sẽ không còn lỗi nữa
        file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, 'flask_app.log'),
            maxBytes=102400, backupCount=10, encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        app.logger.addHandler(file_handler)
        app.logger.setLevel(app.config.get('LOG_LEVEL', 'INFO'))
        app.logger.info('Ứng dụng Flask đã khởi động ở chế độ production.')
    else:
        app.logger.setLevel(logging.DEBUG)
        app.logger.info('Ứng dụng Flask đã khởi động ở chế độ DEBUG.')

    # 5. Create Necessary Directories (lấy đường dẫn từ app.config)
    # -----------------------------------------------------------
    try:
        # Ví dụ: các thư mục trong config.py như UPLOAD_FOLDER_EXCEL, LOG_FOLDER_EMAIL
        # DOWNLOAD_BASE_PATH cũng nên nằm trong config.py
        download_base = app.config.get('DOWNLOAD_BASE_PATH', os.path.join(app.instance_path, 'downloads'))
        os.makedirs(download_base, exist_ok=True)
        app.logger.info(f"Thư mục download mặc định: {download_base}")

        # Các thư mục khác từ config.py
        for folder_key in ['UPLOAD_FOLDER_EXCEL', 'LOG_FOLDER_EMAIL', 'TEMPLATE_FOLDER']:
            folder_path = app.config.get(folder_key)
            if folder_path:
                os.makedirs(folder_path, exist_ok=True)
                app.logger.info(f"Đã kiểm tra/tạo thư mục {folder_key}: {folder_path}")
            else:
                app.logger.warning(f"Đường dẫn cho {folder_key} không được định nghĩa trong config.")

        # Tạo file configs.json nếu chưa có (nên quản lý qua một service thay vì trực tiếp)
        legacy_config_path = app.config.get('LEGACY_CONFIG_FILE_PATH',
                                            os.path.join(app.instance_path, 'configs.json'))
        if not os.path.exists(legacy_config_path):
            app.logger.warning(f"File cấu hình {legacy_config_path} không tồn tại. Tạo file trống.")
            try:
                with open(legacy_config_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f)
            except IOError as e:
                app.logger.error(f"Không thể tạo file cấu hình mặc định: {e}")
                # Có thể raise lỗi ở đây để dừng ứng dụng nếu file này là bắt buộc
    except OSError as e:
        app.logger.error(f"Lỗi khi tạo thư mục cần thiết: {e}")


    # 6. Initialize Scheduler
    # -----------------------
    # (scheduler đã được khởi tạo ở global scope)
    if not scheduler.running:
        try:
            # Bạn có thể thêm job stores hoặc executors khác ở đây nếu cần,
            # ví dụ: SQLAlchemyJobStore nếu muốn lưu jobs vào DB
            # scheduler.add_jobstore(SQLAlchemyJobStore(url=app.config['SQLALCHEMY_DATABASE_URI']), 'default_db')
            scheduler.start(paused=False)
            app.logger.info("APScheduler đã khởi động.")
            # Attach scheduler to app context
            app.scheduler = scheduler 
            app.logger.info("APScheduler attached to Flask app context.")
            # Đảm bảo scheduler được tắt khi ứng dụng thoát
            atexit.register(lambda: scheduler.shutdown())
            app.logger.info("Đã đăng ký hook tắt APScheduler.")
        except Exception as e:
            app.logger.error(f"LỖI NGHIÊM TRỌNG: Không thể khởi động APScheduler: {e}")
            app.logger.error(traceback.format_exc())
            # Trong production, bạn có thể muốn dừng ứng dụng nếu scheduler là cốt lõi

    # 7. Register Blueprints
    # --------------------
    # Import blueprints here to avoid circular imports
    from blueprints.download import download_bp
    from blueprints.email import init_email
    from blueprints.email.api import api_email_bp
    from blueprints.email import api_templates
    
    # Initialize email blueprint with the app
    # This will register the email_bp blueprint
    init_email(app)
    
    # Register other blueprints with proper URL prefixes
    # Note: email_bp is already registered by init_email()
    app.register_blueprint(api_email_bp)  # Already has /api/email prefix defined in the blueprint
    app.register_blueprint(api_templates.templates_api_bp, url_prefix='/api/email')
    app.register_blueprint(download_bp, url_prefix='/download')
    # app.register_blueprint(auth_bp, url_prefix='/auth')

    # 8. Define Basic Routes (Login, Logout, Index, Docs)
    # --------------------------------------------------
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')
            app.logger.debug(f"Login attempt - Email: {email}, Password: {'*' * len(password) if password else 'None'}")
            
            if not email or not password:
                flash('Vui lòng nhập email và mật khẩu.', 'warning')
                return render_template('login.html', title="Đăng nhập")

            # Verify user credentials
            credentials_valid = auth_google_sheet.check_user_credentials(email, password)
            app.logger.debug(f"Credentials valid: {credentials_valid}")
            
            if credentials_valid:
                # Get additional user info
                user_info = auth_google_sheet.get_user_auth_data(email) or {}
                app.logger.debug(f"User info from Google Sheet: {user_info}")
                
                # Default permissions if not specified
                if not user_info.get('permissions') and user_info.get('role') == 'owner':
                    user_info['permissions'] = ['all']  # Grant all permissions to owners by default
                
                # Set up session
                session.permanent = True
                session['user'] = email
                session['role'] = user_info.get('role', 'user')
                # Set web_access to True if user has any permissions or is an owner
                has_permissions = bool(user_info.get('permissions')) or user_info.get('role') == 'owner'
                session['web_access'] = has_permissions
                session['logged_in_time'] = datetime.now(timezone.utc).isoformat()
                
                app.logger.info(f"Session after login: {dict(session)}")
                app.logger.info(f"User '{email}' logged in with role '{session['role']}' and web_access: {has_permissions}")
                
                # Debug: Check session before redirect
                app.logger.debug(f"Session before redirect: {dict(session)}")
                
                response = redirect(url_for('index'))
                app.logger.debug(f"Response headers: {response.headers}")
                
                flash(f'Chào mừng {email}!', 'success')
                return response
            else:
                flash('Email hoặc mật khẩu không đúng.', 'danger')
                app.logger.warning(f"Đăng nhập thất bại cho email '{email}'.")
                
        # For GET requests or failed logins
        app.logger.debug("Rendering login page")
        return render_template('login.html', title="Đăng nhập")

    @app.route('/logout')
    def logout():
        user = session.pop('user', None)
        session.pop('role', None)
        session.pop('web_access', None)
        session.pop('logged_in_time', None)
        flash('Bạn đã đăng xuất.', 'info')
        app.logger.info(f"Người dùng '{user}' đã đăng xuất.")
        return redirect(url_for('login'))

    @app.route('/')
    def index():
        app.logger.debug(f"Index route - Session data: {dict(session)}")
        app.logger.debug(f"Request headers: {dict(request.headers)}")
        
        if 'user' not in session:
            app.logger.warning("No user in session, redirecting to login")
            flash('Vui lòng đăng nhập để truy cập.', 'warning')
            return redirect(url_for('login'))
        
        # Get fresh user info from the database
        user_info = auth_google_sheet.get_user_auth_data(session['user']) or {}
        
        # Update session with fresh data
        if user_info:
            session['role'] = user_info.get('role', 'user')
            session['user_role'] = user_info.get('role', 'user')  # For template
            session['user_permissions'] = user_info.get('permissions', []) or []  # Ensure it's a list
            has_permissions = bool(user_info.get('permissions')) or user_info.get('role') == 'owner'
            session['web_access'] = has_permissions
            app.logger.debug(f"Updated session with fresh data: {dict(session)}")
            app.logger.debug(f"User permissions: {session.get('user_permissions')}")
        
        if not session.get('web_access'):
            app.logger.warning(f"User {session.get('user')} with role {session.get('role')} does not have web access")
            app.logger.warning(f"User info from DB: {user_info}")
            flash('Tài khoản của bạn không có quyền truy cập. Vui lòng liên hệ quản trị viên.', 'danger')
            return redirect(url_for('login'))

        app.logger.debug(f"User {session.get('user')} with role {session.get('role')} accessing index with web_access: {session.get('web_access')}")
        
        # Lấy các giá trị mặc định từ config.py (nên được load vào app.config)
        # Ví dụ: app.config.get('DEFAULT_PERIOD_MONTH'), app.config.get('DEFAULT_PERIOD_YEAR')
        try:
            # Set the config file path in the app config if not already set
            if 'CONFIG_FILE_PATH' not in current_app.config:
                current_app.config['CONFIG_FILE_PATH'] = os.path.join(
                    current_app.instance_path, 'configs.json'
                )
            # Load configs using the function that reads from current_app.config
            default_config = load_legacy_configs()
            app.logger.debug(f"Loaded default config: {default_config}")
        except Exception as e:
            app.logger.error(f"Error loading config: {e}")
            default_config = {}
        # Get download configuration
        download_config = {}
        try:
            # Load download configuration from file or database
            download_config_path = os.path.join(current_app.instance_path, 'download_config.json')
            if os.path.exists(download_config_path):
                with open(download_config_path, 'r', encoding='utf-8') as f:
                    download_config = json.load(f)
        except Exception as e:
            app.logger.error(f"Error loading download config: {e}")
            download_config = {}
            
        # Ensure default values for required fields
        if 'reports' not in download_config:
            download_config['reports'] = []
        if 'regions' not in download_config:
            download_config['regions'] = []
            
        app.logger.debug(f"Serving index with download config: {download_config}")
        
        return render_template(
            'index.html',
            title="Trang chủ",
            username=session.get('user'),
            role=session.get('role'),
            user_role=session.get('user_role'),
            user_permissions=session.get('user_permissions', []),
            default_period_month=default_config.get('DEFAULT_PERIOD_MONTH', datetime.now().month),
            default_period_year=default_config.get('DEFAULT_PERIOD_YEAR', datetime.now().year),
            default_start_date=default_config.get('DEFAULT_START_DATE', (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')),
            default_end_date=default_config.get('DEFAULT_END_DATE', datetime.now().strftime('%Y-%m-%d')),
            download_config=json.dumps(download_config)  # Pass as JSON string for JavaScript
        )

    @app.route('/docs/')
    @app.route('/docs/<path:path>')
    def serve_docs(path="index.html"):
        # Đảm bảo rằng người dùng đã đăng nhập và có quyền truy cập
        if 'user' not in session or not session.get('web_access'):
            flash('Vui lòng đăng nhập để xem tài liệu.', 'warning')
            return redirect(url_for('login'))

        # Đường dẫn tới thư mục 'site' của MkDocs, nên lấy từ config
        mkdocs_site_dir = app.config.get('MKDOCS_SITE_DIR', os.path.join(app.root_path, 'site'))
        if not os.path.isdir(mkdocs_site_dir):
            app.logger.error(f"Thư mục tài liệu MkDocs không tìm thấy: {mkdocs_site_dir}")
            flash('Không tìm thấy thư mục tài liệu.', 'danger')
            return redirect(url_for('index')) # Hoặc trang lỗi 404
        return send_from_directory(mkdocs_site_dir, path)


    @app.route('/change-password', methods=['GET', 'POST'])
    def change_password_route():
        if 'user' not in session:
            flash('Vui lòng đăng nhập.', 'warning')
            return redirect(url_for('login'))

        if request.method == 'POST':
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            username = session['user']

            if not all([current_password, new_password, confirm_password]):
                flash('Vui lòng điền đầy đủ thông tin.', 'warning')
                return render_template('change_password.html', title="Đổi mật khẩu")

            if new_password != confirm_password:
                flash('Mật khẩu mới và xác nhận mật khẩu không khớp.', 'danger')
                return render_template('change_password.html', title="Đổi mật khẩu")

            success, message = auth_google_sheet.change_password(username, current_password, new_password)
            if success:
                flash(message, 'success')
                app.logger.info(f"Người dùng '{username}' đổi mật khẩu thành công.")
                return redirect(url_for('index'))
            else:
                flash(message, 'danger')
                app.logger.warning(f"Người dùng '{username}' đổi mật khẩu thất bại: {message}")

        return render_template('change_password.html', title="Đổi mật khẩu")

    # 9. Add Context Processors or Error Handlers if needed
    # ---------------------------------------------------
    # @app.context_processor
    # def inject_global_vars():
    #     return dict(app_version="1.0.0")

    # @app.errorhandler(404)
    # def page_not_found(e):
    #    return render_template('404.html'), 404 # Cần tạo template 404.html

    app.logger.info("Ứng dụng Flask đã được cấu hình và sẵn sàng.")
    return app

# --- Điểm khởi chạy ứng dụng (ví dụ: trong file run.py hoặc wsgi.py) ---
# Nếu bạn muốn chạy trực tiếp file này (ví dụ khi phát triển):
if __name__ == '__main__':
    # Lấy tên class config từ biến môi trường hoặc dùng mặc định
    # Ví dụ: FLASK_CONFIG=config.DevelopmentConfig python app.py
    config_name = os.environ.get('FLASK_CONFIG') or 'config.Config'
    app = create_app(config_object_name=config_name)

    # Sử dụng Waitress cho môi trường "production-like" khi chạy trực tiếp
    # Trong production thực tế, bạn sẽ dùng Gunicorn/uWSGI + Nginx
    HOST = app.config.get('HOST', '127.0.0.1')
    PORT = app.config.get('PORT', 5000)
    DEBUG_MODE = app.config.get('DEBUG', False) # Lấy DEBUG từ config

    if not DEBUG_MODE: # Chỉ dùng Waitress nếu không ở chế độ DEBUG
        try:
            from waitress import serve
            print(f"Khởi chạy ứng dụng với Waitress trên http://{HOST}:{PORT}")
            serve(app, host=HOST, port=PORT, threads=app.config.get('WAITRESS_THREADS', 10))
        except ImportError:
            print("\n--- CẢNH BÁO ---")
            print("Waitress không được cài đặt (pip install waitress).")
            print("Sử dụng server phát triển của Flask (KHÔNG PHÙ HỢP CHO PRODUCTION).")
            print("-----------------\n")
            app.run(host=HOST, port=PORT, debug=DEBUG_MODE, threaded=True)
    else:
        # Chạy với server phát triển của Flask khi DEBUG=True
        print(f"Khởi chạy ứng dụng với server phát triển của Flask trên http://{HOST}:{PORT} (DEBUG MODE)")
        app.run(host=HOST, port=PORT, debug=True, threaded=True)
