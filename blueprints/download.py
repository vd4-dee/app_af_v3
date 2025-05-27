from flask import Blueprint, request, jsonify, Response, stream_with_context # type: ignore
import threading
import time
import os
import json
import sys
from flask import current_app

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Add the parent directory to the Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from utils.config_manager import save_config_values, load_config_values
import traceback
from datetime import datetime, timezone, timedelta
from apscheduler.jobstores.base import JobLookupError # type: ignore
from apscheduler.triggers.date import DateTrigger # type: ignore
from selenium.common.exceptions import WebDriverException # Added
import csv # Import csv for get_download_logs fallback
import pandas as pd
import numpy as np
import sqlite3
import uuid

# --- Local Imports --- 
# Assuming these are in the root directory or accessible
# Adjust paths if necessary (e.g., from .. import config)
import config
import link_report
from logic_download import WebAutomation, regions_data, DownloadFailedException # Added
from utils_legacy import load_configs, save_configs, stream_status_update # Import from utils_legacy

# --- Remove direct import from app --- 
# from app import lock, status_messages, is_running 

# Global state should be accessed via current_app.config or current_app attributes
# (These placeholders are removed as they are not used consistently)

# --- Blueprint Definition ---
download_bp = Blueprint('download', __name__, url_prefix='/download')

# --- Utility Functions (Cần xem xét vị trí đặt) ---
# Ví dụ: stream_status_update, load_configs, save_configs có thể ở module riêng

# --- SQLite Utility Functions ---
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'scheduler.db')
WEB_SESSION_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'web_sessions.db')
def handle_start_download():
    app_state = current_app.config['SHARED_APP_STATE']
    with current_app.config['GLOBAL_LOCK']:
        if app_state.get('is_automation_running', False): # SỬ DỤNG TÊN KEY ĐÚNG
            return jsonify({'status': 'error', 'message': 'Quá trình tải đã chạy rồi, vui lòng đợi hoàn tất.'}), 409
        app_state['is_automation_running'] = True # SỬ DỤNG TÊN KEY ĐÚNG
        
def init_web_sessions_db():
    print(f"Attempting to initialize web sessions DB at {WEB_SESSION_DB_PATH}")
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'web_sessions_schema.sql')
    try:
        with sqlite3.connect(WEB_SESSION_DB_PATH) as conn, open(schema_path, 'r', encoding='utf-8') as f:
            script = f.read()
            conn.executescript(script)
            print(f"Successfully executed web_sessions_schema.sql. Schema: {script[:100]}...")
        print("Web sessions DB initialized successfully.")
    except Exception as e:
        print(f"Error initializing web sessions DB: {e}")
        traceback.print_exc()

def create_web_session(session_id, user_id=None, job_id=None, last_page=None):
    with sqlite3.connect(WEB_SESSION_DB_PATH) as conn:
        conn.execute(
            'INSERT OR REPLACE INTO web_sessions (session_id, user_id, job_id, last_page) VALUES (?, ?, ?, ?)',
            (session_id, user_id, job_id, last_page)
        )
        conn.commit()

def update_web_session_status(session_id, status):
    with sqlite3.connect(WEB_SESSION_DB_PATH) as conn:
        conn.execute('UPDATE web_sessions SET status=?, updated_at=CURRENT_TIMESTAMP WHERE session_id=?', (status, session_id))
        conn.commit()

def update_web_session_page(session_id, last_page):
    with sqlite3.connect(WEB_SESSION_DB_PATH) as conn:
        conn.execute('UPDATE web_sessions SET last_page=?, updated_at=CURRENT_TIMESTAMP WHERE session_id=?', (last_page, session_id))
        conn.commit()

def get_web_session(session_id):
    with sqlite3.connect(WEB_SESSION_DB_PATH) as conn:
        cur = conn.execute('SELECT * FROM web_sessions WHERE session_id=?', (session_id,))
        row = cur.fetchone()
        if row:
            return dict(zip([column[0] for column in cur.description], row))
        return None

# Khởi tạo db khi load module
init_web_sessions_db()

def init_scheduler_db():
    print(f"Attempting to initialize scheduler DB at {DB_PATH}")
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'scheduler_schema.sql')
    try:
        with sqlite3.connect(DB_PATH) as conn, open(schema_path, 'r', encoding='utf-8') as f:
            script = f.read()
            conn.executescript(script)
            print(f"Successfully executed scheduler_schema.sql. Schema: {script[:100]}...")
        print("Scheduler DB initialized successfully.")
    except Exception as e:
        print(f"Error initializing scheduler DB: {e}")
        traceback.print_exc()

def insert_job_to_db(job_id, config_name, next_run_time, session_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            'INSERT OR REPLACE INTO jobs (id, config_name, next_run_time, status, session_id) VALUES (?, ?, ?, ?, ?)',
            (job_id, config_name, next_run_time, 'scheduled', session_id)
        )
        conn.commit()

def update_job_status(job_id, status):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('UPDATE jobs SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?', (status, job_id))
        conn.commit()

def update_job_status_by_session(session_id, status):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('UPDATE jobs SET status=?, updated_at=CURRENT_TIMESTAMP WHERE session_id=?', (status, session_id))
        conn.commit()

