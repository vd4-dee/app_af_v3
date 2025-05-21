# wsgi.py
import os
from your_application_root_package_name import create_app # Thay thế your_application_root_package_name

# Lấy tên class config từ biến môi trường, ví dụ PRODUCTION_CONFIG
# Hoặc bạn có thể hardcode nếu chỉ có 1 config cho production
config_name = os.environ.get('FLASK_CONFIG') or 'config.ProductionConfig'
application = create_app(config_object_name=config_name)

# Gunicorn sẽ tìm biến 'application' này