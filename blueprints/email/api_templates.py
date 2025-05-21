# blueprints/email/api_templates.py
from flask import Blueprint, request, jsonify, current_app, send_from_directory
import os
import shutil # Để xóa thư mục nếu cần
# from .models import EmailTemplate # Import nếu bạn quản lý template qua DB

# ĐỊNH NGHĨA BLUEPRINT Ở ĐÂY VỚI TÊN CHÍNH XÁC
templates_api_bp = Blueprint(
    'templates_api',  # Tên nội bộ của Blueprint
    __name__,
    url_prefix='/api/email/templates' # Tiền tố URL cho tất cả các route trong blueprint này
)

# --- Hằng số hoặc cấu hình cho blueprint này ---
# TEMPLATE_FOLDER nên được lấy từ app.config
# Ví dụ: template_storage_path = current_app.config.get('TEMPLATE_FOLDER')

# --- Hàm helper (nếu có) ---
# Ví dụ hàm get_template_content_by_id mà chúng ta đã thảo luận,
# nếu bạn quyết định nó thuộc về đây và được dùng bởi cả api_templates.py và api.py
# def get_template_content_by_id(template_id_str):
#     # ... logic của bạn ...
#     pass

# --- Định nghĩa các API endpoints cho việc quản lý template ---

@templates_api_bp.route('', methods=['GET'])
def get_email_templates():
    """API để lấy danh sách tất cả các mẫu email."""
    template_storage_path = current_app.config.get('TEMPLATE_FOLDER')
    if not template_storage_path or not os.path.isdir(template_storage_path):
        current_app.logger.error(f"Thư mục template ('{template_storage_path}') không được cấu hình hoặc không tồn tại.")
        return jsonify({'success': False, 'message': 'Lỗi cấu hình server: Thư mục template không tìm thấy.'}), 500

    templates = []
    try:
        for filename in os.listdir(template_storage_path):
            if filename.endswith((".html", ".txt")): # Chỉ lấy file .html hoặc .txt
                template_id = os.path.splitext(filename)[0] # Lấy tên file không có phần mở rộng làm ID
                templates.append({
                    'id': template_id,
                    'name': template_id.replace('_', ' ').title() # Tên hiển thị cơ bản
                })
        return jsonify({'success': True, 'templates': templates})
    except Exception as e:
        current_app.logger.error(f"Lỗi khi liệt kê các mẫu email từ '{template_storage_path}': {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Lỗi server khi lấy danh sách mẫu: {str(e)}'}), 500


@templates_api_bp.route('/<string:template_id>', methods=['GET'])
def get_email_template_by_id(template_id):
    """API để lấy nội dung của một mẫu email cụ thể."""
    template_storage_path = current_app.config.get('TEMPLATE_FOLDER')
    if not template_storage_path:
        return jsonify({'success': False, 'message': 'Lỗi cấu hình server: Thư mục template chưa được định nghĩa.'}), 500

    # Thử tìm file .html trước, sau đó là .txt nếu không thấy
    found_file_path = None
    possible_extensions = ['.html', '.txt']
    actual_filename = ""

    for ext in possible_extensions:
        filename_with_ext = f"{template_id}{ext}"
        file_path = os.path.join(template_storage_path, filename_with_ext)
        if os.path.exists(file_path):
            found_file_path = file_path
            actual_filename = filename_with_ext
            break
    
    if not found_file_path:
        return jsonify({'success': False, 'message': f'Mẫu email với ID "{template_id}" không tìm thấy.'}), 404

    try:
        with open(found_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({
            'success': True,
            'id': template_id,
            'name': template_id.replace('_', ' ').title(), # Hoặc bạn có thể lưu tên riêng
            'filename': actual_filename,
            'content': content
        })
    except Exception as e:
        current_app.logger.error(f"Lỗi khi đọc mẫu email '{found_file_path}': {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Lỗi server khi đọc mẫu email: {str(e)}'}), 500


@templates_api_bp.route('', methods=['POST'])
def create_email_template():
    """API để tạo một mẫu email mới (lưu dưới dạng file)."""
    data = request.json
    if not data or 'name' not in data or 'content' not in data:
        return jsonify({'success': False, 'message': 'Dữ liệu không hợp lệ. Cần có "name" và "content".'}), 400

    template_name = data['name'].strip().lower().replace(' ', '_') # Tạo ID từ tên
    content = data['content']
    # Mặc định lưu là .html, bạn có thể cho người dùng chọn extension
    filename = f"{template_name}.html" 
    template_storage_path = current_app.config.get('TEMPLATE_FOLDER')

    if not template_storage_path:
        return jsonify({'success': False, 'message': 'Lỗi cấu hình server: Thư mục template chưa được định nghĩa.'}), 500

    file_path = os.path.join(template_storage_path, filename)

    if os.path.exists(file_path):
        return jsonify({'success': False, 'message': f'Mẫu email với tên "{template_name}" (file: {filename}) đã tồn tại.'}), 409 # Conflict

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({
            'success': True,
            'message': 'Mẫu email đã được tạo thành công.',
            'id': template_name,
            'filename': filename
        }), 201
    except Exception as e:
        current_app.logger.error(f"Lỗi khi tạo mẫu email '{file_path}': {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Lỗi server khi tạo mẫu email: {str(e)}'}), 500


@templates_api_bp.route('/<string:template_id>', methods=['PUT'])
def update_email_template(template_id):
    """API để cập nhật một mẫu email hiện có (dựa trên ID là tên file không có extension)."""
    data = request.json
    if not data or 'content' not in data:
        return jsonify({'success': False, 'message': 'Dữ liệu không hợp lệ. Cần có "content".'}), 400

    content = data['content']
    template_storage_path = current_app.config.get('TEMPLATE_FOLDER')
    if not template_storage_path:
        return jsonify({'success': False, 'message': 'Lỗi cấu hình server: Thư mục template chưa được định nghĩa.'}), 500

    # Tìm file với ID đã cho (bất kể .html hay .txt)
    found_file_path = None
    possible_extensions = ['.html', '.txt']
    for ext in possible_extensions:
        file_path_try = os.path.join(template_storage_path, f"{template_id}{ext}")
        if os.path.exists(file_path_try):
            found_file_path = file_path_try
            break
    
    if not found_file_path:
        return jsonify({'success': False, 'message': f'Mẫu email với ID "{template_id}" không tìm thấy để cập nhật.'}), 404

    try:
        with open(found_file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({
            'success': True,
            'message': f'Mẫu email "{template_id}" đã được cập nhật.',
            'id': template_id,
            'filename': os.path.basename(found_file_path)
        })
    except Exception as e:
        current_app.logger.error(f"Lỗi khi cập nhật mẫu email '{found_file_path}': {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Lỗi server khi cập nhật mẫu email: {str(e)}'}), 500


@templates_api_bp.route('/<string:template_id>', methods=['DELETE'])
def delete_email_template(template_id):
    """API để xóa một mẫu email (dựa trên ID là tên file không có extension)."""
    template_storage_path = current_app.config.get('TEMPLATE_FOLDER')
    if not template_storage_path:
        return jsonify({'success': False, 'message': 'Lỗi cấu hình server: Thư mục template chưa được định nghĩa.'}), 500

    found_file_path = None
    possible_extensions = ['.html', '.txt']
    for ext in possible_extensions:
        file_path_try = os.path.join(template_storage_path, f"{template_id}{ext}")
        if os.path.exists(file_path_try):
            found_file_path = file_path_try
            break
            
    if not found_file_path:
        return jsonify({'success': False, 'message': f'Mẫu email với ID "{template_id}" không tìm thấy để xóa.'}), 404

    try:
        os.remove(found_file_path)
        return jsonify({
            'success': True,
            'message': f'Mẫu email "{template_id}" (file: {os.path.basename(found_file_path)}) đã được xóa.'
        })
    except Exception as e:
        current_app.logger.error(f"Lỗi khi xóa mẫu email '{found_file_path}': {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Lỗi server khi xóa mẫu email: {str(e)}'}), 500


@templates_api_bp.route('/<string:template_id>/preview', methods=['POST']) # Hoặc GET nếu sample data qua query params
def preview_email_template(template_id):
    """API để xem trước một mẫu email với dữ liệu mẫu (nếu có)."""
    from jinja2 import Environment, select_autoescape # Import Jinja2 ở đây

    template_data = get_email_template_by_id(template_id).get_json() # Gọi lại API lấy nội dung
    if not template_data or not template_data.get('success'):
        return jsonify({'success': False, 'message': f'Không thể lấy nội dung mẫu "{template_id}" để xem trước.'}), template_data.get('status_code', 404)

    html_content = template_data['content']
    sample_data = request.json if request.is_json else {} # Lấy sample data từ body request (JSON)

    try:
        # Sử dụng Jinja2 để render template với sample_data
        env = Environment(autoescape=select_autoescape(['html', 'xml']))
        jinja_template = env.from_string(html_content)
        rendered_preview = jinja_template.render(sample_data)
        return jsonify({'success': True, 'preview_html': rendered_preview})
    except Exception as e:
        current_app.logger.error(f"Lỗi khi render xem trước cho mẫu '{template_id}': {e}", exc_info=True)
        # Trả về nội dung gốc nếu không render được, kèm thông báo lỗi
        return jsonify({
            'success': False,
            'message': f'Lỗi khi render xem trước: {str(e)}. Hiển thị nội dung gốc.',
            'preview_html': html_content # Fallback to raw content
        }), 500

# Bạn có thể thêm các API khác như sao chép template, import/export templates, v.v.