def get_job_id_by_session(session_id):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute('SELECT id FROM jobs WHERE session_id=?', (session_id,))
        row = cur.fetchone()
        return row[0] if row else None

def delete_job_from_db(job_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('DELETE FROM jobs WHERE id=?', (job_id,))
        conn.commit()

def get_all_jobs_from_db():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute('SELECT id, config_name, status, next_run_time, created_at, updated_at FROM jobs')
        return [dict(zip([column[0] for column in cur.description], row)) for row in cur.fetchall()]

# Khởi tạo db khi load module
init_scheduler_db()

# --- Download Process Function (Uses current_app) ---
def run_download_process(params, session_id=None, stop_event=None):
    """Main download function executed in a background thread."""
    automation = None # Ensure automation is always defined
    process_successful = True

    try:
        # Access global state from current_app.config
        lock = current_app.config['GLOBAL_LOCK']
        shared_state = current_app.config['SHARED_APP_STATE']
        status_list = current_app.status_messages # This is correctly attached in app.py

        # --- Setup within Lock ---
        with lock:
            if shared_state['is_automation_running']: 
                print("Download process already running, exiting new thread request.")
                return
            shared_state['is_automation_running'] = True # Modify shared state dict
            status_list.clear() # Clear the shared list

        if session_id:
            update_job_status_by_session(session_id, 'running') # Update jobs table
            update_web_session_status(session_id, 'running') # Update web_sessions table

        # Use the utility function which now uses current_app
        stream_status_update("Starting report download process...", log_entry={
            'SessionID': session_id,
            'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'File Name': None,
            'Start Date': None,
            'End Date': None,
            'Status': 'Started',
            'Error Message': None
        })

        # --- Extract Parameters ---
        email = params['email']
        password = params['password']
        reports_to_download = params.get('reports', [])
        selected_regions_indices_str = params.get('regions', [])

        if not reports_to_download:
            raise ValueError("No reports configured for download.")

        # --- Prepare Download Folder ---
        timestamp_folder = "001" + datetime.now().strftime("%Y%m%d")
        # Use current_app.config for DOWNLOAD_BASE_PATH
        download_base_path = current_app.config.get('DOWNLOAD_BASE_PATH', '')
        if not download_base_path:
            raise ValueError("DOWNLOAD_BASE_PATH is not configured in app settings.")
        specific_download_folder = os.path.join(download_base_path, timestamp_folder)
        try:
            os.makedirs(specific_download_folder, exist_ok=True)
            stream_status_update(f"Download folder for this run: {specific_download_folder}")
        except OSError as e:
            raise RuntimeError(f"Failed to create download directory '{specific_download_folder}': {e}")

        # --- Initialize Automation ---
        stream_status_update("Initializing browser automation...")
        # Use current_app.config for DRIVER_PATH
        driver_path = current_app.config.get('DRIVER_PATH', '')
        if not driver_path:
            raise ValueError("DRIVER_PATH is not configured in app settings.")
        automation = WebAutomation(driver_path, specific_download_folder, status_callback=stream_status_update)
        
        if stop_event and stop_event.is_set():
            stream_status_update("Download process cancelled before login.")
            process_successful = False
            return

        # --- Login ---
        stream_status_update(f"Logging in with user: {email}...")
        first_report_info = reports_to_download[0]
        first_report_url = link_report.get_report_url(first_report_info.get('report_type'))
        if not first_report_url:
            raise ValueError(f"Could not find URL for initial report type '{first_report_info.get('report_type')}' needed for login.")
        # Use current_app.config for OTP_SECRET
        otp_secret = current_app.config.get('OTP_SECRET', '')
        if not otp_secret:
            raise ValueError("OTP_SECRET is not configured in app settings.")

        if not automation.login(first_report_url, email, password, otp_secret, status_callback=stream_status_update):
            raise RuntimeError("Login failed after multiple attempts. Cannot proceed.")
        stream_status_update("Login successful.")

        # --- Download Reports Loop ---
        for report_info in reports_to_download:
            report_type_key = report_info.get('report_type')
            from_date = report_info.get('from_date')
            to_date = report_info.get('to_date')
            chunk_size_str = report_info.get('chunk_size', '5') 

            if not all([report_type_key, from_date, to_date]):
                 stream_status_update(f"Warning: Skipping report entry due to missing info: {report_info}")
                 process_successful = False
                 continue

            chunk_size = 5
            try:
                if isinstance(chunk_size_str, str) and chunk_size_str.lower() == 'month':
                    chunk_size = 'month'
                elif chunk_size_str:
                    chunk_size_days = int(chunk_size_str)
                    chunk_size = chunk_size_days if chunk_size_days > 0 else 5
            except (ValueError, TypeError):
                stream_status_update(f"Warning: Invalid chunk size '{chunk_size_str}' for '{report_type_key}'. Using default: 5 days.")
                chunk_size = 5

            report_url = link_report.get_report_url(report_type_key)
            if not report_url:
                stream_status_update(f"Error: Could not find URL for report type '{report_type_key}'. Skipping.")
                process_successful = False
                continue

            stream_status_update(f"--- Starting download for report: {report_type_key} ---", log_entry={
                'SessionID': session_id,
                'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'File Name': report_type_key,
                'Start Date': from_date,
                'End Date': to_date,
                'Status': 'In Progress',
                'Error Message': None
            })
            stream_status_update(f"Date Range: {from_date} to {to_date}, Chunk Size/Mode: {chunk_size}")

            report_failed = False
            error_message = None
            try:
                # Use current_app.config for REGION_REQUIRED_REPORT_URLS
                if report_url in current_app.config.get('REGION_REQUIRED_REPORT_URLS', []):
                    if not selected_regions_indices_str:
                        error_message = f"Report '{report_type_key}' requires region selection, but none provided. Skipping."
                        stream_status_update(f"Error: {error_message}")
                        report_failed = True
                    else:
                        try:
                            selected_regions_indices_int = [int(idx) for idx in selected_regions_indices_str]
                            region_names = [regions_data[i]['name'] for i in selected_regions_indices_int if i in regions_data]
                            stream_status_update(f"Downloading '{report_type_key}' for regions: {', '.join(region_names)}")

                            if hasattr(automation, 'download_reports_for_all_regions'):
                                automation.download_reports_for_all_regions(
                                    report_url, from_date, to_date, chunk_size,
                                    region_indices=selected_regions_indices_int,
                                    status_callback=stream_status_update
                                )
                            else:
                                error_message = "'download_reports_for_all_regions' method missing."
                                stream_status_update(f"ERROR: {error_message}")
                                report_failed = True
                        except (ValueError, TypeError, KeyError) as region_err:
                            error_message = f"Error processing region indices for '{report_type_key}': {region_err}."
                            stream_status_update(f"Error: {error_message} Skipping.")
                            report_failed = True
                elif report_type_key == "FAF001 - Sales Report" and hasattr(automation, 'download_reports_in_chunks_1'):
                    automation.download_reports_in_chunks_1(report_url, from_date, to_date, chunk_size, stream_status_update)
                elif report_type_key == "FAF004N - Internal Rotation Report (Imports)" and hasattr(automation, 'download_reports_in_chunks_4n'):
                     automation.download_reports_in_chunks_4n(report_url, from_date, to_date, chunk_size, stream_status_update)
                elif report_type_key == "FAF004X - Internal Rotation Report (Exports)" and hasattr(automation, 'download_reports_in_chunks_4x'):
                     automation.download_reports_in_chunks_4x(report_url, from_date, to_date, chunk_size, stream_status_update)
                elif report_type_key == "FAF002 - Dosage Report" and hasattr(automation, 'download_reports_in_chunks_2'):
                     automation.download_reports_in_chunks_2(report_url, from_date, to_date, chunk_size, stream_status_update)
                elif report_type_key == "FAF003 - Report Of Other Imports And Exports" and hasattr(automation, 'download_reports_in_chunks_3'):
                     automation.download_reports_in_chunks_3(report_url, from_date, to_date, chunk_size, stream_status_update)
                elif report_type_key == "FAF005 - Detailed Report Of Imports" and hasattr(automation, 'download_reports_in_chunks_5'):
                     automation.download_reports_in_chunks_5(report_url, from_date, to_date, chunk_size, stream_status_update)
                elif report_type_key == "FAF006 - Supplier Return Report" and hasattr(automation, 'download_reports_in_chunks_6'):
                     automation.download_reports_in_chunks_6(report_url, from_date, to_date, chunk_size, stream_status_update)
                elif report_type_key == "FAF028 - Detailed Import - Export Transaction Report" and hasattr(automation, 'download_reports_in_chunks_28'):
                     automation.download_reports_in_chunks_28(report_url, from_date, to_date, chunk_size, stream_status_update)
                elif hasattr(automation, 'download_reports_in_chunks'):
                    stream_status_update(f"Using generic chunking download logic for '{report_type_key}'.")
                    automation.download_reports_in_chunks(report_url, from_date, to_date, chunk_size, stream_status_update)
                else:
                    error_message = f"No suitable download method found for report type '{report_type_key}'. Skipping."
                    stream_status_update(f"ERROR: {error_message}")
                    report_failed = True

            except DownloadFailedException as report_err:
                 error_message = str(report_err)
                 stream_status_update(f"ERROR downloading report {report_type_key}: {error_message}")
                 report_failed = True
            except WebDriverException as wd_err:
                 error_message = str(wd_err)
                 stream_status_update(f"ERROR (WebDriver) during download of {report_type_key}: {error_message}")
                 report_failed = True
                 traceback.print_exc()
                 if "invalid session id" in str(wd_err).lower():
                     stream_status_update("FATAL: Session invalid. Stopping further report downloads for this run.")
                     process_successful = False
                     break 
            except Exception as generic_err:
                 error_message = str(generic_err)
                 stream_status_update(f"FATAL UNEXPECTED ERROR during processing of {report_type_key}: {error_message}")
                 report_failed = True
                 traceback.print_exc()

            if report_failed:
                process_successful = False
                stream_status_update(f"--- Download FAILED for report: {report_type_key} ---", log_entry={
                    'SessionID': session_id,
                    'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'File Name': report_type_key,
                    'Start Date': from_date,
                    'End Date': to_date,
                    'Status': 'Failed',
                    'Error Message': error_message
                })
            else:
                stream_status_update(f"--- Download COMPLETED for report: {report_type_key} ---", log_entry={
                    'SessionID': session_id,
                    'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'File Name': report_type_key,
                    'Start Date': from_date,
                    'End Date': to_date,
                    'Status': 'Success',
                    'Error Message': None
                })
        # --- End of Reports Loop ---

    except (RuntimeError, ValueError, WebDriverException, AttributeError, KeyError) as setup_err:
        error_message = f"A critical error occurred during setup or login: {setup_err}"
        print(f"FATAL ERROR: {error_message}") 
        traceback.print_exc()
        process_successful = False
        stream_status_update(f"FATAL ERROR: {error_message}", log_entry={
            'SessionID': session_id,
            'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'File Name': None,
            'Start Date': None,
            'End Date': None,
            'Status': 'Process Failed',
            'Error Message': error_message
        })
    except Exception as e:
        error_message = f"An unexpected critical error occurred: {e}"
        print(f"FATAL ERROR: {error_message}")
        traceback.print_exc()
        process_successful = False
        stream_status_update(f"FATAL ERROR: {error_message}", log_entry={
            'SessionID': session_id,
            'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'File Name': None,
            'Start Date': None,
            'End Date': None,
            'Status': 'Process Failed',
            'Error Message': error_message
        })

    finally:
        if automation:
            try:
                stream_status_update("Attempting to close browser...")
                automation.close()
            except Exception as close_e:
                stream_status_update(f"CRITICAL ERROR: Failed to close browser session properly: {close_e}")
                traceback.print_exc()

        final_message = "PROCESS FINISHED: "
        final_status = 'Completed'
        if not process_successful:
             final_message += " One or more errors occurred. Please review logs and CSV file."
             final_status = 'Completed with Errors'
        else:
             final_message += " Check logs and CSV file for individual report status."
        
        stream_status_update(f"--- {final_message} ---", log_entry={
            'SessionID': session_id,
            'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'File Name': None, # Overall process, no specific file
            'Start Date': None,
            'End Date': None,
            'Status': final_status,
            'Error Message': None if process_successful else "See previous log entries for details."
        })

        if session_id:
            update_job_status_by_session(session_id, 'finished') # Update jobs table
            update_web_session_status(session_id, final_status.lower()) # Update web_sessions table

        try:
            # Reset running state using the global lock and shared state
            with current_app.config['GLOBAL_LOCK']:
                current_app.config['SHARED_APP_STATE']['is_automation_running'] = False # Use the key from shared_app_state
        except (AttributeError, KeyError) as final_e:
             print(f"Error resetting running state via current_app.config: {final_e}")
    return None # Explicitly return None to ensure function scope is properly closed

# --- Scheduled Task Trigger (Uses app context) ---
def trigger_scheduled_download(config_name, app, session_id):
    print(f"Scheduler attempting job for config: {config_name}, session: {session_id}")
    with app.app_context():
        try:
            # Access global state from the app object passed to the scheduled function
            lock = app.config['GLOBAL_LOCK']
            shared_state = app.config['SHARED_APP_STATE']
            # Check if already running
            with lock:
                if shared_state['is_automation_running']: # Use the key from shared_app_state
                    print(f"Scheduler: Download process already running. Skipping job for '{config_name}'.")
                    return

            configs = load_configs() 
            params = configs.get(config_name)

            if not params:
                print(f"Scheduler: Configuration '{config_name}' not found.")
                return

            required_keys = ['email', 'password', 'reports']
            if not all(key in params for key in required_keys) or not isinstance(params['reports'], list):
                print(f"Scheduler: Config '{config_name}' missing required keys or 'reports' is not a list.")
                return
            if not params['reports']:
                print(f"Scheduler: Config '{config_name}' has no reports defined.")
                return

            print(f"Scheduler: Starting download thread for config '{config_name}'...")
            thread_params = params.copy()
            def run_with_context(app, params, session_id):
                with app.app_context():
                    run_download_process(params, session_id)
            scheduled_thread = threading.Thread(target=run_with_context, args=(app, thread_params, session_id,))
            scheduled_thread.daemon = True
            scheduled_thread.start()

            update_job_status_by_session(session_id, 'running')

        except Exception as e:
            print(f"Scheduler ERROR for job '{config_name}': {e}")
            traceback.print_exc()
    return None # Explicitly return None to ensure function scope is properly closed

# --- Routes (Use current_app) ---

@download_bp.route('/get-reports-regions', methods=['GET'])
def get_reports_regions():
    from link_report import get_report_url
    report_urls = get_report_url()
    report_types = list(report_urls.keys())
    report_urls_map = report_urls
    region_required_urls = []  # Bổ sung logic nếu cần
    regions = {"1": "North", "2": "South"}
    return jsonify({
        "reports": report_types,
        "report_urls_map": report_urls_map,
        "region_required_urls": region_required_urls,
        "regions": regions
    })

@download_bp.route('/start-download', methods=['POST'])
def handle_start_download():
    """Handles the request to start the download process."""
    current_app.logger.debug("handle_start_download: Received request.")
    try:
        # Access global state from current_app.config
        lock = current_app.config['GLOBAL_LOCK']
        shared_state = current_app.config['SHARED_APP_STATE']
        with lock:
            if shared_state['is_automation_running']: # Use the key from shared_app_state
                current_app.logger.warning("handle_start_download: Download process already running, returning 409.")
                return jsonify({"status": "error", "message": "Download process already running."}), 409

        data_from_frontend = request.get_json()
        if not data_from_frontend:
            current_app.logger.error("handle_start_download: Missing request data.")
            return jsonify({"status": "error", "message": "Missing request data."}) , 400

        current_app.logger.debug(f"handle_start_download: Received data: {data_from_frontend}")

        # Extract core parameters from frontend
        email = data_from_frontend.get('email')
        password = data_from_frontend.get('password')
        reports = data_from_frontend.get('reports')
        regions = data_from_frontend.get('regions', []) # Regions might be optional

        if not all([email, password, reports]) or not isinstance(reports, list) or not reports:
            current_app.logger.error(f"handle_start_download: Missing required parameters. Email: {bool(email)}, Password: {bool(password)}, Reports: {bool(reports) and isinstance(reports, list) and bool(reports)}")
            return jsonify({"status": "error", "message": "Missing required parameters (email, password, reports) or 'reports' is empty/invalid."}), 400

        current_app.logger.debug("handle_start_download: Required parameters validated.")

        # Construct params for run_download_process, prioritizing backend config for sensitive/global settings
        params_for_download = {
            'email': email,
            'password': password,
            'reports': reports,
            'regions': regions,
            'otp_secret': current_app.config.get('OTP_SECRET', ''),
            'driver_path': current_app.config.get('DRIVER_PATH', ''),
            'download_base_path': current_app.config.get('DOWNLOAD_BASE_PATH', '')
        }
        current_app.logger.debug(f"handle_start_download: Params for download: {params_for_download}")

        # Run download in a separate thread within app context
        app = current_app._get_current_object()
        session_id = str(uuid.uuid4())
        stop_event = threading.Event() # Create a stop event for this session

        # Store the stop_event in the shared state
        with lock:
            shared_state['active_download_events'][session_id] = stop_event
        
        # Create and update web session in DB
        create_web_session(session_id) # Create initial entry
        update_web_session_status(session_id, 'started') # Set initial status
        current_app.logger.debug(f"handle_start_download: Web session {session_id} created and status set to 'started'.")

        def run_with_context(app, download_params, session_id, stop_event):
             with app.app_context():
                 current_app.logger.debug(f"run_with_context: Starting run_download_process for session {session_id}.")
                 run_download_process(download_params, session_id, stop_event)
                 current_app.logger.debug(f"run_with_context: Finished run_download_process for session {session_id}.")
        
        thread = threading.Thread(target=run_with_context, args=(app, params_for_download, session_id, stop_event), daemon=True)
        current_app.logger.debug(f"handle_start_download: Starting download thread for session {session_id}.")
        thread.start()
        current_app.logger.debug(f"handle_start_download: Download thread started for session {session_id}.")

        return jsonify({"status": "success", "message": "Download process started in background.", "session_id": session_id}) , 202
    except Exception as e:
        current_app.logger.error(f"Error starting download: {e}")
        traceback.print_exc()
        return jsonify({"status": "error", "message": "Failed to start download process"}), 500

@download_bp.route('/stream-status')
def stream_status_events():
    """Streams status messages using Server-Sent Events (SSE)."""
    def event_stream():
        last_sent_count = 0
        while True:
            try:
                # Access shared state via current_app within the loop
                # Access global state from current_app.config
                lock = current_app.config['GLOBAL_LOCK']
                status_messages_list = current_app.status_messages # This is correctly attached to app object
                shared_state = current_app.config['SHARED_APP_STATE']
                
                with lock:
                    current_count = len(status_messages_list)
                    new_messages = status_messages_list[last_sent_count:]
                    is_process_active = shared_state['is_automation_running']

                if new_messages:
                    for msg in new_messages:
                        yield f"data: {json.dumps({'message': msg})}\n\n"
                    last_sent_count = current_count
                
                # Check finish condition
                if not is_process_active and last_sent_count == current_count:
                    time.sleep(0.1) # Brief pause
                    with lock:
                         final_process_check = shared_state['is_automation_running']
                         final_message_count = len(status_messages_list)
                    if not final_process_check and last_sent_count == final_message_count:
                         yield f"data: FINISHED\n\n"
                         break # Exit loop
            except (AttributeError, KeyError, RuntimeError) as e:
                 print(f"SSE Error accessing current_app: {e}. Stream might stop.")
                 # Decide how to handle context loss - maybe break?
                 yield f"data: {json.dumps({'error': 'Server stream error'})}\n\n"
                 break # Stop streaming on error
            except Exception as e:
                 print(f"Unexpected SSE Error: {e}")
                 yield f"data: {json.dumps({'error': 'Unexpected server stream error'})}\n\n"
                 break # Stop streaming on error

            time.sleep(1)

    resp = Response(stream_with_context(event_stream()), mimetype='text/event-stream')
    resp.headers['Cache-Control'] = 'no-cache'
    resp.headers['X-Accel-Buffering'] = 'no'
    return resp

@download_bp.route('/get-logs', methods=['GET'])
def get_download_logs():
    """Retrieves download log entries, handling potential NaN values."""
    try:
        log_file = current_app.config['LOG_FILE_PATH'] 
        logs = []
        max_logs = int(request.args.get('limit', 100))
        if os.path.exists(log_file):
            try:
                # Read CSV, explicitly handle potential NaNs
                df = pd.read_csv(log_file, keep_default_na=True) # keep_default_na=True is default, but explicit
                # Replace NaN/NaT values with None (which becomes JSON null)
                df = df.replace({pd.NA: None, pd.NaT: None})
                # Replace numpy.nan just in case
                df = df.replace({np.nan: None})
                
                # Get the last N logs
                logs = df.tail(max_logs).to_dict('records')
                 # Optional: Sort logs if needed (client-side might be better for performance)
                # try:
                #     df['TimestampParsed'] = pd.to_datetime(df['Timestamp'], errors='coerce')
                #     df_sorted = df.sort_values(by='TimestampParsed', ascending=False, na_position='last')
                #     logs = df_sorted.drop(columns=['TimestampParsed']).tail(max_logs).to_dict('records')
                # except KeyError: # Handle if Timestamp column doesn't exist
                #     logs = df.tail(max_logs).to_dict('records')
            except ImportError:
                current_app.logger.warning("Pandas not installed. Falling back to basic CSV reading.")
                # Fallback might still have issues if CSV contains literal 'NaN'
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        all_logs = list(reader)
                        # Manually replace potential string 'NaN' or empty strings if needed
                        cleaned_logs = []
                        for row in all_logs[-max_logs:]:
                            cleaned_row = {k: (None if v in ['NaN', ''] else v) for k, v in row.items()}
                            cleaned_logs.append(cleaned_row)
                        logs = cleaned_logs
                except Exception as e:
                     current_app.logger.error(f"Error reading log file {log_file}: {e}")
                     return jsonify({"error": f"Could not read log file: {e}"}), 500
            except Exception as e:
                 current_app.logger.error(f"Error processing log file {log_file}: {e}")
                 traceback.print_exc() # Log full traceback for pandas errors
                 return jsonify({"error": f"Could not process log file: {e}"}), 500
        else:
            current_app.logger.info(f"Log file not found at {log_file}")
        # Return the list directly, which jsonify handles correctly
        return jsonify(logs) 
    except Exception as e:
        current_app.logger.error(f"Error in get_download_logs: {e}")
        traceback.print_exc()
        return jsonify({"error": "Failed to retrieve logs"}), 500

@download_bp.route('/get-configs', methods=['GET'])
def get_configs():
    config_path = current_app.config.get('CONFIG_FILE_PATH', '')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            configs = json.load(f)
        return jsonify(list(configs.keys()))
    return jsonify([])

@download_bp.route('/save-config', methods=['POST'])
def save_config():
    """Saves a new configuration or updates an existing one."""
    data = request.get_json()
    if not data or 'name' not in data or 'config' not in data:
        return jsonify({'status': 'error', 'message': 'Invalid data. Required: {"name": "config_name", "config": {...}}'}), 400
    config_name = data['name']
    config_data = data['config']
    if not isinstance(config_data, dict) or not all(k in config_data for k in ('email', 'password', 'reports')):
         return jsonify({'status': 'error', 'message': 'Config data must include email, password, and reports.'}), 400
    try:
        configs = load_configs()
        configs[config_name] = config_data
        save_configs(configs) # Uses current_app implicitly
        return jsonify({'status': 'success', 'message': f'Configuration "{config_name}" saved.'})
    except Exception as e:
        current_app.logger.error(f"Error saving config '{config_name}': {e}")
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'Failed to save config: {e}'}), 500

