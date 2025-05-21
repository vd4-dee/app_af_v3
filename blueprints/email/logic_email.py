# blueprints/email/logic_email.py

import pandas as pd
from flask import current_app, jsonify
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
import win32com.client as win32
from datetime import datetime
import pythoncom # Thêm dòng này
import logging

# Thiết lập logging
logger = logging.getLogger(__name__)
# (Bạn có thể cấu hình logger chi tiết hơn trong __init__.py của ứng dụng hoặc blueprint)

# Hàm helper để gửi một email qua Outlook
def send_outlook_email(to_email, subject, html_body, attachments=None):
    """
    Gửi một email sử dụng Outlook.

    Args:
        to_email (str): Địa chỉ email người nhận.
        subject (str): Chủ đề email.
        html_body (str): Nội dung email dạng HTML.
        attachments (list): Danh sách đường dẫn tuyệt đối tới các file đính kèm.

    Returns:
        bool: True nếu gửi thành công, False nếu có lỗi.
    """
    pythoncom.CoInitialize() # Khởi tạo COM cho thread này
    try:
        outlook = win32.Dispatch('outlook.application')
        mail = outlook.CreateItem(0)
        mail.To = to_email
        mail.Subject = subject
        mail.HTMLBody = html_body

        if attachments:
            for attachment_path in attachments:
                if os.path.exists(attachment_path):
                    mail.Attachments.Add(attachment_path)
                else:
                    logger.warning(f"File đính kèm không tồn tại: {attachment_path} cho email tới {to_email}")
        
        mail.Send()
        logger.info(f"Email đã gửi thành công tới: {to_email}, Chủ đề: {subject}")
        return True
    except Exception as e:
        logger.error(f"Lỗi khi gửi email tới {to_email}: {e}")
        return False
    finally:
        pythoncom.CoUninitialize() # Giải phóng COM

def parse_excel_data(excel_file_path):
    """
    Đọc dữ liệu từ file Excel.
    Chuyển đổi tên cột thành chữ thường và loại bỏ khoảng trắng thừa.
    """
    try:
        df = pd.read_excel(excel_file_path)
        # Chuẩn hóa tên cột: chữ thường, bỏ khoảng trắng, thay thế ký tự đặc biệt nếu cần
        df.columns = [str(col).lower().strip().replace(' ', '_') for col in df.columns]
        # Chuyển đổi tất cả dữ liệu thành chuỗi để tránh lỗi render template với kiểu số
        df = df.astype(str)
        # Thay thế 'nan' thành chuỗi rỗng
        df.fillna('', inplace=True)
        return df.to_dict(orient='records')
    except Exception as e:
        logger.error(f"Lỗi khi đọc file Excel {excel_file_path}: {e}")
        raise # Ném lại lỗi để API endpoint xử lý

def render_email_template_from_string(template_string, data):
    """
    Render nội dung email từ một chuỗi template HTML và dữ liệu.
    """
    try:
        env = Environment(loader=FileSystemLoader('.'), autoescape=select_autoescape(['html', 'xml'])) # Loader tạm thời, không quan trọng vì template_string được truyền trực tiếp
        template = env.from_string(template_string)
        return template.render(data)
    except Exception as e:
        logger.error(f"Lỗi khi render template: {e}")
        raise

