import os 
import json
from datetime import datetime
import threading # Keep for type hinting if needed, but lock comes from current_app
from flask import current_app # Import current_app
import sys
import csv # Import csv for writing logs

if sys.stdout.encoding.lower() != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
# --- Remove direct import from app ---
# from app import lock, status_messages, CONFIG_FILE_PATH

def load_configs():
    """Loads configurations safely using app context."""
    config_path = current_app.config.get('CONFIG_FILE_PATH', '')
    if not os.path.exists(config_path): return {}
    try:
        # Access lock from the app context
        with current_app.lock: 
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content: return {}
                return json.loads(content)
    except (json.JSONDecodeError, IOError, AttributeError, KeyError) as e:
        # Added AttributeError/KeyError for cases where current_app isn't fully loaded or configured
        print(f"Error loading config file via current_app ({config_path}): {e}")
        return {}

def save_configs(configs):
    """Saves configurations safely using app context."""
    config_path = current_app.config.get('CONFIG_FILE_PATH', '')
    try:
        # Access lock from the app context
        with current_app.lock: 
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(configs, f, indent=4, ensure_ascii=False)
    except (IOError, AttributeError, KeyError) as e:
        print(f"Error saving config file via current_app ({config_path}): {e}")

def stream_status_update(message, log_entry=None):
    """
    Adds a message to the status list via app context and optionally writes to a CSV log file.
    
    Args:
        message (str): The message to display in the UI stream.
        log_entry (dict, optional): A dictionary containing structured log data
                                    for CSV. Expected keys: 'SessionID', 'Timestamp',
                                    'File Name', 'Start Date', 'End Date', 'Status',
                                    'Error Message'.
    """
    try:
        lock = current_app.lock
        status_list = current_app.status_messages 
        log_file_path = current_app.config.get('LOG_FILE_PATH')
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"{timestamp}: {message}"
        print(full_message) # Log to console

        with lock:
            status_list.append(full_message)
            MAX_LOG_MESSAGES = 500 # Consider moving to app.config
            if len(status_list) > MAX_LOG_MESSAGES:
                current_app.status_messages = status_list[-MAX_LOG_MESSAGES:] 

            # Write to CSV log file if log_entry is provided
            if log_entry and log_file_path:
                # Ensure all expected headers are present, even if values are None
                headers = ['SessionID', 'Timestamp', 'File Name', 'Start Date', 'End Date', 'Status', 'Error Message']
                
                # Prepare the row, filling missing keys with None
                row_to_write = {header: log_entry.get(header) for header in headers}
                
                file_exists = os.path.exists(log_file_path)
                try:
                    with open(log_file_path, 'a', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=headers)
                        if not file_exists:
                            writer.writeheader()
                        writer.writerow(row_to_write)
                except IOError as e:
                    current_app.logger.error(f"Error writing to log file {log_file_path}: {e}")
                except Exception as e:
                    current_app.logger.error(f"Unexpected error writing log entry to CSV: {e}")
                    current_app.logger.error(f"Log entry: {log_entry}")

    except (AttributeError, KeyError) as e:
         print(f"Error updating status via current_app: {e}. App context might not be available.")