@download_bp.route('/load-config/<config_name>', methods=['GET'])
def load_config(config_name):
    """Loads a specific saved configuration."""
    current_app.logger.debug(f"Attempting to load config: '{config_name}'")
    try:
        configs = load_configs()
        current_app.logger.debug(f"Available configs: {list(configs.keys())}")
        config_data = configs.get(config_name)
        if config_data:
            current_app.logger.debug(f"Config '{config_name}' found.")
            return jsonify(config_data)
        else:
            current_app.logger.warning(f"Config '{config_name}' not found in loaded configs.")
            return jsonify({'status': 'error', 'message': 'Configuration not found.'}), 404
    except Exception as e:
        current_app.logger.error(f"Error loading config '{config_name}': {e}")
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'Failed to load config: {e}'}), 500

@download_bp.route('/delete-config/<config_name>', methods=['DELETE'])
def delete_config(config_name):
    """Deletes a saved configuration."""
    try:
        configs = load_configs()
        if config_name in configs:
            del configs[config_name]
            save_configs(configs)
            return jsonify({'status': 'success', 'message': f'Configuration "{config_name}" deleted.'})
        else:
            return jsonify({'status': 'error', 'message': 'Configuration not found.'}), 404
    except Exception as e:
        current_app.logger.error(f"Error deleting config '{config_name}': {e}")
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'Failed to delete config: {e}'}), 500

