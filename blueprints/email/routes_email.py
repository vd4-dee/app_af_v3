from . import email_bp
from flask import render_template, request, redirect, url_for, flash, current_app, session, jsonify
import os
import re
import json

# Define the path for the bulk email configuration file
BULK_EMAIL_CONFIG_FILENAME = 'bulk_email_config.json'
BULK_EMAIL_CONFIG_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..', 'instance', BULK_EMAIL_CONFIG_FILENAME)
# from .logic_email import process_and_send_emails # No longer needed here for direct processing
# from werkzeug.utils import secure_filename
# import tempfile

# The load_email_templates function is no longer needed for the bulk sender page
# as template loading is now handled via API calls from the frontend.
# If this function is used elsewhere, it should be refactored or kept for those specific uses.
# For the purpose of the bulk sender, we can remove it.

@email_bp.route('/bulk', methods=['GET'])
def bulk_email():
    if 'user' not in session:
        flash('Please log in to access the bulk email sender.', 'warning')
        return redirect(url_for('login'))
    
    if not session.get('web_access'):
        flash('Your account does not have access to this feature. Please contact administrator.', 'danger')
        return redirect(url_for('login'))

    return render_template(
        'email/bulk_sender/bulk_sender.html',
        default_email=current_app.config.get('DEFAULT_EMAIL', ''),
        default_password=current_app.config.get('DEFAULT_PASSWORD', ''),
        default_otp_secret=current_app.config.get('OTP_SECRET', ''),
        default_driver_path=current_app.config.get('DRIVER_PATH', ''),
        default_download_base_path=current_app.config.get('DOWNLOAD_BASE_PATH', '')
    )

@email_bp.route('/api/email/save-bulk-config', methods=['POST'])
def save_bulk_config():
    if 'user' not in session or not session.get('web_access'):
        return jsonify({'success': False, 'message': 'Unauthorized access.'}), 403

    try:
        config_data = request.get_json()
        if not config_data:
            return jsonify({'success': False, 'message': 'No data provided.'}), 400

        # Ensure the instance directory exists
        os.makedirs(os.path.dirname(BULK_EMAIL_CONFIG_PATH), exist_ok=True)

        with open(BULK_EMAIL_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)
        
        return jsonify({'success': True, 'message': 'Configuration saved successfully.'}), 200
    except Exception as e:
        current_app.logger.error(f"Error saving bulk email config: {e}")
        return jsonify({'success': False, 'message': f'Error saving configuration: {str(e)}'}), 500

@email_bp.route('/api/email/load-bulk-config', methods=['GET'])
def load_bulk_config():
    if 'user' not in session or not session.get('web_access'):
        return jsonify({'success': False, 'message': 'Unauthorized access.'}), 403

    try:
        if os.path.exists(BULK_EMAIL_CONFIG_PATH):
            with open(BULK_EMAIL_CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return jsonify({'success': True, 'config': config, 'message': 'Configuration loaded successfully.'}), 200
        else:
            return jsonify({'success': False, 'message': 'No saved configuration found.', 'config': {}}), 404
    except json.JSONDecodeError:
        current_app.logger.error(f"Error decoding JSON from {BULK_EMAIL_CONFIG_PATH}")
        return jsonify({'success': False, 'message': 'Error reading configuration file (invalid JSON).', 'config': {}}), 500
    except Exception as e:
        current_app.logger.error(f"Error loading bulk email config: {e}")
        return jsonify({'success': False, 'message': f'Error loading configuration: {str(e)}', 'config': {}}), 500
