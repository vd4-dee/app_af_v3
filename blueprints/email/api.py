import os
import pandas as pd
from flask import Blueprint, request, jsonify, abort
from .logic_email import process_and_send_emails

api_email = Blueprint('api_email', __name__)

@api_email.route('/api/email/send-bulk', methods=['POST'])
def send_bulk():
    # Validate and get files/fields
    excel_file = request.files.get('excel_file')
    subject_template = request.form.get('email_subject')
    html_template_content = request.form.get('html_template_content')
    selected_template_name = request.form.get('selected_template_name')
    # Optionally support upload template file
    html_template_file = request.files.get('html_template_file')
    # Save excel file to temp
    if not excel_file:
        abort(400, 'Excel file required')
    excel_path = os.path.join('uploads', excel_file.filename)
    excel_file.save(excel_path)
    # Determine template content
    if selected_template_name:
        # Load from storage
        template_path = os.path.join('email_templates_storage', f'{selected_template_name}.html')
        if not os.path.exists(template_path):
            abort(404, 'Selected template not found')
        with open(template_path, 'r', encoding='utf-8') as f:
            html_template_content = f.read()
    elif html_template_file:
        html_template_content = html_template_file.read().decode('utf-8')
    elif not html_template_content:
        abort(400, 'No template content provided')
    # Send emails
    result = process_and_send_emails(excel_path, html_template_content, subject_template)
    return jsonify(result)

@api_email.route('/api/email/get-excel-headers', methods=['POST'])
def get_excel_headers():
    excel_file = request.files.get('excel_file')
    if not excel_file:
        abort(400, 'Excel file required')
    temp_path = os.path.join('uploads', excel_file.filename)
    excel_file.save(temp_path)
    try:
        df = pd.read_excel(temp_path)
        headers = list(df.columns)
    except Exception as e:
        abort(400, f'Error reading Excel: {e}')
    finally:
        os.remove(temp_path)
    return jsonify({'headers': headers})