@download_bp.route('/schedule-job', methods=['POST'])
def schedule_job():
    """Schedules a download job."""
    data = request.get_json()
    if not data or 'config_name' not in data or 'run_datetime' not in data:
        return jsonify({'status': 'error', 'message': 'Missing config_name or run_datetime.'}), 400
    config_name = data['config_name']
    run_datetime_str = data['run_datetime']
    try:
        # Access global state from current_app.config
        lock = current_app.config['GLOBAL_LOCK']
        scheduler = current_app.scheduler # Access scheduler via context (this is attached directly to app)
        
        if not run_datetime_str: return jsonify({'status': 'error', 'message': 'Run date/time required.'}), 400
        configs = load_configs()
        if config_name not in configs:
             return jsonify({'status': 'error', 'message': f'Configuration "{config_name}" not found.'}), 404

        session_id = str(uuid.uuid4())
        job_id = f"sched_{config_name.replace(' ','_').lower()}_{int(time.time())}"
        try:
            run_datetime_naive = datetime.fromisoformat(run_datetime_str)
            if run_datetime_naive <= datetime.now() + timedelta(seconds=60):
                return jsonify({'status': 'error', 'message': 'Scheduled time must be > 1 min in the future.'}), 400
            trigger = DateTrigger(run_date=run_datetime_naive)
        except ValueError:
             return jsonify({'status': 'error', 'message': 'Invalid date/time format (YYYY-MM-DDTHH:MM).'}), 400

        with lock: 
            scheduler.add_job(
                func=trigger_scheduled_download, trigger=trigger, args=[config_name, current_app._get_current_object(), session_id],
                id=job_id, name=f"Download: {config_name}", replace_existing=False,
                misfire_grace_time=600 
            )
            insert_job_to_db(job_id, config_name, run_datetime_naive.isoformat(), session_id)
            # Lấy danh sách jobs ngay sau khi thêm
            jobs = scheduler.get_jobs()
            jobs_info = []
            for job in jobs:
                next_run_iso = None
                if job.next_run_time:
                    try:
                        next_run_iso = job.next_run_time.isoformat()
                    except Exception as fmt_e:
                        current_app.logger.error(f"Error formatting next_run_time for job {job.id}: {fmt_e}")
                        next_run_iso = str(job.next_run_time)
                jobs_info.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': next_run_iso,
                    'trigger': str(job.trigger),
                    'config_name': job.args[0] if job.args else None
                })
        current_app.logger.info(f"Successfully added job {job_id} to scheduler.")
        return jsonify({'status': 'success', 'message': f'Job scheduled for config "{config_name}".', 'job_id': job_id, 'schedules': jobs_info, 'db_jobs': get_all_jobs_from_db()})

    except Exception as e:
        current_app.logger.error(f"Error scheduling job: {e}")
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'Failed to schedule job: {e}'}), 500

