# blueprints/email/logic_email.py
import pandas as pd
from string import Template
from datetime import datetime
import os
import logging
from .models import EmailTemplate
import jinja2

logger = logging.getLogger(__name__)

def parse_excel_data(file_path):
    """Parse Excel file and return list of dictionaries"""
    try:
        df = pd.read_excel(file_path)
        # Convert all column names to lowercase and strip whitespace
        df.columns = [str(col).strip().lower() for col in df.columns]
        return df.to_dict('records')
    except Exception as e:
        logger.error(f"Error parsing Excel file: {str(e)}")
        raise ValueError(f"Error parsing Excel file: {str(e)}")

import jinja2
# ...existing code...

def render_email_template(template_content, variables, row_data):
    """Render email template with dynamic variables from Excel row using Jinja2"""
    if not isinstance(row_data, dict):
        row_data = row_data._asdict() if hasattr(row_data, '_asdict') else dict(row_data)
    # Add common variables
    row_data['current_date'] = datetime.now().strftime('%d/%m/%Y')
    try:
        # Use Jinja2 to render the template from string
        env = jinja2.Environment(autoescape=True)
        template = env.from_string(template_content)
        return template.render(**row_data)
    except Exception as e:
        logger.error(f"Error rendering template with Jinja2: {str(e)}")
        raise

def send_bulk_emails_backend(excel_path, template_id, attachments_folder=None, start_index=None, end_index=None):
    """Send bulk emails using template and Excel data"""
    # Get template from database
    template = EmailTemplate.query.get(template_id)
    if not template:
        return {
            'success': False,
            'message': f'Template with ID {template_id} not found'
        }
    
    try:
        # Parse Excel data
        recipients = parse_excel_data(excel_path)
        
        # Process each recipient
        results = {
            'success_count': 0,
            'failure_count': 0,
            'details': []
        }
        
        # Apply row range if specified
        if start_index is not None and end_index is not None:
            recipients = recipients[start_index:end_index+1]
        
        for idx, recipient in enumerate(recipients, 1):
            try:
                # Render email content
                email_html = render_email_template(
                    template.html_content,
                    template.variables or [],
                    recipient
                )
                
                # TODO: Send email using your email sending logic
                # send_email(
                #     to=recipient.get('email'),
                #     subject=template.subject,
                #     html=email_html
                # )
                
                results['success_count'] += 1
                results['details'].append({
                    'row': idx,
                    'status': 'success',
                    'message': f'Email sent to {recipient.get("email", "unknown")}'
                })
                
            except Exception as e:
                logger.error(f"Error processing row {idx}: {str(e)}")
                results['failure_count'] += 1
                results['details'].append({
                    'row': idx,
                    'status': 'error',
                    'message': str(e)
                })
        
        return {
            'success': True,
            'message': f'Processed {len(recipients)} rows. Success: {results["success_count"]}, Failed: {results["failure_count"]}',
            **results
        }
        
    except Exception as e:
        logger.error(f"Error in send_bulk_emails_backend: {str(e)}")
        return {
            'success': False,
            'message': f'Error processing request: {str(e)}'
        }