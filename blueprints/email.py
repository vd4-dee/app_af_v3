import os
import pandas as pd
import win32com.client as win32
from datetime import datetime
import csv
import shutil
from flask import Blueprint, request, jsonify, current_app, send_from_directory, flash, redirect, url_for, render_template
from werkzeug.utils import secure_filename
import uuid

# Initialize Blueprint
email_api = Blueprint('email_api', __name__)

# Ensure upload and log directories exist
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uploads')
LOG_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
TEMPLATE_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static', 'email_templates')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(LOG_FOLDER, exist_ok=True)
os.makedirs(TEMPLATE_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xls'}

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
        log_url = f"/api/email/logs/{os.path.basename(log_path)}" if success else None
        
        return jsonify({
            'success': success, 
            'message': message,
            'log_file': log_url
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in api_send_bulk_emails: {str(e)}", exc_info=True)
        return jsonify({
            'success': False, 
            'message': f'Đã xảy ra lỗi: {str(e)}'
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
        
    except Exception as e:
        current_app.logger.error(f"Error in api_send_bulk_emails: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'An error occurred: {str(e)}'
        }), 500

@email_api.route('/logs/<filename>')
def download_log(filename):
    """Route to download log files"""
    try:
        return send_from_directory(
            LOG_FOLDER,
            filename,
            as_attachment=True,
            download_name=f"email_log_{datetime.now().strftime('%Y%m%d')}.csv"
        )
    except Exception as e:
        current_app.logger.error(f"Error serving log file {filename}: {e}")
        return jsonify({'success': False, 'message': 'Log file not found'}), 404