@download_bp.route('/get-schedules', methods=['GET'])
def get_schedules():
    """Gets the list of currently scheduled jobs."""
    try:
        # Access global state from current_app.config
        lock = current_app.config['GLOBAL_LOCK']
        scheduler = current_app.scheduler
        jobs_info = []
        with lock: 
            jobs = scheduler.get_jobs()
            for job in jobs:
                next_run_iso = None
                if job.next_run_time:
                    try: 
                        next_run_iso = job.next_run_time.isoformat()
                    except Exception as fmt_e:
                        current_app.logger.error(f"Error formatting next_run_time for job {job.id}: {fmt_e}")
                        next_run_iso = str(job.next_run_time)
                jobs_info.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': next_run_iso,
                    'trigger': str(job.trigger),
                    'config_name': job.args[0] if job.args else None
                })
        # Lấy thêm từ db
        db_jobs = get_all_jobs_from_db()
        return jsonify({'status': 'success', 'schedules': jobs_info, 'db_jobs': db_jobs})
    except Exception as e:
        current_app.logger.error(f"Error getting schedules: {e}")
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'Failed to get schedules: {e}'})

@download_bp.route('/cancel-schedule/<job_id>', methods=['DELETE'])
def cancel_schedule(job_id):
    """Cancels (removes) a scheduled job."""
    try:
        lock = current_app.lock
        scheduler = current_app.scheduler
        current_app.logger.info(f"Received request to cancel job: {job_id}")
        with lock: 
            try:
                scheduler.remove_job(job_id)
                update_job_status(job_id, 'cancelled')
                current_app.logger.info(f"Removed job {job_id} from scheduler.")
                return jsonify({'status': 'success', 'message': f'Job "{job_id}" cancelled.'})
            except JobLookupError:
                # Nếu không tìm thấy trong APScheduler, xóa hẳn khỏi db
                delete_job_from_db(job_id)
                current_app.logger.warning(f"Job {job_id} not found for cancellation, deleted from db.")
                return jsonify({'status': 'success', 'message': f'Job "{job_id}" not found in scheduler, deleted from database.'})
    except Exception as e:
        current_app.logger.error(f"Error cancelling job {job_id}: {e}")
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'Failed to cancel job "{job_id}": {e}'})

