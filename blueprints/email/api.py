# blueprints/email/api.py
from flask import Blueprint, request, jsonify, current_app, send_from_directory
import os
from werkzeug.utils import secure_filename

# Import logic xử lý email và model (nếu cần)
from .logic_email import process_and_send_emails, parse_excel_data
from .models import EmailTemplate # Đảm bảo model này được định nghĩa trong models.py

api_email_bp = Blueprint('api_email', __name__, url_prefix='/api/email')

# Cấu hình thư mục upload, nên lấy từ config của app
# UPLOAD_FOLDER_EXCEL nên được định nghĩa trong config.py và truy cập qua current_app.config
# Ví dụ: UPLOAD_FOLDER_EXCEL = current_app.config.get('UPLOAD_FOLDER_EXCEL', 'uploads/excels')
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_template_content_by_id(template_id_str):
    """
    Lấy nội dung template email bằng ID từ database.
    Hàm này được định nghĩa trực tiếp trong api.py hoặc import từ models/logic.
    """
    try:
        template_id = int(template_id_str) # Chuyển đổi ID sang integer
        template = EmailTemplate.query.get(template_id)
        if template:
            current_app.logger.info(f"Đã tìm thấy template ID {template_id} trong database.")
            return {'id': template.id, 'name': template.name, 'content': template.content}
        else:
            current_app.logger.warning(f"Không tìm thấy template với ID {template_id} trong database.")
            return None
    except ValueError:
        current_app.logger.error(f"Template ID không hợp lệ (không phải số nguyên): {template_id_str}")
        return None
    except Exception as e:
        # Bắt lỗi tổng quát hơn nếu có vấn đề với DB session hoặc query
        current_app.logger.error(f"Lỗi khi query EmailTemplate với ID {template_id_str}: {e}")
        return None