def process_and_send_emails(excel_file_path, email_subject, html_template_content, 
                            email_column_name='email', attachment_column_name=None, 
                            attachments_base_folder=None, start_index=0, end_index=None):
    """
    Xử lý file Excel, render template và gửi email hàng loạt qua Outlook.

    Args:
        excel_file_path (str): Đường dẫn tới file Excel.
        email_subject (str): Chủ đề của email.
        html_template_content (str): Nội dung template HTML.
        email_column_name (str): Tên cột trong Excel chứa địa chỉ email người nhận (mặc định là 'email').
        attachment_column_name (str): Tên cột trong Excel chứa tên file hoặc đường dẫn tương đối của file đính kèm.
        attachments_base_folder (str): Thư mục gốc chứa các file đính kèm.
        start_index (int): Chỉ mục bắt đầu gửi (mặc định là 0, hàng đầu tiên sau header).
        end_index (int): Chỉ mục kết thúc gửi (mặc định là None, gửi đến hết).

    Returns:
        dict: Kết quả gửi email.
    """
    try:
        email_data_list = parse_excel_data(excel_file_path)
    except Exception as e:
        return {'success': False, 'message': f"Lỗi đọc file Excel: {str(e)}", 'results': []}

    if not email_data_list:
        return {'success': False, 'message': "Không có dữ liệu trong file Excel hoặc file không hợp lệ.", 'results': []}

    # Chuẩn hóa email_column_name và attachment_column_name
    email_column_name = email_column_name.lower().strip().replace(' ', '_')
    if attachment_column_name:
        attachment_column_name = attachment_column_name.lower().strip().replace(' ', '_')

    results = []
    success_count = 0
    error_count = 0
    
    # Xác định phạm vi gửi email
    if end_index is None or end_index > len(email_data_list):
        end_index = len(email_data_list)
    
    if start_index < 0:
        start_index = 0

    records_to_send = email_data_list[start_index:end_index]

    log_entries = []
    log_filename = f"email_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    log_folder = current_app.config.get('LOG_FOLDER_EMAIL', os.path.join(current_app.root_path, 'logs', 'email_module')) # Lấy từ config hoặc mặc định
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)
    log_file_path = os.path.join(log_folder, log_filename)

    for i, record in enumerate(records_to_send):
        actual_index = start_index + i # Chỉ số thực tế trong file Excel
        recipient_email = record.get(email_column_name)

        if not recipient_email or pd.isna(recipient_email):
            error_msg = f"Bỏ qua dòng {actual_index + 2}: Thiếu địa chỉ email ở cột '{email_column_name}'."
            logger.warning(error_msg)
            results.append({'row': actual_index + 2, 'email': '', 'status': 'error', 'message': error_msg})
            log_entries.append({'row': actual_index + 2, 'email': '', 'status': 'error', 'message': error_msg, 'subject': email_subject, 'attachments': ''})
            error_count += 1
            continue
        
        recipient_email = str(recipient_email).strip()

        try:
            rendered_html = render_email_template_from_string(html_template_content, record)
            
            current_attachments = []
            attachment_names_excel = "" # Để ghi log
            if attachment_column_name and attachments_base_folder and record.get(attachment_column_name):
                # Giả sử cột attachment chứa tên file, hoặc danh sách tên file phân cách bằng dấu phẩy/chấm phẩy
                attachment_names_excel = str(record.get(attachment_column_name))
                attachment_files = [name.strip() for name in attachment_names_excel.replace(';', ',').split(',') if name.strip()]
                
                for att_file in attachment_files:
                    # Nếu att_file là đường dẫn tuyệt đối thì dùng luôn
                    if os.path.isabs(att_file) and os.path.exists(att_file):
                        current_attachments.append(att_file)
                    # Nếu là đường dẫn tương đối, kết hợp với attachments_base_folder
                    else:
                        full_att_path = os.path.join(attachments_base_folder, att_file)
                        if os.path.exists(full_att_path):
                            current_attachments.append(full_att_path)
                        else:
                            logger.warning(f"File đính kèm '{att_file}' (đường dẫn: {full_att_path}) không tìm thấy cho email tới {recipient_email}.")
            
            if send_outlook_email(recipient_email, email_subject, rendered_html, current_attachments):
                results.append({'row': actual_index + 2, 'email': recipient_email, 'status': 'success', 'message': 'Đã gửi'})
                log_entries.append({'row': actual_index + 2, 'email': recipient_email, 'status': 'success', 'message': 'Đã gửi', 'subject': email_subject, 'attachments': ", ".join(current_attachments)})
                success_count += 1
            else:
                results.append({'row': actual_index + 2, 'email': recipient_email, 'status': 'error', 'message': 'Lỗi gửi email qua Outlook'})
                log_entries.append({'row': actual_index + 2, 'email': recipient_email, 'status': 'error', 'message': 'Lỗi gửi email qua Outlook', 'subject': email_subject, 'attachments': ", ".join(current_attachments)})
                error_count += 1
        except Exception as e:
            error_msg = f"Lỗi xử lý email cho {recipient_email}: {str(e)}"
            logger.error(error_msg)
            results.append({'row': actual_index + 2, 'email': recipient_email, 'status': 'error', 'message': error_msg})
            log_entries.append({'row': actual_index + 2, 'email': recipient_email, 'status': 'error', 'message': error_msg, 'subject': email_subject, 'attachments': ''})
            error_count += 1

    # Ghi log vào file CSV
    try:
        log_df = pd.DataFrame(log_entries)
        log_df.to_csv(log_file_path, index=False, encoding='utf-8-sig')
        logger.info(f"Log gửi email đã được lưu tại: {log_file_path}")
    except Exception as e:
        logger.error(f"Lỗi khi ghi file log CSV: {e}")

    return {
        'success': True, # API call thành công, nhưng có thể có lỗi gửi từng email
        'message': f"Hoàn tất gửi. Thành công: {success_count}, Lỗi: {error_count}. Chi tiết trong kết quả và file log.",
        'results': results,
        'log_file': log_filename # Trả về tên file log để có thể tải xuống
    }