@download_bp.route('/get-active-sessions', methods=['GET'])
def get_active_sessions():
    """Retrieves a list of currently active download sessions."""
    try:
        print(f"get_active_sessions: Connecting to WEB_SESSION_DB_PATH: {WEB_SESSION_DB_PATH}")
        print(f"get_active_sessions: Attempting to attach scheduler DB from DB_PATH: {DB_PATH}")
        with sqlite3.connect(WEB_SESSION_DB_PATH) as conn:
            # Attach the scheduler database to the current connection
            conn.execute(f"ATTACH DATABASE '{DB_PATH}' AS scheduler_db;")
            
            # Fetch sessions that are 'running' or 'started' and not yet 'finished' or 'cancelled'
            # Also join with jobs table to get config_name if available
            cur = conn.execute("""
                SELECT ws.session_id, ws.user_id, ws.job_id, ws.last_page, ws.status, ws.created_at, ws.updated_at, scheduler_db.jobs.config_name
                FROM web_sessions ws
                LEFT JOIN scheduler_db.jobs ON ws.job_id = scheduler_db.jobs.id
                WHERE ws.status IN ('running', 'started', 'in progress')
                ORDER BY ws.created_at DESC
            """)
            sessions = [dict(zip([column[0] for column in cur.description], row)) for row in cur.fetchall()]
        
        # Filter out sessions that might have finished but not yet updated in web_sessions table
        # by checking against active_download_events
        active_events = current_app.config['SHARED_APP_STATE']['active_download_events']
        filtered_sessions = [
            s for s in sessions if s['session_id'] in active_events and not active_events[s['session_id']].is_set()
        ]

        return jsonify({'status': 'success', 'active_sessions': filtered_sessions})
    except Exception as e:
        current_app.logger.error(f"Error getting active sessions: {e}")
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'Failed to retrieve active sessions: {e}'}), 500

