import os
import re
from pathlib import Path

def get_config_path():
    """Get the absolute path to config.py"""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config.py'))

def load_config_values():
    """Load the current configuration values from config.py"""
    config_path = get_config_path()
    config_values = {
        'OTP_SECRET': '',
        'DRIVER_PATH': '',
        'DOWNLOAD_BASE_PATH': ''
    }
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Use regex to find the values
            for key in config_values.keys():
                # Look for patterns like: KEY = 'value' or KEY = "value" or KEY = value
                match = re.search(fr"^{key}\s*=\s*['\"]([^'\"]*)['\"]|{key}\s*=\s*([^\n#]+)", content, re.MULTILINE)
                if match:
                    # Get the first non-None group (either quoted or unquoted value)
                    value = next((g for g in match.groups() if g is not None), '')
                    # Clean up the value (remove surrounding whitespace and quotes if any)
                    value = value.strip().strip('\'"')
                    config_values[key] = value
    except Exception as e:
        print(f"Error loading config values: {e}")
    
    return config_values

def save_config_values(config_values):
    """Save new configuration values to config.py using a more reliable method"""
    config_path = get_config_path()
    try:
        # Read the current content line by line
        with open(config_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Create a set of keys we're updating for faster lookup
        update_keys = set(config_values.keys())
        updated = False
        
        # Process each line to find and update configuration values
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            # Split the line into key and value parts
            if '=' in line:
                key = line.split('=')[0].strip()
                if key in update_keys:
                    # Found a line to update
                    value = config_values[key]
                    if value is None:
                        value = ""
                    
                    # Format the new line with proper quoting
                    value_str = str(value).replace("'", "\\'")
                    if '\\' in value_str or '/' in value_str:
                        # Use raw string for paths
                        new_line = f"{key} = r'{value_str}'\n"
                    else:
                        new_line = f"{key} = '{value_str}'\n"
                    
                    lines[i] = new_line
                    update_keys.remove(key)
                    updated = True
        
        # Add any new keys that weren't found in the file
        if update_keys:
            # Find the first line with # --- to insert new values before it
            for i, line in enumerate(lines):
                if line.strip().startswith('# ---'):
                    # Insert new values before this line
                    new_lines = []
                    for key in update_keys:
                        value = str(config_values[key])
                        if '\\' in value or '/' in value:
                            new_lines.append(f"{key} = r'{value}'\n")
                        else:
                            new_lines.append(f"{key} = '{value}'\n")
                    lines[i:i] = new_lines + ['\n']  # Add newline after new values
                    updated = True
                    break
        
        # Only write if there were changes
        if updated:
            with open(config_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
        
        return True, "Configuration saved successfully"
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error details in save_config_values:\n{error_details}")
        return False, f"Error saving configuration: {str(e)}"
