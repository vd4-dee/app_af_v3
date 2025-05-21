import os
import pandas as pd
import win32com.client as win32
from datetime import datetime
import csv
import shutil
from flask import request, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename
import uuid

# Ensure upload and log directories exist
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'uploads')
LOG_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logs')
TEMPLATE_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'static', 'email_templates')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(LOG_FOLDER, exist_ok=True)
os.makedirs(TEMPLATE_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xls'}

def send_bulk_emails_backend(excel_path, html_file, attachments_folder, log_file, var_kibaocao, var_deadline, start_index=None, end_index=None):
    """
    Process and send bulk emails based on Excel data
    
    Args:
        excel_path (str): Path to the Excel file with recipient data
        html_file (str): Path to the HTML email template
        attachments_folder (str): Directory containing attachment files
        log_file (str): Path to the log file
        var_kibaocao (str): Reporting period (e.g., 'Tháng 3/2024')
        var_deadline (str): Deadline for response
        start_index (int, optional): Starting index for batch processing
        end_index (int, optional): Ending index for batch processing
        
    Returns:
        tuple: (success, message)
    """
    # Initialize log file with header
    with open(log_file, 'w', newline='', encoding='utf-8') as log:
        writer = csv.writer(log)
        writer.writerow(["Timestamp", "Recipient", "Status/Message"])
        
    def log_message(recipient, message):
        """Helper function to log messages"""
        with open(log_file, 'a', newline='', encoding='utf-8') as log:
            writer = csv.writer(log)
            writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), recipient, message])
    
    try:
        # Read Excel file
        try:
            df = pd.read_excel(excel_path, sheet_name='Data')
            if df.empty:
                error_msg = "The Excel file is empty or could not be read correctly. Please ensure the 'Data' sheet exists and contains data."
                log_message("SYSTEM", error_msg)
                return False, error_msg
                
            # Ensure all required columns exist
            required_columns = ['Name', 'To', 'CC', 'Title', 'Receiver', 'Tuxung', 'Is_New', 'Attachment', 'Attachment2']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                error_msg = f"Missing required columns in Excel file: {', '.join(missing_columns)}. Required columns are: {', '.join(required_columns)}"
                log_message("SYSTEM", error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Error reading Excel file. Please ensure it is a valid Excel file with a sheet named 'Data'. Error: {str(e)}"
            log_message("SYSTEM", error_msg)
            return False, error_msg
        
        # Read HTML template
        try:
            with open(html_file, 'r', encoding='utf-8') as file:
                html_template = file.read()
        except Exception as e:
            error_msg = f"Error reading HTML template: {str(e)}"
            log_message("SYSTEM", error_msg)
            return False, error_msg
            
        # Initialize Outlook
        try:
            outlook = win32.Dispatch('outlook.application')
        except Exception as e:
            error_msg = f"Error initializing Microsoft Outlook. Please ensure Outlook is installed and configured on this machine. Error: {str(e)}"
            log_message("SYSTEM", error_msg)
            return False, error_msg
            
        # Process emails
        success_count = 0
        error_count = 0
        
        # Determine processing range
        if start_index is None:
            start_index = 0
        if end_index is None or end_index >= len(df):
            end_index = len(df) - 1
            
        # Process each row in the Excel file
        for index, row in df.iloc[start_index:end_index + 1].iterrows():
            try:
                # Skip if email is empty
                if pd.isna(row['To']) or not str(row['To']).strip():
                    log_message("", "Skipped - No email address")
                    error_count += 1
                    continue
                    
                # Prepare email content with template variables
                html_content = html_template
                replacements = {
                    "var_kibaocao": var_kibaocao,
                    "var_deadline": var_deadline,
                    "tuxung": row.get('Tuxung', ''),
                    "anh/chị": row.get('Name', ''),
                    "Dear Anh/Chị ASM,": f"Kính gửi {row.get('Name', 'Anh/Chị')},",
                    "is_new": "Kì KPI hiện tại anh chị vẫn nhận full điểm KPI nhưng em vẫn gửi chi tiết để nắm thông tin." 
                             if row.get('Is_New') == 1 else ""
                }
                
                for key, value in replacements.items():
                    html_content = html_content.replace(key, str(value))
                
                # Create Outlook email
                mail = outlook.CreateItem(0)  # 0 = olMailItem
                mail.To = row['To']
                if pd.notna(row.get('CC')) and str(row['CC']).strip():
                    mail.CC = str(row['CC']).strip()
                    
                mail.Subject = f"[FAF-KPIs] KPIs {row.get('Title', '')} {var_kibaocao} - {row.get('Receiver', '')}"
                mail.HTMLBody = html_content
                
                # Add attachments if they exist
                for col in ['Attachment', 'Attachment2']:
                    if pd.notna(row.get(col)) and str(row[col]).strip():
                        attachment_path = os.path.join(attachments_folder, str(row[col]).strip())
                        if os.path.exists(attachment_path):
                            if os.path.getsize(attachment_path) < 10 * 1024 * 1024:  # 10MB limit
                                mail.Attachments.Add(attachment_path)
                            else:
                                log_message(row['To'], f"Attachment too large: {os.path.basename(attachment_path)}")
                        else:
                            log_message(row['To'], f"Attachment not found: {os.path.basename(attachment_path)}")
                
                # Send the email
                mail.Send()
                success_count += 1
                log_message(row['To'], "Email sent successfully")
                
            except Exception as e:
                error_count += 1
                log_message(row.get('To', 'Unknown'), f"Error sending email: {str(e)}")
                continue
                
        # Return success with statistics
        message = f"Successfully sent {success_count} emails. "
        if error_count > 0:
            message += f"{error_count} emails failed. "
        message += f"Check the log file for details."
        
        return True, message
        
    except Exception as e:
        log_message("SYSTEM", f"Unexpected error: {str(e)}")
        return False, f"An unexpected error occurred: {str(e)}"
    
    finally:
        # Clean up the uploaded file
        try:
            if os.path.exists(excel_path):
                os.remove(excel_path)
        except Exception as e:
            current_app.logger.error(f"Error removing temporary file: {e}")

def init_email_api_routes(email_api):
    """
    Initialize email API routes
    
    Args:
        email_api: The Flask Blueprint for email API routes
    """
    @email_api.route('/send_bulk_emails', methods=['POST'])
    def api_send_bulk_emails():
        """
        API endpoint to handle bulk email sending
        """
        try:
            # Check if the request has the file part
            if 'excel_file' not in request.files:
                return jsonify({'success': False, 'message': 'Không có file được tải lên'}), 400
                
            file = request.files['excel_file']
            if file.filename == '':
                return jsonify({'success': False, 'message': 'Không có file được chọn'}), 400
                
            if not allowed_file(file.filename):
                return jsonify({'success': False, 'message': 'Định dạng file không hỗ trợ. Vui lòng tải lên file Excel (.xlsx, .xls)'}), 400
            
            # Get form data
            var_kibaocao = request.form.get('var_kibaocao', '').strip()
            if not var_kibaocao:
                return jsonify({'success': False, 'message': 'Vui lòng nhập kỳ báo cáo'}), 400
                
            var_deadline = request.form.get('var_deadline', '').strip()
            if not var_deadline:
                return jsonify({'success': False, 'message': 'Vui lòng nhập hạn chót'}), 400
                
            html_file = request.form.get('html_file', '').strip()
            if not html_file or not os.path.exists(html_file):
                return jsonify({'success': False, 'message': 'Mẫu email không hợp lệ'}), 400
                
            # Convert start_index and end_index to integers if provided
            try:
                start_index = int(request.form.get('start_index', 0))
                end_index = int(request.form.get('end_index', 0)) or None
            except (ValueError, TypeError):
                start_index = 0
                end_index = None
            
            # Ensure upload directory exists
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            
            # Save uploaded file with a unique name
            filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
            excel_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(excel_path)
            
            # Create a unique log file
            log_filename = f"email_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            log_path = os.path.join(LOG_FOLDER, log_filename)
            
            # Process the email sending
            success, message = send_bulk_emails_backend(
                excel_path=excel_path,  # Path to the uploaded Excel file
                html_file=html_file,    # Path to the selected HTML template
                attachments_folder=UPLOAD_FOLDER,  # Folder containing attachments
                log_file=log_path,      # Path to the log file
                var_kibaocao=var_kibaocao,
                var_deadline=var_deadline,
                start_index=start_index,
                end_index=end_index
            )
            
            # Return the log file path for download
            log_url = f"/api/email/logs/{os.path.basename(log_path)}" if success or os.path.exists(log_path) else None # Provide log file even on partial failure
            
            return jsonify({
                'success': success, 
                'message': message,
                'log_file': log_url
            })
            
        except Exception as e:
            current_app.logger.error(f"Error in api_send_bulk_emails: {str(e)}", exc_info=True)
            # Log the unexpected error
            log_filename = f"email_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}_error.csv"
            log_path = os.path.join(LOG_FOLDER, log_filename)
            try:
                with open(log_path, 'w', newline='', encoding='utf-8') as log:
                    writer = csv.writer(log)
                    writer.writerow(["Timestamp", "Recipient", "Status/Message"])
                    writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "SYSTEM", f"Unexpected error in API: {str(e)}"])
            except Exception as log_e:
                 current_app.logger.error(f"Failed to write error log {log_path}: {log_e}")

            log_url = f"/api/email/logs/{os.path.basename(log_path)}" if os.path.exists(log_path) else None

            return jsonify({
                'success': False, 
                'message': f'Đã xảy ra lỗi không mong muốn: {str(e)}',
                'log_file': log_url
            }), 500

    @email_api.route('/logs/<filename>')
    def download_log(filename):
        """
        Route to download log files
        """
        try:
            # Prevent directory traversal
            if '..' in filename or filename.startswith('/'):
                return jsonify({'success': False, 'message': 'Invalid filename'}), 400
                
            log_path = os.path.join(LOG_FOLDER, filename)
            
            if not os.path.exists(log_path):
                return jsonify({'success': False, 'message': 'Log file not found'}), 404
                
            return send_from_directory(
                LOG_FOLDER,
                filename,
                as_attachment=True,
                download_name=f"email_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
        except Exception as e:
            current_app.logger.error(f"Error serving log file {filename}: {e}")
            return jsonify({'success': False, 'message': 'Error serving log file'}), 500