@download_bp.route('/cancel-active-session/<session_id>', methods=['POST'])
def cancel_active_session(session_id):
    """Cancels an active download session."""
    lock = current_app.config['GLOBAL_LOCK']
    shared_state = current_app.config['SHARED_APP_STATE']
    current_app.logger.info(f"Received request to cancel active session: {session_id}")

    with lock:
        stop_event = shared_state['active_download_events'].get(session_id)
        if stop_event:
            stop_event.set() # Signal the thread to stop
            current_app.logger.info(f"Signaled stop for session {session_id}.")
            
            # Update status in web_sessions DB
            update_web_session_status(session_id, 'cancelled')
            current_app.logger.info(f"Updated web_session {session_id} status to 'cancelled'.")

            # Update status in jobs DB if associated job exists
            job_id = get_job_id_by_session(session_id)
            if job_id:
                update_job_status(job_id, 'cancelled')
                current_app.logger.info(f"Updated job {job_id} status to 'cancelled'.")
            
            # Remove from active_download_events
            del shared_state['active_download_events'][session_id]
            current_app.logger.info(f"Removed session {session_id} from active_download_events.")

            # Optionally, reset is_automation_running if this was the only active session
            if not shared_state['active_download_events']:
                shared_state['is_automation_running'] = False
                current_app.logger.info("No more active sessions, resetting is_automation_running to False.")

            return jsonify({'status': 'success', 'message': f'Session "{session_id}" cancellation initiated.'})
        else:
            current_app.logger.warning(f"Session {session_id} not found in active_download_events or already finished.")
            # Even if not in active_download_events, try to update DB status in case it was missed
            update_web_session_status(session_id, 'cancelled')
            job_id = get_job_id_by_session(session_id)
            if job_id:
                update_job_status(job_id, 'cancelled')
            return jsonify({'status': 'error', 'message': f'Session "{session_id}" not found or already inactive.'}), 404

