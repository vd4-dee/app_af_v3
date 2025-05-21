# blueprints/email/__init__.py
from flask import Blueprint

# Create blueprint without importing routes yet to avoid circular imports
email_bp = Blueprint('email', __name__)

def init_email(app):
    # Import routes here to avoid circular imports
    from . import routes_email
    from . import api
    from . import api_templates
    
    # Register blueprints
    app.register_blueprint(email_bp)
    app.register_blueprint(api_templates.templates_bp, url_prefix='/api/email')
    
    return app