@api_email_bp.route('/send-bulk', methods=['POST'])
def send_bulk_email_api():
    if 'excel_file' not in request.files:
        return jsonify({'success': False, 'message': 'Không có file Excel nào được tải lên'}), 400

    excel_file = request.files['excel_file']
    email_subject = request.form.get('email_subject', 'Chủ đề mặc định')
    template_id_str = request.form.get('template_id') # Frontend gửi template_id (dưới dạng chuỗi)

    email_column = request.form.get('email_column', 'email')
    attachment_column = request.form.get('attachment_column')
    attachments_base_folder = request.form.get('attachments_base_folder')

    start_index_str = request.form.get('start_index')
    end_index_str = request.form.get('end_index')

    start_index = 0
    if start_index_str and start_index_str.isdigit():
        start_index = int(start_index_str)
        if start_index > 0: # Nếu người dùng nhập 1 nghĩa là dòng đầu tiên sau header
            start_index -= 1

    end_index = None
    if end_index_str and end_index_str.isdigit():
        end_index = int(end_index_str)

    if not excel_file or not excel_file.filename or not allowed_file(excel_file.filename):
        return jsonify({'success': False, 'message': 'File không hợp lệ hoặc không được phép'}), 400

    # Lấy nội dung template dựa trên template_id
    html_template_content = None
    if not template_id_str:
        return jsonify({'success': False, 'message': 'Cần cung cấp template_id'}), 400

    try:
        template_data = get_template_content_by_id(template_id_str) # Gọi hàm đã định nghĩa ở trên
        if template_data and 'content' in template_data:
            html_template_content = template_data['content']
            current_app.logger.info(f"Đã lấy nội dung cho template ID: {template_id_str}")
        else:
            # get_template_content_by_id đã log lỗi, chỉ cần trả về thông báo cho client
            return jsonify({'success': False, 'message': f'Không tìm thấy nội dung cho template ID {template_id_str}'}), 404
    except Exception as e: # Bắt các lỗi không mong muốn khác khi gọi get_template_content_by_id
        current_app.logger.error(f"Lỗi nghiêm trọng khi xử lý template ID {template_id_str}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Lỗi khi lấy template: {str(e)}'}), 500


    upload_folder_excel_config = current_app.config.get('UPLOAD_FOLDER_EXCEL')
    if not upload_folder_excel_config:
        current_app.logger.error("UPLOAD_FOLDER_EXCEL không được cấu hình trong ứng dụng.")
        return jsonify({'success': False, 'message': 'Lỗi cấu hình server: Thư mục upload chưa được định nghĩa.'}), 500

    upload_folder_abs = os.path.join(current_app.root_path, upload_folder_excel_config)
    # Trong thực tế, current_app.config['UPLOAD_FOLDER_EXCEL'] nên là đường dẫn tuyệt đối rồi
    # Nếu nó là tương đối, thì os.path.join(current_app.instance_path, ...) có thể phù hợp hơn
    # Hoặc đảm bảo UPLOAD_FOLDER_EXCEL trong config.py đã là đường dẫn tuyệt đối
    # Ví dụ: UPLOAD_FOLDER_EXCEL = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'uploads', 'excels')

    if not os.path.exists(upload_folder_abs):
        try:
            os.makedirs(upload_folder_abs)
            current_app.logger.info(f"Đã tạo thư mục upload: {upload_folder_abs}")
        except OSError as e:
            current_app.logger.error(f"Không thể tạo thư mục upload {upload_folder_abs}: {e}")
            return jsonify({'success': False, 'message': 'Lỗi server: Không thể tạo thư mục upload.'}), 500


    filename = secure_filename(excel_file.filename)
    excel_file_path = os.path.join(upload_folder_abs, filename)

    try:
        excel_file.save(excel_file_path)
        current_app.logger.info(f"File Excel đã được lưu tại: {excel_file_path}")
    except Exception as e:
        current_app.logger.error(f"Không thể lưu file Excel {excel_file_path}: {e}")
        return jsonify({'success': False, 'message': f'Lỗi server: Không thể lưu file Excel: {str(e)}'}), 500

    # Gọi hàm xử lý chính
    try:
        result = process_and_send_emails(
            excel_file_path=excel_file_path,
            email_subject=email_subject,
            html_template_content=html_template_content,
            email_column_name=email_column,
            attachment_column_name=attachment_column,
            attachments_base_folder=attachments_base_folder,
            start_index=start_index,
            end_index=end_index
        )
    except Exception as e:
        current_app.logger.error(f"Lỗi không mong muốn trong quá trình process_and_send_emails: {e}", exc_info=True)
        # Cân nhắc không xóa file excel nếu có lỗi ở đây để debug
        return jsonify({'success': False, 'message': f'Lỗi nghiêm trọng trong quá trình xử lý email: {str(e)}'}), 500
    
    # Cân nhắc việc xóa file excel sau khi xử lý thành công nếu không cần giữ lại
    # if os.path.exists(excel_file_path):
    #     try:
    #         os.remove(excel_file_path)
    #         current_app.logger.info(f"Đã xóa file Excel tạm: {excel_file_path}")
    #     except OSError as e:
    #         current_app.logger.warning(f"Không thể xóa file Excel tạm {excel_file_path}: {e}")
            
    return jsonify(result)

# Bạn cũng cần có các endpoint khác như /get-excel-headers và /download-log
# Chúng cũng nên nằm trong api_email_bp này

@api_email_bp.route('/get-excel-headers', methods=['POST'])
def get_excel_headers_api():
    if 'excel_file' not in request.files:
        return jsonify({'success': False, 'message': 'Không có file Excel'}), 400

    excel_file = request.files['excel_file']
    if not excel_file or not excel_file.filename or not allowed_file(excel_file.filename):
        return jsonify({'success': False, 'message': 'File không hợp lệ hoặc không được phép'}), 400
        
    upload_folder_excel_config = current_app.config.get('UPLOAD_FOLDER_EXCEL')
    if not upload_folder_excel_config:
        current_app.logger.error("UPLOAD_FOLDER_EXCEL không được cấu hình trong ứng dụng (get_excel_headers).")
        return jsonify({'success': False, 'message': 'Lỗi cấu hình server: Thư mục upload chưa được định nghĩa.'}), 500
    
    upload_folder_abs = upload_folder_excel_config # Giả sử đây là đường dẫn tuyệt đối từ config
    if not os.path.isabs(upload_folder_abs): # Nếu là tương đối, join với instance_path
        upload_folder_abs = os.path.join(current_app.instance_path, upload_folder_excel_config)

    if not os.path.exists(upload_folder_abs):
        try:
            os.makedirs(upload_folder_abs)
        except OSError as e:
            current_app.logger.error(f"Không thể tạo thư mục upload {upload_folder_abs} (get_excel_headers): {e}")
            return jsonify({'success': False, 'message': 'Lỗi server: Không thể tạo thư mục upload.'}), 500
            
    filename = secure_filename(f"temp_header_{excel_file.filename}") # Thêm prefix để tránh trùng lặp
    temp_excel_path = os.path.join(upload_folder_abs, filename)
    
    try:
        excel_file.save(temp_excel_path)
        data = parse_excel_data(temp_excel_path)
        if not data:
            return jsonify({'success': False, 'message': 'Không có dữ liệu hoặc không đọc được header từ file Excel'}), 400
        headers = list(data[0].keys()) if data else []
        return jsonify({'success': True, 'headers': headers})
    except Exception as e:
        current_app.logger.error(f"Lỗi khi lấy header Excel: {e}", exc_info=True)
        return jsonify({'success': False, 'message': f'Lỗi xử lý file Excel: {str(e)}'}), 500
    finally:
        if os.path.exists(temp_excel_path):
            try:
                os.remove(temp_excel_path)
            except OSError as e:
                current_app.logger.warning(f"Không thể xóa file Excel tạm (headers) {temp_excel_path}: {e}")


@api_email_bp.route('/download-log/<filename>', methods=['GET'])
def download_log_file(filename):
    log_folder_email_config = current_app.config.get('LOG_FOLDER_EMAIL')
    if not log_folder_email_config:
        current_app.logger.error("LOG_FOLDER_EMAIL không được cấu hình trong ứng dụng.")
        return jsonify({"success": False, "message": "Lỗi cấu hình server: Thư mục log chưa được định nghĩa."}), 500

    # Giả sử LOG_FOLDER_EMAIL trong config là đường dẫn tuyệt đối
    # Nếu không, bạn cần join với current_app.instance_path hoặc current_app.root_path
    log_folder_abs = log_folder_email_config
    if not os.path.isabs(log_folder_abs):
        log_folder_abs = os.path.join(current_app.instance_path, log_folder_email_config)


    try:
        return send_from_directory(log_folder_abs, filename, as_attachment=True)
    except FileNotFoundError:
        current_app.logger.warning(f"Yêu cầu tải file log không tìm thấy: {os.path.join(log_folder_abs, filename)}")
        return jsonify({"success": False, "message": "File log không tìm thấy."}), 404
    except Exception as e:
        current_app.logger.error(f"Lỗi khi cố gắng gửi file log {filename}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Lỗi server khi tải file log."}), 500