@download_bp.route('/get-advanced-settings', methods=['GET'])
def get_advanced_settings():
    try:
        otp_secret = current_app.config.get('OTP_SECRET', 'DefaultOTP') # Thêm giá trị default để dễ nhận biết
        driver_path = current_app.config.get('DRIVER_PATH', 'DefaultDriverPath')
        download_base_path = current_app.config.get('DOWNLOAD_BASE_PATH', 'DefaultDownloadPath')

        # DEBUGGING: In ra những gì current_app.config chứa
        print(f"[DEBUG] In /get-advanced-settings:")
        print(f"[DEBUG]   OTP_SECRET from current_app.config: {otp_secret}")
        print(f"[DEBUG]   DRIVER_PATH from current_app.config: {driver_path}")
        print(f"[DEBUG]   DOWNLOAD_BASE_PATH from current_app.config: {download_base_path}")
        # print(f"[DEBUG]   All current_app.config keys: {list(current_app.config.keys())}") # Nếu cần xem tất cả

        return jsonify({
            'status': 'success',
            'otp_secret': otp_secret,
            'driver_path': driver_path,
            'download_base_path': download_base_path
        })
    except Exception as e:
        current_app.logger.error(f"Error in /get-advanced-settings: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': str(e)}), 500

@download_bp.route('/save-advanced-settings', methods=['POST'])
def save_advanced_settings():
    try:
        data = request.get_json()
        config_to_save = {
            'OTP_SECRET': data.get('otp_secret'),
            'DRIVER_PATH': data.get('driver_path'),
            'DOWNLOAD_BASE_PATH': data.get('download_base_path')
        }

        success, message = save_config_values(config_to_save) # Gọi hàm lưu từ config_manager

        if success:
            # Cập nhật config của app đang chạy
            current_app.config['OTP_SECRET'] = config_to_save['OTP_SECRET']
            current_app.config['DRIVER_PATH'] = config_to_save['DRIVER_PATH']
            current_app.config['DOWNLOAD_BASE_PATH'] = config_to_save['DOWNLOAD_BASE_PATH']
            return jsonify({'status': 'success', 'message': message})
        else:
            return jsonify({'status': 'error', 'message': message}), 500
    except Exception as e:
        current_app.logger.error(f"Error saving advanced settings: {e}")
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'Failed to save advanced settings: {e}'})
