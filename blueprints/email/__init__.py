# blueprints/email/__init__.py
from flask import Blueprint

# Create blueprint without importing routes yet to avoid circular imports
email_bp = Blueprint('email', __name__)

def init_email(app):
    # Import routes here to avoid circular imports
    from . import routes_email
    from . import api
    
    # Register the main email blueprint
    app.register_blueprint(email_bp)
    
    # Note: api_templates.templates_api_bp is registered in app.py
    # to properly handle URL prefixes and avoid duplicate registration
    
    return app