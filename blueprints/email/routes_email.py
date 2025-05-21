from . import email_bp
from flask import render_template, request, redirect, url_for, flash, current_app, session
import os
import re
# from .logic_email import process_and_send_emails # No longer needed here for direct processing
# from werkzeug.utils import secure_filename
# import tempfile

# The load_email_templates function is no longer needed for the bulk sender page
# as template loading is now handled via API calls from the frontend.
# If this function is used elsewhere, it should be refactored or kept for those specific uses.
# For the purpose of the bulk sender, we can remove it.

@email_bp.route('/bulk', methods=['GET']) # Only GET method is needed to serve the page
# Renamed function and route
def bulk_email(): 
    # The frontend JavaScript (main.js) will handle loading templates via API
    # and submitting data to /api/email/send-bulk.
    # This route simply serves the HTML page.
    
    # Ensure user is logged in and has web access (similar to index route)
    if 'user' not in session:
        flash('Please log in to access the bulk email sender.', 'warning')
        return redirect(url_for('login'))
    
    if not session.get('web_access'):
        flash('Your account does not have access to this feature. Please contact administrator.', 'danger')
        return redirect(url_for('login'))

    # Render the bulk sender HTML page, passing default config values
    return render_template(
        'email/bulk_sender/bulk_sender.html',
        default_email=current_app.config.get('DEFAULT_EMAIL', ''),
        default_password=current_app.config.get('DEFAULT_PASSWORD', ''),
        default_otp_secret=current_app.config.get('OTP_SECRET', ''),
        default_driver_path=current_app.config.get('DRIVER_PATH', ''),
        default_download_base_path=current_app.config.get('DOWNLOAD_BASE_PATH', '')
    )

# Optional: Add route for viewing send history if needed
# @email_bp.route('/history')
# def history():
#    # Logic to read and display EMAIL_LOG_PATH
#    try:
#        # Read EMAIL_LOG_PATH (defined in config)
#        # Paginate or limit results
#        # Pass logs to a template email/history.html
#        pass
#    except Exception as e:
#        flash(f'Error loading email history: {e}', 'danger')
#        return render_template('email/history.html', logs=[])
